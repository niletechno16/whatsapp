import json
import pymssql
from config import DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD, DB_TDS_VERSION


def get_connection():
    return pymssql.connect(
        server=DB_SERVER,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        tds_version=DB_TDS_VERSION,
        charset="UTF-8",
    )


def encode_text(text: str) -> str:
    """يحول النص لـ unicode escape عشان يتحفظ صح في VARCHAR"""
    if text is None:
        return None
    return text.encode("unicode_escape").decode("ascii")


def decode_text(text) -> str:
    """يرجع النص من unicode escape لعربي طبيعي"""
    if text is None:
        return None
    if isinstance(text, bytes):
        text = text.decode("ascii", errors="replace")
    try:
        return text.encode("ascii").decode("unicode_escape")
    except Exception:
        return text


def setup_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='whatsapp_messages_byA' AND xtype='U')
        CREATE TABLE whatsapp_messages_byA (
            id          INT IDENTITY(1,1) PRIMARY KEY,
            phone       VARCHAR(30)       NOT NULL,
            message     VARCHAR(MAX)      NOT NULL,
            received_at DATETIME          DEFAULT GETDATE()
        )
    """)

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='conversation_state_byA' AND xtype='U')
        CREATE TABLE conversation_state_byA (
            phone           VARCHAR(30)   PRIMARY KEY,
            stage           VARCHAR(30)   NOT NULL DEFAULT 'idle',
            pending_summary VARCHAR(MAX)  NULL,
            chat_history    VARCHAR(MAX)  NULL,
            updated_at      DATETIME      DEFAULT GETDATE()
        )
    """)

    cursor.execute("""
        IF EXISTS (SELECT * FROM sysobjects WHERE name='conversation_state_byA' AND xtype='U')
        AND NOT EXISTS (
            SELECT * FROM sys.columns
            WHERE object_id = OBJECT_ID('conversation_state_byA') AND name = 'chat_history'
        )
        ALTER TABLE conversation_state_byA ADD chat_history VARCHAR(MAX) NULL
    """)

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='registrations_byA' AND xtype='U')
        CREATE TABLE registrations_byA (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            phone        VARCHAR(30)       NOT NULL,
            details      VARCHAR(MAX)      NOT NULL,
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
        (phone, encode_text(message)),
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
               CAST(pending_summary AS VARCHAR(MAX)) AS pending_summary,
               CAST(chat_history    AS VARCHAR(MAX)) AS chat_history
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

    row["pending_summary"] = decode_text(row.get("pending_summary"))

    raw_history = row.get("chat_history")
    if raw_history:
        try:
            decoded_history = decode_text(raw_history)
            row["chat_history"] = json.loads(decoded_history)
        except Exception:
            row["chat_history"] = []
    else:
        row["chat_history"] = []

    return row


def update_state(phone: str, stage: str, pending_summary: str = None, chat_history: list = None):
    conn = get_connection()
    cursor = conn.cursor()

    encoded_summary = encode_text(pending_summary)

    if chat_history is not None:
        history_json = json.dumps(chat_history, ensure_ascii=False)
        encoded_history = encode_text(history_json)
    else:
        encoded_history = None

    cursor.execute(
        """
        UPDATE conversation_state_byA
        SET stage = %s, pending_summary = %s, chat_history = %s, updated_at = GETDATE()
        WHERE phone = %s
        """,
        (stage, encoded_summary, encoded_history, phone),
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
            (phone, encode_text(details)),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
