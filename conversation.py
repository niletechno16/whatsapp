from config import REGISTRATION_PASSWORD
from database import get_state, update_state, reset_state, save_registration
from ai import chat_response, summarize_details, is_affirmative, check_has_modification, apply_modification


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


async def handle_message(phone: str, text: str) -> str:
    state = get_state(phone)
    stage = state["stage"]
    history = state.get("chat_history") or []
    pending_summary = _safe(state.get("pending_summary"))

    # ─── انتظار الباسورد ──────────────────────────────────────────────────────
    if stage == "awaiting_password":
        if text.strip() == REGISTRATION_PASSWORD:
            reply = "تمام ✅ قولي التفاصيل اللي عايز تسجلها."
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

    # ─── استقبال التفاصيل ────────────────────────────────────────────────────
    if stage == "awaiting_details":
        summary = _safe(await summarize_details(text, history=history))
        reply = f"تمام، دي التفاصيل اللي هسجلها:\n\n{summary}\n\nمتأكد عايز أسجلها كده؟"
        new_history = _add_to_history(history, text, reply)
        update_state(phone, "awaiting_confirmation", pending_summary=summary, chat_history=new_history)
        return reply

    # ─── انتظار التأكيد أو التعديل ───────────────────────────────────────────
    if stage == "awaiting_confirmation":
        confirmed = await is_affirmative(text)

        if confirmed:
            success = save_registration(phone, pending_summary)
            if success:
                reply = (
                    "✅ تم التسجيل بنجاح!\n\n"
                    f"التفاصيل المسجلة:\n{pending_summary}\n\n"
                    "لو عايز تسجل حاجة تانية ابعتلي التفاصيل وانا هساعدك. 😊"
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
                new_summary = _safe(await apply_modification(pending_summary, text, history=history))
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
