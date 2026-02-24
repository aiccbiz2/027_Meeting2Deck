"""Google OAuth2 인증 설정.
실행: python3.13 scripts/auth_setup.py
한 번만 실행하면 token.json이 생성되어 이후 자동 인증됩니다."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import json

SCOPES = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive",
]

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PATH = os.path.join(PROJECT_DIR, "token.json")
CREDS_PATH = os.path.join(PROJECT_DIR, "credentials.json")


def main():
    # credentials.json을 OAuth2 클라이언트 형식으로 변환 필요
    # Service Account JSON이 아닌 OAuth2 Client ID가 필요
    oauth_creds_path = os.path.join(PROJECT_DIR, "oauth_credentials.json")

    if not os.path.exists(oauth_creds_path):
        print("=" * 60)
        print("OAuth2 Client ID가 필요합니다.")
        print()
        print("Google Cloud Console에서 생성해주세요:")
        print("1. APIs & Services → Credentials")
        print("2. + CREATE CREDENTIALS → OAuth client ID")
        print("3. Application type: Desktop app")
        print("4. Name: Meeting2Deck")
        print("5. CREATE → JSON 다운로드")
        print(f"6. 파일을 {oauth_creds_path} 로 저장")
        print("=" * 60)
        return

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(oauth_creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        print(f"토큰 저장 완료: {TOKEN_PATH}")

    print("인증 성공! 이제 Google Slides를 생성할 수 있습니다.")


if __name__ == "__main__":
    main()
