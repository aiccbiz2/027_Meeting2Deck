import json
import os
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PATH = os.path.join(PROJECT_DIR, "token.json")
SCOPES = ["https://www.googleapis.com/auth/presentations", "https://www.googleapis.com/auth/drive"]


def _get_credentials():
    if not os.path.exists(TOKEN_PATH):
        logger.error(f"token.json not found: {TOKEN_PATH}")
        return None
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def upload_pptx_to_drive(pptx_path: str, title: str = "Meeting2Deck") -> dict:
    """PPTX 파일을 Google Drive에 업로드하고 Google Slides로 변환한다.

    Args:
        pptx_path: 업로드할 .pptx 파일 경로
        title: Google Slides 제목

    Returns:
        {"slides_url": "https://...", "file_id": "..."} 또는 {"error": "..."}
    """
    creds = _get_credentials()
    if not creds:
        return {"error": "Google OAuth2 인증 없음. scripts/auth_setup.py를 먼저 실행하세요."}

    if not os.path.exists(pptx_path):
        return {"error": f"PPTX 파일 없음: {pptx_path}"}

    try:
        drive = build("drive", "v3", credentials=creds)

        file_metadata = {
            "name": title,
            "mimeType": "application/vnd.google-apps.presentation",
        }
        media = MediaFileUpload(
            pptx_path,
            mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            resumable=True,
        )

        file = drive.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,webViewLink",
        ).execute()

        file_id = file.get("id")
        web_link = file.get("webViewLink", f"https://docs.google.com/presentation/d/{file_id}/edit")

        # 링크 공유 설정 (링크가 있는 사람은 누구나 볼 수 있음)
        drive.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        logger.info(f"Drive 업로드 성공: {web_link}")
        return {"slides_url": web_link, "file_id": file_id}

    except Exception as e:
        logger.error(f"Drive 업로드 실패: {e}")
        return {"error": str(e)}
