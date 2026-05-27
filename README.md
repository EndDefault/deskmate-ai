# DeskMate AI

DeskMate AI는 개인 PC에서 실행하는 로컬 데스크톱 AI 비서입니다. 텍스트 명령을 입력하면 사이트 열기, 문서 요약, 메모 저장, 사용자 정보 기억, 로컬 AI 답변, TTS 음성 출력 같은 작업을 수행합니다.

## 현재 목표

작고 가볍게 시작하되, 실제 개인 작업에서 쓸 수 있는 AI 비서를 단계적으로 만드는 것이 목표입니다.

현재 구조는 모든 질문을 LLM에 바로 보내지 않고, 간단한 요청은 로컬 라우터와 SQLite 저장소에서 먼저 처리합니다. 이렇게 해서 Ollama 호출 횟수를 줄이고, 응답 체감 속도를 개선합니다.

## 주요 기능

- CustomTkinter 기반 데스크톱 UI
- 텍스트 명령 입력 및 채팅 로그 출력
- PDF, TXT, MD 문서 선택 및 요약 미리보기
- 자주 여는 사이트 열기
- Ollama 기반 로컬 LLM 답변
- TTS 음성 출력 선택
- SQLite 기반 사용자 프로필 저장
- SQLite 기반 메모 저장 및 최근 메모 조회
- SQLite 기반 응답 캐시
- LLM/TTS 백그라운드 실행으로 UI 멈춤 완화
- Ollama `keep_alive`, timeout, 생성 토큰 제한 설정

## 예시 명령

```text
내 이름은 민수
내 이름 뭐야?
기억해 SQLite 캐시 먼저 만들기
최근 메모 보여줘
이 문서 요약해줘
유튜브 열어줘
```

## 기술 스택

- Python 3.11+
- CustomTkinter: 데스크톱 UI
- Ollama: 로컬 LLM 실행
- SQLite: 로컬 프로필, 메모, 응답 캐시 저장
- pypdf: PDF 텍스트 추출
- pyttsx3: 로컬 TTS
- pytest: 테스트
- Docker: 테스트 환경 검증
- GitHub Actions: CI

## 프로젝트 구조

```text
.
├── Dockerfile
├── README.md
├── docs/
│   ├── architecture.md
│   ├── model-selection.md
│   └── roadmap.md
├── pyproject.toml
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
│       │   ├── storage_service.py
│       │   └── web_service.py
│       └── ui/
│           └── desktop_app.py
└── tests/
```

## 로컬 실행

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
deskmate-ai
```

Ollama 모델은 기본값으로 `qwen3:4b`를 사용합니다.

```powershell
ollama pull qwen3:4b
ollama run qwen3:4b
```

모델을 바꾸려면 환경 변수를 설정합니다.

```powershell
$env:DESKMATE_OLLAMA_MODEL="llama3.2:3b"
deskmate-ai
```

## 설정

| 환경 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `DESKMATE_OLLAMA_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `DESKMATE_OLLAMA_MODEL` | `qwen3:4b` | 사용할 Ollama 모델 |
| `DESKMATE_OLLAMA_TIMEOUT_SECONDS` | `15` | Ollama 응답 대기 시간 |
| `DESKMATE_OLLAMA_KEEP_ALIVE` | `10m` | 모델을 메모리에 유지할 시간 |
| `DESKMATE_OLLAMA_MAX_TOKENS` | `512` | 최대 생성 토큰 수 |
| `DESKMATE_DOCUMENT_PREVIEW_CHARS` | `1200` | 문서 미리보기 최대 글자 수 |
| `DESKMATE_DATA_DIR` | `~/.deskmate_ai` | SQLite DB 저장 폴더 |

기본 SQLite DB 위치는 Windows 기준으로 다음과 같습니다.

```text
C:\Users\user\.deskmate_ai\deskmate.db
```

DB Browser for SQLite로 이 파일을 열면 `user_profile`, `memos`, `response_cache` 테이블을 확인할 수 있습니다.

## 테스트

```powershell
pytest
python -m compileall src tests
```

`tests` 폴더는 자동 점검용 코드입니다. 기능을 수정한 뒤 기존 동작이 깨졌는지 빠르게 확인하는 역할을 합니다.

## Docker

현재 Dockerfile은 데스크톱 GUI 실행보다 테스트 검증에 초점이 맞춰져 있습니다.

```powershell
docker build -t deskmate-ai .
docker run --rm deskmate-ai
```

SQLite는 Python 내장 `sqlite3`를 사용하므로 Docker 이미지 안에 별도 SQLite 프로그램을 설치하지 않아도 동작합니다.

단, 컨테이너를 삭제해도 DB 데이터를 유지하려면 volume을 연결해야 합니다.

```powershell
docker run --rm `
  -e DESKMATE_DATA_DIR=/data `
  -v deskmate_data:/data `
  deskmate-ai
```

GUI 앱을 Docker에서 직접 사용하는 것은 권장하지 않습니다. Docker는 향후 FastAPI 백엔드나 RAG 서버를 분리할 때 더 적합합니다.

## 현재 아키텍처 흐름

```text
사용자 입력
-> UI
-> core.assistant.handle_prompt
-> 로컬 라우터 확인
   -> 프로필/메모/캐시 요청이면 SQLite에서 처리
-> 문서 요약 또는 사이트 열기 확인
-> 캐시된 응답 확인
-> Ollama 호출
-> 응답 캐시 저장
-> UI 출력
-> TTS 선택 시 음성 출력
```

## 다음 작업 후보

- 스트리밍 응답으로 답변 체감 속도 개선
- 앱 시작 시 Ollama 모델 워밍업
- 일정 저장 및 조회 기능
- 문서 chunking 및 embedding 저장
- FAISS 또는 ChromaDB 기반 RAG 검색
- FastAPI 백엔드 분리
- Docker 실행 모드를 테스트용과 서버용으로 분리

