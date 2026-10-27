# مرحله ۲ - فهرست و شناخت داده‌ها

<div dir="rtl" align="right">

## ۱. هدف مرحله

پیش از تحلیل، باید بدانیم دقیقاً چه داده‌ای داریم: هر جدول چند ردیف و چند ستون
دارد، هر سطر چه معنایی دارد، کلیدها کدام‌اند، چه مقداری گم است و چه مشکلی در کیفیت
داده وجود دارد. خروجی این مرحله، **قرارداد داده** است که همه تحلیل‌های بعدی بر آن
بنا می‌شود.

## ۲. مسئول اصلی و بازبین

- مسئول اصلی: **Member A**
- بازبین: **Member B**
- مشورت: **Member C** (برای اطمینان از کافی بودن داده در تحلیل‌های محصول و ارسال)

## ۳. پیش‌نیازها

- مرحله ۰ و ۱ کامل شده باشند
- هر ۹ فایل CSV در `data/raw/` حاضر باشند

## ۴. شاخه Git

```bash
git checkout main && git pull origin main
git checkout -b feat/data-inventory
```

## ۵. فایل‌های موردنیاز

| فایل | کار |
| :--- | :--- |
| `src/olist_analysis/data_loader.py` | بارگذاری CSV + کش parquet با اعتبارسنجی مهر زمانی |
| `src/olist_analysis/data_quality.py` | پروفایل ستون، گم‌شده، تکرار، یکتایی کلید، یکپارچگی ارجاعی |
| `scripts/validate_data.py` | دروازه کیفیت داده با کد خروجی |
| `notebooks/00_data_inventory.ipynb` | روایت فهرست و پروفایل داده |
| `notebooks/01_data_understanding.ipynb` | روایت روابط و اعتبارسنجی کلیدها |
| `docs/data_dictionary.md` | فرهنگ داده |
| `docs/data_relationships.md` | نمودار و قواعد روابط |

## ۶. محتوای مورد انتظار

### `data_loader.py`

- `file_inventory()`: فهرست فایل‌ها با حجم دقیق و ۱۶ کاراکتر اول SHA-256
- `load_raw_tables(names=None)`: بارگذاری گروهی با کش parquet
- کش باید با **اندازه و زمان تغییر** فایل خام اعتبارسنجی شود؛ پس تغییر داده، کش
  را خودکار باطل کند
- ستون‌های تاریخ در این مرحله **متن** بمانند تا کیفیت خام قابل مشاهده باشد

### `data_quality.py`

این توابع را بسازید: `column_profile`، `missing_values_table`،
`duplicate_rows_table`، `key_uniqueness`، `referential_integrity`،
`value_counts_table`، `numeric_range_check`، `datetime_parse_report`،
`group_size_distribution`.

نکته طراحی مهم: هر تابع یک DataFrame برگرداند (نه چاپ کن)، تا خروجی مستقیماً به
`reports/tables/` نوشته شود و در نوتبوک و مستندات قابل بازاستفاده باشد.

### دو کنترل حیاتی که در پیاده‌سازی مرجع به مسئله تبدیل شدند

۱. **شمارش سطر با خط فایل اشتباه است.** فایل `olist_order_reviews_dataset.csv`
   ۱۰۴٬۷۲۰ خط فیزیکی دارد اما ۹۹٬۲۲۴ ردیف منطقی، چون متن بعضی نظرات شامل خط
   جدید است. همیشه با `pandas.read_csv` یا ماژول `csv` بشمارید.
۲. **کلید اعلام‌شده لزوماً یکتا نیست.** `review_id` به‌عنوان کلید اصلی اعلام شده
   اما ۷۸۹ مقدار آن در ۱٬۶۰۳ سطر تکرار شده است. حتماً یکتایی را **اعتبارسنجی**
   کنید و فرض نکنید.

## ۷. دستورات ترمینال

### ویندوز (PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1

# فهرست و حجم فایل‌ها
Get-ChildItem data\raw\*.csv | Select-Object Name, Length

# اجرای دروازه کیفیت داده
python scripts\validate_data.py
```

### بررسی سریع مستقل (لینوکس / مک)

```bash
ls -la data/raw/
wc -l data/raw/*.csv
du -sh data/raw/
```

### تولید جدول‌های شناخت داده

```bash
python scripts/run_all.py --quick
```

سپس در نوتبوک‌ها جدول‌های `00_column_profiles`, `00_missing_values`,
`00_duplicate_rows`, `00_key_uniqueness`, `00_referential_integrity`,
`01_file_inventory`, `01_table_shapes` را نمایش دهید.

## ۸. آزمون‌ها

```bash
python -m pytest tests/test_data_loading.py tests/test_data_quality.py -q
```

انتظار: همه PASS. این آزمون‌ها روی داده مصنوعی کوچک اجرا می‌شوند تا منطق توابع
مستقل از داده واقعی بررسی شود.

## ۹. خروجی مورد انتظار (اعداد واقعی تأییدشده)

| مورد | مقدار |
| :--- | ---: |
| حجم کل داده خام | ۱۲۰.۲۵ مگابایت |
| بزرگ‌ترین فایل | `olist_geolocation_dataset.csv` با ۵۸.۴۴ مگابایت |
| سطر سفارش‌ها / مشتریان | ۹۹٬۴۴۱ / ۹۹٬۴۴۱ |
| سطر اقلام سفارش | ۱۱۲٬۶۵۰ |
| سطر پرداخت‌ها | ۱۰۳٬۸۸۶ |
| سطر منطقی نظرات (در برابر ۱۰۴٬۷۲۰ خط فیزیکی) | ۹۹٬۲۲۴ |
| سطر محصولات / فروشندگان / ژئولوکیشن / ترجمه | ۳۲٬۹۵۱ / ۳٬۰۹۵ / ۱٬۰۰۰٬۱۶۳ / ۷۱ |
| ردیف کاملاً تکراری در ۷ جدول اصلی | صفر |
| ردیف کاملاً تکراری در ژئولوکیشن | ۲۶۱٬۸۳۱ (۲۶.۱۸٪) |
| شناسه یتیم در ۶ رابطه | صفر |

## ۱۰. پیام Commit پیشنهادی

```text
feat: add data inventory, quality probes and relationship validation

- add portable CSV loader with mtime-validated parquet cache
- add reusable quality probes (missingness, keys, referential integrity)
- document the data dictionary and the real table relationships
- record that review_id is not unique and geolocation has 261k duplicate rows
```

## ۱۱. Push و Pull Request

```bash
git add src/olist_analysis/data_loader.py src/olist_analysis/data_quality.py \
        scripts/validate_data.py notebooks/00_data_inventory.ipynb \
        notebooks/01_data_understanding.ipynb docs/data_dictionary.md \
        docs/data_relationships.md
git commit -m "feat: add data inventory, quality probes and relationship validation"
git push -u origin feat/data-inventory
```

PR را با برچسب `data` بسازید و Member B را بازبین کنید. در توضیحات PR، جدول
سطر/ستون هر جدول را کپی کنید.

## ۱۲. مواردی که بازبین باید کنترل کند

۱. تعداد سطر هر جدول با `wc -l` (با در نظر گرفتن خطوط چندخطی) سازگار باشد.
۲. یکتایی هر کلید اعلام‌شده اجرا و نتیجه ثبت شده باشد؛ استثنا مستند شده باشد.
۳. یکپارچگی ارجاعی همه ۶ رابطه بررسی شده باشد.
۴. درصد گم‌شده‌ها برای ستون‌های مهم محاسبه شده باشد.
۵. نمودار روابط با داده واقعی تطبیق داشته باشد (نه فقط با تصویر صورت‌مسئله).
۶. توابع کیفیت داده **برگرداننده مقدار** باشند، نه چاپ‌کننده.

## ۱۳. معیار پذیرش

- [ ] هر ۹ جدول با سطر/ستون، نوع داده و درصد گم‌شده مستند شده است
- [ ] کلید اصلی هر جدول اعتبارسنجی شده و تکرار `review_id` مستند شده است
- [ ] صفر شناسه یتیم در همه روابط تأیید شده باشد
- [ ] فرهنگ داده کامل و قابل ارجاع باشد
- [ ] نوتبوک ۰۰ و ۰۱ از ابتدا و بدون خطا اجرا شوند
- [ ] PR تأیید و ادغام شده باشد

## ۱۴. شرط شروع مرحله بعد

تا وقتی تکرار `review_id` و ساختار چندردیفی ژئولوکیشن **مستند نشده باشد**، وارد
مرحله پاک‌سازی نشوید؛ چون تصمیم‌های پاک‌سازی مستقیماً بر این دو مسئله بنا
می‌شوند.

</div>
