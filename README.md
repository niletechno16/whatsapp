# WhatsApp Registration Bot 🤖

بوت واتساب يسجل طلبات العملاء عبر محادثة ذكية بكلمة سر.

## آلية العمل (Conversation Flow)

```
العميل يبعت أي رسالة
        ↓
البوت: "محتاج الباسورد"
        ↓
   باسورد صح؟ ──لا──> "باسورد غلط، حاول تاني"
        │
       نعم
        ↓
البوت: "قولي التفاصيل اللي عايز تسجلها"
        ↓
العميل يكتب بحرية
        ↓
AI يلخص ➜ "دي التفاصيل: [...] متأكد؟"
        ↓
   موافق؟ ──لا (تعديل)──> يدمج التعديل ويعيد التأكيد (loop)
        │
       نعم
        ↓
يسجل في DB
   نجح ──> "تم التسجيل بنجاح ✅" (يرجع لأول الـ flow)
   فشل ──> "فشل التسجيل، أكد تاني" (إعادة محاولة)
```

## الملفات

| ملف | وظيفة |
|-----|--------|
| `main.py` | FastAPI + webhook endpoints |
| `conversation.py` | الـ state machine لمراحل المحادثة |
| `database.py` | SQL Server: رسايل خام + حالة المحادثة + التسجيلات |
| `ai.py` | تلخيص AI + تحديد الموافقة/التعديل (Groq) |
| `whatsapp.py` | إرسال الردود عبر Meta API + typing indicator + تأخير طبيعي |
| `keepalive.py` | thread خلفي يحافظ على السيرفر شغال دايماً على Render |
| `config.py` | كل البيانات الحساسة من Environment Variables فقط |

## مميزات إضافية

- **Typing indicator**: قبل كل رد، البوت يعلّم الرسالة كمقروءة ويظهر "يكتب الآن..." لمدة 2-4 ثانية عشوائية، عشان يبان طبيعي ومايتحظرش.
- **Keep-alive**: thread في الخلفية بيعمل ping للسيرفر نفسه كل 10 دقايق عشان Render (الخطة المجانية) ميقفلش السيرفر بسبب عدم النشاط.

## الجداول في الـ DB

- **whatsapp_messages**: لوج لكل رسالة وصلت (للمراجعة)
- **conversation_state**: مرحلة كل عميل حالياً (phone, stage, pending_summary)
- **registrations**: التسجيلات النهائية المؤكدة

## Environment Variables المطلوبة في Render

| المتغير | الوصف |
|---------|--------|
| `WHATSAPP_TOKEN` | Access Token من Meta |
| `PHONE_NUMBER_ID` | من Meta API Setup |
| `VERIFY_TOKEN` | أي كلمة تختارها لتفعيل الـ webhook |
| `REGISTRATION_PASSWORD` | الباسورد الثابت اللي العميل هيدخله |
| `GROQ_API_KEY` | من console.groq.com (مجاني) |
| `DB_SERVER` | عنوان سيرفر SQL Server |
| `DB_NAME` | اسم قاعدة البيانات |
| `DB_USER` | اسم المستخدم |
| `DB_PASSWORD` | كلمة السر |
| `TDS_VERSION` | افتراضي `4.2` |
| `DB_CHARSET` | افتراضي `UTF-8` |

⚠️ **لا يوجد أي بيانات حساسة في الكود** — كل حاجة بتتقرأ من environment variables فقط.

## رفع المشروع

```bash
git init
git add .
git commit -m "whatsapp registration bot"
git remote add origin YOUR_REPO_URL
git push -u origin main
```

بعدها على Render: New Web Service → اربط الـ repo → حط الـ Environment Variables → Deploy.

Start Command (لو محتاج تحطه يدوي):
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```
