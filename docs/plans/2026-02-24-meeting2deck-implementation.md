# Meeting2Deck Orchestrator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Discord에 PDF를 업로드하면 Claude CLI가 분석하여 Google Slides, Notion 요약, 이메일 초안을 자동 생성하는 에이전트 구축

**Architecture:** Discord Bot(Python)이 PDF를 수신하고 Claude CLI를 subprocess로 호출. Claude CLI는 CLAUDE.md 마스터 프롬프트를 따라 7단계 워크플로우를 실행하며, MCP 서버(Notion, Google Slides)를 통해 외부 서비스에 직접 저장. Make.com 웹훅은 Discord Bot이 처리.

**Tech Stack:** Python 3.13, discord.py, Claude CLI, MCP (stdio), Google Slides API, Notion API, Make.com webhook, python-dotenv, aiohttp

**Design Doc:** `docs/plans/2026-02-24-meeting2deck-design.md`

---

## Task 1: 프로젝트 초기 설정

**Files:**
- Create: `027_Meeting2Deck/requirements.txt`
- Create: `027_Meeting2Deck/.env.example`
- Create: `027_Meeting2Deck/.gitignore`

**Step 1: requirements.txt 생성**

```txt
discord.py>=2.3.0
python-dotenv>=1.0.0
aiohttp>=3.9.0
google-api-python-client>=2.100.0
google-auth>=2.25.0
google-auth-oauthlib>=1.2.0
mcp>=1.0.0
```

**Step 2: .env.example 생성**

```env
# Discord
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id

# Google Slides API
GOOGLE_SERVICE_ACCOUNT_JSON=path/to/credentials.json

# Notion
NOTION_API_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id

# Make.com
MAKECOM_WEBHOOK_URL=https://hook.make.com/your_webhook_id
EMAIL_RECIPIENT=recipient@example.com

# Claude CLI
CLAUDE_PROJECT_DIR=./
```

**Step 3: .gitignore 생성**

```
.env
*.pyc
__pycache__/
venv/
output/
*.pdf
credentials.json
```

**Step 4: output 디렉토리 생성**

Run: `mkdir -p output && touch output/.gitkeep`

**Step 5: venv 생성 및 의존성 설치**

Run: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`

**Step 6: Commit**

```bash
git init
git add requirements.txt .env.example .gitignore output/.gitkeep docs/
git commit -m "chore: initial project setup with dependencies"
```

---

## Task 2: CLAUDE.md 마스터 프롬프트 작성

**Files:**
- Create: `027_Meeting2Deck/CLAUDE.md`

**Step 1: CLAUDE.md 작성**

이 파일이 Claude CLI Agent의 두뇌 역할. 사용자 제공 마스터 프롬프트 전문 + MCP 도구 사용 지시 + 출력 파일 규칙을 포함.

```markdown
# Meeting2Deck Orchestrator

## 역할 정의

너는 "Meeting2Deck Orchestrator"라는 고급 자동화 에이전트다.

사용자가 업로드한 단일 PDF 파일(손글씨 다이어그램 + STT 전사문 포함)을 기반으로:
1. 회의 내용을 전문적으로 구조화하고
2. 다이어그램을 정제된 시각 구조로 변환하고
3. 전문가 수준의 프레젠테이션 슬라이드 기획안을 생성하고
4. Google Slides 생성용 데이터 구조를 출력하고
5. 노션 공유용 요약본과
6. 팀 이메일 송부용 메시지까지 생성한다.

너는 단순 요약기가 아니라, 컨설팅 회사 수준의 프레젠테이션 설계자로 행동해야 한다.

---

## MCP 도구 사용 규칙

### 파일 저장 (항상 수행)
- `output/slides.json` — Google Slides JSON 스펙
- `output/notion_summary.md` — 노션 공유용 Markdown
- `output/email_draft.md` — 이메일 본문 초안
- `output/result.json` — 처리 결과 메타 정보

### MCP 도구 호출 (best effort)
- STEP 5 완료 후: Google Slides MCP로 실제 슬라이드 생성 시도
- STEP 6 완료 후: Notion MCP로 페이지 생성 시도
- MCP 실패 시: 파일은 이미 저장되어 있으므로 에러 로그만 남기고 계속 진행

### result.json 형식
```json
{
  "status": "completed",
  "slides_url": "https://docs.google.com/presentation/d/...",
  "notion_url": "https://www.notion.so/...",
  "slides_json_path": "output/slides.json",
  "notion_md_path": "output/notion_summary.md",
  "email_draft_path": "output/email_draft.md",
  "errors": []
}
```

---

## 전체 Workflow 단계

### STEP 1: 입력 해석

입력:
- 단일 PDF 파일
- 해당 PDF는 다음을 포함:
  - 손글씨 구성도 (이미지 기반)
  - 그 아래 위치한 STT 전사문 텍스트

작업:
- 텍스트 전사문을 완전히 읽고 구조 파악
- 이미지 기반 구성도를 시각적 구조로 해석
- 암묵적 의도와 핵심 맥락을 추론

출력하지 말고 내부 분석만 수행.

### STEP 2: 회의 구조 재구성

다음 항목을 논리적으로 정리:
- 회의 목적
- 배경 및 문제 정의
- 현재 상태
- 핵심 논의 흐름
- 주요 의사결정
- 전략 방향
- 리스크
- 미해결 이슈
- 액션 아이템
- 다음 단계

조건:
- 중복 제거
- 모호한 표현 제거
- 구어체를 보고서체로 변환
- 필요 시 추론하되 반드시 [추정] 표시

### STEP 3: 손그림 다이어그램 전문화

손글씨 이미지를 분석하여:
1. 노드(컴포넌트)
2. 관계(화살표)
3. 흐름 방향
4. 계층 구조
5. 그룹/영역

를 추출한다.

그 후 다음 중 하나의 구조 유형으로 정제:
- 프로세스 흐름도
- 아키텍처 구조도
- 전략 맵
- 로드맵
- 의사결정 트리
- 시스템 상호작용도

출력은 텍스트 다이어그램 스펙(JSON 구조)으로 제공한다.

### STEP 4: 슬라이드 구성 설계

슬라이드는 다음 순서를 기본 구조로 한다:
1. Title
2. Executive Summary
3. Background / Problem
4. Current State Analysis
5. Key Discussion Points
6. Strategic Direction
7. Architecture / Process Diagram
8. Risks & Considerations
9. Action Items
10. Roadmap / Next Steps

규칙:
- 한 슬라이드당 핵심 메시지 1개
- Bullet 최대 5개
- 문장 길이 15단어 이하
- 명사형 중심
- 발표자가 설명할 여지를 남길 것
- 경영진 보고 수준 유지

### STEP 5: Google Slides 생성용 구조 출력

다음 JSON 형식으로 `output/slides.json`에 저장:

```json
{
  "deck_title": "",
  "deck_subtitle": "",
  "tone": "Professional / Executive",
  "slides": [
    {
      "slide_number": 1,
      "type": "title",
      "title": "",
      "subtitle": ""
    },
    {
      "slide_number": 2,
      "type": "bullet",
      "title": "",
      "bullets": []
    },
    {
      "slide_number": 7,
      "type": "diagram",
      "title": "",
      "diagram_spec": {
        "nodes": [],
        "edges": [],
        "layout_hint": ""
      }
    }
  ]
}
```

파일 저장 후, Google Slides MCP 도구를 사용하여 실제 슬라이드를 생성한다.
MCP 호출 실패 시 에러를 result.json의 errors 배열에 기록하고 계속 진행.

### STEP 6: 노션 공유용 요약 생성

다음 항목 포함:
- TL;DR (5줄 이내)
- 주요 의사결정
- 액션 아이템 표 형식
- 다음 회의 준비사항

Markdown 형식으로 `output/notion_summary.md`에 저장.

파일 저장 후, Notion MCP 도구를 사용하여 노션 페이지를 생성한다.
MCP 호출 실패 시 에러를 result.json의 errors 배열에 기록하고 계속 진행.

### STEP 7: 팀 이메일 송부용 메시지 생성

구성:
- 제목
- 간단한 회의 요약
- 슬라이드 링크 안내 문구
- 액션아이템 강조
- 다음 일정 안내

격식 있는 비즈니스 톤 사용.
`output/email_draft.md`에 저장.

### 최종: result.json 작성

모든 STEP 완료 후, `output/result.json`에 처리 결과를 기록한다.

---

## 금지 사항
- 사실 왜곡 금지
- 과도한 미사여구 금지
- 회의 내용에 없는 전략 창작 금지
- 모호한 경우 반드시 [추정] 표시

## 출력 순서
1. Google Slides JSON (파일 저장 + MCP 생성)
2. 노션 공유용 요약 (파일 저장 + MCP 생성)
3. 이메일 송부용 메시지 (파일 저장)
4. result.json (메타 정보)

## 기대 수준
- BCG / McKinsey 스타일의 구조적 사고
- 경영진이 바로 이해 가능한 명확성
- 시각적으로 변환 가능한 구조화
- 자동화 파이프라인에서 바로 사용 가능한 포맷
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: add master orchestration prompt for Claude CLI agent"
```

---

## Task 3: Google Slides MCP Server 구축

**Files:**
- Create: `027_Meeting2Deck/services/__init__.py`
- Create: `027_Meeting2Deck/services/slides_mcp_server.py`

**Step 1: `services/__init__.py` 생성**

```python
```

빈 파일.

**Step 2: `slides_mcp_server.py` 작성**

Google Slides API를 MCP 도구로 노출하는 stdio MCP 서버.

참조 문서: Google Slides API - https://developers.google.com/slides/api/guides/overview

```python
import json
import os
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/presentations", "https://www.googleapis.com/auth/drive"]

server = Server("google-slides-mcp")

def get_slides_service():
    creds_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
    credentials = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return build("slides", "v1", credentials=credentials)

def get_drive_service():
    creds_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
    credentials = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return build("drive", "v3", credentials=credentials)


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="create_presentation",
            description="Create a new Google Slides presentation and return its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Presentation title"},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="add_slide",
            description="Add a slide to an existing presentation. Types: title, bullet, diagram",
            inputSchema={
                "type": "object",
                "properties": {
                    "presentation_id": {"type": "string"},
                    "slide_type": {"type": "string", "enum": ["title", "bullet", "diagram"]},
                    "title": {"type": "string"},
                    "subtitle": {"type": "string", "description": "For title slides"},
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "For bullet slides",
                    },
                    "diagram_description": {
                        "type": "string",
                        "description": "For diagram slides - text description of the diagram",
                    },
                },
                "required": ["presentation_id", "slide_type", "title"],
            },
        ),
        Tool(
            name="build_deck_from_json",
            description="Build a complete presentation from a Meeting2Deck JSON spec",
            inputSchema={
                "type": "object",
                "properties": {
                    "deck_json": {
                        "type": "object",
                        "description": "The full deck JSON spec with deck_title, deck_subtitle, slides array",
                    },
                    "share_with_email": {
                        "type": "string",
                        "description": "Optional email to share the presentation with",
                    },
                },
                "required": ["deck_json"],
            },
        ),
        Tool(
            name="get_presentation_url",
            description="Get the URL for an existing presentation",
            inputSchema={
                "type": "object",
                "properties": {
                    "presentation_id": {"type": "string"},
                },
                "required": ["presentation_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "create_presentation":
        service = get_slides_service()
        body = {"title": arguments["title"]}
        presentation = service.presentations().create(body=body).execute()
        pid = presentation.get("presentationId")
        return [TextContent(type="text", text=json.dumps({"presentation_id": pid, "url": f"https://docs.google.com/presentation/d/{pid}/edit"}))]

    elif name == "add_slide":
        service = get_slides_service()
        pid = arguments["presentation_id"]
        slide_type = arguments["slide_type"]
        title = arguments["title"]

        requests = []

        # Create a new slide
        import uuid
        slide_id = f"slide_{uuid.uuid4().hex[:8]}"
        title_id = f"title_{uuid.uuid4().hex[:8]}"
        body_id = f"body_{uuid.uuid4().hex[:8]}"

        if slide_type == "title":
            requests.append({
                "createSlide": {
                    "objectId": slide_id,
                    "slideLayoutReference": {"predefinedLayout": "TITLE"},
                    "placeholderIdMappings": [
                        {"layoutPlaceholder": {"type": "CENTERED_TITLE"}, "objectId": title_id},
                        {"layoutPlaceholder": {"type": "SUBTITLE"}, "objectId": body_id},
                    ],
                }
            })
            requests.append({
                "insertText": {"objectId": title_id, "text": title}
            })
            if arguments.get("subtitle"):
                requests.append({
                    "insertText": {"objectId": body_id, "text": arguments["subtitle"]}
                })

        elif slide_type == "bullet":
            requests.append({
                "createSlide": {
                    "objectId": slide_id,
                    "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
                    "placeholderIdMappings": [
                        {"layoutPlaceholder": {"type": "TITLE"}, "objectId": title_id},
                        {"layoutPlaceholder": {"type": "BODY"}, "objectId": body_id},
                    ],
                }
            })
            requests.append({
                "insertText": {"objectId": title_id, "text": title}
            })
            bullets = arguments.get("bullets", [])
            if bullets:
                bullet_text = "\n".join(bullets)
                requests.append({
                    "insertText": {"objectId": body_id, "text": bullet_text}
                })

        elif slide_type == "diagram":
            requests.append({
                "createSlide": {
                    "objectId": slide_id,
                    "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
                    "placeholderIdMappings": [
                        {"layoutPlaceholder": {"type": "TITLE"}, "objectId": title_id},
                        {"layoutPlaceholder": {"type": "BODY"}, "objectId": body_id},
                    ],
                }
            })
            requests.append({
                "insertText": {"objectId": title_id, "text": title}
            })
            desc = arguments.get("diagram_description", "[Diagram placeholder]")
            requests.append({
                "insertText": {"objectId": body_id, "text": desc}
            })

        service.presentations().batchUpdate(presentationId=pid, body={"requests": requests}).execute()
        return [TextContent(type="text", text=json.dumps({"slide_id": slide_id, "status": "added"}))]

    elif name == "build_deck_from_json":
        deck = arguments["deck_json"]
        service = get_slides_service()

        # Create presentation
        body = {"title": deck.get("deck_title", "Meeting2Deck")}
        presentation = service.presentations().create(body=body).execute()
        pid = presentation.get("presentationId")

        # Delete default blank slide
        default_slides = presentation.get("slides", [])
        if default_slides:
            del_requests = [{"deleteObject": {"objectId": default_slides[0]["objectId"]}}]
            service.presentations().batchUpdate(presentationId=pid, body={"requests": del_requests}).execute()

        # Add each slide
        for slide_spec in deck.get("slides", []):
            import uuid
            slide_id = f"slide_{uuid.uuid4().hex[:8]}"
            title_id = f"title_{uuid.uuid4().hex[:8]}"
            body_id = f"body_{uuid.uuid4().hex[:8]}"
            requests = []

            s_type = slide_spec.get("type", "bullet")

            if s_type == "title":
                requests.append({
                    "createSlide": {
                        "objectId": slide_id,
                        "slideLayoutReference": {"predefinedLayout": "TITLE"},
                        "placeholderIdMappings": [
                            {"layoutPlaceholder": {"type": "CENTERED_TITLE"}, "objectId": title_id},
                            {"layoutPlaceholder": {"type": "SUBTITLE"}, "objectId": body_id},
                        ],
                    }
                })
                requests.append({"insertText": {"objectId": title_id, "text": slide_spec.get("title", "")}})
                if slide_spec.get("subtitle"):
                    requests.append({"insertText": {"objectId": body_id, "text": slide_spec["subtitle"]}})
            else:
                requests.append({
                    "createSlide": {
                        "objectId": slide_id,
                        "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
                        "placeholderIdMappings": [
                            {"layoutPlaceholder": {"type": "TITLE"}, "objectId": title_id},
                            {"layoutPlaceholder": {"type": "BODY"}, "objectId": body_id},
                        ],
                    }
                })
                requests.append({"insertText": {"objectId": title_id, "text": slide_spec.get("title", "")}})

                if s_type == "bullet":
                    bullets = slide_spec.get("bullets", [])
                    if bullets:
                        requests.append({"insertText": {"objectId": body_id, "text": "\n".join(bullets)}})
                elif s_type == "diagram":
                    ds = slide_spec.get("diagram_spec", {})
                    nodes = ds.get("nodes", [])
                    edges = ds.get("edges", [])
                    layout = ds.get("layout_hint", "")
                    desc_lines = []
                    if nodes:
                        desc_lines.append("Components: " + ", ".join(str(n) for n in nodes))
                    if edges:
                        desc_lines.append("Connections: " + ", ".join(str(e) for e in edges))
                    if layout:
                        desc_lines.append("Layout: " + layout)
                    requests.append({"insertText": {"objectId": body_id, "text": "\n".join(desc_lines) if desc_lines else "[Diagram]"}})

            service.presentations().batchUpdate(presentationId=pid, body={"requests": requests}).execute()

        # Share if email provided
        share_email = arguments.get("share_with_email")
        if share_email:
            drive = get_drive_service()
            drive.permissions().create(
                fileId=pid,
                body={"type": "user", "role": "writer", "emailAddress": share_email},
                sendNotificationEmail=False,
            ).execute()

        url = f"https://docs.google.com/presentation/d/{pid}/edit"
        return [TextContent(type="text", text=json.dumps({"presentation_id": pid, "url": url, "slides_count": len(deck.get("slides", []))}))]

    elif name == "get_presentation_url":
        pid = arguments["presentation_id"]
        url = f"https://docs.google.com/presentation/d/{pid}/edit"
        return [TextContent(type="text", text=json.dumps({"url": url}))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**Step 3: Commit**

```bash
git add services/
git commit -m "feat: add Google Slides MCP server with stdio transport"
```

---

## Task 4: MCP 설정 파일 작성

**Files:**
- Create: `027_Meeting2Deck/config/mcp_config.json`
- Create: `027_Meeting2Deck/.claude/settings.json` (프로젝트 레벨 MCP 설정)

**Step 1: `.claude/settings.json` 작성**

Claude CLI가 이 프로젝트에서 사용할 MCP 서버 설정.

```json
{
  "mcpServers": {
    "google-slides": {
      "command": "python3",
      "args": ["services/slides_mcp_server.py"],
      "env": {
        "GOOGLE_SERVICE_ACCOUNT_JSON": "${GOOGLE_SERVICE_ACCOUNT_JSON}"
      }
    }
  }
}
```

참고: Notion MCP는 글로벌 설정에 이미 존재하므로 여기서는 Google Slides만 추가.

**Step 2: `config/mcp_config.json` 작성 (문서용)**

```json
{
  "description": "Meeting2Deck MCP server configuration reference",
  "servers": {
    "google-slides": {
      "type": "custom",
      "transport": "stdio",
      "command": "python3 services/slides_mcp_server.py",
      "tools": [
        "create_presentation",
        "add_slide",
        "build_deck_from_json",
        "get_presentation_url"
      ]
    },
    "notion": {
      "type": "pre-installed",
      "note": "Uses globally configured Notion MCP",
      "tools": [
        "API-post-page",
        "API-patch-block-children",
        "API-retrieve-a-database"
      ]
    }
  }
}
```

**Step 3: Commit**

```bash
mkdir -p .claude
git add .claude/settings.json config/
git commit -m "feat: add MCP server configuration for Google Slides"
```

---

## Task 5: Claude CLI Runner Service

**Files:**
- Create: `027_Meeting2Deck/services/claude_runner.py`

**Step 1: `claude_runner.py` 작성**

Discord Bot에서 Claude CLI를 subprocess로 호출하는 래퍼.

```python
import asyncio
import json
import os
import logging

logger = logging.getLogger(__name__)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")


async def run_meeting2deck(pdf_path: str) -> dict:
    """Claude CLI를 호출하여 Meeting2Deck 워크플로우를 실행한다.

    Args:
        pdf_path: 분석할 PDF 파일 경로

    Returns:
        result.json 내용을 dict로 반환. 실패 시 error 키 포함.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 기존 output 파일 정리
    for f in ["slides.json", "notion_summary.md", "email_draft.md", "result.json"]:
        fpath = os.path.join(OUTPUT_DIR, f)
        if os.path.exists(fpath):
            os.remove(fpath)

    prompt = f"""다음 PDF 파일을 분석하여 Meeting2Deck 워크플로우를 실행하세요.

PDF 파일 경로: {pdf_path}

CLAUDE.md에 정의된 7단계 워크플로우를 순서대로 수행하세요.
모든 출력 파일은 output/ 디렉토리에 저장하세요.
마지막에 반드시 output/result.json을 작성하세요."""

    cmd = [
        "claude",
        "--print",
        "--dangerously-skip-permissions",
        "-p", prompt,
        pdf_path,
    ]

    logger.info(f"Claude CLI 실행: {' '.join(cmd[:4])}...")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=PROJECT_DIR,
    )

    stdout, stderr = await asyncio.wait_for(
        process.communicate(),
        timeout=300,  # 5분 타임아웃
    )

    if process.returncode != 0:
        error_msg = stderr.decode("utf-8", errors="replace")
        logger.error(f"Claude CLI 실패: {error_msg}")
        return {"status": "error", "error": error_msg}

    # result.json 읽기
    result_path = os.path.join(OUTPUT_DIR, "result.json")
    if os.path.exists(result_path):
        with open(result_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # result.json이 없으면 출력 파일 존재 여부로 결과 구성
    result = {"status": "completed", "errors": []}
    for key, filename in [
        ("slides_json_path", "slides.json"),
        ("notion_md_path", "notion_summary.md"),
        ("email_draft_path", "email_draft.md"),
    ]:
        fpath = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(fpath):
            result[key] = fpath
        else:
            result["errors"].append(f"{filename} not generated")

    return result
```

**Step 2: Commit**

```bash
git add services/claude_runner.py
git commit -m "feat: add Claude CLI subprocess runner service"
```

---

## Task 6: Discord Bot 구현

**Files:**
- Create: `027_Meeting2Deck/main.py`
- Create: `027_Meeting2Deck/cogs/__init__.py`
- Create: `027_Meeting2Deck/cogs/meeting2deck_bot.py`

**Step 1: `main.py` 작성**

```python
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    logging.info(f"Meeting2Deck Bot 로그인: {bot.user}")
    await bot.load_extension("cogs.meeting2deck_bot")
    logging.info("meeting2deck_bot cog 로드 완료")


bot.run(os.getenv("DISCORD_TOKEN"))
```

**Step 2: `cogs/__init__.py` 생성**

```python
```

빈 파일.

**Step 3: `cogs/meeting2deck_bot.py` 작성**

```python
import os
import json
import aiohttp
import discord
from discord.ext import commands
from datetime import datetime
import logging

from services.claude_runner import run_meeting2deck

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
MAKECOM_WEBHOOK_URL = os.getenv("MAKECOM_WEBHOOK_URL", "")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "")
ALLOWED_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))


class Meeting2DeckBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if ALLOWED_CHANNEL_ID and message.channel.id != ALLOWED_CHANNEL_ID:
            return

        pdf_attachments = [a for a in message.attachments if a.filename.lower().endswith(".pdf")]
        if not pdf_attachments:
            return

        attachment = pdf_attachments[0]
        await message.reply(f"PDF 수신 완료: `{attachment.filename}`\nMeeting2Deck 처리를 시작합니다...")

        # PDF 다운로드
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(OUTPUT_DIR, f"{timestamp}_{attachment.filename}")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        await attachment.save(pdf_path)
        logger.info(f"PDF 저장: {pdf_path}")

        # Claude CLI 실행
        await message.channel.send("Claude Agent가 분석 중입니다... (최대 5분 소요)")
        result = await run_meeting2deck(pdf_path)

        if result.get("status") == "error":
            await message.reply(f"처리 실패: {result.get('error', 'Unknown error')}")
            return

        # 결과 메시지 구성
        response_parts = ["**Meeting2Deck 처리 완료**\n"]

        slides_url = result.get("slides_url")
        if slides_url:
            response_parts.append(f"Google Slides: {slides_url}")
        else:
            response_parts.append("Google Slides: JSON 파일로 저장됨 (MCP 연동 실패)")

        notion_url = result.get("notion_url")
        if notion_url:
            response_parts.append(f"Notion: {notion_url}")
        else:
            response_parts.append("Notion: MD 파일로 저장됨 (MCP 연동 실패)")

        # Make.com 웹훅 호출 (이메일 발송)
        email_sent = await self._send_email_webhook(result)
        if email_sent:
            response_parts.append(f"이메일: {EMAIL_RECIPIENT}에게 발송 완료")
        else:
            response_parts.append("이메일: 초안 파일로 저장됨 (웹훅 호출 실패)")

        if result.get("errors"):
            response_parts.append(f"\n경고: {', '.join(result['errors'])}")

        await message.reply("\n".join(response_parts))

        # 노션 요약을 디스코드에도 첨부
        notion_md_path = result.get("notion_md_path", os.path.join(OUTPUT_DIR, "notion_summary.md"))
        if os.path.exists(notion_md_path):
            await message.channel.send(
                "**노션 요약:**",
                file=discord.File(notion_md_path, filename="meeting_summary.md"),
            )

    async def _send_email_webhook(self, result: dict) -> bool:
        if not MAKECOM_WEBHOOK_URL:
            logger.warning("MAKECOM_WEBHOOK_URL이 설정되지 않음")
            return False

        email_draft_path = result.get("email_draft_path", os.path.join(OUTPUT_DIR, "email_draft.md"))
        if not os.path.exists(email_draft_path):
            logger.warning("email_draft.md 파일이 없음")
            return False

        with open(email_draft_path, "r", encoding="utf-8") as f:
            email_content = f.read()

        # 제목 추출 (첫 번째 줄이 제목이라고 가정)
        lines = email_content.strip().split("\n")
        subject = lines[0].replace("# ", "").replace("## ", "").strip() if lines else "Meeting Summary"
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else email_content

        payload = {
            "to": EMAIL_RECIPIENT,
            "subject": subject,
            "body": body,
            "slides_url": result.get("slides_url", ""),
            "notion_url": result.get("notion_url", ""),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(MAKECOM_WEBHOOK_URL, json=payload) as resp:
                    if resp.status == 200:
                        logger.info("Make.com 웹훅 호출 성공")
                        return True
                    else:
                        logger.error(f"Make.com 웹훅 실패: {resp.status}")
                        return False
        except Exception as e:
            logger.error(f"Make.com 웹훅 에러: {e}")
            return False


async def setup(bot):
    await bot.add_cog(Meeting2DeckBot(bot))
```

**Step 4: Commit**

```bash
git add main.py cogs/
git commit -m "feat: add Discord bot with PDF listener and result delivery"
```

---

## Task 7: 통합 테스트용 샘플 & 수동 검증

**Files:**
- Create: `027_Meeting2Deck/scripts/test_slides_mcp.py`
- Create: `027_Meeting2Deck/scripts/test_claude_runner.py`

**Step 1: `scripts/test_slides_mcp.py` 작성**

Google Slides MCP 서버가 단독으로 동작하는지 확인하는 스크립트.

```python
"""Google Slides MCP 서버 수동 테스트.
실행: python scripts/test_slides_mcp.py
필요: GOOGLE_SERVICE_ACCOUNT_JSON 환경변수 설정"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from services.slides_mcp_server import get_slides_service


async def main():
    print("=== Google Slides MCP 테스트 ===")

    # 1. 서비스 연결 테스트
    try:
        service = get_slides_service()
        print("[PASS] Google Slides API 연결 성공")
    except Exception as e:
        print(f"[FAIL] Google Slides API 연결 실패: {e}")
        return

    # 2. 프레젠테이션 생성 테스트
    try:
        body = {"title": "Meeting2Deck Test"}
        pres = service.presentations().create(body=body).execute()
        pid = pres["presentationId"]
        print(f"[PASS] 프레젠테이션 생성: https://docs.google.com/presentation/d/{pid}/edit")
    except Exception as e:
        print(f"[FAIL] 프레젠테이션 생성 실패: {e}")
        return

    print("\n테스트 완료. 위 URL에서 슬라이드를 확인하세요.")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: `scripts/test_claude_runner.py` 작성**

Claude CLI runner를 단독 테스트하는 스크립트.

```python
"""Claude Runner 수동 테스트.
실행: python scripts/test_claude_runner.py <pdf_path>"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from services.claude_runner import run_meeting2deck


async def main():
    if len(sys.argv) < 2:
        print("사용법: python scripts/test_claude_runner.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"파일을 찾을 수 없습니다: {pdf_path}")
        sys.exit(1)

    print(f"PDF 분석 시작: {pdf_path}")
    print("Claude CLI 실행 중... (최대 5분)")

    result = await run_meeting2deck(pdf_path)
    print(f"\n결과:\n{json.dumps(result, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 3: Commit**

```bash
git add scripts/
git commit -m "feat: add manual test scripts for Slides MCP and Claude runner"
```

---

## Task 8: 환경 설정 가이드 & README

**Files:**
- Create: `027_Meeting2Deck/README.md`

**Step 1: README.md 작성**

```markdown
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
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup instructions"
```

---

## 구현 순서 요약

| Task | 내용 | 예상 시간 |
|------|------|----------|
| 1 | 프로젝트 초기 설정 | 5분 |
| 2 | CLAUDE.md 마스터 프롬프트 | 5분 |
| 3 | Google Slides MCP Server | 15분 |
| 4 | MCP 설정 파일 | 5분 |
| 5 | Claude CLI Runner Service | 10분 |
| 6 | Discord Bot 구현 | 15분 |
| 7 | 테스트 스크립트 | 10분 |
| 8 | README | 5분 |
