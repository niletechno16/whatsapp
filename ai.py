import httpx
import json
from config import GROQ_API_KEY

GROQ_URL = ""


async def _call_groq(system_prompt: str, user_message: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 400,
                "temperature": 0.3,
            },
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


async def summarize_details(raw_text: str) -> str:
    """يحول كلام العميل الحر لملخص منظم بالعربي"""
    system_prompt = (
        "أنت مساعد يقوم بتلخيص طلب تسجيل عميل بشكل منظم وواضح بالعربية. "
        "اقرأ النص التالي واستخرج التفاصيل المهمة فقط في نقاط مختصرة وواضحة. "
        "لا تضف أي معلومة غير موجودة في النص. أعد فقط الملخص بدون مقدمات."
    )
    return await _call_groq(system_prompt, raw_text)


async def is_affirmative(user_message: str) -> bool:
    """يحدد هل رد العميل موافقة (أيوه/تمام) ولا فيه تعديل/رفض"""
    system_prompt = (
        "حدد هل الرسالة التالية من العميل تعني الموافقة الصريحة (مثل: أيوه، تمام، صح، اه، موافق) "
        "أم لا (فيها تعديل أو رفض أو استفسار). "
        "أجب بكلمة واحدة فقط: YES أو NO."
    )
    result = await _call_groq(system_prompt, user_message)
    return "YES" in result.upper()


async def apply_modification(previous_summary: str, modification_text: str) -> str:
    """يدمج التعديل المطلوب من العميل مع الملخص السابق"""
    system_prompt = (
        "لديك ملخص تسجيل سابق وتعديل مطلوب من العميل عليه. "
        "ادمج التعديل مع الملخص القديم وأعد ملخصاً جديداً نهائياً منظماً بالعربية. "
        "أعد فقط الملخص الجديد بدون مقدمات أو شرح.\n\n"
        f"الملخص السابق:\n{previous_summary}"
    )
    return await _call_groq(system_prompt, modification_text)
