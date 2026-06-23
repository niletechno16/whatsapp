import asyncio
import random
import httpx
from config import WHATSAPP_TOKEN, PHONE_NUMBER_ID

GRAPH_URL = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
HEADERS = {
    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    "Content-Type": "application/json; charset=utf-8",
}


async def mark_as_read_and_type(message_id: str):
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
        "typing_indicator": {"type": "text"},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            await client.post(GRAPH_URL, headers=HEADERS, json=payload)
        except Exception:
            pass


async def send_whatsapp_message(to_phone: str, message: str, message_id: str = None):
    if message_id:
        await mark_as_read_and_type(message_id)

    await asyncio.sleep(random.uniform(2, 4))

    # تأكد إن الرسالة encoded صح
    clean_message = message.encode("utf-8").decode("utf-8")

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": clean_message},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(GRAPH_URL, headers=HEADERS, json=payload)
        return resp.json()
