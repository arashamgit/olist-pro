# مرحله ۳ - پاک‌سازی و ساخت ویژگی‌های تحلیلی

<div dir="rtl" align="right">

## ۱. هدف مرحله

تبدیل داده خام و ناسازگار به چهار گرین تحلیلی تمیز، با تعریف‌های قفل‌شده. این
مرحله **گلوگاه پروژه** است: تا وقتی گرین‌ها و تعریف‌ها تثبیت نشوند، هیچ نوتبوک
تحلیلی نباید نهایی شود.

## ۲. مسئول اصلی و بازبین

- مسئول اصلی: **Member A**
- بازبین: **Member B** و **Member C**
- تأییدکننده: هر سه عضو (چون همه بر این تعریف‌ها بنا می‌کنند)

## ۳. پیش‌نیازها

- مرحله ۲ کامل شده باشد (قرارداد داده تثبیت‌شده)
- همه تصمیم‌های پاک‌سازی مستند شده باشند

## ۴. شاخه Git

```bash
git checkout main && git pull origin main
git checkout -b feat/data-cleaning
```

## ۵. فایل‌های موردنیاز

| فایل | کار |
| :--- | :--- |
| `src/olist_analysis/cleaning.py` | پاک‌سازی هر جدول + ثبت شمارنده تصمیم‌ها |
| `src/olist_analysis/features.py` | ساخت چهار گرین تحلیلی + کنترل گرین اتصال |
| `notebooks/02_data_cleaning.ipynb` | روایت تصمیم‌ها با شواهد |
| `docs/cleaning_decisions.md` | مستند شش‌بندی هر تصمیم |
| `data/processed/_manifest.json` | ثبت تعداد ردیف و مهر زمانی منبع |

## ۶. محتوای مورد انتظار

### سه قاعده پایه `cleaning.py`

۱. داده خام هرگز تغییر نمی‌کند (همیشه `.copy()`).
۲. هیچ ردیفی به دلیل گم‌بودن مقدار حذف نمی‌شود.
۳. هر تصمیم شمارنده عددی دارد (`CleaningLog`) تا شواهدش قابل ثبت باشد.

### تصمیم‌هایی که باید بگیرید و دلیلشان

| مسئله | تصمیم درست | چرا |
| :--- | :--- | :--- |
| تاریخ‌های گم‌شده سفارش | نگه‌داشتن `NaT` | گم‌بودن ساختاری است؛ سفارش لغوشده تاریخ تحویل ندارد |
| `review_id` تکراری (۷۸۹ شناسه) | نگه‌داشتن همه، تغییر هویت به `(review_id, order_id)` | هر ردیف به سفارش واقعی متفاوتی تعلق دارد |
| چند نظر برای یک سفارش (۵۴۷ مورد) | نگه‌داشتن جدیدترین `review_answer_timestamp` | قطعی، بدون ساخت مقدار ساختگی |
| ۶۱۰ محصول بدون دسته‌بندی | برچسب `unknown` | فروش واقعی دارند؛ حذفشان مبلغ کل را کم‌نمایی می‌کند |
| دو دسته بدون ترجمه | بازگشت به نام پرتغالی + پرچم | هیچ فروشی از دست نمی‌رود |
| ژئولوکیشن (۲۶۱٬۸۳۱ سطر تکراری) | تجمیع به میانه مختصات برای هر کد پستی | اتصال خام ردیف‌ها را تا ۱٬۱۴۶ برابر می‌کند |
| ۳۱ مختصات خارج از مرز برزیل | حذف پیش از تجمیع | مقادیر ناممکن |
| ۲ پرداخت با صفر قسط | نگه‌داشتن در مبلغ، حذف از توزیع اقساط | بخش دوم پرداخت چندمرحله‌ای است |
| ۹ پرداخت با مبلغ صفر | نگه‌داشتن | قلم حسابداری واقعی است |

### چهار گرین در `features.py`

| گرین | ستون کلید | تعداد ردیف |
| :--- | :--- | ---: |
| `order_features` | `order_id` | ۹۹٬۴۴۱ |
| `item_features` | `order_id` + `order_item_id` | ۱۱۲٬۶۵۰ |
| `order_category` | `order_id` + `category_label` | ۹۹٬۴۷۰ |
| `order_seller` | `order_id` + `seller_id` | ۱۰۰٬۰۱۰ |

دو گرین آخر برای این ساخته می‌شوند که **یک امتیاز در هر گروه فقط یک بار** شمرده
شود. اگر امتیاز را روی ردیف‌های اقلام حساب کنید، سفارشی که سه قلم از یک دسته
دارد امتیازش سه بار شمرده می‌شود.

### تعریف حیاتی: تأخیر بر پایه تاریخ تقویمی

```python
delay = (delivered.dt.normalize() - estimated.dt.normalize()).dt.days
```

اگر به‌جای این، اختلاف خام زمان‌سنجی بگیرید، چون `order_estimated_delivery_date`
همیشه ساعت ۰۰:۰۰:۰۰ دارد:

- گروه «به‌موقع» **خالی** می‌شود (هیچ سفارشی دقیقاً در نیمه‌شب تحویل نمی‌شود)؛
- ۷٬۸۲۶ سفارش دیرکرددار شمرده می‌شوند به‌جای ۶٬۵۳۴؛
- ۱٬۲۹۲ سفارشی که در همان **روز** وعده تحویل شده‌اند، به‌اشتباه دیرکرددار
  محسوب می‌شوند.

### کنترل خودکار گرین (نکته مهندسی مهم)

در `features.py` یک تابع کمکی بسازید که پیش از هر اتصال، نوع رابطه را اعلام و
تعداد ردیف پیش و پس از اتصال را مقایسه کند و در صورت اختلاف خطا بدهد:

```python
def _merge(frame, other, on, how, validate, label):
    before = len(frame)
    merged = frame.merge(other, on=on, how=how, validate=validate)
    assert len(merged) == before, f"Join '{label}' changed row count"
    return merged
```

این یک تابع کوچک، در عمل جلوی بیشتر اشتباه‌های خاموش اتصال را می‌گیرد.

## ۷. دستورات ترمینال

```powershell
.\.venv\Scripts\Activate.ps1

# ساخت گرین‌ها و ذخیره در data\processed\
python -c "import sys; sys.path.insert(0,'src'); from olist_analysis.features import load_dataset, save_dataset; d = load_dataset(force_rebuild=True); save_dataset(d); print(len(d.orders), len(d.items))"

# اجرای آزمون‌های ویژگی
python -m pytest tests\test_features.py -q
```

## ۸. آزمون‌ها

```bash
python -m pytest tests/test_features.py -q
```

آزمون‌هایی که **باید** بنویسید (روی داده مصنوعی کوچک):

| آزمون | چه چیزی را قفل می‌کند |
| :--- | :--- |
| `test_delay_is_computed_on_calendar_dates` | سفارش تحویل‌شده در همان روز وعده، `on_time` است |
| `test_delivery_duration_uses_purchase_and_delivery_timestamps` | مدت تحویل درست محاسبه می‌شود |
| `test_reviews_are_deduplicated_to_one_row_per_order` | جدیدترین نظر برنده می‌شود |
| `test_category_and_seller_grains_have_one_score_per_group` | امتیاز در گروه تکرار نمی‌شود |
| `test_joins_do_not_change_row_counts` | اتصال‌ها ردیف اضافه نمی‌کنند |
| `test_geolocation_is_collapsed_to_one_row_per_zip_prefix` | تجمیع ژئولوکیشن درست است |
| `test_order_totals_reconcile_with_item_lines` | جمع اقلام با کل سفارش می‌خواند |
| `test_untranlated_category_falls_back_to_portuguese_name` | بازگشت نام دسته‌بندی |

## ۹. خروجی مورد انتظار (اعداد واقعی تأییدشده)

| مورد | مقدار |
| :--- | ---: |
| سفارش تحویل‌شده / با تاریخ تحویل معتبر | ۹۶٬۴۷۸ / ۹۶٬۴۷۰ |
| سفارش دیرکرددار | ۶٬۵۳۴ (۶.۷۷٪ از ۹۶٬۴۷۰) |
| سفارش دقیقاً به‌موقع | ۱٬۲۹۲ (۱.۳۴٪) |
| سفارش زودتر از موعد | ۸۸٬۶۴۴ (۹۱.۸۹٪) |
| سفارش در پنجره تحلیلی | ۹۹٬۰۹۲ (۹۹.۶۵٪) |
| ردیف نظرات پس از کاهش | ۹۸٬۶۷۳ (۵۵۱ ردیف کنار گذاشته شد) |
| ردیف مرجع ژئولوکیشن پس از تجمیع | ۱۹٬۰۱۱ (از ۱۹٬۰۱۵ پیش‌شمار) |
| جمع مبلغ اقلام | ۱۳٬۵۹۱٬۶۴۳.۷۰ رئال |
| جمع کرایه | ۲٬۲۵۱٬۹۰۹.۵۴ رئال |
| میانگین مدت تحویل | ۱۲.۵۶ روز (میانه ۱۰.۲۲) |

## ۱۰. پیام Commit پیشنهادی

```text
feat: add documented cleaning pipeline and analysis feature grains

- add cleaning.py with a numeric log for every decision (no rows deleted)
- add features.py building four grains with join-cardinality guards
- define delay on calendar dates, not raw timestamps
- reduce reviews to one row per order to prevent score duplication
- collapse geolocation to one centroid per zip prefix
```

## ۱۱. Push و Pull Request

```bash
git add src/olist_analysis/cleaning.py src/olist_analysis/features.py \
        notebooks/02_data_cleaning.ipynb docs/cleaning_decisions.md
git commit -m "feat: add documented cleaning pipeline and analysis feature grains"
git push -u origin feat/data-cleaning
```

در توضیحات PR، جدول تصمیم‌ها و شمارنده‌های `02_cleaning_summary` را بگذارید تا
بازبین بدون اجرای کد بتواند کنترل کند.

## ۱۲. مواردی که بازبین باید کنترل کند

۱. تعداد ردیف چهار گرین با اعداد مرحله ۲ سازگار باشد.
۲. هیچ ردیفی در پاک‌سازی حذف نشده باشد (به‌جز کاهش کنترل‌شده نظرات و تجمیع
   ژئولوکیشن که مستند شده‌اند).
۳. تعریف تأخیر تاریخ‌محور باشد، نه زمان‌سنجی محور.
۴. جمع‌های تجمیعی با جداول پایه دقیقاً برابر باشند.
۵. هر تصمیم شش بند لازم را داشته باشد (مشکل، شواهد، گزینه‌ها، تصمیم، دلیل، تأثیر).
۶. آزمون‌های `test_features.py` سبز باشند.

## ۱۳. معیار پذیرش

- [ ] چهار گرین با گرین و کلید مستند ساخته شده باشند
- [ ] تعریف تأخیر و طبقه‌بندی آن در یک فایل مستند قفل شده باشد
- [ ] کنترل گرین اتصال در کد فعال باشد
- [ ] `tests/test_features.py` سبز باشد
- [ ] `data/processed/` ساخته شده و در `.gitignore` باشد
- [ ] PR تأیید و ادغام شده باشد

## ۱۴. شرط شروع مرحله بعد

پس از ادغام این مرحله، **توسعه موازی سه عضو آزاد می‌شود**. از این نقطه هیچ عضوی
نباید منتظر دیگری بماند: گرین‌ها، تعریف‌ها و توابع مشترک تثبیت شده‌اند و هر
نوتبوک تحلیلی فقط از آن‌ها استفاده می‌کند.

</div>
