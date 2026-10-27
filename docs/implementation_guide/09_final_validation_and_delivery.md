# مرحله ۹ - کنترل کیفیت نهایی و تحویل

<div dir="rtl" align="right">

## ۱. هدف مرحله

پیش از تحویل، مطمئن شویم همه‌چیز واقعاً کار می‌کند: نوتبوک‌ها از ابتدا اجرا می‌شوند،
آزمون‌ها سبز هستند، اعداد سازگارند، گزارش خوانا است و بسته ZIP کامل و بدون داده
حساس است.

## ۲. مسئول اصلی و بازبین

- مسئول اصلی: **Member C**
- بازبین: **Member A** و **Member B**
- تأییدکننده نهایی: هر سه عضو

## ۳. پیش‌نیازها

- مراحل ۰ تا ۸ ادغام شده باشند
- `main` آخرین نسخه پایدار باشد

## ۴. شاخه Git

```bash
git checkout main && git pull origin main
git checkout -b release/v1.0
```

## ۵. فایل‌های موردنیاز

| فایل | کار |
| :--- | :--- |
| `docs/validation/final_validation_report.md` | نتیجه هر بررسی با وضعیت PASS/FAIL/BLOCKED |
| `scripts/build_deliverables.py` | ساخت بسته ZIP |
| `deliverables/README.md` | توضیح محتوای بسته تحویل |
| `deliverables/olist-pro-deliverables.zip` | بسته نهایی |

## ۶. محتوای مورد انتظار

### شش ممیزی الزامی

۱. **ممیزی تحلیل‌ها:** همه سؤال‌های دوره پاسخ داده شده‌اند؟ حداقل سه تحلیل ترکیبی
   اجرا شده؟ درصدها و مخرج‌ها درست‌اند؟ پیامدهای اتصال بررسی شده‌اند؟
۲. **ممیزی کد:** نوتبوک‌ها از ابتدا اجرا می‌شوند؟ مسیرها قابل حمل‌اند؟ توابع مشترک
   آزمون‌پذیرند؟ کد تکراری غیرضروری وجود ندارد؟
۳. **ممیزی نمودارها:** عنوان، برچسب محور، واحد، ترتیب صحیح روند و رتبه، خوانایی و
   انطباق تفسیر با داده.
۴. **ممیزی گزارش:** پنج یافته، شواهد عددی، سه پیشنهاد، خوانایی PDF، عدم فراتر رفتن
   نتیجه‌گیری از داده.
۵. **ممیزی Git و مستندات:** وضعیت مخزن روشن، `.gitignore` درست، داده ناخواسته وارد
   Git نشده، ساختار شاخه‌ها مشخص، راهنمای بازسازی کامل، README با وضعیت واقعی
   منطبق، دستورالعمل ZIP آماده.
۶. **ممیزی بسته تحویل:** ZIP شامل همه فایل‌های ضروری و **بدون** داده حجیم، محیط
   مجازی، کش و فایل حساس.

### قاعده گزارش اعتبارسنجی

برای هر بررسی یکی از این وضعیت‌ها ثبت می‌شود: `PASS`، `FAIL`، `BLOCKED`،
`NOT APPLICABLE`. برای هر `FAIL` یا `BLOCKED` علت و اقدام لازم نوشته می‌شود.
**تا زمانی که آزمون لازم اجرا نشده، نتیجه PASS اعلام نمی‌شود.**

### محتوای مجاز و غیرمجاز در ZIP

| مجاز | غیرمجاز |
| :--- | :--- |
| کد `src/` و `scripts/` | `data/raw/*.csv` (حجیم؛ مسیر تهیه در `data/README.md`) |
| ۱۳ نوتبوک با خروجی | `data/interim/`, `data/processed/` |
| گزارش MD و PDF | `.venv/`, `__pycache__/`, `.ipynb_checkpoints/` |
| ۳۱ نمودار و ۵۸ جدول تحلیل | هر فایل کلید، رمز یا اطلاعات حساس |
| آزمون‌ها و مستندات | `artifacts/` موقت |

## ۷. دستورات ترمینال

### ویندوز (PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1

# ۱. دروازه کیفیت داده
python scripts\validate_data.py

# ۲. آزمون‌ها
python -m pytest -q

# ۳. بازسازی کامل از صفر (خط لوله + نوتبوک + گزارش)
python scripts\run_all.py

# ۴. ساخت بسته تحویل
python scripts\build_deliverables.py

# ۵. بررسی محتوای ZIP
Expand-Archive deliverables\olist-pro-deliverables.zip -DestinationPath $env:TEMP\zipcheck -Force
Get-ChildItem $env:TEMP\zipcheck -Recurse | Measure-Object
```

### بررسی نبود داده حساس در ZIP (لینوکس / مک)

```bash
unzip -l deliverables/olist-pro-deliverables.zip | head -40
unzip -l deliverables/olist-pro-deliverables.zip | grep -Ei "\.env|key|token|secret|\.csv" || echo "no sensitive or raw data files"
```

## ۸. آزمون‌ها

| آزمون | دستور | معیار قبولی |
| :--- | :--- | :--- |
| دروازه داده | `python scripts/validate_data.py` | کد خروجی ۰ و همه بررسی‌ها PASS |
| آزمون واحد | `python -m pytest -q` | ۵۶ آزمون PASS |
| اجرای نوتبوک‌ها | `python scripts/execute_notebooks.py` | ۱۳/۱۳ اجرا، صفر خطا |
| بازسازی از صفر | `python scripts/run_all.py` | پایان بدون خطا |
| ساخت گزارش | `python scripts/build_report.py` | MD و PDF تولید شوند |
| سالم بودن ZIP | باز کردن بسته | همه فایل‌های ضروری حاضر |

## ۹. خروجی مورد انتظار (اعداد واقعی تأییدشده)

| مورد | مقدار |
| :--- | ---: |
| بررسی‌های دروازه داده | ۲۲ بررسی، همه PASS |
| آزمون‌های واحد | ۵۶ آزمون، همه PASS |
| نوتبوک اجراشده | ۱۳ از ۱۳ |
| نمودار تولیدشده | ۳۱ |
| جدول تحلیل تولیدشده | ۵۸ |
| اندازه گزارش PDF | حدود ۴۶۶ کیلوبایت |

> اندازه فایل ZIP به‌صورت عدد ثابت در مستند ثبت نمی‌شود؛ چون با هر اجرا کمی
> تغییر می‌کند. اندازه واقعی را از خروجی `build_deliverables.py` بخوانید.

## ۱۰. پیام Commit پیشنهادی

```text
chore: add final validation audit and deliverable packaging

- record the outcome of every audit check with PASS/FAIL/BLOCKED status
- add build_deliverables.py packing source, notebooks and reports only
- exclude raw data, caches and virtual environments from the archive
```

## ۱۱. Push و Pull Request

```bash
git add docs/validation/final_validation_report.md scripts/build_deliverables.py \
        deliverables/README.md
git commit -m "chore: add final validation audit and deliverable packaging"
git push -u origin release/v1.0
```

PR نهایی را به `main` بسازید و در توضیحات آن نتیجه هر شش ممیزی را خلاصه کنید.

## ۱۲. مواردی که بازبین باید کنترل کند

۱. نتیجه هر بررسی با شاهد واقعی پشتیبانی شود (خروجی دستور، نه ادعا).
۲. هیچ بررسی‌ای بدون اجرا PASS علامت نخورده باشد.
۳. ZIP داده خام، کش یا فایل حساس نداشته باشد.
۴. README با وضعیت واقعی پروژه منطبق باشد (تحلیلی که کامل نیست، کامل معرفی نشده
   باشد).
۵. موارد باقی‌مانده و PARTIAL صریح فهرست شده باشند.
۶. هیچ تاریخچه ساختگی یا فعالیت جعلی به اعضا نسبت داده نشده باشد.

## ۱۳. معیار پذیرش

- [ ] `validate_data.py` با کد خروجی ۰ اجرا شود
- [ ] `pytest` سبز باشد (۵۶ آزمون)
- [ ] همه ۱۳ نوتبوک بدون خطا اجرا شوند
- [ ] گزارش MD و PDF موجود و خوانا باشند
- [ ] ZIP ساخته شده و محتوای آن مطابق فهرست مجاز باشد
- [ ] گزارش اعتبارسنجی کامل و صادقانه نوشته شده باشد
- [ ] PR نهایی ادغام شده باشد

## ۱۴. شرط پایان پروژه

پروژه زمانی «تکمیل» اعلام می‌شود که همه شرط‌های معیار پذیرش بالا برقرار باشند و
`docs/validation/final_validation_report.md` هیچ مورد `FAIL` یا `BLOCKED`
نداشته باشد. موارد `PARTIAL` مجازند، به شرط آنکه علت و اقدام لازم برای هرکدام
صریح نوشته شده باشد.

</div>
