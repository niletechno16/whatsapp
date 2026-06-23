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


async def wants_to_register(user_message: str, history: list = None) -> bool:
    """
    بيحدد بس هل المستخدم بيطلب تسجيل بيانات عميل صيانة أم لا.
    مفيش رد حر للبوت في أي سياق تاني، البوت مخصص للتسجيل بس.
    """
    system_prompt = (
        "مهمتك الوحيدة إنك تحدد هل المستخدم بيطلب تسجيل بيانات عميل صيانة أم لا.\n"
        "لو طلب تسجيل بيانات عميل (اسم، ID، تواريخ تعاقد أو صيانة) أو قال كلام زي "
        "'عايز أسجل'، 'سجل لي'، 'تسجيل عميل': أجب بكلمة REGISTER بس.\n"
        "غير كده (أي سؤال أو طلب أو كلام عادي مش متعلق بتسجيل بيانات عميل): "
        "أجب بكلمة OTHER بس.\n"
        "أجب بكلمة واحدة فقط بدون أي شرح."
    )
    result = await _call_ai(system_prompt, user_message, history)
    return "REGISTER" in result.upper()


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


# ================================================================
# استخراج بيانات التسجيل المنظمة من كلام العميل الحر
# ================================================================
EXTRACTION_SYSTEM_PROMPT = (
    "أنت تستخرج بيانات تسجيل عميل صيانة من كلام المستخدم (والمحادثة السابقة لو موجودة). "
    "المطلوب 5 حقول بس:\n"
    "1) اسم العميل\n"
    "2) ID العميل (رقم أو كود تعريفي للعميل)\n"
    "3) تاريخ التعاقد\n"
    "4) تاريخ بدء الصيانة\n"
    "5) تاريخ انتهاء الصيانة\n\n"
    "لازم تكتب كل التواريخ بصيغة YYYY-MM-DD بالأرقام بس (حوّل أي صيغة تاريخ تانية لهذه الصيغة). "
    "رد بالشكل ده بالضبط، سطر لكل حقل، وبدون أي شرح أو مقدمات:\n"
    "اسم العميل: <القيمة أو NULL>\n"
    "ID العميل: <القيمة أو NULL>\n"
    "تاريخ التعاقد: <القيمة أو NULL>\n"
    "تاريخ بدء الصيانة: <القيمة أو NULL>\n"
    "تاريخ انتهاء الصيانة: <القيمة أو NULL>\n\n"
    "لو حقل غير موجود أو غير واضح في كلام المستخدم اكتب NULL بالظبط بدل قيمته. "
    "لا تخترع أي معلومة مش موجودة في النص."
)


def _parse_extraction(raw_text: str) -> dict:
    mapping = {
        "اسم العميل": "customer_name",
        "ID العميل": "customer_id",
        "تاريخ التعاقد": "contract_date",
        "تاريخ بدء الصيانة": "maintenance_start",
        "تاريخ انتهاء الصيانة": "maintenance_end",
    }
    result = {v: None for v in mapping.values()}

    for line in raw_text.splitlines():
        line = line.strip()
        for label, key in mapping.items():
            prefix = f"{label}:"
            if line.startswith(prefix):
                val = line.replace(prefix, "", 1).strip()
                if val and val.upper() != "NULL":
                    result[key] = val

    return result


async def extract_registration_info(raw_text: str, history: list = None) -> dict:
    """
    بيستخرج الحقول المطلوبة من كلام العميل.
    يرجّع dict فيها:
        customer_name, customer_id, contract_date,
        maintenance_start, maintenance_end  (أي منهم ممكن يكون None لو ناقص)
        missing_fields: list بأسماء الحقول الناقصة بالعربي
    """
    raw_result = await _call_ai(EXTRACTION_SYSTEM_PROMPT, raw_text, history)
    parsed = _parse_extraction(raw_result)

    label_by_key = {
        "customer_name": "اسم العميل",
        "customer_id": "ID العميل",
        "contract_date": "تاريخ التعاقد",
        "maintenance_start": "تاريخ بدء الصيانة",
        "maintenance_end": "تاريخ انتهاء الصيانة",
    }
    missing = [label for key, label in label_by_key.items() if not parsed.get(key)]
    parsed["missing_fields"] = missing
    return parsed
