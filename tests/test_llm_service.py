from deskmate_ai.services import llm_service


def test_ask_local_model_returns_none_when_ollama_is_unavailable(monkeypatch) -> None:
    def raise_url_error(*args, **kwargs):
        raise OSError("not running")

    monkeypatch.setattr(llm_service.request, "urlopen", raise_url_error)

    assert llm_service.ask_local_model("안녕") is None


def test_ask_local_model_sends_speed_options(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"message": {"content": "ok"}}'

    def fake_urlopen(req, timeout):
        captured["payload"] = req.data
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(llm_service.request, "urlopen", fake_urlopen)

    assert llm_service.ask_local_model("hello") == "ok"

    payload = llm_service.json.loads(captured["payload"].decode("utf-8"))
    assert captured["timeout"] == 15
    assert payload["keep_alive"] == "10m"
    assert payload["options"]["num_predict"] == 512
