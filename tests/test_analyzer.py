import pytest

from seo_audit import analyzer


class _FailingProvider:
    def __init__(self, *args, **kwargs):
        pass

    def analyze(self, prompt: str):
        raise analyzer.ProviderError("openai failed")


class _SuccessProvider:
    def __init__(self, *args, **kwargs):
        pass

    def analyze(self, prompt: str):
        return analyzer.AIResult(provider_used="DeepSeekProvider", content="ok", raw={})


def test_provider_fallback(monkeypatch):
    monkeypatch.setattr(analyzer, "OpenAIProvider", _FailingProvider)
    monkeypatch.setattr(analyzer, "DeepSeekProvider", _SuccessProvider)

    result = analyzer.analyze_with_fallback(
        "test prompt",
        openai_key="x",
        deepseek_key="y",
        openai_model="m1",
        deepseek_model="m2",
        retries=0,
    )

    assert result.provider_used == "DeepSeekProvider"


def test_provider_no_success():
    with pytest.raises(analyzer.ProviderError):
        analyzer.analyze_with_fallback(
            "test",
            openai_key=None,
            deepseek_key=None,
            openai_model="a",
            deepseek_model="b",
        )
