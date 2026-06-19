import os
import threading
import time
import logging
import httpx

logger = logging.getLogger(__name__)

# Render بيديك الـ URL بتاع السيرفر تلقائياً في المتغير ده
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")
PING_INTERVAL_SECONDS = 10 * 60  # كل 10 دقايق (قبل الـ 15 دقيقة بتاعة Render free tier)


def _keep_alive_loop():
    if not RENDER_URL:
        logger.warning("⚠️ RENDER_EXTERNAL_URL غير موجود - keep-alive متوقف")
        return

    while True:
        time.sleep(PING_INTERVAL_SECONDS)
        try:
            httpx.get(RENDER_URL, timeout=10)
            logger.info("💓 Keep-alive ping sent")
        except Exception as e:
            logger.warning(f"⚠️ Keep-alive ping failed: {e}")


def start_keep_alive():
    """يشغل thread في الخلفية يبعت ping للسيرفر نفسه عشان Render ميقفلوش"""
    thread = threading.Thread(target=_keep_alive_loop, daemon=True)
    thread.start()
    logger.info("✅ Keep-alive thread started")
