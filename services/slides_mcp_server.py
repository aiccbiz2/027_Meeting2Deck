import json
import os
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/presentations", "https://www.googleapis.com/auth/drive"]

server = Server("google-slides-mcp")

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _get_credentials():
    token_path = os.path.join(PROJECT_DIR, "token.json")
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds

def get_slides_service():
    return build("slides", "v1", credentials=_get_credentials())

def get_drive_service():
    return build("drive", "v3", credentials=_get_credentials())


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
