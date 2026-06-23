import logging
import httpx
from config import GROQ_API_KEY, CEREBRAS_API_KEY

logger = logging.getLogger(__name__)

ARABIC_INSTRUCTION = (
    "مهم جداً: يجب أن يكون ردك بالكامل باللغة العربية الفصحى السليمة "
    "نحوياً وإملائياً، بأسلوب واضح وطبيعي ومهذب. لا تستخدم أي كلمات إنجليزية "
    "إلا إذا كانت أسماء أو مصطلحات لا بديل عربي لها. "
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"


async def _call_openai_compatible(url: str, api_key: str, model: str, system_prompt: str, user_message: str) -> str:
    """استدعاء أي API متوافق مع OpenAI format"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": f"{ARABIC_INSTRUCTION}\n\n{system_prompt}"},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.3,
                "max_tokens": 500,
            },
        )
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError):
            raise RuntimeError(f"API error: {data.get('error', data)}")


async def _call_ai(system_prompt: str, user_message: str) -> str:
    """يجرب Groq الأول، لو فشل يجرب Cerebras"""

    # المحاولة الأولى: Groq
    if GROQ_API_KEY:
        try:
            result = await _call_openai_compatible(
                url=GROQ_URL,
                api_key=GROQ_API_KEY,
                model="llama-3.3-70b-versatile",
                system_prompt=system_prompt,
                user_message=user_message,
            )
            logger.info("✅ AI response via Groq")
            return result
        except Exception as e:
            logger.warning(f"⚠️ Groq failed: {e} — trying Cerebras...")

    # المحاولة الثانية: Cerebras
    if CEREBRAS_API_KEY:
        try:
            result = await _call_openai_compatible(
                url=CEREBRAS_URL,
                api_key=CEREBRAS_API_KEY,
                model="llama-3.3-70b",
                system_prompt=system_prompt,
                user_message=user_message,
            )
            logger.info("✅ AI response via Cerebras")
            return result
        except Exception as e:
            logger.error(f"❌ Cerebras also failed: {e}")

    raise RuntimeError("كل الـ AI providers فشلوا، حاول تاني بعد شوية.")


async def summarize_details(raw_text: str) -> str:
    """يحول كلام العميل الحر لملخص منظم بالعربي"""
    system_prompt = (
        "أنت مساعد يقوم بتلخيص طلب تسجيل عميل بشكل منظم وواضح. "
        "اقرأ نص العميل واستخرج التفاصيل المهمة فقط في نقاط مختصرة وواضحة. "
        "لا تضف أي معلومة غير موجودة في النص الأصلي. "
        "أعد فقط الملخص بدون أي مقدمات أو تعليقات إضافية."
    )
    return await _call_ai(system_prompt, raw_text)


async def is_affirmative(user_message: str) -> bool:
    """يحدد هل رد العميل موافقة (أيوه/تمام) ولا فيه تعديل/رفض"""
    system_prompt = (
        "حدد هل رسالة العميل التالية تعني الموافقة الصريحة "
        "(مثل: أيوه، تمام، صح، موافق، اه) أم لا (فيها تعديل أو رفض أو استفسار). "
        "أجب بكلمة واحدة فقط بدون أي شرح: YES أو NO."
    )
    result = await _call_ai(system_prompt, user_message)
    return "YES" in result.upper()


async def apply_modification(previous_summary: str, modification_text: str) -> str:
    """يدمج التعديل المطلوب من العميل مع الملخص السابق"""
    system_prompt = (
        "لديك ملخص تسجيل سابق وتعديل مطلوب من العميل عليه. "
        "ادمج التعديل مع الملخص القديم وأعد ملخصاً جديداً نهائياً منظماً وواضحاً. "
        "أعد فقط الملخص الجديد بدون أي مقدمات أو شرح.\n\n"
        f"الملخص السابق:\n{previous_summary}\n\nالتعديل المطلوب من العميل:"
    )
    return await _call_ai(system_prompt, modification_text)
