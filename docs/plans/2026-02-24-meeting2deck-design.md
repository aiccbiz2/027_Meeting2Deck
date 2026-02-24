# Meeting2Deck Orchestrator - Design Document

**Date**: 2026-02-24
**Status**: Approved

---

## 1. 프로젝트 개요

**Meeting2Deck Orchestrator**는 PDF(손글씨 다이어그램 + STT 전사문)를 입력받아 컨설팅 수준의 프레젠테이션 기획안, 노션 요약, 이메일 초안을 자동 생성하는 에이전트다.

### 핵심 가치
- 회의 PDF 하나로 → 슬라이드 + 노션 요약 + 이메일까지 엔드투엔드 자동화
- BCG/McKinsey 수준의 구조적 사고와 경영진 보고 수준의 명확성

---

## 2. 아키텍처

### 선택된 접근 방식: Discord Bot → Claude CLI + MCP

```
┌─────────────────────────────────────────────────────────┐
│                    Discord Channel                       │
│              (사용자가 PDF 업로드)                        │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│              Discord Bot (Python)                        │
│  - PDF 다운로드 & 저장                                   │
│  - Claude CLI subprocess 실행                            │
│  - Make.com 웹훅 호출 (이메일 발송)                      │
│  - Discord 채널에 결과 전송                              │
└──────────────────┬──────────────────────────────────────┘
                   │ subprocess: claude CLI
                   ▼
┌─────────────────────────────────────────────────────────┐
│           Claude CLI Agent (CLAUDE.md)                   │
│                                                          │
│  마스터 프롬프트: Meeting2Deck Orchestrator               │
│                                                          │
│  STEP 1: PDF 읽기 (Vision + 텍스트)                      │
│  STEP 2: 회의 구조 재구성                                │
│  STEP 3: 손그림 → 다이어그램 스펙 (JSON)                  │
│  STEP 4: 슬라이드 구성 설계                              │
│  STEP 5: Google Slides JSON → MCP로 슬라이드 생성        │
│  STEP 6: 노션 요약 → MCP로 Notion 저장                   │
│  STEP 7: 이메일 초안 → 파일 저장                         │
│                                                          │
│  ┌─── MCP Servers ───────────────────────┐               │
│  │  ✅ Notion MCP (기설치)              │               │
│  │  🔧 Google Slides MCP (커스텀)       │               │
│  └───────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    [Notion]    [Google Slides]   [Make.com → Gmail]
                                  (Python Bot 직접 호출)
```

### 아키텍처 결정 근거
- **Claude CLI**: PDF를 네이티브로 읽고 Vision으로 이미지 해석 가능
- **MCP (Notion + Slides)**: Claude가 분석 후 즉시 외부 서비스에 저장/생성
- **Python Bot (Make.com)**: 이메일 발송은 단순 웹훅이므로 MCP 불필요
- **파일 저장 fallback**: MCP 실패 시에도 JSON/MD 파일은 항상 남김

---

## 3. 프로젝트 구조

```
027_Meeting2Deck/
├── CLAUDE.md                    # 마스터 프롬프트 (Meeting2Deck Orchestrator)
├── main.py                      # Discord Bot 엔트리포인트
├── cogs/
│   └── meeting2deck_bot.py      # PDF 수신 → CLI 호출 → 결과 전송
├── services/
│   ├── claude_runner.py         # Claude CLI subprocess 래퍼
│   └── slides_mcp_server.py     # Google Slides MCP 서버
├── config/
│   └── mcp_config.json          # MCP 서버 설정
├── output/                      # Claude 출력 임시 저장
├── .env                         # 토큰, API 키
├── .env.example                 # 환경변수 예시
├── requirements.txt
└── docs/plans/
    └── 2026-02-24-meeting2deck-design.md
```

---

## 4. 컴포넌트 상세

### 4-1. Discord Bot (`main.py` + `cogs/meeting2deck_bot.py`)

**역할**: 얇은 레이어. PDF 수신, CLI 호출, 최종 결과 전달만 담당.

**동작 흐름**:
1. 사용자가 `#meeting-deck` 채널에 PDF 업로드
2. Bot이 PDF 다운로드 → `output/{timestamp}.pdf`
3. `claude_runner.py`로 CLI 호출
4. Claude 출력 결과 파싱 (slides_url, notion_url, email_draft)
5. Make.com 웹훅 호출 (이메일 발송)
6. Discord 채널에 결과 메시지 전송 (노션 링크 + 슬라이드 링크 + 발송 확인)

### 4-2. Claude CLI Agent (`CLAUDE.md`)

**역할**: 두뇌. 7단계 워크플로우 전체를 수행.

**CLAUDE.md 내용**: 사용자 제공 마스터 프롬프트 전문 + MCP 도구 사용 지시

**MCP 도구 사용 규칙**:
- STEP 5 완료 시: `slides.json` 파일 저장 + Google Slides MCP로 실제 생성
- STEP 6 완료 시: `notion_summary.md` 파일 저장 + Notion MCP로 페이지 생성
- STEP 7 완료 시: `email_draft.md` 파일 저장 (Make.com은 Bot이 처리)

**출력 파일 규칙**:
- `output/slides.json` — Google Slides 생성용 JSON 스펙
- `output/notion_summary.md` — 노션 공유용 Markdown
- `output/email_draft.md` — 이메일 본문 초안
- `output/result.json` — 처리 결과 메타 (slides_url, notion_url 등)

### 4-3. Google Slides MCP Server (`services/slides_mcp_server.py`)

**역할**: Claude CLI가 호출하는 MCP 도구. Google Slides API wrapper.

**제공 도구**:
- `create_presentation(title, subtitle)` → presentation_id 반환
- `add_title_slide(presentation_id, title, subtitle)`
- `add_bullet_slide(presentation_id, title, bullets[])`
- `add_diagram_slide(presentation_id, title, diagram_spec)`
- `get_presentation_url(presentation_id)` → URL 반환

**프로토콜**: stdio (Claude CLI ↔ MCP)
**인증**: Google Service Account (credentials.json)

### 4-4. Notion MCP (기설치)

**역할**: 노션 페이지 생성/저장. 기존 설치된 MCP 서버 사용.

**사용할 도구**:
- `API-post-page`: 새 페이지 생성 (요약 내용 포함)
- `API-patch-block-children`: 블록 추가 (테이블, 리스트 등)

---

## 5. 데이터 플로우

```
[PDF 업로드]
    │
    ▼
Discord Bot: PDF 다운로드 → output/{timestamp}.pdf
    │
    ▼
Claude CLI 호출 (CLAUDE.md 마스터 프롬프트)
    │
    ├─ STEP 1-4: 내부 분석 (출력 없음)
    │
    ├─ STEP 5: Google Slides
    │   ├─ slides.json 파일 저장 (항상)
    │   └─ MCP: Slides 생성 시도
    │       ├─ 성공 → slides_url 반환
    │       └─ 실패 → JSON 파일만 남김 (fallback)
    │
    ├─ STEP 6: Notion
    │   ├─ notion_summary.md 파일 저장 (항상)
    │   └─ MCP: Notion 페이지 생성 시도
    │       ├─ 성공 → notion_url 반환
    │       └─ 실패 → MD 파일만 남김 (fallback)
    │
    └─ STEP 7: 이메일 초안
        └─ email_draft.md 파일 저장 (항상)
    │
    ▼
Discord Bot: 결과 수집
    ├─ result.json에서 slides_url / notion_url 파싱
    ├─ email_draft.md 읽기
    ├─ Make.com 웹훅 호출 (이메일 발송)
    └─ Discord 채널에 결과 메시지 전송
        ├─ 노션 링크
        ├─ 슬라이드 링크
        └─ "이메일 발송 완료" 확인
```

**에러 핸들링 원칙**:
- 파일 저장 = 항상 (MCP 성공 여부와 무관)
- MCP = best effort (실패 시 파일 fallback으로 graceful degradation)
- Discord Bot = 최종 조율자 (Claude 출력 파싱 → 외부 전달)

---

## 6. Claude CLI 마스터 프롬프트 (CLAUDE.md)

사용자 제공 프롬프트 전문 포함. 추가 지시:
- MCP 도구를 사용하여 Notion 저장 및 Google Slides 생성
- 모든 출력은 파일로도 저장 (fallback)
- 최종 result.json에 처리 결과 메타 정보 기록

### 7단계 워크플로우 요약

| STEP | 작업 | 출력 |
|------|------|------|
| 1 | PDF 입력 해석 (Vision + 텍스트) | 내부 분석 |
| 2 | 회의 구조 재구성 | 내부 분석 |
| 3 | 손그림 다이어그램 전문화 | 다이어그램 JSON 스펙 |
| 4 | 슬라이드 구성 설계 | 슬라이드 구조 |
| 5 | Google Slides JSON + 실제 생성 | slides.json + slides_url |
| 6 | 노션 공유용 요약 + 저장 | notion_summary.md + notion_url |
| 7 | 이메일 초안 | email_draft.md |

---

## 7. 외부 연동

| 서비스 | 연동 방식 | 담당 |
|--------|----------|------|
| Notion | MCP (기설치) | Claude CLI |
| Google Slides | MCP (커스텀) | Claude CLI |
| Make.com → Gmail | HTTP POST 웹훅 | Discord Bot (Python) |
| Discord | discord.py | Discord Bot |

---

## 8. 환경변수

```
# Discord
DISCORD_TOKEN=
DISCORD_CHANNEL_ID=

# Google Slides API
GOOGLE_SERVICE_ACCOUNT_JSON=

# Notion
NOTION_API_TOKEN=
NOTION_DATABASE_ID=

# Make.com
MAKECOM_WEBHOOK_URL=
EMAIL_RECIPIENT=
```

---

## 9. 기대 수준

- BCG/McKinsey 스타일의 구조적 사고
- 경영진이 바로 이해 가능한 명확성
- 시각적으로 변환 가능한 구조화
- 자동화 파이프라인에서 바로 사용 가능한 포맷

---

## 10. 금지 사항

- 사실 왜곡 금지
- 과도한 미사여구 금지
- 회의 내용에 없는 전략 창작 금지
- 모호한 경우 반드시 [추정] 표시
