from deskmate_ai.services import web_service


def test_open_site_uses_known_site(monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(web_service.webbrowser, "open", opened.append)

    url = web_service.open_site("github 열어줘")

    assert url == "https://github.com"
    assert opened == ["https://github.com"]


def test_open_site_falls_back_to_google_search(monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(web_service.webbrowser, "open", opened.append)

    url = web_service.open_site("파이썬 공부")

    assert url == "https://www.google.com/search?q=%ED%8C%8C%EC%9D%B4%EC%8D%AC+%EA%B3%B5%EB%B6%80"
    assert opened == [url]
