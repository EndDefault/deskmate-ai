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


## 패치 노트

## Ollama 필수 모델 설치 메모

다른 컴퓨터에서 DeskMate AI를 처음 실행할 때는 Ollama 설치 후 아래 3개 모델을 받아두면 됩니다.

```powershell
ollama pull qwen3:4b
ollama pull nomic-embed-text
ollama pull mxbai-embed-large
ollama list
```

모델 역할:

- `qwen3:4b`: 일반 대화, 질문 답변, 문서 요약 답변 생성용 LLM
- `nomic-embed-text`: 가볍고 빠른 임베딩/RAG 시작용 모델
- `mxbai-embed-large`: 문서 검색 품질을 더 높일 때 쓰는 고품질 임베딩 모델

최소 실행만 확인하려면 `qwen3:4b`만 있어도 되지만, 문서 검색/RAG 기능까지 확장하려면 임베딩 모델이 필요합니다.

### v1.01 - 캐시/AI 응답 기반 보강

이번 업데이트는 기존 구조를 유지하면서 로컬 비서의 응답 속도와 재사용성을 높이는 데 초점을 맞췄습니다.

- 새 작업 브랜치: `codex/enhance-cache-ai`
- 실행 환경 확인: 이 PC에서 의존성 설치 후 `pytest` 기준 전체 테스트 통과
- 테스트 범위 확장: 기존 14개에서 19개 테스트로 확대
- 깨져 보이던 핵심 비서 응답 문구 일부를 정상 한글 문구로 정리
- 일반 질문 응답 캐시 강화
  - 질문을 정규화한 뒤 저장/조회
  - Ollama 모델명과 옵션 해시를 함께 기록
  - 같은 질문이라도 모델/옵션이 다르면 잘못된 캐시를 재사용하지 않도록 조회 조건 강화
- 유사 질문 캐시 추가
  - 완전히 같은 질문이 아니어도 토큰 유사도가 높은 경우 기존 답변을 재사용
  - 너무 넓게 재사용하지 않도록 보수적인 기준으로 동작
  - 캐시로 처리되면 `similar_cached_response` 액션으로 구분
- 문서 요약 캐시 추가
  - PDF/TXT/MD 문서 요약 결과를 파일 해시 기준으로 저장
  - 같은 내용의 문서는 파일명이 달라도 요약 결과를 재사용
  - 문서 미리보기 길이(`DESKMATE_DOCUMENT_PREVIEW_CHARS`)가 달라지면 별도 캐시로 취급
- SQLite 스키마 확장
  - `response_cache`에 `prompt_hash`, `model`, `options_hash`, `expires_at` 컬럼 추가
  - `document_summary_cache` 테이블 추가
  - 기존 DB가 있어도 필요한 컬럼을 자동으로 보강하도록 마이그레이션 처리

다음 개선 후보:

- 문서 내용을 chunk로 나누고 관련 부분만 LLM에 전달하는 RAG형 요약
- 메모 검색을 최근 목록 중심에서 키워드/의미 검색 중심으로 확장
- 모델 선택 UI와 캐시 상태 표시
- 캐시 만료 정책과 수동 캐시 비우기 기능

### v1.02 - 액션 캐시와 사이드바 보강

이번 업데이트는 사용자가 직접 관리하는 캐시를 단순 텍스트 저장소가 아니라 실행 가능한 액션 단위로 확장하는 데 초점을 맞췄습니다.

- 작업 브랜치: `codex/manual-cache-manager`
- 캐시 구조를 `키워드 + 액션 종류 + 내용`으로 확장
- 액션 종류 추가
  - `내용 보여주기`: 키워드에 맞는 저장 내용을 채팅창에 표시
  - `사이트 열기`: 키워드에 맞는 URL을 브라우저로 직접 실행
- `keyword_cache` 테이블에 `action_type` 컬럼 추가
- 기존 캐시는 기본 `내용 보여주기` 액션으로 유지되도록 자동 보강
- 프롬프트가 키워드와 완전히 같지 않아도 문장 안에 키워드가 있으면 캐시를 찾도록 개선
- `사이트 열기` 액션 캐시는 `열어줘` 같은 표현이 없어도 키워드만으로 URL 실행 가능
- 구글 검색으로 빠지던 사용자 정의 사이트 열기 흐름 개선
- UI 사이드바를 오른쪽으로 이동
- 사이드바에는 `전체 캐시 보기`만 남기고, 캐시 추가는 캐시 관리 창 안에서 처리
- 캐시 추가/수정 화면에 액션 종류 선택 메뉴 추가
- 캐시 저장 후 상세 화면이 아니라 전체 캐시 목록으로 돌아가도록 변경
- 캐시 목록과 삭제 확인 창에서 액션 종류를 함께 표시
- 웹 열기 서비스의 기본 한글 사이트 키워드 정리
- 테스트 범위 확장: 27개 테스트 통과

다음 개선 후보:

- `복사하기`, `파일 열기`, `폴더 열기`, `API 호출` 액션 추가
- 액션 캐시 그룹/폴더 기능 추가
- 이미지 번역 작업용 별도 브랜치에서 OCR/번역 파이프라인 설계

### v1.03 - 이미지 번역 검수 워크플로우

이번 업데이트는 이미지 번역을 한 번에 저장하지 않고, OCR 검수와 번역 검수를 나누어 사용자가 직접 확인할 수 있게 만드는 데 초점을 맞췄습니다.

- 작업 브랜치: `codex/image-translation-workflow`
- 이미지 번역 창 추가
  - 이미지 또는 폴더 선택
  - 원문 언어와 번역 언어 선택
  - OCR 반복, 업스케일, 대비 강화, 흑백 처리, 최소 신뢰도 설정
  - 번역용 캐시 최대 3개 선택
  - 강제 종료 버튼으로 긴 작업 중단 가능
- OCR 검수 단계 추가
  - OCR이 감지한 위치를 이미지 위 흰색 네모로 표시
  - 오른쪽 목록에서 감지된 원문과 좌표/신뢰도 확인
  - 필요 없는 OCR 줄은 `X` 버튼으로 삭제
  - 누락된 말풍선이나 문장은 이미지 위에서 영역을 드래그한 뒤 원문을 직접 입력해 추가
  - OCR 검수 통과 후에만 번역 단계로 이동
- 번역 검수 단계 추가
  - 원문과 번역 결과를 대응해서 확인
  - 번역이 적용된 미리보기 이미지를 별도 창에서 확인
  - 통과하면 최종 번역 이미지 저장, 불통과하면 작업 중단
- OCR 안정성 보강
  - 과하게 많은 텍스트를 끌고 오던 공격적인 OCR 패스는 제거
  - 기존 안정적인 OCR 흐름으로 되돌림
  - 같은 OCR 줄 안에서도 가로 간격이 너무 크면 다른 컷으로 보고 분리
- 번역 캐시 보강
  - 번역용 캐시 그룹과 용어 관리 창 추가
  - 원문 언어에 맞는 캐시만 이미지 번역 설정에 표시
  - 같은 캐시를 중복 선택하지 못하도록 제한
  - 완전 일치하는 문장은 모델보다 번역 캐시를 먼저 사용
  - 짧은 표현 캐시는 문장 안 힌트로 프롬프트에 전달
  - 모델이 원문을 그대로 반환하면 캐시 힌트를 직접 치환해 최소한 캐시 내용이 반영되도록 보정
- 번역 Provider 골자 추가
  - 기본 로컬 AI 번역 유지
  - DeepL Free API 키가 있을 때 사용할 수 있는 선택 Provider 추가
  - `DESKMATE_DEEPL_API_KEY`, `DESKMATE_DEEPL_API_URL`, `DESKMATE_DEEPL_TIMEOUT_SECONDS` 환경 변수 추가
- UI 구조 정리
  - 이미지 번역 검수는 메인 창 안에 끼우지 않고 별도 검수 창으로 표시
  - 메인 창의 진행도 막대, 로그, 시작/강제 종료 버튼 유지
  - 검수 창의 통과/불통과 버튼은 하단에 고정
- 테스트 범위 확장
  - OCR 수동 추가/삭제
  - OCR 줄 분리
  - 번역 캐시 우선 적용
  - 문장 안 캐시 힌트 적용
  - 모델 원문 반환 시 캐시 치환 fallback
  - 전체 테스트 47개 기준 검증

사용 흐름:

```text
이미지 선택
-> 시작
-> OCR 검수 창에서 감지 원문 확인
-> 필요 없는 줄 삭제 또는 누락 영역 수동 추가
-> 통과
-> 번역 검수 창에서 원문/번역 확인
-> 통과 시 최종 이미지 저장
```

다음 개선 후보:

- OCR 검수 창에서 기존 OCR 텍스트 직접 수정
- 번역 검수 창에서 번역문 직접 수정 후 저장
- 수동으로 고친 번역을 번역 캐시에 바로 저장하는 버튼
- 말풍선/검은 박스별 렌더링 스타일 자동 선택
- 이미지 번역 작업 결과 JSON 저장 및 재개 기능
