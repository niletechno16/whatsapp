import json
import pymssql
from config import DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD, DB_TDS_VERSION, DB_CHARSET


def get_connection():
    return pymssql.connect(
        server=DB_SERVER,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        tds_version=DB_TDS_VERSION,
        charset=DB_CHARSET,
    )


def _sanitize_cp1256(text):
    """يشيل أي حرف ما ينفعش يتخزن بترميز CP1256 (مثلاً حروف غريبة
    ممكن الـ AI يطلعها غلط)، بدل ما الإدخال في الداتابيز يفشل بالكامل."""
    if text is None:
        return text
    return text.encode("cp1256", errors="ignore").decode("cp1256")


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

    # ─── جدول بيانات العميل المنظمة (الجدول الوحيد اللي بيتسجل فيه التسجيل دلوقتي) ───
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='bot_information_byA' AND xtype='U')
        CREATE TABLE bot_information_byA (
            id                    INT IDENTITY(1,1) PRIMARY KEY,
            phone                 VARCHAR(30)   NOT NULL,
            customer_name         VARCHAR(255)  NOT NULL,
            customer_id           VARCHAR(100)  NOT NULL,
            contract_date         VARCHAR(20)   NOT NULL,
            maintenance_start     VARCHAR(20)   NOT NULL,
            maintenance_end       VARCHAR(20)   NOT NULL,
            remaining_days        INT           NOT NULL,
            created_at            DATETIME      DEFAULT GETDATE()
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
        (phone, _sanitize_cp1256(message)),
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

    raw_history = row.get("chat_history")
    if raw_history:
        try:
            row["chat_history"] = json.loads(raw_history)
        except Exception:
            row["chat_history"] = []
    else:
        row["chat_history"] = []

    return row


def update_state(phone: str, stage: str, pending_summary: str = None, chat_history: list = None):
    conn = get_connection()
    cursor = conn.cursor()

    encoded_summary = _sanitize_cp1256(pending_summary)

    if chat_history is not None:
        history_json = json.dumps(chat_history, ensure_ascii=False)
        encoded_history = _sanitize_cp1256(history_json)
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


# ─── Bot information (الجدول المنظم الوحيد اللي بيتسجل فيه) ────────────────
def save_bot_information(phone: str, info: dict) -> bool:
    """
    info لازم يحتوي على المفاتيح:
    customer_name, customer_id, contract_date,
    maintenance_start, maintenance_end, remaining_days
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bot_information_byA
                (phone, customer_name, customer_id, contract_date,
                 maintenance_start, maintenance_end, remaining_days)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                phone,
                _sanitize_cp1256(info["customer_name"]),
                _sanitize_cp1256(info["customer_id"]),
                info["contract_date"],
                info["maintenance_start"],
                info["maintenance_end"],
                info["remaining_days"],
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
