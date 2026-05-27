# DeskMate AI

DeskMate AI는 개인 노트북에서 실행하는 데스크톱 AI 비서 프로젝트입니다. 사용자는 텍스트 또는 음성으로 명령하고, 앱은 문서 요약, 사이트 실행, 화면 출력, TTS 음성 출력을 지원하는 것을 목표로 합니다.

## 프로젝트 목표

이 프로젝트는 "학교에서 실제로 쓰고 싶은 개인 AI 비서"를 만드는 것을 목표로 합니다. 처음에는 작게 완성 가능한 MVP를 만들고, 이후 음성 대화, PPT 요약, 대화 기록 저장 같은 기능을 단계적으로 확장합니다.

## MVP 기능

- 텍스트 프롬프트 입력
- 화면 하단 대화창 출력
- TTS 음성 출력 선택
- PDF 문서 요약
- 원하는 사이트 열기

## 추후 확장 기능

- 음성 인식 입력
- PPT 문서 요약
- 자주 쓰는 사이트 등록
- 대화 기록 저장
- 파일 내용 기반 질의응답
- 게임 대화창 스타일 UI 개선

## 기술 스택

- Python 3.11
- CustomTkinter: 데스크톱 UI
- pypdf: PDF 텍스트 추출
- pyttsx3: 로컬 TTS
- pytest: 테스트
- Docker: 실행 환경 패키징
- GitHub Actions: CI

## 프로젝트 구조

```text
.
├── .github/workflows/ci.yml
├── Dockerfile
├── README.md
├── requirements.txt
├── src/
│   └── deskmate_ai/
│       ├── __init__.py
│       ├── app.py
│       ├── assistant.py
│       ├── document.py
│       ├── speech.py
│       └── web_actions.py
└── tests/
    └── test_assistant.py
```

## 동작 흐름

```text
사용자 입력
→ 명령 의도 분석
→ 기능 실행
   - 문서 요약
   - 사이트 열기
   - 일반 답변
→ 화면 출력
→ TTS 옵션이 켜져 있으면 음성 출력
```

## 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
deskmate-ai
```

Windows PowerShell에서는 다음처럼 가상환경을 활성화합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
deskmate-ai
```

## 테스트

```bash
pytest
```

## Docker 실행

Docker 환경에서는 GUI 표시가 제한될 수 있으므로, 기본 이미지는 앱 의존성 설치와 테스트 실행 검증을 우선합니다.

```bash
docker build -t deskmate-ai .
docker run --rm deskmate-ai
```

## CI

GitHub Actions는 push와 pull request마다 다음을 확인합니다.

- Python 의존성 설치
- 테스트 실행
- Docker 이미지 빌드

## 포트폴리오 설명 문장

> DeskMate AI는 개인 학습과 작업을 보조하기 위해 개발한 데스크톱 AI 비서입니다. 사용자는 텍스트 또는 음성으로 명령할 수 있으며, 앱은 문서 요약, 사이트 실행, TTS 출력 기능을 통해 반복적인 학습 및 작업 과정을 줄이는 것을 목표로 합니다.
