"""
تخزين حالة المحادثة (stage / pending_summary / chat_history) في الميموري
بدل جدول conversation_state_byA في السيكوال.

ملحوظة: الداتا دي بتتمسح لو السيرفر اتعمل له ريستارت أو ديپلوي جديد،
لكن ده مقبول لإن دي حالة محادثة مؤقتة بس (مش بيانات نهائية محتاجة تتحفظ
دايمًا)، والبيانات النهائية بتتسجل في bot_information_byA في السيكوال.
"""

_STATE = {}


def get_state(phone: str) -> dict:
    if phone not in _STATE:
        _STATE[phone] = {
            "phone": phone,
            "stage": "idle",
            "pending_summary": None,
            "chat_history": [],
        }
    return _STATE[phone]


def update_state(phone: str, stage: str, pending_summary: str = None, chat_history: list = None):
    state = get_state(phone)
    state["stage"] = stage
    state["pending_summary"] = pending_summary
    if chat_history is not None:
        state["chat_history"] = chat_history


def reset_state(phone: str):
    update_state(phone, "idle", pending_summary=None, chat_history=[])
