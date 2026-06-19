from config import REGISTRATION_PASSWORD
from database import get_state, update_state, reset_state, save_registration
from ai import summarize_details, is_affirmative, apply_modification


async def handle_message(phone: str, text: str) -> str:
    """
    بيستقبل رسالة العميل ويرجع الرد المناسب حسب مرحلة المحادثة.
    المراحل: awaiting_password -> awaiting_details -> awaiting_confirmation -> (تسجيل) -> awaiting_password
    """
    state = get_state(phone)
    stage = state["stage"]

    # ─── المرحلة 1: انتظار الباسورد ─────────────────────────────────────────
    if stage == "awaiting_password":
        if text.strip() == REGISTRATION_PASSWORD:
            update_state(phone, "awaiting_details")
            return "تمام ✅ تفضل قولي التفاصيل اللي عايز تسجلها."
        else:
            return "الباسورد غير صحيح ❌ من فضلك ابعت الباسورد الصحيح عشان نكمل عملية التسجيل."

    # ─── المرحلة 2: استقبال التفاصيل الحرة من العميل ───────────────────────
    if stage == "awaiting_details":
        summary = await summarize_details(text)
        update_state(phone, "awaiting_confirmation", pending_summary=summary)
        return (
            f"تمام، دي التفاصيل اللي هسجلها:\n\n{summary}\n\n"
            "متأكد عايز أسجلها كده؟ (لو فيها تعديل قولي إيه التعديل)"
        )

    # ─── المرحلة 3: انتظار التأكيد أو التعديل ───────────────────────────────
    if stage == "awaiting_confirmation":
        confirmed = await is_affirmative(text)

        if confirmed:
            success = save_registration(phone, state["pending_summary"])
            if success:
                reset_state(phone)
                return "تم التسجيل بنجاح ✅"
            else:
                # فشل التسجيل - نسيب العميل في نفس المرحلة عشان يعيد المحاولة
                return "فشل التسجيل ❌ هيتم إعادة المحاولة، من فضلك أكد تاني."
        else:
            # العميل طلب تعديل - ندمج التعديل مع الملخص القديم
            new_summary = await apply_modification(state["pending_summary"], text)
            update_state(phone, "awaiting_confirmation", pending_summary=new_summary)
            return (
                f"تمام، دي التعديلات الجديدة:\n\n{new_summary}\n\n"
                "متأكد عايز أسجلها كده؟"
            )

    # fallback - حالة غير متوقعة
    reset_state(phone)
    return "محتاج منك الباسورد عشان أكمل عملية التسجيل."
