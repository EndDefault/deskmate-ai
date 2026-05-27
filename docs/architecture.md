# 프로젝트 구조

DeskMate AI는 기능을 한 파일에 몰아넣지 않고, 역할별 폴더로 나눕니다.

```text
src/deskmate_ai/
├── app.py
├── config.py
├── core/
│   └── assistant.py
├── services/
│   ├── document_service.py
│   ├── llm_service.py
│   ├── speech_service.py
│   └── web_service.py
└── ui/
    └── desktop_app.py
```

## 폴더 역할

| 위치 | 역할 |
| --- | --- |
| `app.py` | 실행 진입점입니다. 콘솔 명령 `deskmate-ai`가 여기로 들어옵니다. |
| `config.py` | 앱 이름, Ollama 주소, 모델명 같은 설정을 관리합니다. |
| `core/` | 사용자의 명령을 해석하고 어떤 기능을 실행할지 결정합니다. |
| `services/` | 문서, 웹, 음성, LLM처럼 외부 기능과 연결되는 코드를 둡니다. |
| `ui/` | CustomTkinter 화면과 사용자 입력 처리를 둡니다. |
| `tests/` | 기능별 테스트를 둡니다. |

## 현재 동작 흐름

```text
사용자 입력
-> ui.desktop_app
-> core.assistant.handle_prompt
-> services 중 필요한 기능 실행
-> AssistantResult 반환
-> 화면 출력
-> TTS가 켜져 있으면 음성 출력
```

## 설계 의도

UI와 실제 기능을 분리하면 나중에 CLI, 웹 UI, 모바일 UI를 붙여도 `core`와 `services`를 다시 쓸 수 있습니다.

또한 LLM 모델을 바꾸거나 문서 요약 방식을 개선해도 화면 코드를 크게 건드리지 않아도 됩니다.
