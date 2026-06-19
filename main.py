import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Query, HTTPException

from config import VERIFY_TOKEN
from database import setup_tables, save_message
from conversation import handle_message
from whatsapp import send_whatsapp_message
from keepalive import start_keep_alive

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        setup_tables()
        logger.info("✅ Database tables ready")
    except Exception as e:
        logger.error(f"❌ DB setup error: {e}")

    start_keep_alive()
    yield


app = FastAPI(title="WhatsApp Registration Bot", lifespan=lifespan)


@app.get("/")
async def health():
    return {"status": "WhatsApp Bot is running 🤖"}


# ─── Webhook Verification ──────────────────────────────────────────────────
@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("✅ Webhook verified")
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Invalid verify token")


# ─── Receive & Process Messages ─────────────────────────────────────────────
@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()

    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return {"status": "ignored"}

        msg = value["messages"][0]
        phone = msg["from"]
        message_id = msg.get("id")
        msg_type = msg.get("type", "")

        if msg_type != "text":
            await send_whatsapp_message(phone, "من فضلك ابعت رسالة نصية فقط 🙏", message_id)
            return {"status": "non-text handled"}

        text = msg["text"]["body"]
        logger.info(f"📩 From {phone}: {text}")

        # 1) حفظ الرسالة الخام في اللوج
        save_message(phone, text)

        # 2) تشغيل الـ conversation flow
        reply = await handle_message(phone, text)

        # 3) إرسال الرد (مع typing indicator وتأخير طبيعي)
        await send_whatsapp_message(phone, reply, message_id)

        logger.info(f"✅ Replied to {phone}: {reply[:80]}")
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"❌ Error processing message: {e}")
        return {"status": "error", "detail": str(e)}
