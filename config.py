import os

# WhatsApp Meta API
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "test123")

# Registration password (ثابت لكل العملاء)
REGISTRATION_PASSWORD = os.getenv("REGISTRATION_PASSWORD", "")

# AI Provider (Groq - مجاني)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# SQL Server
DB_SERVER = os.getenv("DB_SERVER", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
TDS_VERSION = os.getenv("TDS_VERSION")  # ممكن تحتاج تعدل حسب نسخة SQL Server عندك
CHARSET = os.getenv("DB_CHARSET")  # ممكن تحتاج تعدل حسب إعدادات قاعدة البيانات عندك