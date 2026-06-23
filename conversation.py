from config import REGISTRATION_PASSWORD
from database import get_state, update_state, reset_state, save_registration
from ai import chat_response, summarize_details, is_affirmative, apply_modification


async def handle_message(phone: str, text: str) -> str:
    """
    محادثة طبيعية مع الحفاظ على state لعملية التسجيل.

    المراحل:
    - idle: محادثة عادية، لو المستخدم عايز يسجل يطلب منه الباسورد
    - awaiting_password: انتظار الباسورد
    - awaiting_details: استقبال التفاصيل
    - awaiting_confirmation: تأكيد أو تعديل
    """
    state = get_state(phone)
    stage = state["stage"]

    # ─── في منتصف عملية تسجيل: انتظار الباسورد ──────────────────────────────
    if stage == "awaiting_password":
        if text.strip() == REGISTRATION_PASSWORD:
            update_state(phone, "awaiting_details")
            return "تمام ✅ قولي التفاصيل اللي عايز تسجلها."
        else:
            # ممكن يكون بيتكلم عادي مش بيدخل باسورد
            ai_reply = await chat_response(
                text,
                context="المستخدم ده طلب قبل كده إنه يسجل بيانات وانت بتستنى الباسورد منه. "
                        "لو بيتكلم عادي رد عليه طبيعي وذكّره إنك محتاج الباسورد عشان تكمل التسجيل."
            )
            return ai_reply

    # ─── في منتصف عملية تسجيل: استقبال التفاصيل ────────────────────────────
    if stage == "awaiting_details":
        summary = await summarize_details(text)
        update_state(phone, "awaiting_confirmation", pending_summary=summary)
        return (
            f"تمام، دي التفاصيل اللي هسجلها:\n\n{summary}\n\n"
            "متأكد عايز أسجلها كده؟"
        )

    # ─── في منتصف عملية تسجيل: انتظار التأكيد ──────────────────────────────
    if stage == "awaiting_confirmation":
        confirmed = await is_affirmative(text)

        if confirmed:
            success = save_registration(phone, state["pending_summary"])
            if success:
                reset_state(phone)
                return (
                    "✅ تم التسجيل بنجاح!\n\n"
                    f"*التفاصيل المسجلة:*\n{state['pending_summary']}\n\n"
                    "لو عايز تسجل حاجة تانية ابعتلي التفاصيل وانا هساعدك. 😊"
                )
            else:
                return "❌ فشل التسجيل، حاول تاني."
        else:
            new_summary = await apply_modification(state["pending_summary"], text)
            update_state(phone, "awaiting_confirmation", pending_summary=new_summary)
            return (
                f"تمام، دي التعديلات الجديدة:\n\n{new_summary}\n\n"
                "متأكد عايز أسجلها كده؟"
            )

    # ─── idle: محادثة عادية ──────────────────────────────────────────────────
    # الـ AI هيقرر لو المستخدم عايز يسجل ويطلب منه الباسورد
    ai_reply = await chat_response(
        text,
        context=(
            "لو المستخدم بيطلب تسجيل أي بيانات أو حاجة محتاج تتسجل، "
            "قوله 'عشان أسجلها محتاج الباسورد أولاً' وخليه يبعتهولك. "
            "لو بيتكلم عادي أو بيسأل، رد عليه بشكل طبيعي ومفيد."
        )
    )

    # لو الـ AI طلب الباسورد، نحوّل الـ stage
    keywords = ["الباسورد", "باسورد", "كلمة السر", "password"]
    if any(kw in ai_reply for kw in keywords):
        update_state(phone, "awaiting_password")

    return ai_reply
