import asyncio
import random
import httpx
from config import WHATSAPP_TOKEN, PHONE_NUMBER_ID

GRAPH_URL = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
HEADERS = {
    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    "Content-Type": "application/json",
}


async def mark_as_read_and_type(message_id: str):
    """يعلّم الرسالة كمقروءة ويظهر مؤشر 'يكتب الآن' في واتساب"""
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
            pass  # لو فشل التايبنج، نكمل عادي من غيره


async def send_whatsapp_message(to_phone: str, message: str, message_id: str = None):
    """
    يبعت رسالة بعد تأخير بسيط عشوائي (2-4 ثواني) مع إظهار 'يكتب الآن'
    عشان يحس واتساب إن في إنسان بيرد مش بوت.
    """
    if message_id:
        await mark_as_read_and_type(message_id)

    # تأخير عشوائي يحاكي وقت الكتابة الطبيعي
    await asyncio.sleep(random.uniform(2, 4))

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": message},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(GRAPH_URL, headers=HEADERS, json=payload)
        return resp.json()
