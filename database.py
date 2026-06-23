import pymssql
from config import DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD, DB_TDS_VERSION, DB_CHARSET ,DB_PORT


def get_connection():
    return pymssql.connect(
        server=DB_SERVER,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        tds_version=DB_TDS_VERSION,
        charset=DB_CHARSET,
        port=DB_PORT,
    )


def _sanitize_text(text):
    """يشيل أي حرف NULL محتمل يكسر الـ SQL، ويحافظ على العربي كامل بـ Unicode."""
    if not text:
        return text
    return text.replace('\x00', '')


def setup_tables():
    """
    بيعمل الجداول لو مش موجودة. الجدولين الوحيدين دلوقتي:
    whatsapp_messages_byA و bot_information_byA.
    بنستخدم NVARCHAR لكل عمود فيه نص، بنفس الطريقة المستخدمة في
    مشروع الفاست اي بي اي الناجح.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'whatsapp_messages_byA'
        )
        BEGIN
            CREATE TABLE whatsapp_messages_byA (
                id          INT IDENTITY(1,1) PRIMARY KEY,
                phone       NVARCHAR(30)   NOT NULL,
                message     NVARCHAR(MAX)  NOT NULL,
                received_at DATETIME       DEFAULT GETDATE()
            )
        END
    """)

    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'bot_information_byA'
        )
        BEGIN
            CREATE TABLE bot_information_byA (
                id                    INT IDENTITY(1,1) PRIMARY KEY,
                phone                 NVARCHAR(30)   NOT NULL,
                customer_name         NVARCHAR(255)  NOT NULL,
                customer_id           NVARCHAR(100)  NOT NULL,
                contract_date         NVARCHAR(20)   NOT NULL,
                maintenance_start     NVARCHAR(20)   NOT NULL,
                maintenance_end       NVARCHAR(20)   NOT NULL,
                remaining_days        INT            NOT NULL,
                created_at            DATETIME       DEFAULT GETDATE()
            )
        END
    """)

    conn.commit()
    conn.close()


# ─── Raw messages log ──────────────────────────────────────────────────────
def save_message(phone: str, message: str):
    message = _sanitize_text(message)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO whatsapp_messages_byA (phone, message) VALUES (%s, %s)",
        (phone, message),
    )
    conn.commit()
    conn.close()


# ─── Bot information (الجدول المنظم الوحيد اللي بيتسجل فيه) ────────────────
def save_bot_information(phone: str, info: dict, remaining_days: int) -> bool:
    """
    info لازم يحتوي على المفاتيح:
    customer_name, customer_id, contract_date,
    maintenance_start, maintenance_end
    remaining_days: الفرق بالأيام بين تاريخ انتهاء الصيانة واليوم الحالي
    """
    customer_name = _sanitize_text(info["customer_name"])
    customer_id = _sanitize_text(info["customer_id"])
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
                customer_name,
                customer_id,
                info["contract_date"],
                info["maintenance_start"],
                info["maintenance_end"],
                remaining_days,
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
