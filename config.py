import os

# WhatsApp Meta API
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "test123")

# Registration password
REGISTRATION_PASSWORD = os.getenv("REGISTRATION_PASSWORD", "")

# AI Providers
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")

# SQL Server
DB_SERVER = os.getenv("DB_SERVER", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_TDS_VERSION = os.getenv("TDS_VERSION", "7.0")
DB_CHARSET = os.getenv("DB_CHARSET", "UTF-8")
