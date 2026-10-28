# راهنمای بازسازی مرحله‌به‌مرحله پروژه olist-pro

<div dir="rtl" align="right">

## هدف این راهنما

این پوشه، مسیر ساخت پروژه را به مراحل کوچک، قابل اجرا و قابل ارزیابی تقسیم می‌کند.
هدف این است که هر سه عضو تیم بتوانند همین پروژه را روی شاخه‌های اختصاصی خودشان
بازسازی کنند، **بفهمند چرا هر بخش به این شکل طراحی شده** و رابطه میان
«سؤال کسب‌وکاری → داده → روش محاسبه → نمودار → نتیجه‌گیری» را ببینند.

این راهنما فقط فهرست دستور نیست. برای هر مرحله توضیح داده می‌شود که آن مرحله چه
مسئله‌ای را حل می‌کند و خروجی‌اش چگونه اعتبارسنجی می‌شود.

## وضعیت پیاده‌سازی مرجع

پیاده‌سازی مرجع (همین مخزن) کامل و اجراشده است. کدها در `src/olist_analysis/`
هستند و می‌توانید به آن‌ها ارجاع بدهید. **تاریخچه Git هیچ فعالیتی را به نام
اعضا جعل نکرده است**؛ برای بازسازی، هر عضو خودش شاخه می‌سازد و کامیت‌های واقعی
ثبت می‌کند. پیام کامیت پیشنهادی هر مرحله در همان مرحله آمده است.

## فهرست مراحل

| مرحله | فایل | مسئول اصلی | بازبین | خروجی |
| :--- | :--- | :--- | :--- | :--- |
| ۰ | [00_environment_setup.md](00_environment_setup.md) | Member A | Member C | محیط قابل اجرا |
| ۱ | [01_repository_setup.md](01_repository_setup.md) | Member A | Member C | اسکلت پروژه و قاعده Git |
| ۲ | [02_data_inventory_and_understanding.md](02_data_inventory_and_understanding.md) | Member A | Member B | NB 00 و 01، فرهنگ داده، روابط |
| ۳ | [03_data_cleaning_and_features.md](03_data_cleaning_and_features.md) | Member A | Member B, C | NB 02، `cleaning.py`، `features.py` |
| ۴ | [04_orders_and_customers_analysis.md](04_orders_and_customers_analysis.md) | A و B | C و A | NB 03 و 04 |
| ۵ | [05_products_and_payments_analysis.md](05_products_and_payments_analysis.md) | C و B | A و C | NB 05 و 06 |
| ۶ | [06_delivery_and_satisfaction_analysis.md](06_delivery_and_satisfaction_analysis.md) | C و B | B و C | NB 07، 08 و 09 |
| ۷ | [07_sellers_and_combined_analysis.md](07_sellers_and_combined_analysis.md) | C و هر سه | A | NB 10 و 11 |
| ۸ | [08_executive_report.md](08_executive_report.md) | هر سه | متقابل | NB 12، گزارش MD و PDF |
| ۹ | [09_final_validation_and_delivery.md](09_final_validation_and_delivery.md) | Member C | A و B | ممیزی نهایی و ZIP |

## ساختار ثابت هر فایل راهنما

هر مرحله دقیقاً این چهارده بخش را دارد:

۱. هدف مرحله
۲. مسئول اصلی و بازبین
۳. پیش‌نیازها
۴. شاخه Git
۵. فایل‌های موردنیاز
۶. محتوای مورد انتظار (با ارجاع دقیق به کد مرجع)
۷. دستورات ترمینال (PowerShell برای ویندوز و معادل bash)
۸. آزمون‌ها
۹. خروجی مورد انتظار (فقط اعداد واقعی تأییدشده)
۱۰. پیام Commit پیشنهادی
۱۱. Push و Pull Request
۱۲. مواردی که بازبین باید کنترل کند
۱۳. معیار پذیرش
۱۴. شرط شروع مرحله بعد

## قراردادهای مشترک پروژه

### مسیرها

```text
<repo>/                      ریشه مخزن
├── data/raw/                ۹ فایل CSV ورودی (دست‌نخورده)
├── data/interim/            کش و فایل میانی (در Git نیست)
├── data/processed/          گرین‌های تحلیلی (در Git نیست)
├── notebooks/               ۱۳ نوتبوک تحلیلی
├── src/olist_analysis/      کتابخانه قابل استفاده مجدد
├── tests/                   آزمون‌ها
├── reports/figures/         ۳۲ نمودار PNG + فایل توضیح هر نمودار
├── reports/tables/          ۵۸ جدول CSV (به‌همراه figure_manifest.csv)
├── reports/metrics.json     همه اعداد کلیدی در یک فایل
├── reports/executive_report.md و .pdf
├── docs/                    مستندات و راهنماها
└── deliverables/            بسته تحویل نهایی (ZIP)
```

هیچ مسیر مطلقی در کد وجود ندارد. `PROJECT_ROOT` در `config.py` از محل خود فایل
محاسبه می‌شود، پس پروژه روی ویندوز، لینوکس و مک بدون تغییر کد اجرا می‌شود.

### گرین‌های تحلیلی (قرارداد داده قفل‌شده)

| گرین | تعداد ردیف | کلید |
| :--- | ---: | :--- |
| `order_features` | ۹۹٬۴۴۱ | `order_id` |
| `item_features` | ۱۱۲٬۶۵۰ | `order_id` + `order_item_id` |
| `order_category` | ۹۹٬۴۷۰ | `order_id` + `category_label` |
| `order_seller` | ۱۰۰٬۰۱۰ | `order_id` + `seller_id` |

### تعریف‌های قفل‌شده

- تأخیر = (تاریخ تقویمی تحویل واقعی − تاریخ تقویمی تخمینی) به روز
- `early` اگر تأخیر < ۰ ، `on_time` اگر = ۰ ، `late` اگر > ۰
- بازه‌ها: به‌موقع یا زودتر / ۱-۳ روز / ۴-۷ روز / بیش از ۷ روز
- مبلغ فروش اقلام = مجموع `price` (بدون کرایه)، نه درآمد خالص
- حداقل نمونه: ۳۰ نظر برای مقایسه امتیاز، ۱۰۰ سفارش برای مقایسه ایالت

### قاعده طلایی کار تیمی

منطق تحلیل در `src/olist_analysis/` می‌ماند؛ نوتبوک‌ها فقط فراخوانی و تفسیر
می‌کنند. این تصمیم، تعارض Git در فایل‌های `.ipynb` را تقریباً به صفر می‌رساند و
باعث می‌شود عددی که در نوتبوک دیده می‌شود با عدد گزارش یکسان بماند.

### کتابخانه نمودار

همه نمودارها با **Matplotlib** رسم می‌شوند و فقط **یک** نمودار (ماتریس سال و ماه
سفارش‌ها، `fig_32_year_month_heatmap`) با **Seaborn** ساخته می‌شود. این تقسیم تصادفی
نیست: heatmap دقیقاً همان مقایسه‌ای است که بند ۵.۲ صورت‌مسئله می‌خواهد و Seaborn
نوار رنگ و مقدار هر خانه را بدون کد دستی می‌دهد. هر دو کتابخانه در `requirements.txt`
قفل شده‌اند و باید در همان مرحله ۴ پروژه ساخته شوند.

### هفت دستور پرکاربرد

```powershell
python scripts\validate_data.py        # بررسی سلامت داده و محیط
python scripts\run_all.py --quick      # خط لوله + گزارش (بدون نوتبوک)
python scripts\run_all.py              # همه چیز از صفر
python -m pytest -q                    # آزمون‌ها
python scripts\build_notebooks.py      # ساخت نوتبوک‌ها از مشخصات
python scripts\execute_notebooks.py    # اجرای نوتبوک‌ها
python scripts\build_report.py         # ساخت گزارش MD و PDF
```

</div>
