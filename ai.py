import logging
import httpx
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

ARABIC_INSTRUCTION = (
    "مهم جداً: يجب أن يكون ردك بالكامل باللغة العربية الفصحى السليمة "
    "نحوياً وإملائياً، بأسلوب واضح وطبيعي ومهذب. لا تستخدم أي كلمات إنجليزية "
    "إلا إذا كانت أسماء أو مصطلحات لا بديل عربي لها. "
)


async def _call_gemini(system_prompt: str, user_message: str) -> str:
    full_prompt = f"{ARABIC_INSTRUCTION}\n\n{system_prompt}\n\nنص العميل:\n{user_message}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={
                "contents": [
                    {"parts": [{"text": full_prompt}]}
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 500,
                },
            },
        )
        data = resp.json()

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            logger.error(f"❌ Gemini API error response: {data}")
            raise RuntimeError(f"Gemini API error: {data.get('error', data)}")


async def summarize_details(raw_text: str) -> str:
    """يحول كلام العميل الحر لملخص منظم بالعربي"""
    system_prompt = (
        "أنت مساعد يقوم بتلخيص طلب تسجيل عميل بشكل منظم وواضح. "
        "اقرأ نص العميل واستخرج التفاصيل المهمة فقط في نقاط مختصرة وواضحة. "
        "لا تضف أي معلومة غير موجودة في النص الأصلي. "
        "أعد فقط الملخص بدون أي مقدمات أو تعليقات إضافية."
    )
    return await _call_gemini(system_prompt, raw_text)


async def is_affirmative(user_message: str) -> bool:
    """يحدد هل رد العميل موافقة (أيوه/تمام) ولا فيه تعديل/رفض"""
    system_prompt = (
        "حدد هل رسالة العميل التالية تعني الموافقة الصريحة "
        "(مثل: أيوه، تمام، صح، موافق، اه) أم لا (فيها تعديل أو رفض أو استفسار). "
        "أجب بكلمة واحدة فقط بدون أي شرح: YES أو NO."
    )
    result = await _call_gemini(system_prompt, user_message)
    return "YES" in result.upper()


async def apply_modification(previous_summary: str, modification_text: str) -> str:
    """يدمج التعديل المطلوب من العميل مع الملخص السابق"""
    system_prompt = (
        "لديك ملخص تسجيل سابق وتعديل مطلوب من العميل عليه. "
        "ادمج التعديل مع الملخص القديم وأعد ملخصاً جديداً نهائياً منظماً وواضحاً. "
        "أعد فقط الملخص الجديد بدون أي مقدمات أو شرح.\n\n"
        f"الملخص السابق:\n{previous_summary}\n\nالتعديل المطلوب من العميل:"
    )
    return await _call_gemini(system_prompt, modification_text)
