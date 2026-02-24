import os
import json
import aiohttp
import discord
from discord.ext import commands
from datetime import datetime
import logging

from services.claude_runner import run_meeting2deck
from services.drive_uploader import upload_pptx_to_drive

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
        await message.channel.send("Claude Agent가 분석 중입니다... (최대 10분 소요)")
        result = await run_meeting2deck(pdf_path)

        if result.get("status") == "error":
            await message.reply(f"처리 실패: {result.get('error', 'Unknown error')}")
            return

        # 결과 메시지 구성
        response_parts = ["**Meeting2Deck 처리 완료**\n"]

        # PPTX → Google Drive 업로드
        slides_url = result.get("slides_url")
        pptx_path = os.path.join(OUTPUT_DIR, "slides.pptx")
        if not slides_url and os.path.exists(pptx_path):
            await message.channel.send("PPTX를 Google Drive에 업로드 중...")
            upload_result = upload_pptx_to_drive(pptx_path, title=f"Meeting2Deck {datetime.now().strftime('%Y-%m-%d')}")
            if upload_result.get("slides_url"):
                slides_url = upload_result["slides_url"]
                result["slides_url"] = slides_url

        if slides_url:
            response_parts.append(f"Google Slides: {slides_url}")
        else:
            response_parts.append("Google Slides: PPTX 파일로 저장됨 (Drive 업로드 실패)")

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
