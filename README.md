# Meeting2Deck Orchestrator

PDF(손글씨 다이어그램 + STT 전사문) → Google Slides + Notion 요약 + 이메일 자동 생성

## 아키텍처

```
Discord (PDF 업로드) → Discord Bot → Claude CLI Agent → MCP (Notion + Slides) + Make.com (Email)
```

## 설정

### 1. 환경변수

```bash
cp .env.example .env
# .env 파일을 열어 각 값을 채워주세요
```

### 2. Google Service Account

1. Google Cloud Console에서 프로젝트 생성
2. Google Slides API, Google Drive API 활성화
3. Service Account 생성 → JSON 키 다운로드
4. JSON 파일을 프로젝트 루트에 `credentials.json`으로 저장
5. `.env`에 `GOOGLE_SERVICE_ACCOUNT_JSON=credentials.json` 설정

### 3. Discord Bot

1. Discord Developer Portal에서 Bot 생성
2. MESSAGE CONTENT intent 활성화
3. Bot 토큰을 `.env`의 `DISCORD_TOKEN`에 설정
4. 사용할 채널 ID를 `DISCORD_CHANNEL_ID`에 설정

### 4. Notion

1. Notion Integration 생성 (https://www.notion.so/my-integrations)
2. 토큰을 `.env`의 `NOTION_API_TOKEN`에 설정
3. 대상 데이터베이스 ID를 `NOTION_DATABASE_ID`에 설정

### 5. Make.com

1. Make.com에서 Webhook → Gmail 시나리오 생성
2. Webhook URL을 `.env`의 `MAKECOM_WEBHOOK_URL`에 설정
3. 수신자 이메일을 `EMAIL_RECIPIENT`에 설정

## 실행

```bash
source venv/bin/activate
python main.py
```

## 테스트

```bash
# Google Slides API 연결 테스트
python scripts/test_slides_mcp.py

# Claude CLI runner 테스트 (PDF 필요)
python scripts/test_claude_runner.py path/to/test.pdf
```

## 사용법

Discord의 지정 채널에 PDF 파일을 업로드하면 자동으로 처리됩니다.
