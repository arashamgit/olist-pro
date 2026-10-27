# مرحله ۰ - راه‌اندازی محیط

<div dir="rtl" align="right">

## ۱. هدف مرحله

پیش از هر تحلیل، باید مطمئن شویم هر سه عضو می‌توانند داده را بارگذاری کنند و همان
نسخه کتابخانه‌ها را دارند. هدف این مرحله حذف کامل جمله «روی سیستم من کار می‌کند»
است.

## ۲. مسئول اصلی و بازبین

- مسئول اصلی: **Member A**
- بازبین: **Member C**
- تأییدکننده نهایی: هر سه عضو (چون محیط مشترک است)

## ۳. پیش‌نیازها

- دسترسی به مخزن GitHub
- Python 3.11 یا بالاتر نصب‌شده
- دسترسی به فایل‌های داده در `data/raw/`

## ۴. شاخه Git

```bash
git checkout main
git pull origin main
git checkout -b chore/project-setup
```

## ۵. فایل‌های موردنیاز

| فایل | وضعیت | کار |
| :--- | :--- | :--- |
| `requirements.txt` | ایجاد | قفل نسخه وابستگی‌ها |
| `pyproject.toml` | ایجاد | فراداده پروژه و پیکربندی pytest |
| `.gitignore` | ویرایش | کنارگذاشتن داده میانی، محیط و بسته ZIP |
| `src/olist_analysis/__init__.py` | ایجاد | معرفی بسته |
| `src/olist_analysis/config.py` | ایجاد | مسیرهای قابل حمل و فراداده جدول‌ها |
| `assets/fonts/Vazirmatn-Regular.ttf` | افزودن | فونت فارسی برای نمودار و PDF |

## ۶. محتوای مورد انتظار

**`src/olist_analysis/config.py`** باید حداقل این موارد را داشته باشد:

- محاسبه `PROJECT_ROOT` از محل خود فایل (نه مسیر مطلق):
  ```python
  PROJECT_ROOT = Path(__file__).resolve().parents[2]
  ```
- مسیرهای `data/raw`, `data/interim`, `data/processed`, `reports/figures`,
  `reports/tables`
- ساختار `TableSpec` برای هر جدول با: نام، نام فایل، کلید اصلی اعلام‌شده،
  ستون‌های تاریخ و توضیح یک‌خطی
- دیکشنری `RAW_TABLES` با ۹ کلید
- آستانه‌های تحلیل: `MIN_REVIEWS_PER_GROUP = 30`،
  `MIN_ORDERS_PER_STATE = 100`، `MIN_ORDERS_PER_MONTH = 100`
- پنجره تحلیلی: `CORE_WINDOW_START = "2017-01-01"` و
  `CORE_WINDOW_END = "2018-08-31"` همراه با دلیل مستند در کامنت

**`requirements.txt`** باید نسخه‌ها را قفل کند (نسخه‌های واقعی همین پروژه):

```text
pandas==3.1.0
numpy==2.5.4
matplotlib==3.11.2
seaborn==0.13.2
pyarrow==22.0.0
nbformat==5.11.1
nbclient==0.11.0
ipykernel==7.1.0
pytest==9.1.1
reportlab==5.1.0
arabic-reshaper==3.0.0
python-bidi==0.6.6
```

> اگر نسخه‌ای روی سیستم شما موجود نبود، نسخه‌های سازگار نزدیک را نصب کنید و
> نسخه نصب‌شده را در همان فایل ثبت کنید تا هر سه عضو یکی باشند.

**`.gitignore`** باید این موارد را کنار بگذارد:

```text
/data/interim/
/data/processed/
/data/raw/_cache/
.venv/
venv/
__pycache__/
.ipynb_checkpoints/
*.tmp
*.log
/deliverables/*.zip
```

نکته صریح: قرار داشتن داده خام در `.gitignore` **ضروری نیست** و در این پروژه
داده خام کامیت شده است. `.gitignore` تنها از کامیت داده‌های قابل بازتولید و حجیم
جلوگیری می‌کند.

## ۷. دستورات ترمینال

### ویندوز (PowerShell)

```powershell
Set-Location <مسیر مخزن>
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import pandas, matplotlib, reportlab, arabic_reshaper, bidi; print('ok')"
```

### لینوکس / مک (bash)

```bash
cd <مسیر مخزن>
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import pandas, matplotlib, reportlab, arabic_reshaper, bidi; print('ok')"
```

### گرفتن فونت فارسی

فونت Vazirmatn باید در `assets/fonts/Vazirmatn-Regular.ttf` باشد. این فونت برای
نمایش صحیح حروف فارسی در نمودارها و PDF لازم است. اگر فایل نبود، می‌توانید هر
فونت فارسی دیگری با پشتیبانی عربی/فارسی استفاده کنید و مسیر آن را در
`config.PERSIAN_FONT_PATH` تغییر دهید.

بررسی سریع دسترسی فونت:

```bash
python -c "import sys; sys.path.insert(0,'src'); from olist_analysis.font_utils import persian_available; print('persian:', persian_available())"
```

## ۸. آزمون‌ها

```bash
python -m pytest tests/test_data_loading.py -q
python scripts/validate_data.py
```

در این مرحله انتظار می‌رود بررسی‌های مربوط به حضور فایل‌ها و شکل جداول PASS شوند.

## ۹. خروجی مورد انتظار

- محیط مجازی فعال با همه وابستگی‌ها
- `python -c "import pandas; print(pandas.__version__)"` نسخه ۳.۱.۰ را چاپ کند
- `persian_available()` مقدار `True` بدهد
- `python scripts/validate_data.py` بررسی «حضور هر ۹ فایل» را PASS کند

## ۱۰. پیام Commit پیشنهادی

```text
chore: pin analysis environment and portable project paths

- add requirements.txt and pyproject.toml with pinned versions
- add olist_analysis.config with repo-relative paths and table metadata
- bundle Vazirmatn font for Persian chart and PDF rendering
- extend .gitignore for intermediate data and deliverables archives
```

## ۱۱. Push و Pull Request

```bash
git add requirements.txt pyproject.toml .gitignore src/ assets/
git commit -m "chore: pin analysis environment and portable project paths"
git push -u origin chore/project-setup
```

سپس در GitHub یک Pull Request از `chore/project-setup` به `main` بسازید و
Member C را به‌عنوان بازبین انتخاب کنید.

## ۱۲. مواردی که بازبین باید کنترل کند

۱. هیچ مسیر مطلق ویندوزی (`C:\Users\...`) در کد نباشد.
۲. نسخه‌ها در `requirements.txt` قفل شده باشند.
۳. `.gitignore` داده میانی و پردازش‌شده را کنار بگذارد، اما داده خام را ناخواسته
   حذف نکرده باشد.
۴. فونت در `assets/fonts/` حاضر و مسیر آن در `config` ثبت شده باشد.
۵. هیچ کلید، رمز یا اطلاعات حساسی کامیت نشده باشد.

## ۱۳. معیار پذیرش

- [ ] هر سه عضو بتوانند محیط را نصب و فعال کنند
- [ ] `persian_available()` روی هر سه سیستم `True` بدهد
- [ ] `python scripts/validate_data.py` بدون خطای غیرمنتظره اجرا شود
- [ ] `git status` پس از کامیت پاک باشد
- [ ] PR توسط بازبین تأیید و ادغام شده باشد

## ۱۴. شرط شروع مرحله بعد

پس از تأیید محیط، هر سه عضو باید بتوانند `load_raw_tables()` را بدون خطا اجرا
کنند. اگر روی سیستمی عدد سطرها با بقیه متفاوت است، **پیش از رفتن به مرحله بعد**
علت را پیدا کنید؛ تفاوت در تعداد ردیف داده، همه نتایج بعدی را بی‌اعتبار می‌کند.

</div>
