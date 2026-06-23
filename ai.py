import logging
import httpx
from config import GROQ_API_KEY, CEREBRAS_API_KEY

logger = logging.getLogger(__name__)

ARABIC_INSTRUCTION = (
    "أنت مساعد واتساب ذكي ودود. يجب أن يكون ردك بالكامل باللغة العربية "
    "بأسلوب طبيعي ومحادثاتي. لا تستخدم أي كلمات إنجليزية أو أحرف لاتينية إطلاقاً. "
    "ردودك قصيرة وطبيعية مثل المحادثات اليومية. "
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"


async def _call_openai_compatible(url: str, api_key: str, model: str, system_prompt: str, user_message: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json; charset=utf-8",
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
            text = data["choices"][0]["message"]["content"].strip()
            # تأكد إن النص عربي صح
            return text.encode("utf-8").decode("utf-8")
        except (KeyError, IndexError):
            raise RuntimeError(f"API error: {data.get('error', data)}")


async def _call_ai(system_prompt: str, user_message: str) -> str:
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

    raise RuntimeError("عذراً، في مشكلة مؤقتة. حاول تاني بعد شوية.")


async def chat_response(user_message: str, context: str = "") -> str:
    """رد محادثة طبيعي وتفاعلي"""
    system_prompt = (
        "أنت مساعد واتساب بشري ودود. رد بشكل طبيعي وقصير على رسالة المستخدم. "
        "لو المستخدم بيسأل عن حاجة أو بيتكلم بشكل عام، رد عليه بشكل طبيعي. "
        "لو حس إن المستخدم عايز يسجل بيانات أو طلب حاجة محتاج يسجلها، "
        "قوله إنه محتاج الباسورد الأول عشان يقدر يسجل. "
        f"{context}"
    )
    return await _call_ai(system_prompt, user_message)


async def summarize_details(raw_text: str) -> str:
    system_prompt = (
        "لخّص طلب التسجيل ده في نقاط واضحة ومنظمة. "
        "استخرج التفاصيل المهمة بس. لا تضيف أي معلومة مش موجودة في النص. "
        "أعد الملخص بس بدون أي مقدمات."
    )
    return await _call_ai(system_prompt, raw_text)


async def is_affirmative(user_message: str) -> bool:
    system_prompt = (
        "هل رسالة المستخدم دي موافقة صريحة (أيوه، تمام، صح، موافق، اه، أكيد) "
        "ولا فيها تعديل أو رفض أو سؤال؟ "
        "أجب بكلمة واحدة فقط: YES أو NO."
    )
    result = await _call_ai(system_prompt, user_message)
    return "YES" in result.upper()


async def apply_modification(previous_summary: str, modification_text: str) -> str:
    system_prompt = (
        "عندك ملخص تسجيل سابق وتعديل مطلوب من المستخدم. "
        "ادمج التعديل مع الملخص القديم وأعد ملخصاً جديداً نهائياً منظماً. "
        "أعد الملخص الجديد بس بدون أي مقدمات.\n\n"
        f"الملخص السابق:\n{previous_summary}\n\nالتعديل:"
    )
    return await _call_ai(system_prompt, modification_text)
