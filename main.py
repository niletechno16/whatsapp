import os
import logging
from fastapi import FastAPI, Request, Query, HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "test123")

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "running"}


@app.get("/webhook")
async def verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("✅ Webhook verified")
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Invalid verify token")


@app.post("/webhook")
async def receive(request: Request):
    body = await request.json()
    logger.info(f"📩 RAW BODY: {body}")

    try:
        msg = body["entry"][0]["changes"][0]["value"]["messages"][0]
        phone = msg["from"]
        text = msg["text"]["body"]
        logger.info(f"✅ FROM: {phone} | MESSAGE: {text}")
    except Exception as e:
        logger.warning(f"⚠️ Could not parse message: {e}")

    return {"status": "ok"}
