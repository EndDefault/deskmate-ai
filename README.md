# DeskMate AI

DeskMate AI는 개인 노트북에서 실행되는 데스크톱 AI 비서 프로젝트입니다.

텍스트 명령을 입력하면 사이트 열기, 문서 요약, 로컬 AI 답변, TTS 음성 출력 같은 작업을 수행하는 것을 목표로 합니다.

## 프로젝트 목표

학교와 개인 작업에서 실제로 쓸 수 있는 작은 AI 비서를 만드는 것이 목표입니다.

처음에는 완성 가능한 MVP를 만들고, 이후 음성 인식, PPT 요약, 대화 기록 저장, 파일 기반 질의응답 같은 기능을 단계적으로 확장합니다.

## 현재 MVP 기능

- 텍스트 명령 입력
- 화면 채팅 로그 출력
- TTS 음성 출력 선택
- PDF, TXT, MD 문서 선택 및 요약 미리보기
- 자주 쓰는 사이트 열기
- Ollama 기반 로컬 AI 모델 답변

## 추천 AI 모델

기본 추천 모델은 `qwen3:4b`입니다.

```powershell
ollama pull qwen3:4b
ollama run qwen3:4b
```

자세한 모델 비교는 [docs/model-selection.md](docs/model-selection.md)를 참고하세요.

## 기술 스택

- Python 3.11+
- CustomTkinter: 데스크톱 UI
- Ollama: 로컬 LLM 실행
- pypdf: PDF 텍스트 추출
- pyttsx3: 로컬 TTS
- pytest: 테스트
- Docker: 실행 환경 검증
- GitHub Actions: CI

## 프로젝트 구조

```text
.
├── .github/workflows/ci.yml
├── Dockerfile
├── README.md
├── docs/
│   ├── architecture.md
│   ├── model-selection.md
│   └── roadmap.md
├── requirements.txt
├── src/
│   └── deskmate_ai/
│       ├── app.py
│       ├── config.py
│       ├── core/
│       │   └── assistant.py
│       ├── services/
│       │   ├── document_service.py
│       │   ├── llm_service.py
│       │   ├── speech_service.py
│       │   └── web_service.py
│       └── ui/
│           └── desktop_app.py
└── tests/
```

더 자세한 구조 설명은 [docs/architecture.md](docs/architecture.md)를 참고하세요.

## 로컬 실행

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
deskmate-ai
```

Ollama 모델을 바꾸고 싶으면 다음처럼 환경 변수를 설정합니다.

```powershell
$env:DESKMATE_OLLAMA_MODEL="qwen3:8b"
deskmate-ai
```

## 테스트

```powershell
pytest
```

## Docker 실행

Docker 환경에서는 GUI 실행보다 의존성 설치와 테스트 실행 검증을 우선합니다.

```powershell
docker build -t deskmate-ai .
docker run --rm deskmate-ai
```

## CI

GitHub Actions는 `main`과 `develop` 브랜치의 push, pull request에서 실행됩니다.

- Python 의존성 설치
- 테스트 실행
- Docker 이미지 빌드

## 다음 작업

다음 구현 계획은 [docs/roadmap.md](docs/roadmap.md)를 참고하세요.
