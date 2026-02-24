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
