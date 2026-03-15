from __future__ import annotations

import json
import time
from dataclasses import dataclass

import requests


class ProviderError(RuntimeError):
    pass


@dataclass
class AIResult:
    provider_used: str
    content: str
    raw: dict


class BaseProvider:
    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 20.0):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def analyze(self, prompt: str) -> AIResult:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=self.timeout)
        if resp.status_code >= 400:
            raise ProviderError(f"{self.__class__.__name__} HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return AIResult(provider_used=self.__class__.__name__, content=content, raw=data)


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str, model: str, timeout: float = 20.0):
        super().__init__(api_key=api_key, model=model, base_url="https://api.openai.com/v1", timeout=timeout)


class DeepSeekProvider(BaseProvider):
    def __init__(self, api_key: str, model: str, timeout: float = 20.0):
        super().__init__(api_key=api_key, model=model, base_url="https://api.deepseek.com/v1", timeout=timeout)


def analyze_with_fallback(
    prompt: str,
    openai_key: str | None,
    deepseek_key: str | None,
    openai_model: str,
    deepseek_model: str,
    timeout: float = 20.0,
    retries: int = 2,
) -> AIResult:
    errors: list[str] = []

    def _attempt(provider: BaseProvider) -> AIResult:
        for attempt in range(retries + 1):
            try:
                return provider.analyze(prompt)
            except (requests.Timeout, requests.ConnectionError, ProviderError) as exc:
                errors.append(f"{provider.__class__.__name__} attempt {attempt + 1}: {exc}")
                if attempt < retries:
                    time.sleep(0.8 * (attempt + 1))
        raise ProviderError(f"{provider.__class__.__name__} exhausted retries")

    if openai_key:
        try:
            return _attempt(OpenAIProvider(openai_key, openai_model, timeout=timeout))
        except ProviderError as exc:
            errors.append(str(exc))

    if deepseek_key:
        try:
            return _attempt(DeepSeekProvider(deepseek_key, deepseek_model, timeout=timeout))
        except ProviderError as exc:
            errors.append(str(exc))

    raise ProviderError("No AI provider succeeded: " + " | ".join(errors))
