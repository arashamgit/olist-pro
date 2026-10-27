# مرحله ۴ - تحلیل سفارش‌ها و مشتریان

<div dir="rtl" align="right">

## ۱. هدف مرحله

پاسخ به دو حوزه نخست صورت‌مسئله: روند فعالیت کسب‌وکار (بخش ۵) و تمرکز بازار
جغرافیایی (بخش ۶). این مرحله تصویر «کسب‌وکار در چه وضعیتی است» را می‌سازد.

## ۲. مسئول اصلی و بازبین

| نوتبوک | مسئول اصلی | بازبین |
| :--- | :--- | :--- |
| `03_order_analysis.ipynb` | **Member A** | **Member C** |
| `04_customer_analysis.ipynb` | **Member B** | **Member A** |

این دو نوتبوک مستقل هستند و هم‌زمان انجام می‌شوند.

## ۳. پیش‌نیازها

- مرحله ۳ ادغام شده باشد
- گرین `order_features` ساخته و قفل شده باشد

## ۴. شاخه Git

```bash
# Member A
git checkout main && git pull origin main
git checkout -b feat/order-analysis

# Member B (در کنار A، شاخه مستقل)
git checkout main && git pull origin main
git checkout -b feat/customer-analysis
```

## ۵. فایل‌های موردنیاز

| فایل | کار |
| :--- | :--- |
| `src/olist_analysis/metrics.py` | توابع شاخص (بخش ۵ و ۶) |
| `notebooks/03_order_analysis.ipynb` | روایت روند و وضعیت سفارش |
| `notebooks/04_customer_analysis.ipynb` | روایت مشتری و جغرافیا |
| `reports/tables/05_*` | جدول‌های بخش سفارش |
| `reports/tables/06_*` | جدول‌های بخش مشتری |

## ۶. محتوای مورد انتظار

### توابع بخش ۵ (سفارش‌ها)

| تابع | خروجی | نکته طراحی |
| :--- | :--- | :--- |
| `order_status_summary` | شمارش و درصد هر وضعیت | جمع درصدها باید ۱۰۰ شود |
| `monthly_orders` | شمارش ماهانه + میانگین متحرک ۳ ماهه | فقط پنجره تحلیلی برای روند |
| `year_month_matrix` | ماتریس سال × ماه | ترتیب تقویمی صحیح |
| `weekday_orders` | شمارش و میانگین روزانه هر روز هفته | ترتیب دوشنبه تا یکشنبه، نه الفبایی |
| `top_months` | پنج ماه پرترافیک | باید مشخص شود به کدام سال‌ها تعلق دارند |
| `growth_evidence` | مقایسه هم‌دوره و نیمه‌به‌نیمه | برای پاسخ «رشد یا فصلی بودن» |

### توابع بخش ۶ (مشتریان)

| تابع | خروجی | نکته طراحی |
| :--- | :--- | :--- |
| `customer_overview` | ردیف، `customer_id` یکتا، خریدار یکتا | تفاوت این سه عدد باید صریح باشد |
| `customers_by_state` | مشتری و سهم هر ایالت | شمارش با `customer_unique_id` |
| `top_n_state_share` | سهم n ایالت اول از مشتریان و سفارش‌ها | مخرج صریح |
| `customers_by_city` | ده شهر اول | ادغام شهر و ایالت برای رفع ابهام |
| `state_customers_vs_orders` | مقایسه سهم مشتری و سفارش | ستون اختلاف به واحد درصد |

### نکته کلیدی که باید رعایت شود

`customer_id` در این دیتاست **معادل یک سفارش** است، نه یک شخص. شمارش مشتری باید
با `customer_unique_id` انجام شود؛ در غیر این صورت ۹۹٬۴۴۱ «مشتری» می‌شمارید در
حالی که ۹۶٬۰۹۶ خریدار واقعی وجود دارد و ۲٬۹۹۷ نفر بیش از یک سفارش دارند.

## ۷. دستورات ترمینال

### ویندوز (PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import sys; sys.path.insert(0,'src'); from olist_analysis.features import load_dataset; from olist_analysis import metrics as M; d=load_dataset(); print(M.order_status_summary(d).to_string())"
python -m pytest tests\test_metrics.py -q
```

### اجرای نوتبوک خودتان (الزامی پیش از PR)

```bash
python -c "import nbformat, sys; from nbclient import NotebookClient; nb=nbformat.read('notebooks/03_order_analysis.ipynb', as_version=4); NotebookClient(nb, timeout=600, kernel_name='olist-pro', resources={'metadata': {'path': 'notebooks'}}).execute()"
```

## ۸. آزمون‌ها

| آزمون | چه چیزی را قفل می‌کند |
| :--- | :--- |
| `test_order_status_summary_percentages_sum_to_one_hundred` | جمع درصد وضعیت‌ها |
| `test_customer_overview_counts_people_not_rows` | شمارش با خریدار یکتا |
| `test_top_n_state_share_matches_table` | سازگاری سهم با جدول تفصیلی |
| `test_real_status_percentages_sum_to_one_hundred` | همان کنترل روی داده واقعی |
| `test_real_customer_counts` | ۹۶٬۰۹۶ خریدار یکتا و ۹۹٬۴۴۱ ردیف |

## ۹. خروجی مورد انتظار (اعداد واقعی تأییدشده)

### بخش سفارش‌ها

| مورد | مقدار |
| :--- | ---: |
| کل سفارش | ۹۹٬۴۴۱ |
| تحویل‌شده | ۹۶٬۴۷۸ (۹۷.۰۲٪) |
| اوج ماهانه | آبان ۲۰۱۷ با ۷٬۵۴۴ سفارش (۷.۵۹٪) |
| مقایسه ژانویه تا اوت | ۲۲٬۹۶۸ در ۲۰۱۷ در برابر ۵۳٬۹۹۱ در ۲۰۱۸ (۱۴۲.۰۷٪+) |
| پرترافیک‌ترین روز هفته | دوشنبه با ۱۶٬۲۹۶ سفارش (۱۶.۲۹٪) |
| پنج ماه پرترافیک | ۲۰۱۷-۱۱، ۲۰۱۸-۰۱، ۲۰۱۸-۰۳، ۲۰۱۸-۰۴، ۲۰۱۸-۰۵ |

### بخش مشتریان

| مورد | مقدار |
| :--- | ---: |
| خریدار یکتا | ۹۶٬۰۹۶ |
| خریدار بازگشتی | ۲٬۹۹۷ (۳.۱۲٪) |
| ایالت اول (SP) | ۴۰٬۳۰۲ خریدار (۴۱.۹۲٪) |
| سهم پنج ایالت اول | ۷۷.۰۸٪ مشتریان و ۷۷.۱۸٪ سفارش‌ها |
| شهر اول | سائوپائولو با ۱۴٬۹۸۴ خریدار (۱۵.۵۹٪) |

## ۱۰. پیام Commit پیشنهادی

```text
feat: implement order trend and customer geography analysis

- add monthly, yearly and weekday order metrics on the core window
- add customer metrics counted by customer_unique_id, not by order rows
- document that order growth plateaued after January 2018
```

## ۱۱. Push و Pull Request

```bash
git add src/olist_analysis/metrics.py notebooks/03_order_analysis.ipynb
git commit -m "feat: implement order trend and customer geography analysis"
git push -u origin feat/order-analysis
```

برای Member B به‌جای آن، `feat/customer-analysis` و نوتبوک ۰۴ را پوش کنید.

## ۱۲. مواردی که بازبین باید کنترل کند

۱. روند ماهانه از ترتیب تقویمی درست استفاده کند (نه ترتیب الفبایی رشته).
۲. ماه‌های ناقص حاشیه از تحلیل روند کنار گذاشته شوند و در نمودار مشخص باشند.
۳. شمارش مشتری با `customer_unique_id` انجام شده باشد.
۴. هر درصد مخرج صریح داشته باشد.
۵. در نتیجه‌گیری جغرافیایی، جمله «تعداد کم مشتری اثبات فرصت رشد نیست» آمده باشد.
۶. متن تفسیر با اعداد جدول انطباق داشته باشد.

## ۱۳. معیار پذیرش

- [ ] هر هفت سؤال بخش ۵ و هر هفت سؤال بخش ۶ پاسخ داده شده باشند
- [ ] نمودارها عنوان، برچسب محور و واحد داشته باشند
- [ ] نتیجه‌گیری کسب‌وکاری در پایان هر نوتبوک نوشته شده باشد
- [ ] نوتبوک‌ها از ابتدا و بدون خطا اجرا شوند
- [ ] PR هر دو نوتبوک تأیید و ادغام شده باشد

## ۱۴. شرط شروع مرحله بعد

پس از ادغام، ارقام پایه (تعداد سفارش، تعداد خریدار، سهم ایالت‌ها) در `main`
قفل می‌شود. اگر تحلیلی در مراحل بعد به این ارقام ارجاع می‌دهد، باید همان مقدار
را ببیند؛ در غیر این صورت یک اشتباه در upstream وجود دارد.

</div>
