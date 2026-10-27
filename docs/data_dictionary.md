# فرهنگ داده‌ها (Data Dictionary) - دیتاست Olist

<div dir="rtl" align="right">

منبع: ۹ فایل CSV در `data/raw/`، مجموعاً ۱۲۰.۲۵ مگابایت.
اعداد ستون «گمشده» از اجرای واقعی `scripts/run_all.py` و فایل
`reports/tables/00_column_profiles.csv` استخراج شده‌اند.

## خلاصه جداول

| جدول | فایل | سطر | ستون | کلید اصلی اعلام‌شده | وضعیت یکتایی |
| :--- | :--- | ---: | ---: | :--- | :--- |
| orders | `olist_orders_dataset.csv` | ۹۹٬۴۴۱ | ۸ | `order_id` | یکتا ✔ |
| customers | `olist_customers_dataset.csv` | ۹۹٬۴۴۱ | ۵ | `customer_id` | یکتا ✔ |
| order_items | `olist_order_items_dataset.csv` | ۱۱۲٬۶۵۰ | ۷ | `order_id` + `order_item_id` | یکتا ✔ |
| order_payments | `olist_order_payments_dataset.csv` | ۱۰۳٬۸۸۶ | ۵ | `order_id` + `payment_sequential` | یکتا ✔ |
| order_reviews | `olist_order_reviews_dataset.csv` | ۹۹٬۲۲۴ | ۷ | `review_id` | **یکتا نیست ✘** |
| products | `olist_products_dataset.csv` | ۳۲٬۹۵۱ | ۹ | `product_id` | یکتا ✔ |
| sellers | `olist_sellers_dataset.csv` | ۳٬۰۹۵ | ۴ | `seller_id` | یکتا ✔ |
| geolocation | `olist_geolocation_dataset.csv` | ۱٬۰۰۰٬۱۶۳ | ۵ | - | کلید اعلام‌شده ندارد |
| product_category_name_translation | `product_category_name_translation.csv` | ۷۱ | ۲ | `product_category_name` | یکتا ✔ |

**نکته مهم درباره شمارش سطر جدول نظرات:** فایل آن ۱۰۴٬۷۲۰ خط فیزیکی دارد، اما تعداد
**ردیف منطقی** ۹۹٬۲۲۴ است؛ چون متن برخی نظرات شامل خط جدید است. مبنای همه محاسبات،
تعداد ردیف منطقی است (با `pandas.read_csv` و با ماژول `csv` تأیید شد).

---

## ۱. `orders` - سفارش‌ها

هر سطر یک سفارش. مفهوم `order_status`: `delivered` تحویل‌شده، `shipped` ارسال‌شده،
`invoiced` فاکتور‌شده، `processing`/`approved`/`created` در جریان، `unavailable` ناموجود،
`canceled` لغوشده.

| ستون | نوع | گمشده | درصد | توضیح |
| :--- | :--- | ---: | ---: | :--- |
| `order_id` | str | ۰ | ۰ | شناسه یکتای سفارش (کلید اصلی) |
| `customer_id` | str | ۰ | ۰ | کلید به جدول مشتریان؛ یک‌به‌یک |
| `order_status` | str | ۰ | ۰ | وضعیت سفارش (۸ مقدار) |
| `order_purchase_timestamp` | datetime | ۰ | ۰ | زمان ثبت سفارش |
| `order_approved_at` | datetime | ۱۶۰ | ۰.۱۶۱ | زمان تأیید پرداخت |
| `order_delivered_carrier_date` | datetime | ۱٬۷۸۳ | ۱.۷۹۳ | زمان تحویل به شرکت حمل |
| `order_delivered_customer_date` | datetime | ۲٬۹۶۵ | ۲.۹۸۲ | زمان تحویل واقعی به مشتری |
| `order_estimated_delivery_date` | datetime | ۰ | ۰ | تاریخ تخمینی تحویل (ساعت ۰۰:۰۰) |

## ۲. `customers` - مشتریان

هر سطر یک مشتری **معادل یک سفارش**. شخص حقیقی با `customer_unique_id` شناسایی می‌شود.

| ستون | نوع | گمشده | توضیح |
| :--- | :--- | ---: | :--- |
| `customer_id` | str | ۰ | کلید اصلی؛ یکتا در ۹۹٬۴۴۱ سطر |
| `customer_unique_id` | str | ۰ | شناسه شخص؛ ۹۶٬۰۹۶ مقدار یکتا |
| `customer_zip_code_prefix` | int64 | ۰ | پیش‌شمار کد پستی؛ ۱۴٬۹۹۴ مقدار یکتا |
| `customer_city` | str | ۰ | شهر؛ ۴٬۱۱۹ مقدار یکتا |
| `customer_state` | str | ۰ | ایالت (کد ۲ حرفی)؛ ۲۷ مقدار یکتا |

## ۳. `order_items` - اقلام سفارش

هر سطر یک قلم کالا. هر سطر معادل **یک واحد** است (ستون تعداد وجود ندارد)، پس مبلغ
فروش سطر برابر `price` است.

| ستون | نوع | گمشده | توضیح |
| :--- | :--- | ---: | :--- |
| `order_id` | str | ۰ | کلید خارجی به سفارش‌ها |
| `order_item_id` | int64 | ۰ | شماره ترتیبی قلم در سفارش (۱ تا ۲۱) |
| `product_id` | str | ۰ | کلید خارجی به محصولات |
| `seller_id` | str | ۰ | کلید خارجی به فروشندگان |
| `shipping_limit_date` | datetime | ۰ | مهلت ارسال به حمل |
| `price` | float64 | ۰ | قیمت واحد قلم (BRL)؛ دامنه ۰.۸۵ تا ۶٬۷۳۵ |
| `freight_value` | float64 | ۰ | هزینه ارسال (BRL)؛ ۳۸۳ سطر صفر |

## ۴. `order_payments` - پرداخت‌ها

هر سطر یک **تراکنش** پرداخت؛ یک سفارش می‌تواند چند تراکنش داشته باشد (۱ تا ۲۹).

| ستون | نوع | گمشده | توضیح |
| :--- | :--- | ---: | :--- |
| `order_id` | str | ۰ | کلید خارجی به سفارش‌ها |
| `payment_sequential` | int64 | ۰ | شماره ترتیبی تراکنش در سفارش |
| `payment_type` | str | ۰ | credit_card / boleto / voucher / debit_card / not_defined |
| `payment_installments` | int64 | ۰ | تعداد اقساط؛ ۲ سطر مقدار صفر دارد |
| `payment_value` | float64 | ۰ | مبلغ تراکنش (BRL)؛ ۹ سطر مقدار صفر |

## ۵. `order_reviews` - نظرات مشتریان

هر سطر یک پاسخ نظرسنجی. `review_id` **یکتا نیست** (۷۸۹ شناسه در ۱٬۶۰۳ سطر تکرار شده
و هر شناسه به سفارش‌های متفاوت با امتیاز یکسان اشاره می‌کند).

| ستون | نوع | گمشده | درصد | توضیح |
| :--- | :--- | ---: | ---: | :--- |
| `review_id` | str | ۰ | ۰ | شناسه نظر (اعلام‌شده به‌عنوان کلید، ولی تکراری) |
| `order_id` | str | ۰ | ۰ | کلید خارجی به سفارش‌ها (۹۸٬۶۷۳ مقدار یکتا) |
| `review_score` | int64 | ۰ | ۰ | امتیاز ۱ تا ۵ |
| `review_comment_title` | str | ۸۷٬۶۵۶ | ۸۸.۳۴ | عنوان متن نظر |
| `review_comment_message` | str | ۵۸٬۲۴۷ | ۵۸.۷۰ | متن نظر |
| `review_creation_date` | datetime | ۰ | ۰ | تاریخ ارسال نظرسنجی |
| `review_answer_timestamp` | datetime | ۰ | ۰ | زمان پاسخ مشتری |

## ۶. `products` - محصولات

| ستون | نوع | گمشده | توضیح |
| :--- | :--- | ---: | :--- |
| `product_id` | str | ۰ | کلید اصلی؛ یکتا |
| `product_category_name` | str | ۶۱۰ | نام دسته‌بندی (پرتغالی)؛ ۷۳ مقدار یکتا |
| `product_name_lenght` | float64 | ۶۱۰ | طول نام |
| `product_description_lenght` | float64 | ۶۱۰ | طول توضیحات |
| `product_photos_qty` | float64 | ۶۱۰ | تعداد عکس |
| `product_weight_g` | float64 | ۲ | وزن (گرم)؛ ۴ سطر صفر |
| `product_length_cm` | float64 | ۲ | طول (سانتی‌متر) |
| `product_height_cm` | float64 | ۲ | ارتفاع (سانتی‌متر) |
| `product_width_cm` | float64 | ۲ | عرض (سانتی‌متر) |

> املای `lenght` در فایل اصلی اشتباه است؛ برای حفظ سازگاری با داده خام تغییر داده نشده.

## ۷. `sellers` - فروشندگان

| ستون | نوع | گمشده | توضیح |
| :--- | :--- | ---: | :--- |
| `seller_id` | str | ۰ | کلید اصلی؛ یکتا در ۳٬۰۹۵ سطر |
| `seller_zip_code_prefix` | int64 | ۰ | پیش‌شمار کد پستی؛ ۲٬۲۴۶ مقدار یکتا |
| `seller_city` | str | ۰ | شهر؛ ۶۱۱ مقدار یکتا |
| `seller_state` | str | ۰ | ایالت؛ ۲۳ مقدار یکتا |

## ۸. `geolocation` - موقعیت جغرافیایی

جدول مرجع کد پستی به مختصات. کلید یکتا ندارد: ۱۹٬۰۱۵ پیش‌شمار یکتا در ۱٬۰۰۰٬۱۶۳ سطر،
با ۲۶۱٬۸۳۱ سطر کاملاً تکراری و تا ۱٬۱۴۶ سطر برای یک پیش‌شمار.

| ستون | نوع | توضیح |
| :--- | :--- | :--- |
| `geolocation_zip_code_prefix` | int64 | پیش‌شمار کد پستی |
| `geolocation_lat` | float64 | عرض جغرافیایی؛ ۳۱ سطر خارج از مرزهای برزیل |
| `geolocation_lng` | float64 | طول جغرافیایی |
| `geolocation_city` | str | شهر؛ ۸٬۰۱۱ مقدار یکتا |
| `geolocation_state` | str | ایالت؛ ۸ پیش‌شمار با ایالت متناقض |

## ۹. `product_category_name_translation`

| ستون | نوع | توضیح |
| :--- | :--- | :--- |
| `product_category_name` | str | نام دسته‌بندی به پرتغالی؛ یکتا در ۷۱ سطر |
| `product_category_name_english` | str | معادل انگلیسی؛ یکتا |

دو دسته‌بندی در فایل محصولات ترجمه ندارند:
`pc_gamer` و `portateis_cozinha_e_preparadores_de_alimentos`.

---

## ستون‌های مشتق‌شده (ساخته‌شده در `src/olist_analysis/features.py`)

| ستون | گرین | تعریف |
| :--- | :--- | :--- |
| `purchase_date`, `purchase_ym`, `purchase_year`, `purchase_month` | سفارش | کلیدهای تقویمی از زمان ثبت |
| `purchase_weekday`, `purchase_weekday_num`, `purchase_hour` | سفارش | روز و ساعت ثبت (Monday = ۰) |
| `in_core_window` | سفارش | ثبت در بازه ۲۰۱۷-۰۱-۰۱ تا ۲۰۱۸-۰۸-۳۱ |
| `is_delivered` | سفارش | `order_status == "delivered"` |
| `delivery_days` | سفارش | (تحویل واقعی − ثبت) به روز |
| `promised_days` | سفارش | (تاریخ تخمینی − ثبت) به روز |
| `delay_days` | سفارش | (تاریخ تحویل واقعی − تاریخ تخمینی) به **روز تقویمی** |
| `delivery_class` | سفارش | early (<۰)، on_time (=۰)، late (>۰) |
| `delay_bucket` | سفارش | on_time_or_early / 1_3_days / 4_7_days / more_than_7_days |
| `item_count`, `item_total_price`, `item_total_freight`, `n_sellers` | سفارش | تجمیع اقلام |
| `order_total_value` | سفارش | `item_total_price` + `item_total_freight` |
| `payment_total`, `payment_rows`, `payment_max_installments`, `payment_type_main` | سفارش | تجمیع پرداخت |
| `review_score`, `review_id` | سفارش | امتیاز یک نظر برای هر سفارش |
| `main_category` | سفارش | دسته‌بندی گران‌ترین قلم سفارش |
| `category_label` | محصول | نام انگلیسی دسته‌بندی، در نبود ترجمه نام پرتغالی، در نبود دسته `unknown` |
| `item_revenue` | قلم | برابر `price` (هر سطر یک واحد) |
| `has_translation` | محصول | آیا معادل انگلیسی برای دسته‌بندی وجود دارد |

</div>
