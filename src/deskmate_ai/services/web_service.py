from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus


KNOWN_SITES = {
    "구글": "https://www.google.com",
    "google": "https://www.google.com",
    "네이버": "https://www.naver.com",
    "naver": "https://www.naver.com",
    "유튜브": "https://www.youtube.com",
    "youtube": "https://www.youtube.com",
    "깃허브": "https://github.com",
    "github": "https://github.com",
}


def open_site(prompt: str) -> str:
    lower_prompt = prompt.lower()
    for name, url in KNOWN_SITES.items():
        if name in lower_prompt:
            webbrowser.open(url)
            return url

    query = (
        prompt.replace("열어줘", "")
        .replace("열어", "")
        .replace("켜줘", "")
        .replace("접속", "")
        .strip()
    )
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    webbrowser.open(url)
    return url
