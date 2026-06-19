import pymssql
from datetime import datetime
from config import CHARSET, DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD, TDS_VERSION


def get_connection():
    return pymssql.connect(
        server=DB_SERVER,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        tds_version=TDS_VERSION,
        charset=CHARSET,
    )


def setup_tables():
    """إنشاء الجداول لو مش موجودة"""
    conn = get_connection()
    cursor = conn.cursor()

    # جدول الرسايل الخام (لوج لكل حاجة بتتبعت)
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='whatsapp_messages' AND xtype='U')
        CREATE TABLE whatsapp_messages (
            id          INT IDENTITY(1,1) PRIMARY KEY,
            phone       VARCHAR(30)       NOT NULL,
            message     NVARCHAR(MAX)     NOT NULL,
            received_at DATETIME          DEFAULT GETDATE()
        )
    """)

    # جدول حالة المحادثة لكل عميل (مين واصل لفين في الـ flow)
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='conversation_state' AND xtype='U')
        CREATE TABLE conversation_state (
            phone           VARCHAR(30)   PRIMARY KEY,
            stage           VARCHAR(30)   NOT NULL DEFAULT 'awaiting_password',
            pending_summary NVARCHAR(MAX) NULL,
            updated_at      DATETIME      DEFAULT GETDATE()
        )
    """)

    # جدول التسجيلات النهائية
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='registrations' AND xtype='U')
        CREATE TABLE registrations (
            id           INT IDENTITY(1,1) PRIMARY KEY,
            phone        VARCHAR(30)       NOT NULL,
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
        "INSERT INTO whatsapp_messages (phone, message) VALUES (%s, %s)",
        (phone, message),
    )
    conn.commit()
    conn.close()


# ─── Conversation state ────────────────────────────────────────────────────
def get_state(phone: str) -> dict:
    """رجع حالة العميل، ولو أول مرة يعمله حالة جديدة"""
    conn = get_connection()
    cursor = conn.cursor(as_dict=True)
    cursor.execute(
        "SELECT phone, stage, pending_summary FROM conversation_state WHERE phone = %s",
        (phone,),
    )
    row = cursor.fetchone()

    if row is None:
        cursor.execute(
            "INSERT INTO conversation_state (phone, stage) VALUES (%s, 'awaiting_password')",
            (phone,),
        )
        conn.commit()
        row = {"phone": phone, "stage": "awaiting_password", "pending_summary": None}

    conn.close()
    return row


def update_state(phone: str, stage: str, pending_summary: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE conversation_state
        SET stage = %s, pending_summary = %s, updated_at = GETDATE()
        WHERE phone = %s
        """,
        (stage, pending_summary, phone),
    )
    conn.commit()
    conn.close()


def reset_state(phone: str):
    """يرجع العميل لأول الـ flow (بعد ما يخلص تسجيل مثلاً)"""
    update_state(phone, "awaiting_password", None)


# ─── Registrations ──────────────────────────────────────────────────────────
def save_registration(phone: str, details: str) -> bool:
    """يحفظ التسجيل النهائي. بيرجع True لو نجح و False لو فشل"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO registrations (phone, details) VALUES (%s, %s)",
            (phone, details),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
