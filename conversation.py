from datetime import datetime

from config import REGISTRATION_PASSWORD
from database import get_state, update_state, reset_state, save_bot_information
from ai import (
    chat_response,
    is_affirmative,
    check_has_modification,
    extract_registration_info,
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


def _format_summary(info: dict) -> str:
    return (
        f"اسم العميل: {info['customer_name']}\n"
        f"ID العميل: {info['customer_id']}\n"
        f"تاريخ التعاقد: {info['contract_date']}\n"
        f"تاريخ بدء الصيانة: {info['maintenance_start']}\n"
        f"تاريخ انتهاء الصيانة: {info['maintenance_end']}\n"
        f"المدة المتبقية: {info['remaining_days']} يوم"
    )


def _try_compute_remaining_days(info: dict):
    """يحسب الفرق بالأيام بين تاريخ بدء وانتهاء الصيانة. يرجع None لو التواريخ مش صحيحة."""
    try:
        start = datetime.strptime(info["maintenance_start"], "%Y-%m-%d")
        end = datetime.strptime(info["maintenance_end"], "%Y-%m-%d")
        return (end - start).days
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
            reply = await chat_response(
                text,
                history=history,
                context="المستخدم طلب تسجيل بيانات وانت بتستنى الباسورد منه. "
                        "لو بيتكلم عادي رد عليه طبيعي وذكّره إنك محتاج الباسورد."
            )
            reply = _safe(reply)
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

        remaining_days = _try_compute_remaining_days(info)
        if remaining_days is None:
            reply = (
                "في مشكلة في صيغة التواريخ اللي بعتها 🙏\n"
                "من فضلك اكتب التواريخ بصيغة واضحة (يوم/شهر/سنة) لتاريخ التعاقد وتاريخ بدء وانتهاء الصيانة."
            )
            new_history = _add_to_history(history, text, reply)
            update_state(phone, "awaiting_missing_fields", pending_summary=None, chat_history=new_history)
            return reply

        info["remaining_days"] = remaining_days
        summary = _format_summary(info)
        reply = f"تمام، دي التفاصيل اللي هسجلها:\n\n{summary}\n\nمتأكد عايز أسجلها كده؟"
        new_history = _add_to_history(history, text, reply)
        update_state(phone, "awaiting_confirmation", pending_summary=summary, chat_history=new_history)
        return reply

    # ─── انتظار التأكيد أو التعديل ───────────────────────────────────────────
    if stage == "awaiting_confirmation":
        confirmed = await is_affirmative(text)

        if confirmed:
            info = await extract_registration_info(pending_summary)
            remaining_days = _try_compute_remaining_days(info)

            if info["missing_fields"] or remaining_days is None:
                reply = "حصلت مشكلة في قراءة بعض البيانات، ممكن تبعتها تاني بشكل واضح؟"
                new_history = _add_to_history(history, text, reply)
                update_state(phone, "awaiting_details", pending_summary=None, chat_history=new_history)
                return reply

            info["remaining_days"] = remaining_days
            success = save_bot_information(phone, info)

            if success:
                reply = (
                    "✅ تم التسجيل بنجاح!\n\n"
                    f"{_format_summary(info)}\n\n"
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

                remaining_days = _try_compute_remaining_days(info)
                if remaining_days is None:
                    reply = (
                        "في مشكلة في صيغة التواريخ اللي بعتها 🙏\n"
                        "من فضلك اكتب التواريخ بصيغة واضحة (يوم/شهر/سنة)."
                    )
                    new_history = _add_to_history(history, text, reply)
                    update_state(phone, "awaiting_missing_fields", pending_summary=None, chat_history=new_history)
                    return reply

                info["remaining_days"] = remaining_days
                new_summary = _format_summary(info)
                reply = f"تمام، دي التفاصيل بعد التعديل:\n\n{new_summary}\n\nمتأكد عايز أسجلها كده؟"
                new_history = _add_to_history(history, text, reply)
                update_state(phone, "awaiting_confirmation", pending_summary=new_summary, chat_history=new_history)
                return reply
            else:
                reply = f"التفاصيل دي:\n\n{pending_summary}\n\nهل تأكد تسجيلها ولا عايز تعدّل فيها؟"
                new_history = _add_to_history(history, text, reply)
                update_state(phone, "awaiting_confirmation", pending_summary=pending_summary, chat_history=new_history)
                return reply

    # ─── idle: محادثة عادية ──────────────────────────────────────────────────
    reply = _safe(await chat_response(
        text,
        history=history,
        context=(
            "لو المستخدم بيطلب تسجيل أي بيانات، "
            "قوله 'عشان أسجلها محتاج الباسورد أولاً'. "
            "لو بيتكلم عادي، رد عليه بشكل طبيعي ومفيد."
        )
    ))

    new_history = _add_to_history(history, text, reply)
    keywords = ["الباسورد", "باسورد", "كلمة السر", "password"]
    new_stage = "awaiting_password" if any(kw in reply for kw in keywords) else "idle"
    update_state(phone, new_stage, pending_summary=None, chat_history=new_history)
    return reply
