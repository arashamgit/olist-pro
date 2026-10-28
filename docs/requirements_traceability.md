# جدول ردیابی الزامات دوره (Requirements Traceability)

<div dir="rtl" align="right">

هر سؤال صریح صورت‌مسئله یک ردیف دارد. ستون «وضعیت» یکی از این مقادیر است:
`PASS` (پیاده‌سازی و اعتبارسنجی شده)، `PARTIAL` (اجرا شده با محدودیت مستند)،
`FAIL`، `BLOCKED`.

مخفف‌ها: NB = نوتبوک، F = تابع در `src/olist_analysis/`، Fig = نمودار،
T = آزمون در `tests/`.

| # | الزام دوره | NB | تابع / محاسبه | نمودار یا جدول | آزمون | وضعیت |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| ۳.۱ | فایل‌ها و جداول موجود در دیتاست | 00 | `file_inventory` | جدول `01_file_inventory` | test_data_loading | PASS |
| ۳.۲ | تعداد سطر و ستون هر جدول | 00 | `table_shapes` | جدول `01_table_shapes` | test_data_loading | PASS |
| ۳.۳ | مفهوم هر سطر | 01 | مستند `data_dictionary.md` | `docs/data_dictionary.md` | - | PASS |
| ۳.۴ | ستون‌های مهم هر جدول | 01 | `column_profile` | جدول `00_column_profiles` | test_data_quality | PASS |
| ۳.۵ | نوع داده ستون‌ها | 00 | `column_profile` | جدول `00_column_profiles` | test_data_quality | PASS |
| ۳.۶ | ستون‌های ارتباطی میان جداول | 01 | `_merge` + همانندی کلیدها | `docs/data_relationships.md` | test_features | PASS |
| ۳.۷ | بررسی داده تکراری | 00 | `duplicate_rows_table`, `key_uniqueness` | جداول `00_duplicate_rows`, `00_key_uniqueness` | test_data_quality | PASS |
| ۳.۸ | بررسی مقادیر گمشده | 00 | `missing_values_table` | جدول `00_missing_values` | test_data_quality | PASS |
| ۳.۹ | درصد مقادیر گمشده هر ستون | 00 | `column_profile` | ستون `pct_missing` | test_data_quality | PASS |
| ۴.۱ | تصمیم درباره مقادیر گمشده | 02 | `clean_orders` و ۱۴ تصمیم دیگر | `02_cleaning_decisions` | test_features | PASS |
| ۴.۲ | بررسی رکوردهای تکراری | 02 | `deduplicate_reviews_per_order` | `02_cleaning_summary` | test_features | PASS |
| ۴.۳ | اصلاح نوع داده | 02 | `_parse_datetime` | `02_cleaning_summary` | test_data_quality | PASS |
| ۴.۴ | تبدیل تاریخ‌ها به datetime | 02 | `_parse_datetime` (قالب صریح) | `00_orders_datetime_report` | test_data_quality | PASS |
| ۴.۵ | بررسی مقادیر غیرعادی | 02 | `numeric_range_check`, ترتیب زمانی | `02_cleaning_summary` | test_features | PASS |
| ۴.۶ | ساخت ویژگی‌های زمانی (سال/ماه/روز) | 02 | `_add_calendar_and_delivery_features` | `order_features` | test_features | PASS |
| ۴.۶ | مدت زمان تحویل و روزهای تأخیر | 02 | `delivery_days`, `delay_days` | `09_delivery_*` | T: calendar-delay | PASS |
| ۵.۱.۱ | تعداد کل سفارش و تفکیک وضعیت | 03 | `order_status_summary` | Fig ۱ | test_metrics | PASS |
| ۵.۱.۲ | تعداد و درصد سفارش بر اساس وضعیت | 03 | `order_status_summary` | جدول `05_order_status_summary` | sum(pct)=100 | PASS |
| ۵.۲.۳ | تعداد سفارش در هر ماه + نمودار روند | 03 | `monthly_orders` | Fig ۲ | - | PASS |
| ۵.۲.۴ | تفکیک سال و ماه و بررسی رشد | 03 | `year_month_matrix`, `growth_evidence` | جدول `05_year_month_matrix` | - | PASS |
| ۵.۲.۴ | نمایش ماتریس سال و ماه | 03 | `year_month_matrix` + `sns.heatmap` | Fig ۳۲ | - | PASS |
| ۵.۳.۵ | سفارش در روزهای هفته | 03 | `weekday_orders` | Fig ۳ | - | PASS |
| ۵.۴.۶ | پنج ماه با بیشترین سفارش | 03 | `top_months` | Fig ۴ | - | PASS |
| ۵.ن | نتیجه‌گیری کسب‌وکاری روند | 03 | - | متن تفسیر نوتبوک | - | PASS |
| ۶.۱.۱ | تعداد مشتریان یکتا | 04 | `customer_overview` | جدول `06_*` | test_metrics | PASS |
| ۶.۲.۲ | مشتریان هر ایالت + ده ایالت اول | 04 | `customers_by_state` | Fig ۵ | test_metrics | PASS |
| ۶.۲.۳ | سهم پنج ایالت اول | 04 | `top_n_state_share` | جدول `06_*` | test_metrics | PASS |
| ۶.۳.۴ | ده شهر با بیشترین مشتری | 04 | `customers_by_city` | Fig ۶ | - | PASS |
| ۶.۴.۵ | مقایسه مشتریان و سفارش‌ها به تفکیک ایالت | 04 | `state_customers_vs_orders` | Fig ۷ | - | PASS |
| ۶.۴.۶ | نمودار مقایسه‌ای مشتری/سفارش | 04 | `state_customers_vs_orders` | Fig ۷ | - | PASS |
| ۶.ن | نتیجه‌گیری تمرکز بازار + محدودیت | 04 | - | متن تفسیر | - | PASS |
| ۷.۱.۱ | تعداد دسته‌بندی‌ها + ده دسته برتر حجم | 05 | `category_performance` | Fig ۸ | - | PASS |
| ۷.۲.۲ | مبلغ فروش هر دسته + ده دسته برتر | 05 | `top_categories` | Fig ۹ | T: pct=100 | PASS |
| ۷.۲.۳ | مقایسه رتبه حجم و مبلغ | 05 | `category_rank_comparison` | جدول `07_*` | - | PASS |
| ۷.۳.۴ | پنج دسته با بالاترین متوسط قیمت | 05 | `top_categories(mean_price)` | Fig ۱۱ | - | PASS |
| ۷.۴.۵ | سهم پنج دسته اول از مبلغ فروش | 05 | `top_n_revenue_share` | جدول `07_*` | test_metrics | PASS |
| ۷.۴.۶ | نمودار رابطه‌ای حجم و مبلغ | 05 | `category_performance` | Fig ۱۰ | - | PASS |
| ۷.ن | تفسیر تفاوت عملکرد + هشدار سود | 05 | - | متن تفسیر | - | PASS |
| ۸.۱.۱ | تعداد و سهم تراکنش هر روش پرداخت | 06 | `payment_type_summary` | Fig ۱۲ | test_metrics | PASS |
| ۸.۱.۲ | مجموع مبلغ هر روش | 06 | `payment_type_summary` | Fig ۱۲ | - | PASS |
| ۸.۱.۳ | متوسط مبلغ هر روش | 06 | `payment_type_summary` | جدول `08_*` | - | PASS |
| ۸.۲.۴ | توزیع تعداد اقساط | 06 | `installment_distribution` | Fig ۱۳ | test_metrics | PASS |
| ۸.۲.۵ | پرداخت بدون قسط یا یک‌قسطی | 06 | `zero_or_single_installments` | جدول `08_*` | test_metrics | PASS |
| ۸.۲.۶ | رابطه مبلغ پرداخت و اقساط | 06 | `combined_payment_vs_installments` | Fig ۱۴ | T: rho>0.3 | PASS |
| ۸.۲.۷ | مقایسه روش پرداخت و تعداد اقساط | 06 | `installments_by_type_summary` | جدول `08_*` | - | PASS |
| ۸.ن | تمایز تراکنش/سفارش/مشتری | 06 | `payment_reconciliation` | جدول `08_*` | - | PASS |
| ۹.۱.۱ | مدت ثبت تا تحویل واقعی | 07 | `delivery_duration_summary` | جدول `09_*` | test_metrics | PASS |
| ۹.۱.۲ | میانگین، میانه، کمینه، بیشینه | 07 | `delivery_duration_summary` | جدول `09_*` | - | PASS |
| ۹.۱.۳ | توزیع زمان تحویل و مقادیر دورافتاده | 07 | `delivery_distribution_stats` | Fig ۱۵ | - | PASS |
| ۹.۲.۴ | طبقه‌بندی پیش از موعد/به‌موقع/دیر | 07 | `delivery_class_summary` | Fig ۱۶ | T: partition | PASS |
| ۹.۲.۵ | درصد سفارش دیرکرددار | 07 | `delay_summary` | جدول `09_*` | - | PASS |
| ۹.۲.۵ | میانگین روزهای تأخیر دیرکرددارها | 07 | `delay_summary` | جدول `09_*` | - | PASS |
| ۹.۲.۵ | تعداد سفارش با بیش از هفت روز تأخیر | 07 | `delay_summary` | جدول `09_*` | T: buckets | PASS |
| ۹.۳.۶ | میانگین زمان تحویل به تفکیک ایالت | 07 | `delivery_by_state` | Fig ۱۷ | - | PASS |
| ۹.۳.۶ | ده ایالت با بیشترین میانگین تحویل | 07 | `delivery_by_state` | Fig ۱۷ | - | PASS |
| ۹.۳.۶ | توجه به تعداد نمونه هر ایالت | 07 | `meets_min_sample` | Fig ۱۷ (n) | T: min sample | PASS |
| ۹.۳.۷ | روند زمانی میانگین زمان تحویل | 07 | `monthly_delivery_trend` | Fig ۱۸ | - | PASS |
| ۹.۳.۷ | روند زمانی درصد سفارش دیرکرددار | 07 | `monthly_delivery_trend` | Fig ۱۸ | - | PASS |
| ۱۰.۱.۱ | توزیع فراوانی امتیاز | 08 | `review_score_distribution` | Fig ۱۹ | - | PASS |
| ۱۰.۱.۲ | میانگین امتیاز و درصد ۴-۵ و ۱-۲ | 08 | `satisfaction_kpis` | جدول `10_*` | test_metrics | PASS |
| ۱۰.۲.۳ | ده دسته بالاترین/پایین‌ترین امتیاز | 08 | `category_satisfaction_ranked` | Fig ۲۰ | - | PASS |
| ۱۰.۲.۴ | تعداد نظرات هر دسته و اهمیت آن | 08 | `low_volume_categories` | Fig ۲۰ (n) | - | PASS |
| ۱۰.۳.۵ | روند زمانی میانگین امتیاز | 08 | `monthly_satisfaction_trend` | Fig ۲۱ | - | PASS |
| ۱۰.۳.۶ | مقایسه امتیاز و مبلغ فروش دسته‌ها | 08/11 | `category_satisfaction` | Fig ۲۶ | - | PASS |
| ۱۱.۱.۱ | تعداد و میانگین امتیاز دو گروه تحویل | 09 | `delay_satisfaction_comparison` | Fig ۲۲ | test_metrics | PASS |
| ۱۱.۱.۲ | اختلاف میانگین امتیاز دو گروه | 09 | `delay_satisfaction_difference` | Fig ۲۲ | T: gap | PASS |
| ۱۱.۱.۲ | کفایت تعداد نمونه دو گروه | 09 | `min_sample_reached` | جدول `11_*` | test_metrics | PASS |
| ۱۱.۲.۳ | تقسیم تأخیر به ۱-۳، ۴-۷ و بیش از ۷ | 09 | `delay_bucket_satisfaction` | Fig ۲۳ | T: buckets | PASS |
| ۱۱.۲.۳ | میانگین امتیاز و تعداد هر بازه | 09 | `delay_bucket_satisfaction` | Fig ۲۳ | test_metrics | PASS |
| ۱۱.۲.۳ | مقایسه چند دسته با حجم کافی | 09 | `category_delay_satisfaction` | جدول `11_*` | - | PASS |
| ۱۱.ن | تفسیر و محدودیت استنباط علّی | 09 | - | متن محدودیت | - | PASS |
| ۱۲.۱.۱ | تعداد فروشندگان و توزیع ایالتی | 10 | `seller_overview`, `sellers_by_state` | جدول `12_*` | - | PASS |
| ۱۲.۲.۲ | تعداد اقلام و مبلغ فروش هر فروشنده | 10 | `seller_performance` | جدول `12_*` | T: sum | PASS |
| ۱۲.۲.۲ | ده فروشنده برتر بر اساس مبلغ فروش | 10 | `top_sellers` | Fig ۲۴ | - | PASS |
| ۱۲.۲.۳ | سهم ده فروشنده اول | 10 | `seller_overview` | جدول `12_*` | - | PASS |
| ۱۲.۲.۴ | مقایسه رتبه اقلام و مبلغ فروش | 10 | `rank_gap_*` | جدول `12_*` | - | PASS |
| ۱۲.۳.۵ | میانگین امتیاز فروشندگان با نظر کافی | 10 | `meets_min_reviews` | Fig ۲۵ | - | PASS |
| ۱۲.۳.۶ | فروش بالا با امتیاز پایین + تعداد سفارش | 10 | `high_revenue_low_rating_sellers` | Fig ۲۵ | - | PASS |
| ۱۳.۱ | ترکیبی ۱: دسته پرفروش با رضایت پایین | 11 | `combined_revenue_vs_satisfaction` | Fig ۲۶ | - | PASS |
| ۱۳.۲ | ترکیبی ۲: جغرافیا و عملکرد تحویل | 11 | `combined_geography_delivery` | Fig ۲۷ | T: min sample | PASS |
| ۱۳.۳ | ترکیبی ۳: قیمت محصول و رضایت | 11 | `combined_price_vs_satisfaction` | Fig ۲۸ | T: rho<0.1 | PASS |
| ۱۳.۴ | ترکیبی ۴: مبلغ پرداخت و اقساط | 11 | `combined_payment_vs_installments` | Fig ۱۴ | T: rho>0.3 | PASS |
| ۱۳.۵ | ترکیبی ۵: تغییرات فروش دسته‌ها در زمان | 11 | `combined_category_revenue_over_time` | Fig ۲۹ | - | PASS |
| ۱۳.۶ | ترکیبی ۶: فروشنده و رضایت مشتری | 11 | `high_revenue_low_rating_sellers` | Fig ۳۰ | - | PASS |
| ۱۴.۱ | خلاصه وضعیت کسب‌وکار | 12 | `reporting.build_content` | گزارش PDF بخش ۱ و ۲ | - | PASS |
| ۱۴.۲ | پنج یافته مهم (نتیجه، عدد، نمودار) | 12 | `reporting.Finding` | گزارش PDF بخش ۳ | - | PASS |
| ۱۴.۲ | اهمیت و محدودیت هر یافته | 12 | `Finding.importance/limitation` | گزارش PDF بخش ۳ | - | PASS |
| ۱۴.۳ | سه پیشنهاد عملی | 12 | `reporting.Recommendation` | گزارش PDF بخش ۴ | - | PASS |
| ۱۴.۳ | مسئله، یافته پشتیبان، تغییر، شاخص پایش | 12 | `Recommendation` | گزارش PDF بخش ۴ | - | PASS |
| ۱۵ | الزامات نمودار (عنوان، محور، واحد، تفسیر) | همه | `plotting._save` | ۳۲ نمودار + فایل توضیح | - | PASS |
| ۱۶.۱ | فایل Jupyter Notebook | همه | `scripts/build_notebooks.py` | `notebooks/*.ipynb` | اجرای کامل | PASS |
| ۱۶.۲ | گزارش مدیریتی PDF | 12 | `reporting.render_pdf` | `reports/executive_report.pdf` | - | PASS |
| ۱۶.۳ | اجرای کامل نوتبوک بدون خطا | همه | `scripts/execute_notebooks.py` | خروجی نوتبوک‌ها | ۱۳/۱۳ | PASS |
| ۱۶.۴ | بسته ZIP تحویل | - | `scripts/build_deliverables.py` | `deliverables/olist-pro-deliverables.zip` | - | PASS |

## موارد با محدودیت (PARTIAL) و دلیل آن

| مورد | محدودیت | اقدام لازم |
| :--- | :--- | :--- |
| تحلیل ژئوپردازش (نقشه) | مختصات موجود است اما کاربرد تحلیلی افزوده‌ای بر تحلیل ایالتی ندارد و کتابخانه نقشه‌کشی بخشی از وابستگی‌های پروژه نیست | در صورت نیاز می‌توان با `geo_centroids` نقشه ایالتی افزود |
| تحلیل متن نظرات | خارج از دامنه پروژه تعریف شده است؛ ۵۸.۷۰ درصد نظرات متن ندارند | نیاز به تعریف دامنه و کتابخانه پردازش زبان |
| تحلیل سود و حاشیه | داده هزینه، تخفیف و کارمزد وجود ندارد | نیاز به داده مالی افزوده |
| برآورد تقاضای بالقوه مناطق کم‌مشتری | داده جمعیت، رقبا و هزینه بازاریابی موجود نیست | نیاز به داده بیرونی |
| شاخص‌های قابلیت اطمینان آماری (فاصله اطمینان) | برای خوانایی گزارش مدیریتی وارد نشده | در صورت نیاز می‌توان فاصله اطمینان بوت‌استرپ افزود |

## موارد BLOCKED / FAIL

هیچ الزامی از دوره در وضعیت `FAIL` یا `BLOCKED` نیست. همه سؤال‌های صریح
صورت‌مسئله با داده واقعی پاسخ داده شده و اعتبارسنجی شده‌اند.

</div>
