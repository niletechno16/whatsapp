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

MAX_HISTORY = 20  # أقصى عدد رسايل نبعتهم للـ AI (10 رسالة من كل طرف)


async def _call_openai_compatible(url: str, api_key: str, model: str, messages: list) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 500,
            },
        )
        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"].strip()
            return text.encode("utf-8").decode("utf-8")
        except (KeyError, IndexError):
            raise RuntimeError(f"API error: {data.get('error', data)}")


async def _call_ai(system_prompt: str, user_message: str, history: list = None) -> str:
    """يبني الـ messages list مع الـ history ويبعتها للـ AI"""
    messages = [{"role": "system", "content": f"{ARABIC_INSTRUCTION}\n\n{system_prompt}"}]

    # أضف الـ history (آخر MAX_HISTORY رسالة بس عشان منعداش الـ tokens)
    if history:
        messages += history[-MAX_HISTORY:]

    messages.append({"role": "user", "content": user_message})

    if GROQ_API_KEY:
        try:
            result = await _call_openai_compatible(GROQ_URL, GROQ_API_KEY, "llama-3.3-70b-versatile", messages)
            logger.info("✅ AI response via Groq")
            return result
        except Exception as e:
            logger.warning(f"⚠️ Groq failed: {e} — trying Cerebras...")

    if CEREBRAS_API_KEY:
        try:
            result = await _call_openai_compatible(CEREBRAS_URL, CEREBRAS_API_KEY, "llama-3.3-70b", messages)
            logger.info("✅ AI response via Cerebras")
            return result
        except Exception as e:
            logger.error(f"❌ Cerebras also failed: {e}")

    raise RuntimeError("عذراً، في مشكلة مؤقتة. حاول تاني بعد شوية.")


async def chat_response(user_message: str, history: list = None, context: str = "") -> str:
    system_prompt = (
        "أنت مساعد واتساب بشري ودود. رد بشكل طبيعي وقصير على رسالة المستخدم. "
        "لو المستخدم بيطلب تسجيل أي بيانات، قوله إنه محتاج الباسورد الأول. "
        f"{context}"
    )
    return await _call_ai(system_prompt, user_message, history)


async def summarize_details(raw_text: str, history: list = None) -> str:
    system_prompt = (
        "لخّص طلب التسجيل ده في نقاط واضحة ومنظمة. "
        "استخرج التفاصيل المهمة بس. لا تضيف أي معلومة مش موجودة في النص. "
        "أعد الملخص بس بدون أي مقدمات."
    )
    return await _call_ai(system_prompt, raw_text, history)


async def is_affirmative(user_message: str) -> bool:
    system_prompt = (
        "مهمتك تحديد هل رسالة المستخدم موافقة أم لا.\n"
        "الموافقة تشمل: أيوه، اه، يعم، ايوا، ايوه، اهه، تمام، صح، موافق، أكيد، ماشي، يلا، سجل، اتفضل، عظيم، كويس، اوكي، ok، yes.\n"
        "الرفض أو التعديل يشمل: لا، مش كده، غلط، عدّل، بدّل، فيه خطأ، مش صح، تاني، غيّر.\n"
        "أجب بكلمة واحدة فقط بدون أي شرح: YES أو NO."
    )
    result = await _call_ai(system_prompt, user_message)
    return "YES" in result.upper()


async def check_has_modification(user_message: str) -> bool:
    system_prompt = (
        "هل رسالة المستخدم فيها طلب تعديل حقيقي على بيانات معينة؟ "
        "يعني بيطلب تغيير أو إضافة أو حذف معلومة محددة؟\n"
        "لو قال 'مفيش تعديل' أو 'مش عايز تعديل' أو أي كلام مش فيه تعديل حقيقي: NO.\n"
        "أجب بكلمة واحدة فقط: YES أو NO."
    )
    result = await _call_ai(system_prompt, user_message)
    return "YES" in result.upper()


async def apply_modification(previous_summary: str, modification_text: str, history: list = None) -> str:
    system_prompt = (
        "عندك ملخص تسجيل سابق وتعديل مطلوب من المستخدم. "
        "ادمج التعديل مع الملخص القديم وأعد ملخصاً جديداً نهائياً منظماً. "
        "أعد الملخص الجديد بس بدون أي مقدمات.\n\n"
        f"الملخص السابق:\n{previous_summary}\n\nالتعديل:"
    )
    return await _call_ai(system_prompt, modification_text, history)
