from deskmate_ai.services import llm_service


def test_ask_local_model_returns_none_when_ollama_is_unavailable(monkeypatch) -> None:
    def raise_url_error(*args, **kwargs):
        raise OSError("not running")

    monkeypatch.setattr(llm_service.request, "urlopen", raise_url_error)

    assert llm_service.ask_local_model("안녕") is None
