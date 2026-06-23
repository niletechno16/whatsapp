from datetime import datetime, date

from config import REGISTRATION_PASSWORD
from database import save_bot_information
from state_store import get_state, update_state, reset_state
from ai import (
    wants_to_register,
    is_affirmative,
    check_has_modification,
    extract_registration_info,
)

# الرسالة الثابتة اللي بترجع لو حد طلب من البوت أي حاجة برة سياق التسجيل
OUT_OF_SCOPE_REPLY = (
    "أنا مساعد مخصص بس لتسجيل بيانات صيانة العملاء 🙏\n"
    "مش بقدر أساعدك في أي طلب تاني غير ده.\n"
    "لو عايز تسجل عميل جديد، قولي وهبدأ معاك."
)


def _safe(text) -> str:
    """يضمن إن النص UTF-8 صح"""
    if text is None:
        return ""
    if isinstance(text, bytes):
        return text.decode("utf-8", errors="replace")
    return str(text)


def _add_to_history(history: list, user_msg: str, bot_reply: str) -> list:
    updated = list(history or [])
    updated.append({"role": "user", "content": _safe(user_msg)})
    updated.append({"role": "assistant", "content": _safe(bot_reply)})
    return updated


def _format_summary(info: dict, remaining_days: int) -> str:
    return (
        f"اسم العميل: {info['customer_name']}\n"
        f"ID العميل: {info['customer_id']}\n"
        f"تاريخ التعاقد: {info['contract_date']}\n"
        f"تاريخ بدء الصيانة: {info['maintenance_start']}\n"
        f"تاريخ انتهاء الصيانة: {info['maintenance_end']}\n"
        f"المدة المتبقية لانتهاء العقد: {remaining_days} يوم"
    )


def _validate_dates(info: dict) -> bool:
    """يتأكد إن كل التواريخ المطلوبة بصيغة YYYY-MM-DD صحيحة وقابلة للتحويل."""
    for key in ("contract_date", "maintenance_start", "maintenance_end"):
        try:
            datetime.strptime(info[key], "%Y-%m-%d")
        except Exception:
            return False
    return True


def _compute_days_until_end(maintenance_end: str):
    """
    يحسب الفرق بالأيام بين تاريخ انتهاء الصيانة واليوم الحالي.
    (تاريخ الانتهاء - اليوم الحالي) عشان نعرف فاضل كام يوم على انتهاء العقد.
    ممكن ترجع رقم سالب لو العقد خلص بالفعل.
    يرجع None لو التاريخ نفسه مش صحيح.
    """
    try:
        end = datetime.strptime(maintenance_end, "%Y-%m-%d").date()
        today = date.today()
        return (end - today).days
    except Exception:
        return None


async def handle_message(phone: str, text: str) -> str:
    state = get_state(phone)
    stage = state["stage"]
    history = state.get("chat_history") or []
    pending_summary = _safe(state.get("pending_summary"))

    # ─── انتظار الباسورد ──────────────────────────────────────────────────────
    if stage == "awaiting_password":
        if text.strip() == REGISTRATION_PASSWORD:
            reply = "تمام ✅ قولي تفاصيل العميل اللي عايز تسجلها (الاسم، الـ ID، تاريخ التعاقد، تاريخ بدء وانتهاء الصيانة)."
            new_history = _add_to_history(history, text, reply)
            update_state(phone, "awaiting_details", pending_summary=None, chat_history=new_history)
            return reply
        else:
            reply = "الباسورد ده غلط 🙏\nابعت الباسورد الصحيح عشان نكمل التسجيل."
            new_history = _add_to_history(history, text, reply)
            update_state(phone, "awaiting_password", pending_summary=None, chat_history=new_history)
            return reply

    # ─── استقبال التفاصيل لأول مرة، أو استكمال بيانات ناقصة ──────────────────
    if stage in ("awaiting_details", "awaiting_missing_fields"):
        info = await extract_registration_info(text, history=history)

        if info["missing_fields"]:
            missing_list = "، ".join(info["missing_fields"])
            reply = (
                f"محتاج كمان البيانات دي عشان أكمل التسجيل:\n{missing_list}\n\n"
                "ابعتها وأنا هكمل التسجيل."
            )
            new_history = _add_to_history(history, text, reply)
            update_state(phone, "awaiting_missing_fields", pending_summary=None, chat_history=new_history)
            return reply

        if not _validate_dates(info):
            reply = (
                "في مشكلة في صيغة التواريخ اللي بعتها 🙏\n"
                "من فضلك اكتب التواريخ بصيغة واضحة (يوم/شهر/سنة) لتاريخ التعاقد وتاريخ بدء وانتهاء الصيانة."
            )
            new_history = _add_to_history(history, text, reply)
            update_state(phone, "awaiting_missing_fields", pending_summary=None, chat_history=new_history)
            return reply

        remaining_days = _compute_days_until_end(info["maintenance_end"])
        summary = _format_summary(info, remaining_days)
        reply = f"تمام، دي التفاصيل اللي هسجلها:\n\n{summary}\n\nمتأكد عايز أسجلها كده؟"
        new_history = _add_to_history(history, text, reply)
        update_state(phone, "awaiting_confirmation", pending_summary=summary, chat_history=new_history)
        return reply

    # ─── انتظار التأكيد أو التعديل ───────────────────────────────────────────
    if stage == "awaiting_confirmation":
        confirmed = await is_affirmative(text)

        if confirmed:
            info = await extract_registration_info(pending_summary)

            if info["missing_fields"] or not _validate_dates(info):
                reply = "حصلت مشكلة في قراءة بعض البيانات، ممكن تبعتها تاني بشكل واضح؟"
                new_history = _add_to_history(history, text, reply)
                update_state(phone, "awaiting_details", pending_summary=None, chat_history=new_history)
                return reply

            # نحسب المدة المتبقية بتاريخ اليوم الفعلي وقت التسجيل (مش وقت العرض الأول)
            remaining_days = _compute_days_until_end(info["maintenance_end"])
            success = save_bot_information(phone, info, remaining_days)

            if success:
                reply = (
                    "✅ تم التسجيل بنجاح!\n\n"
                    f"{_format_summary(info, remaining_days)}\n\n"
                    "لو عايز تسجل عميل تاني ابعتلي التفاصيل وانا هساعدك. 😊"
                )
                reset_state(phone)
                return reply
            else:
                reply = "❌ فشل التسجيل، حاول تاني."
                new_history = _add_to_history(history, text, reply)
                update_state(phone, "awaiting_confirmation", pending_summary=pending_summary, chat_history=new_history)
                return reply
        else:
            has_real_modification = await check_has_modification(text)

            if has_real_modification:
                combined_text = f"{pending_summary}\n\nتعديل: {text}"
                info = await extract_registration_info(combined_text, history=history)

                if info["missing_fields"]:
                    missing_list = "، ".join(info["missing_fields"])
                    reply = (
                        f"محتاج كمان البيانات دي عشان أكمل التسجيل:\n{missing_list}\n\n"
                        "ابعتها وأنا هكمل التسجيل."
                    )
                    new_history = _add_to_history(history, text, reply)
                    update_state(phone, "awaiting_missing_fields", pending_summary=None, chat_history=new_history)
                    return reply

                if not _validate_dates(info):
                    reply = (
                        "في مشكلة في صيغة التواريخ اللي بعتها 🙏\n"
                        "من فضلك اكتب التواريخ بصيغة واضحة (يوم/شهر/سنة)."
                    )
                    new_history = _add_to_history(history, text, reply)
                    update_state(phone, "awaiting_missing_fields", pending_summary=None, chat_history=new_history)
                    return reply

                remaining_days = _compute_days_until_end(info["maintenance_end"])
                new_summary = _format_summary(info, remaining_days)
                reply = f"تمام، دي التفاصيل بعد التعديل:\n\n{new_summary}\n\nمتأكد عايز أسجلها كده؟"
                new_history = _add_to_history(history, text, reply)
                update_state(phone, "awaiting_confirmation", pending_summary=new_summary, chat_history=new_history)
                return reply
            else:
                reply = f"التفاصيل دي:\n\n{pending_summary}\n\nهل تأكد تسجيلها ولا عايز تعدّل فيها؟"
                new_history = _add_to_history(history, text, reply)
                update_state(phone, "awaiting_confirmation", pending_summary=pending_summary, chat_history=new_history)
                return reply

    # ─── idle: خارج سياق التسجيل بالكامل ─────────────────────────────────────
    # البوت ميرد على حاجة تانية غير طلب التسجيل، أي رسالة تانية تاخد رد ثابت
    # يوضح مهمته الأساسية، بدل ما الـ AI يحاول يجاوب بحرية على أي سؤال.
    if await wants_to_register(text, history=history):
        reply = "عشان أسجل البيانات محتاج الباسورد الأول 🙏"
        new_history = _add_to_history(history, text, reply)
        update_state(phone, "awaiting_password", pending_summary=None, chat_history=new_history)
        return reply

    reply = OUT_OF_SCOPE_REPLY
    new_history = _add_to_history(history, text, reply)
    update_state(phone, "idle", pending_summary=None, chat_history=new_history)
    return reply
