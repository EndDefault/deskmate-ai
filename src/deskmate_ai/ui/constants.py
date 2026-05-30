ACTION_LABELS = {
    "show_text": "내용 보여주기",
    "open_url": "사이트 열기",
    "translate": "번역",
}
ACTION_VALUES = {label: value for value, label in ACTION_LABELS.items()}

SOURCE_LANGUAGES = {
    "영어": "en",
    "일본어": "ja",
    "한국어": "ko",
}
TARGET_LANGUAGES = {
    "한국어": "ko",
    "영어": "en",
    "일본어": "ja",
}
LANGUAGE_NAMES = {value: key for key, value in {**SOURCE_LANGUAGES, **TARGET_LANGUAGES}.items()}
