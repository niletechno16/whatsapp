import json
import pymssql
from config import DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD, DB_TDS_VERSION


def get_connection():
    # charset لازم يكون UTF-8 عشان العربي يتحفظ صح
    return pymssql.connect(
        server=DB_SERVER,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        tds_version=DB_TDS_VERSION,
        charset="UTF-8",
    )


def _safe_str(value) -> str:
    """يضمن إن النص UTF-8 صح"""
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def setup_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='whatsapp_messages_byA' AND xtype='U')
        CREATE TABLE whatsapp_messages_byA (
            id          INT IDENTITY(1,1) PRIMARY KEY,
            phone       NVARCHAR(30)      NOT NULL,
            message     NVARCHAR(MAX)     NOT NULL,
            received_at DATETIME          DEFAULT GETDATE()
        )
    """)

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='conversation_state_byA' AND xtype='U')
        CREATE TABLE conversation_state_byA (
            phone           NVARCHAR(30)  PRIMARY KEY,
            stage           NVARCHAR(30)  NOT NULL DEFAULT 'idle',
            pending_summary NVARCHAR(MAX) NULL,
            chat_history    NVARCHAR(MAX) NULL,
            updated_at      DATETIME      DEFAULT GETDATE()
        )
    """)

    cursor.execute("""
        IF EXISTS (SELECT * FROM sysobjects WHERE name='conversation_state_byA' AND xtype='U')
        AND NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('conversation_state_byA') AND name = 'chat_history')
        ALTER TABLE conversation_state_byA ADD chat_history NVARCHAR(MAX) NULL
    """)

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='registrations_byA' AND xtype='U')
        CREATE TABLE registrations_byA (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            phone        NVARCHAR(30)      NOT NULL,
            details      NVARCHAR(MAX)     NOT NULL,
            created_at   DATETIME          DEFAULT GETDATE()
        )
    """)

    conn.commit()
    conn.close()


# ─── Raw messages log ──────────────────────────────────────────────────────
def save_message(phone: str, message: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO whatsapp_messages_byA (phone, message) VALUES (%s, %s)",
        (phone, message),
    )
    conn.commit()
    conn.close()


# ─── Conversation state ────────────────────────────────────────────────────
def get_state(phone: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor(as_dict=True)
    cursor.execute(
        """
        SELECT phone, stage,
               CAST(pending_summary AS NVARCHAR(MAX)) AS pending_summary,
               CAST(chat_history    AS NVARCHAR(MAX)) AS chat_history
        FROM conversation_state_byA WHERE phone = %s
        """,
        (phone,),
    )
    row = cursor.fetchone()

    if row is None:
        cursor.execute(
            "INSERT INTO conversation_state_byA (phone, stage) VALUES (%s, 'idle')",
            (phone,),
        )
        conn.commit()
        row = {"phone": phone, "stage": "idle", "pending_summary": None, "chat_history": None}

    conn.close()

    row["pending_summary"] = _safe_str(row.get("pending_summary"))
    raw_history = _safe_str(row.get("chat_history"))
    row["chat_history"] = json.loads(raw_history) if raw_history else []
    return row


def update_state(phone: str, stage: str, pending_summary: str = None, chat_history: list = None):
    conn = get_connection()
    cursor = conn.cursor()
    # نضمن إن النصوص UTF-8 قبل ما نحفظها
    safe_summary = _safe_str(pending_summary)
    history_json = json.dumps(chat_history, ensure_ascii=False) if chat_history is not None else None
    cursor.execute(
        """
        UPDATE conversation_state_byA
        SET stage = %s, pending_summary = %s, chat_history = %s, updated_at = GETDATE()
        WHERE phone = %s
        """,
        (stage, safe_summary, history_json, phone),
    )
    conn.commit()
    conn.close()


def reset_state(phone: str):
    update_state(phone, "idle", pending_summary=None, chat_history=[])


# ─── Registrations ──────────────────────────────────────────────────────────
def save_registration(phone: str, details: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO registrations_byA (phone, details) VALUES (%s, %s)",
            (phone, _safe_str(details)),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
