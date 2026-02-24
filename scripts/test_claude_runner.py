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
