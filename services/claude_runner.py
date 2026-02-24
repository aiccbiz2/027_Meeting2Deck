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
    for f in ["slides.pptx", "notion_summary.md", "email_draft.md", "result.json"]:
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

    # CLAUDECODE 환경변수 제거 (중첩 세션 감지 우회)
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=PROJECT_DIR,
        env=env,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=600,  # 10분 타임아웃
        )
    except asyncio.TimeoutError:
        logger.error("Claude CLI 타임아웃 (10분 초과)")
        process.kill()
        await process.wait()
        # 타임아웃이어도 이미 생성된 파일이 있으면 부분 결과 반환
        result = {"status": "partial", "errors": ["Claude CLI 타임아웃 (10분 초과)"]}
        for key, filename in [
            ("slides_pptx_path", "slides.pptx"),
            ("notion_md_path", "notion_summary.md"),
            ("email_draft_path", "email_draft.md"),
        ]:
            fpath = os.path.join(OUTPUT_DIR, filename)
            if os.path.exists(fpath):
                result[key] = fpath
        return result

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
        ("slides_pptx_path", "slides.pptx"),
        ("notion_md_path", "notion_summary.md"),
        ("email_draft_path", "email_draft.md"),
    ]:
        fpath = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(fpath):
            result[key] = fpath
        else:
            result["errors"].append(f"{filename} not generated")

    return result
