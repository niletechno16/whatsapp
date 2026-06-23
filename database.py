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
    """
    بيعمل الجداول لو مش موجودة، ولو موجودة بالفعل ميعملها تاني (IF NOT EXISTS)
    ويفضل يضيف فيها عادي. الجدولين الوحيدين دلوقتي:
    whatsapp_messages_byA و bot_information_byA.

    العربي بيتسجل صح لإننا بنحدد COLLATE صريح في الأعمدة (Arabic_CI_AS)
    عشان نضمن التوافق مع charset='CP1256' في الكونكشن، بدل ما نعتمد
    على الـ collation الافتراضي للسيرفر اللي ممكن يكون مختلف.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='whatsapp_messages_byA' AND xtype='U')
        CREATE TABLE whatsapp_messages_byA (
            id          INT IDENTITY(1,1) PRIMARY KEY,
            phone       VARCHAR(30)  COLLATE Arabic_CI_AS  NOT NULL,
            message     VARCHAR(MAX) COLLATE Arabic_CI_AS  NOT NULL,
            received_at DATETIME     DEFAULT GETDATE()
        )
    """)

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='bot_information_byA' AND xtype='U')
        CREATE TABLE bot_information_byA (
            id                    INT IDENTITY(1,1) PRIMARY KEY,
            phone                 VARCHAR(30)  COLLATE Arabic_CI_AS  NOT NULL,
            customer_name         VARCHAR(255) COLLATE Arabic_CI_AS  NOT NULL,
            customer_id           VARCHAR(100) COLLATE Arabic_CI_AS  NOT NULL,
            contract_date         VARCHAR(20)  NOT NULL,
            maintenance_start     VARCHAR(20)  NOT NULL,
            maintenance_end       VARCHAR(20)  NOT NULL,
            remaining_days        INT          NOT NULL,
            created_at            DATETIME     DEFAULT GETDATE()
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


# ─── Bot information (الجدول المنظم الوحيد اللي بيتسجل فيه) ────────────────
def save_bot_information(phone: str, info: dict, remaining_days: int) -> bool:
    """
    info لازم يحتوي على المفاتيح:
    customer_name, customer_id, contract_date,
    maintenance_start, maintenance_end
    remaining_days: الفرق بالأيام بين تاريخ انتهاء الصيانة واليوم الحالي
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
                remaining_days,
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
