# UltraMed Egpt

متجر إلكتروني لمستلزمات طبية، مبني بـ Flask (باك اند + REST API) مع فرونت اند HTML/CSS/JS.

## التشغيل محليًا

```bash
python -m venv venv
source venv/bin/activate      # على ويندوز: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# افتح .env وحدد فيه القيم المطلوبة (شوف قسم "متغيرات البيئة" تحت)

python app.py
```

التطبيق هيشتغل على `http://127.0.0.1:3000`.

## التشغيل في الإنتاج

لا تستخدم `python app.py` في الإنتاج (ده سيرفر تطوير فقط). استخدم Gunicorn ورا Nginx:

```bash
gunicorn wsgi:app --workers 4 --bind 0.0.0.0:8000
```

`Procfile` جاهز لو بتنشر على منصة زي Render/Heroku.

تأكد إن:
- `FLASK_DEBUG=False`
- `SESSION_COOKIE_SECURE=True` (لو الموقع شغال على HTTPS)
- `DATABASE_URL` بيشير لقاعدة PostgreSQL حقيقية، مش SQLite
- `SECRET_KEY` و `JWT_SECRET_KEY` نصوص عشوائية طويلة وفريدة (مختلفة عن بعض)

## متغيرات البيئة (`.env`)

| المتغير | الوصف |
|---|---|
| `DATABASE_URL` | رابط الاتصال بقاعدة البيانات (PostgreSQL في الإنتاج) |
| `SECRET_KEY` / `JWT_SECRET_KEY` | مفاتيح تشفير الجلسة والتوكينات |
| `JWT_EXPIRES_HOURS` | مدة صلاحية توكن الدخول |
| `SESSION_COOKIE_SECURE` | `True` لو الموقع HTTPS |
| `ADMIN_USERNAME` / `ADMIN_EMAIL` / `ADMIN_PASSWORD` | بيانات إنشاء حساب الأدمن الأول (لو `ADMIN_PASSWORD` فاضي، مفيش حساب أدمن هيتعمل تلقائيًا) |
| `MAX_UPLOAD_SIZE_MB` | الحد الأقصى لحجم صورة المنتج |
| `S3_BUCKET` وما يتبعها | اختياري: تخزين الصور على S3 بدل القرص المحلي |
| `RATELIMIT_STORAGE_URI` | مكان تخزين عدّادات Rate Limiting (`memory://` للتطوير، Redis في الإنتاج) |
| `LOG_LEVEL` / `LOG_FILE` | إعدادات تسجيل الأحداث |

## قاعدة البيانات والترحيلات (Migrations)

المشروع بيستخدم Flask-Migrate (Alembic). عند أي تعديل مستقبلي على `models.py`:

```bash
flask db migrate -m "وصف التعديل"
flask db upgrade
```

migration أولى (`migrations/versions/0001_initial.py`) موجودة بالفعل وبتنشئ كل الجداول والقيود.

## الاختبارات

```bash
pip install -r requirements-dev.txt
pytest
```

## الأمان

- كلمات المرور مشفّرة (`werkzeug.security`)، مفيش كلمة مرور محفوظة كنص صريح.
- الدخول عبر JWT محفوظ في Cookie بخاصية `HttpOnly` (الجافاسكريبت في المتصفح ماينفعش يقراه).
- حماية CSRF بنمط Double-Submit Cookie على كل طلب بيغيّر بيانات (POST/PUT/DELETE).
- حد أقصى لمحاولات تسجيل الدخول والتسجيل (Rate Limiting) لمنع Brute Force.
- التوكينات قابلة للإلغاء الفوري عند تسجيل الخروج (Blacklist في قاعدة البيانات).
- تحقق صارم من نوع وحجم أي صورة مرفوعة، واسم ملف عشوائي لمنع الكتابة فوق ملف موجود.
- قيود حقيقية على مستوى قاعدة البيانات (NOT NULL, CHECK, UNIQUE, Foreign Keys) مش بس على مستوى الكود.

### ملاحظة مهمة

الأزرار اللي بتمنع الزر اليمين أو فتح Developer Tools (في `script.js`) دي **رادع بسيط فقط وليست حماية حقيقية** — أي حد عنده معرفة بسيطة يقدر يتخطاها، ومفيش طريقة تقنية تمنع فعليًا رؤية كود أي موقع ويب أو أخذ لقطة شاشة له. الحماية الفعلية هي في الباك اند (منطق الأعمال، الأسرار، التحقق من الصلاحيات) — وده موجود بالفعل.
