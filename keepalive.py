import os
import threading
import time
import logging
import httpx

logger = logging.getLogger(__name__)

# Fly.io: حط URL التطبيق يدوياً في متغير APP_URL
# مثال: https://whatsapp-bot.fly.dev
APP_URL = os.getenv("APP_URL", "")
PING_INTERVAL_SECONDS = 10 * 60  # كل 10 دقايق


def _keep_alive_loop():
    if not APP_URL:
        logger.warning("⚠️ APP_URL غير موجود - keep-alive متوقف")
        return

    while True:
        time.sleep(PING_INTERVAL_SECONDS)
        try:
            httpx.get(f"{APP_URL}/", timeout=10)
            logger.info("💓 Keep-alive ping sent")
        except Exception as e:
            logger.warning(f"⚠️ Keep-alive ping failed: {e}")


def start_keep_alive():
    """يشغل thread في الخلفية يبعت ping للسيرفر عشان الماشين ميوقفش"""
    thread = threading.Thread(target=_keep_alive_loop, daemon=True)
    thread.start()
    logger.info("✅ Keep-alive thread started")
