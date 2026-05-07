from app.config import get_settings


def _reload_settings():
    get_settings.cache_clear()
    return get_settings()


def test_openai_key_reads_from_prefixed_env(monkeypatch):
    monkeypatch.setenv("ASKFUSION_OPENAI_API_KEY", "prefixed-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = _reload_settings()

    assert settings.openai_api_key == "prefixed-key"


def test_openai_key_reads_from_standard_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "standard-key")
    monkeypatch.delenv("ASKFUSION_OPENAI_API_KEY", raising=False)

    settings = _reload_settings()

    assert settings.openai_api_key == "standard-key"


def test_prefixed_openai_key_takes_precedence(monkeypatch):
    monkeypatch.setenv("ASKFUSION_OPENAI_API_KEY", "prefixed-key")
    monkeypatch.setenv("OPENAI_API_KEY", "standard-key")

    settings = _reload_settings()

    assert settings.openai_api_key == "prefixed-key"
