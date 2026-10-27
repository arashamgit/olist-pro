# مرحله ۵ - تحلیل محصولات و پرداخت

<div dir="rtl" align="right">

## ۱. هدف مرحله

پاسخ به بخش ۷ (محصولات و عملکرد فروش) و بخش ۸ (رفتار پرداخت) صورت‌مسئله. این دو
حوزه در نگاه اول ساده به نظر می‌رسند، اما هر دو دام پنهان دارند: یکی تفاوت «حجم»
و «ارزش»، دیگری تفاوت «تراکنش» و «سفارش».

## ۲. مسئول اصلی و بازبین

| نوتبوک | مسئول اصلی | بازبین |
| :--- | :--- | :--- |
| `05_product_analysis.ipynb` | **Member C** | **Member A** |
| `06_payment_analysis.ipynb` | **Member B** | **Member C** |

## ۳. پیش‌نیازها

- مرحله ۳ و ۴ ادغام شده باشند
- گرین `item_features` و `order_features` در دسترس باشند

## ۴. شاخه Git

```bash
# Member C
git checkout -b feat/product-analysis
# Member B
git checkout -b feat/payment-analysis
```

## ۵. فایل‌های موردنیاز

| فایل | کار |
| :--- | :--- |
| `src/olist_analysis/metrics.py` | توابع بخش ۷ و ۸ |
| `notebooks/05_product_analysis.ipynb` | روایت محصولات |
| `notebooks/06_payment_analysis.ipynb` | روایت پرداخت |
| `src/olist_analysis/plotting.py` | نمودارهای بخش ۷ و ۸ |

## ۶. محتوای مورد انتظار

### توابع بخش ۷ (محصولات)

| تابع | خروجی | نکته طراحی |
| :--- | :--- | :--- |
| `category_performance` | یک ردیف برای هر دسته‌بندی | هم‌زمان حجم، مبلغ، متوسط قیمت و هر دو رتبه |
| `top_categories` | ده دسته برتر بر اساس معیار انتخابی | برای متوسط قیمت، حداقل حجم لازم است |
| `top_n_revenue_share` | سهم n دسته اول | مخرج صریح |
| `category_rank_comparison` | رتبه حجم در برابر رتبه مبلغ | ستون اختلاف رتبه |

**نکته مهم:** مبلغ فروش دسته‌بندی از ستون `price` جدول اقلام محاسبه می‌شود. هر
سطر آن جدول **یک واحد** کالا است (ستون تعداد وجود ندارد)، پس مبلغ فروش سطر برابر
همان `price` است. کرایه جدا گزارش می‌شود و در مبلغ فروش دسته‌بندی نمی‌آید. این
عدد با درآمد خالص یا سود یکسان نیست و نباید چنین معرفی شود.

برای «پنج دسته با بالاترین متوسط قیمت»، اگر بدون حداقل حجم فیلتر کنید، یک محصول
گران‌قیمت تنها می‌تواند یک دسته‌بندی را به صدر بیاورد. آستانه حجم لازم است.

### توابع بخش ۸ (پرداخت)

| تابع | خروجی | نکته طراحی |
| :--- | :--- | :--- |
| `payment_reconciliation` | تفکیک سه جامعه آماری | پایه همه تفسیرها |
| `payment_type_summary` | تعداد، سهم، مجموع و میانگین هر روش | ستون‌های `n` و `pct` با هم |
| `installment_distribution` | توزیع تعداد اقساط | ردیف‌های صفر قسط کنار گذاشته شوند |
| `zero_or_single_installments` | پرداخت بدون قسط یا یک‌قسطی | هم کل، هم به تفکیک روش |
| `installments_by_type_summary` | ساختار اقساط هر روش | نشان می‌دهد فقط کارت اعتباری اقساط دارد |
| `combined_payment_vs_installments` | رابطه مبلغ و اقساط | هم سطح تراکنش، هم سطح سفارش |

**نکته مهم:** در جدول پرداخت‌ها هر ردیف یک **تراکنش** است. ۱۰۳٬۸۸۶ تراکنش برای
۹۹٬۴۴۰ سفارش و ۹۶٬۰۹۶ خریدار. اگر تعداد ردیف پرداخت را به‌عنوان «تعداد سفارش»
گزارش کنید، دقت تحلیل پایین می‌آید. جدول `payment_reconciliation` این تفکیک را
صریح می‌کند.

## ۷. دستورات ترمینال

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import sys; sys.path.insert(0,'src'); from olist_analysis.features import load_dataset; from olist_analysis import metrics as M; d=load_dataset(); print(M.payment_type_summary(d).to_string())"
python -m pytest tests\test_metrics.py -q
```

## ۸. آزمون‌ها

| آزمون | چه چیزی را قفل می‌کند |
| :--- | :--- |
| `test_payment_type_summary_shares` | جمع سهم تراکنش‌ها = ۱۰۰ |
| `test_zero_or_single_installments_isolates_the_zero_row` | تفکیک ردیف صفر قسط |
| `test_installment_distribution_excludes_zero_installments` | توزیع اقساط فقط با مقادیر مثبت |
| `test_real_category_revenue_share_sums_to_one_hundred` | جمع سهم دسته‌بندی‌ها |
| `test_real_seller_revenue_equals_category_revenue_total` | دو تجمیع از یک مبنا برابر باشند |
| `test_real_payment_correlation_is_positive` | رابطه مثبت مبلغ و اقساط |

## ۹. خروجی مورد انتظار (اعداد واقعی تأییدشده)

### محصولات

| مورد | مقدار |
| :--- | ---: |
| تعداد دسته‌بندی (بدون `unknown`) | ۷۳ |
| رتبه اول حجم | `bed_bath_table` با ۱۱٬۱۱۵ قلم |
| رتبه اول مبلغ فروش | `health_beauty` با ۱٬۲۵۸٬۶۸۱.۳۴ رئال (۹.۲۶٪) |
| بزرگ‌ترین اختلاف رتبه | `watches_gifts` رتبه ۷ حجم و رتبه ۲ مبلغ |
| گران‌ترین دسته | `computers` با متوسط ۱٬۰۹۸.۳۴ رئال |
| سهم پنج دسته اول | ۴۰.۲۷٪ از کل مبلغ فروش |

### پرداخت

| مورد | مقدار |
| :--- | ---: |
| تراکنش پرداخت / سفارش یکتا | ۱۰۳٬۸۸۶ / ۹۹٬۴۴۰ |
| سهم کارت اعتباری از تراکنش | ۷۳.۹۲٪ (۷۶٬۷۹۵ تراکنش) |
| سهم کارت اعتباری از ارزش | ۷۸.۳۴٪ |
| پرداخت یک‌قسطی | ۵۲٬۵۴۶ تراکنش (۵۰.۵۸٪) |
| ردیف با صفر قسط | ۲ ردیف |
| میانگین اقساط کارت اعتباری | ۳.۵۱ (بیشینه ۲۴) |
| ضریب اسپیرمن مبلغ و اقساط | ۰.۴۱۱ (تراکنش) / ۰.۴۷۸ (فقط کارت اعتباری) |

## ۱۰. پیام Commit پیشنهادی

```text
feat: implement product performance and payment behaviour analysis

- compare category rankings by volume and by revenue
- guard the average-price ranking with a minimum volume threshold
- document that installments exist only for credit card payments
```

## ۱۱. Push و Pull Request

```bash
git add src/olist_analysis/metrics.py notebooks/05_product_analysis.ipynb
git commit -m "feat: implement product performance analysis"
git push -u origin feat/product-analysis
```

## ۱۲. مواردی که بازبین باید کنترل کند

۱. مبلغ فروش دسته‌بندی فقط از `price` باشد و کرایه جدا گزارش شود.
۲. هر مقدمه‌ای که «مبلغ فروش» را با «درآمد» یا «سود» یکسان بگیرد، اصلاح شود.
۳. برای متوسط قیمت، آستانه حداقل حجم اعمال شده باشد.
۴. در تحلیل پرداخت، تمایز تراکنش/سفارش/مشتری صریح باشد.
۵. تفسیر اقساط بر پایه مقدار واقعی داده باشد (فقط کارت اعتباری اقساط دارد).
۶. ردیف‌های صفر قسط به‌درستی مدیریت شده باشند (در مجموع بمانند، در توزیع نباشند).

## ۱۳. معیار پذیرش

- [ ] همه سؤال‌های بخش ۷ و ۸ پاسخ داده شده باشند
- [ ] مقایسه رتبه حجم و مبلغ با نمونه مشخص انجام شده باشد
- [ ] سهم پنج دسته اول محاسبه شده باشد
- [ ] رابطه مبلغ و اقساط با ضریب همبستگی گزارش شده باشد
- [ ] نوتبوک‌ها بدون خطا اجرا شوند
- [ ] PR تأیید و ادغام شده باشد

## ۱۴. شرط شروع مرحله بعد

پس از ادغام، توابع بخش ۷ و ۸ در `metrics.py` قفل می‌شوند. مرحله بعد (ارسال و
رضایت) به `order_category` و جدول امتیاز یک‌به‌یک سفارش وابسته است که هر دو در
مرحله ۳ ساخته شده‌اند.

</div>
