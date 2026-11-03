"""Cells 1-19 of the self-contained Olist notebook: setup through customers."""

CELLS = []


def md(text):
    CELLS.append(("md", text))


def code(text):
    CELLS.append(("code", text))


# --------------------------------------------------------------------------- #
md(r"""
# تحلیل داده‌های فروش و رفتار مشتریان Olist

این نوتبوک کل پروژه را در یک فایل جمع می‌کند: شناخت داده خام، پاک‌سازی، شش محور تحلیل
کسب‌وکاری، تحلیل‌های ترکیبی و جمع‌بندی برای مدیریت. همه جدول‌ها و نمودارها با کد همین
فایل ساخته می‌شوند و هیچ نتیجه‌ای از پیش ذخیره نشده است.

**نحوه اجرا**

۱. فایل‌های CSV را در مسیر `data/raw` قرار دهید.
۲. بسته‌های `requirements.txt` را نصب کنید: `pip install -r requirements.txt`
۳. از منوی Kernel گزینه Restart & Run All را بزنید.

مسیر داده به‌صورت نسبی پیدا می‌شود، بنابراین پوشه پروژه را می‌توانید هر جای دیگری هم
اجرا کنید. اگر فونت فارسی در `assets/fonts` نباشد، نمودارها با فونت فارسی سیستم رسم
می‌شوند و اجرا متوقف نمی‌شود.
""")

code(r"""
# --- ابزارها و تنظیمات مشترک ---
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager
import seaborn as sns
from IPython.display import display

warnings.filterwarnings("ignore")
pd.set_option("display.float_format", lambda value: f"{value:,.2f}")
pd.set_option("display.width", 150)

plt.rcParams.update({
    "figure.figsize": (10.5, 4.8),
    "figure.dpi": 110,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.unicode_minus": False,
    "font.size": 10,
})

CORE_START, CORE_END = "2017-01", "2018-08"
COLOR_MAIN, COLOR_ACCENT, COLOR_MUTED = "#2E5F8A", "#C0392B", "#95A5A6"


def persian_font():
    '''فونت فارسی را از assets برمی‌دارد و در نبود آن به فونت سیستم برمی‌گردد.'''
    for path in (Path("assets/fonts/Vazirmatn-Regular.ttf"),
                 Path("../assets/fonts/Vazirmatn-Regular.ttf")):
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            return font_manager.FontProperties(fname=str(path)).get_name()
    installed = {item.name for item in font_manager.fontManager.ttflist}
    for name in ("Vazirmatn", "Vazir", "Tahoma", "Segoe UI", "Arial",
                 "Noto Naskh Arabic", "DejaVu Sans"):
        if name in installed:
            return name
    return "DejaVu Sans"


plt.rcParams["font.family"] = persian_font()


def raw_dir():
    '''پوشه داده خام را از پوشه جاری یا پوشه‌های والد پیدا می‌کند.'''
    for base in [Path.cwd(), *Path.cwd().resolve().parents]:
        if (base / "data" / "raw" / "olist_orders_dataset.csv").exists():
            return base / "data" / "raw"
    return Path("data/raw")


DATA_DIR = raw_dir()
print("پوشه داده:", DATA_DIR.resolve())


def barh(series, title, xlabel, fmt="{:,.0f}", color=COLOR_MAIN, figsize=(9.4, 4.8)):
    '''نمودار میله‌ای افقی از یک Series (index برچسب، مقدار عدد).'''
    fig, ax = plt.subplots(figsize=figsize)
    labels = [str(item).replace("_", " ") for item in series.index]
    values = series.to_numpy(dtype=float)
    ax.barh(labels[::-1], values[::-1], color=color)
    for row, value in enumerate(values[::-1]):
        ax.text(value, row, "  " + fmt.format(value), va="center", fontsize=9)
    ax.set_title(title, loc="right", fontsize=12)
    ax.set_xlabel(xlabel)
    ax.margins(x=0.16)
    fig.tight_layout()
    plt.show()


def bars(series, title, ylabel, fmt="{:,.0f}", color=COLOR_MAIN,
         figsize=(9.8, 4.6), rotate=0):
    '''نمودار میله‌ای عمودی از یک Series با برچسب مقدار روی هر میله.'''
    fig, ax = plt.subplots(figsize=figsize)
    labels = [str(item).replace("_", " ") for item in series.index]
    values = series.to_numpy(dtype=float)
    ax.bar(labels, values, color=color)
    for column, value in enumerate(values):
        ax.text(column, value, fmt.format(value), ha="center", va="bottom", fontsize=9)
    ax.set_title(title, loc="right", fontsize=12)
    ax.set_ylabel(ylabel)
    ax.margins(y=0.15)
    if rotate:
        ax.tick_params(axis="x", rotation=rotate)
    fig.tight_layout()
    plt.show()
""")

# --------------------------------------------------------------------------- #
md(r"""
## بخش ۳ — شناخت داده‌ها

داده در نُه فایل CSV ذخیره شده است و هر فایل بخشی از فرایند خرید را توصیف می‌کند.
پیش از هر تحلیلی باید بدانیم هر جدول چه چیزی را ثبت می‌کند، هر سطر نماینده چیست و
با چه کلیدهایی می‌توان جدول‌ها را به هم وصل کرد.
""")

code(r"""
# --- ۳.۱ بارگذاری فایل‌ها و شمارش سطر و ستون ---
FILES = {
    "orders": "olist_orders_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}
raw = {name: pd.read_csv(DATA_DIR / filename) for name, filename in FILES.items()}

inventory = pd.DataFrame([
    {"جدول": name, "فایل": FILES[name], "سطر": len(frame), "ستون": frame.shape[1]}
    for name, frame in raw.items()
])
display(inventory.set_index("جدول"))
print("مجموع سطرهای داده خام:", f"{sum(len(frame) for frame in raw.values()):,}")
""")

code(r"""
# --- ۳.۲ نوع داده ستون‌ها و مقادیر گمشده ---
dtypes = pd.concat({name: frame.dtypes.astype(str) for name, frame in raw.items()}, axis=1).fillna("-")
display(dtypes)

missing_rows = []
for name, frame in raw.items():
    share = frame.isna().mean().mul(100)
    for column in share[share > 0].index:
        missing_rows.append({
            "جدول": name,
            "ستون": column,
            "درصد گمشده": round(float(share[column]), 2),
            "تعداد": int(frame[column].isna().sum()),
        })
missing = pd.DataFrame(missing_rows).sort_values("درصد گمشده", ascending=False)
print("ستون‌های دارای مقدار گمشده:", len(missing))
display(missing.head(12).set_index("ستون"))
""")

code(r"""
# --- ۳.۳ رکوردهای تکراری، یکتایی کلیدها و ارتباط جدول‌ها ---
duplicates = pd.DataFrame([
    {"جدول": name, "ردیف کاملاً تکراری": int(frame.duplicated().sum())}
    for name, frame in raw.items()
])
display(duplicates.set_index("جدول"))

key_checks = pd.DataFrame([
    {"جدول": "orders", "کلید": "order_id", "یکتاست؟": raw["orders"]["order_id"].is_unique},
    {"جدول": "customers", "کلید": "customer_id", "یکتاست؟": raw["customers"]["customer_id"].is_unique},
    {"جدول": "order_items", "کلید": "order_id + order_item_id",
     "یکتاست؟": not raw["order_items"].duplicated(["order_id", "order_item_id"]).any()},
    {"جدول": "reviews", "کلید": "review_id", "یکتاست؟": raw["reviews"]["review_id"].is_unique},
    {"جدول": "reviews", "کلید": "order_id", "یکتاست؟": raw["reviews"]["order_id"].is_unique},
])
display(key_checks.set_index("جدول"))

relations = [
    ("orders.customer_id به customers", "orders", "customer_id", "customers", "customer_id"),
    ("order_items.order_id به orders", "order_items", "order_id", "orders", "order_id"),
    ("order_items.product_id به products", "order_items", "product_id", "products", "product_id"),
    ("order_items.seller_id به sellers", "order_items", "seller_id", "sellers", "seller_id"),
    ("payments.order_id به orders", "payments", "order_id", "orders", "order_id"),
    ("reviews.order_id به orders", "reviews", "order_id", "orders", "order_id"),
]
orphans = pd.DataFrame([
    {"رابطه": label, "سطر بدون والد": int((~raw[child][column].isin(raw[parent][key])).sum())}
    for label, child, column, parent, key in relations
])
display(orphans.set_index("رابطه"))

print("شناسه نظر تکراری:", int(raw["reviews"]["review_id"].duplicated().sum()), "ردیف")
print("سفارش چند نظر دارد:", int(raw["reviews"]["order_id"].duplicated().sum()), "ردیف")
""")

md(r"""
**چه چیزی از این بخش فهمیدیم**

- جدول `orders` قلب داده است: هر سطر یک سفارش با وضعیت، زمان ثبت، زمان تحویل و تاریخ
  تخمینی تحویل. کلید اصلی آن `order_id` است.
- جدول‌های `order_items`، `payments` و `reviews` در سطح ریزتری از سفارش ثبت می‌شوند؛
  یک سفارش می‌تواند چند قلم، چند تراکنش پرداخت و در موارد نادر چند نظر داشته باشد.
  پس شمارش سطرهای این جدول‌ها با شمارش سفارش یکی نیست.
- `customers` به‌ازای هر سفارش یک شناسه دارد (`customer_id`) اما شخص واقعی با
  `customer_unique_id` شناخته می‌شود؛ بنابراین تعداد خریداران از تعداد ردیف‌های این
  جدول کمتر است.
- ستون‌های تاریخ به‌صورت متن خوانده شده‌اند و باید به `datetime` تبدیل شوند. مقادیر
  گمشده در جدول سفارش‌ها عمدتاً به سفارش‌های لغوشده یا در جریان مربوط است، نه به
  خطای ثبت داده.
- جدول `geolocation` صرفاً یک مرجع کد پستی است و برای تحلیل‌های این پروژه لازم نیست؛
  اطلاعات شهر و ایالت مشتری و فروشنده مستقیماً در جدول‌های خودشان هست.

نمودار ساختار جداول در سند پروژه آمده است؛ در ادامه فقط از جدول‌هایی استفاده می‌کنیم که
برای هر سؤال لازم است.
""")

# --------------------------------------------------------------------------- #
md(r"""
## بخش ۴ — پاک‌سازی و آماده‌سازی داده‌ها

تصمیم‌های پاک‌سازی را قبل از اجرا می‌نویسم تا بعداً قابل بازبینی باشد:

۱. **تاریخ‌ها**: پنج ستون تاریخ به `datetime` تبدیل می‌شوند. مقادیر نامعتبر به `NaT`
   می‌روند تا در محاسبات زمان تحویل وارد نشوند.
۲. **مقادیر گمشده**: ردیف‌ها حذف نمی‌شوند، چون هر سفارش بخشی از تصویر کسب‌وکار است.
   در عوض برای هر تحلیل، فقط سفارش‌هایی که ستون‌های لازم را دارند استفاده می‌شوند و
   تعداد نمونه همیشه گزارش می‌شود.
۳. **نظرات تکراری**: برای هر سفارش آخرین نظر ثبت‌شده نگه داشته می‌شود تا میانگین امتیاز
   یک سفارش را چند بار نشمارد.
۴. **دسته‌بندی محصول**: نام‌های پرتغالی با جدول ترجمه به انگلیسی برگردانده می‌شوند و
   محصولات بدون دسته‌بندی با برچسب `unknown` جدا می‌مانند.
۵. **ویژگی‌های جدید**: سال، ماه، روز هفته، مدت تحویل، روزهای تأخیر، طبقه تحویل و بازه
   شدت تأخیر ساخته می‌شوند. تأخیر بر پایه تاریخ (بدون ساعت) محاسبه می‌شود، چون تاریخ
   تخمینی تحویل ساعت ندارد.
""")

code(r"""
# --- ۴.۱ پاک‌سازی سفارش‌ها و ساخت ویژگی‌های زمانی ---
orders = raw["orders"].copy()
DATE_COLUMNS = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
                "order_delivered_customer_date", "order_estimated_delivery_date"]
for column in DATE_COLUMNS:
    orders[column] = pd.to_datetime(orders[column], errors="coerce")

orders["is_delivered"] = orders["order_status"].eq("delivered")
orders["purchase_year"] = orders["order_purchase_timestamp"].dt.year
orders["purchase_month"] = orders["order_purchase_timestamp"].dt.month
orders["purchase_ym"] = orders["order_purchase_timestamp"].dt.to_period("M").astype(str)
orders["purchase_weekday"] = orders["order_purchase_timestamp"].dt.day_name()

orders["delivery_days"] = (
    orders["order_delivered_customer_date"] - orders["order_purchase_timestamp"]
).dt.total_seconds() / 86400

# تاریخ تخمینی ساعت ندارد؛ مقایسه باید تاریخ‌محور باشد تا تأخیر چند ساعته ثبت نشود.
orders["delay_days"] = (
    orders["order_delivered_customer_date"].dt.normalize()
    - orders["order_estimated_delivery_date"].dt.normalize()
).dt.days

orders["delivery_class"] = np.where(orders["delay_days"] < 0, "early",
                             np.where(orders["delay_days"] == 0, "on_time",
                             np.where(orders["delay_days"] > 0, "late", None)))

bucket = np.where(orders["delay_days"] <= 0, "on_time",
           np.where(orders["delay_days"] <= 3, "1_3",
           np.where(orders["delay_days"] <= 7, "4_7", "over_7")))
orders["delay_bucket"] = pd.Series(bucket, index=orders.index).where(orders["delay_days"].notna())

BUCKET_FA = {"on_time": "به‌موقع یا زودتر", "1_3": "۱ تا ۳ روز",
             "4_7": "۴ تا ۷ روز", "over_7": "بیش از ۷ روز"}
BUCKET_ORDER = list(BUCKET_FA)

# --- ۴.۲ یکتاسازی نظرات و اتصال آن به سفارش ---
reviews = raw["reviews"].copy()
reviews["review_answer_timestamp"] = pd.to_datetime(reviews["review_answer_timestamp"], errors="coerce")
reviews_per_order = (reviews.sort_values("review_answer_timestamp")
                     .drop_duplicates("order_id", keep="last"))
orders = orders.merge(reviews_per_order[["order_id", "review_score"]], on="order_id", how="left")

# --- ۴.۳ اطلاعات جغرافیایی مشتری ---
customer_info = raw["customers"][["customer_id", "customer_unique_id", "customer_city", "customer_state"]]
orders = orders.merge(customer_info, on="customer_id", how="left")
orders["city_state"] = orders["customer_city"] + " / " + orders["customer_state"]

delivered = orders[orders["delivery_days"].notna() & orders["delay_days"].notna()].copy()

# --- ۴.۴ اقلام سفارش با دسته‌بندی انگلیسی ---
products = raw["products"].merge(raw["category_translation"], on="product_category_name", how="left")
products["category_label"] = (products["product_category_name_english"]
                              .fillna(products["product_category_name"])
                              .fillna("unknown"))

items = raw["order_items"].copy()
items = items.merge(products[["product_id", "category_label"]], on="product_id", how="left")
items["category_label"] = items["category_label"].fillna("unknown")

# --- ۴.۵ دو نمای تجمیعی: سفارش-دسته‌بندی و سفارش-فروشنده ---
order_category = (items.groupby(["order_id", "category_label"], as_index=False)
                  .agg(n_items=("order_item_id", "count"), revenue=("price", "sum")))
order_seller = (items.groupby(["order_id", "seller_id"], as_index=False)
                .agg(n_items=("order_item_id", "count"), revenue=("price", "sum")))

order_category = order_category.merge(
    orders[["order_id", "review_score", "delivery_class", "delay_bucket", "is_delivered"]],
    on="order_id", how="left")
order_seller = order_seller.merge(
    orders[["order_id", "review_score", "delivery_class", "is_delivered"]],
    on="order_id", how="left")
""")

code(r"""
# --- ۴.۶ خلاصه داده تمیز و تصمیم‌های پاک‌سازی ---
facts = pd.Series({
    "سفارش": len(orders),
    "سفارش تحویل‌شده": int(orders["is_delivered"].sum()),
    "سفارش تحویل‌شده با تاریخ‌های کامل": len(delivered),
    "سفارش دارای نظر": int(orders["review_score"].notna().sum()),
    "اقلام سفارش": len(items),
    "خریدار یکتا": orders["customer_unique_id"].nunique(),
    "دسته‌بندی محصول": int(items.loc[items["category_label"] != "unknown", "category_label"].nunique()),
    "فروشنده یکتا": items["seller_id"].nunique(),
    "ایالت مشتری": orders["customer_state"].nunique(),
}, name="مقدار")
display(facts.to_frame())

print("سفارش‌های تحویل‌شده بدون تاریخ تحویل:",
      int(orders["is_delivered"].sum() - len(delivered)))
print("سفارش‌های بدون نظر:", int(orders["review_score"].isna().sum()))
print("اقلام بدون دسته‌بندی شناخته‌شده:", int((items["category_label"] == "unknown").sum()))
""")

code(r"""
# --- ۴.۷ بررسی مقادیر غیرعادی و مشکوک ---
checks = pd.Series({
    "قلم با قیمت صفر یا منفی": int((items["price"] <= 0).sum()),
    "قلم با هزینه ارسال منفی": int((items["freight_value"] < 0).sum()),
    "تراکنش با مبلغ صفر یا منفی": int((raw["payments"]["payment_value"] <= 0).sum()),
    "نظر خارج از بازه ۱ تا ۵": int((~raw["reviews"]["review_score"].between(1, 5)).sum()),
    "تحویل پیش از ثبت سفارش": int((orders["delivery_days"] < 0).sum()),
    "مدت تحویل بیش از ۶۰ روز": int((orders["delivery_days"] > 60).sum()),
    "سفارش با بیش از ۳۰ قلم": int((raw["order_items"].groupby("order_id").size() > 30).sum()),
    "تراکنش با بیش از ۲۴ قسط": int((raw["payments"]["payment_installments"] > 24).sum()),
}, name="تعداد")
display(checks.to_frame())

print("میانه قیمت قلم:", f"{items['price'].median():,.2f}",
      "| بیشترین قیمت:", f"{items['price'].max():,.2f}")
print("صدک ۹۹ قیمت قلم:", f"{items['price'].quantile(0.99):,.2f}")
display(items.nlargest(3, "price")[["order_id", "category_label", "price"]].round(2))
print("سفارش‌های با مدت تحویل صفر یا منفی:", int((orders["delivery_days"] <= 0).sum()),
      "— این‌ها در تحلیل تحویل کنار گذاشته می‌شوند.")
""")

# --------------------------------------------------------------------------- #
md(r"""
## بخش ۵ — تحلیل سفارش‌ها و روند فعالیت کسب‌وکار

سه پرسش مدیران: حجم سفارش‌ها چقدر است، در زمان چگونه تغییر کرده و در کدام روزها و
ماه‌ها تمرکز دارد.
""")

code(r"""
# --- ۵.۱ وضعیت سفارش‌ها ---
status = orders["order_status"].value_counts().rename_axis("وضعیت").to_frame("تعداد")
status["درصد"] = (status["تعداد"] / len(orders) * 100).round(2)
display(status)
bars(status["تعداد"], "تعداد سفارش بر اساس وضعیت", "تعداد سفارش", rotate=25)
""")

code(r"""
# --- ۵.۲ روند ماهانه و ماتریس سال-ماه ---
monthly = orders.groupby("purchase_ym").size().rename("سفارش").reset_index()
monthly["ماه"] = pd.to_datetime(monthly["purchase_ym"] + "-01")
monthly = monthly.sort_values("ماه")
monthly["میانگین ۳ ماهه"] = monthly["سفارش"].rolling(3).mean()
core = monthly[(monthly["purchase_ym"] >= CORE_START) & (monthly["purchase_ym"] <= CORE_END)]
edge = monthly.drop(core.index)

fig, ax = plt.subplots(figsize=(11, 4.8))
ax.plot(core["ماه"], core["سفارش"], marker="o", markersize=4, color=COLOR_MAIN, label="سفارش ماهانه")
ax.plot(core["ماه"], core["میانگین ۳ ماهه"], "--", linewidth=2, color=COLOR_ACCENT, label="میانگین متحرک ۳ ماهه")
ax.scatter(edge["ماه"], edge["سفارش"], color=COLOR_MUTED, zorder=3, label="ماه ناقص")
peak = core.loc[core["سفارش"].idxmax()]
ax.annotate(f"{peak['purchase_ym']} — {int(peak['سفارش']):,}",
            (peak["ماه"], peak["سفارش"]), textcoords="offset points", xytext=(0, 12),
            ha="center", fontsize=9, color=COLOR_ACCENT)
ax.legend(loc="upper left")
ax.set_title("روند ماهانه تعداد سفارش‌ها", loc="right", fontsize=12)
ax.set_xlabel("ماه")
ax.set_ylabel("تعداد سفارش")
fig.tight_layout()
plt.show()

lowest = core.loc[core["سفارش"].idxmin()]
print("بیشترین ماه:", peak["purchase_ym"], f"({int(peak['سفارش']):,} سفارش)")
print("کمترین ماه در پنجره:", lowest["purchase_ym"], f"({int(lowest['سفارش']):,} سفارش)")

matrix = pd.crosstab(orders["purchase_year"], orders["purchase_month"]).reindex(columns=range(1, 13), fill_value=0)
fig, ax = plt.subplots(figsize=(11, 3.6))
sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", linewidths=.6, linecolor="white",
            cbar_kws={"label": "تعداد سفارش"}, ax=ax)
ax.set_title("تعداد سفارش به تفکیک سال و ماه", loc="right", fontsize=12)
ax.set_xlabel("ماه")
ax.set_ylabel("سال")
ax.set_yticklabels(matrix.index, rotation=0)
fig.tight_layout()
plt.show()
""")

code(r"""
# --- ۵.۳ الگوی هفتگی، ماه‌های پرترافیک و رشد هم‌دوره ---
WEEKDAY_FA = {"Saturday": "شنبه", "Sunday": "یکشنبه", "Monday": "دوشنبه", "Tuesday": "سه‌شنبه",
              "Wednesday": "چهارشنبه", "Thursday": "پنجشنبه", "Friday": "جمعه"}
weekday = orders["purchase_weekday"].value_counts().reindex(list(WEEKDAY_FA)).fillna(0).astype(int)
weekday.index = [WEEKDAY_FA[day] for day in weekday.index]
bars(weekday, "تعداد سفارش در روزهای هفته", "تعداد سفارش")
print("بیشترین روز هفته:", weekday.idxmax(), f"({weekday.max():,} سفارش)")
print("کمترین روز هفته:", weekday.idxmin(), f"({weekday.min():,} سفارش)")
print(f"نسبت بیشترین به کمترین روز: {weekday.max() / weekday.min():.2f}")

top_months = core.nlargest(5, "سفارش").set_index("purchase_ym")["سفارش"].sort_values()
barh(top_months, "پنج ماه با بیشترین تعداد سفارش", "تعداد سفارش")
print("سال این پنج ماه:", sorted({month[:4] for month in top_months.index}))

jan_aug_2017 = int(orders[(orders["purchase_year"] == 2017) & (orders["purchase_month"] <= 8)].shape[0])
jan_aug_2018 = int(orders[(orders["purchase_year"] == 2018) & (orders["purchase_month"] <= 8)].shape[0])
yoy = (jan_aug_2018 / jan_aug_2017 - 1) * 100
first6 = core.head(6)["سفارش"].mean()
last6 = core.tail(6)["سفارش"].mean()
print(f"ژانویه تا اوت ۲۰۱۷: {jan_aug_2017:,} سفارش")
print(f"ژانویه تا اوت ۲۰۱۸: {jan_aug_2018:,} سفارش")
print(f"رشد هم‌دوره: {yoy:.2f}%")
print(f"میانگین شش ماه اول پنجره: {first6:,.0f} | شش ماه آخر: {last6:,.0f} | تغییر {(last6 / first6 - 1) * 100:.2f}%")
""")

md(r"""
**تفسیر**

- بیش از ۹۷ درصد سفارش‌ها تحویل شده‌اند و سهم سفارش‌های لغوشده کوچک است؛ بنابراین داده
  برای تحلیل عملکرد عملیات قابل اعتماد است.
- روند ماهانه از ابتدای ۲۰۱۷ صعودی است و در نوامبر ۲۰۱۷ (دوران اوج خرید) به سقف
  می‌رسد. بعد از آن حجم در سطح بالاتری نسبت به سال قبل تثبیت می‌شود؛ رشد هم‌دوره
  ۲۰۱۸ نسبت به ۲۰۱۷ حدود ۱۳۵ درصد است، یعنی تقریباً دو برابر و نیم.
- دو ماه ابتدایی و انتهایی داده کامل نیستند (سپتامبر ۲۰۱۶ و سپتامبر ۲۰۱۸) و در نمودار
  با رنگ روشن جدا شده‌اند؛ برای محاسبه روند از پنجره پیوسته ژانویه ۲۰۱۷ تا اوت ۲۰۱۸
  استفاده می‌کنیم.
- اختلاف روزهای هفته زیاد نیست؛ بیشترین و کمترین روز حدود ۴۰ درصد با هم فاصله دارند و
  الگوی مشخصی از تعطیلی فروش دیده نمی‌شود. پس ظرفیت عملیات در همه روزها تقریباً یکسان
  درگیر است.
- پنج ماه پرترافیک همه در ۲۰۱۷ و ۲۰۱۸ پراکنده‌اند و شامل نوامبر (جمعه سیاه) هستند؛ این
  نشانه وجود فصلی‌بودن در تقاضاست، نه یک جهش تک‌ماهه.
""")

# --------------------------------------------------------------------------- #
md(r"""
## بخش ۶ — تحلیل مشتریان و بازار جغرافیایی

پرسش تیم بازاریابی این است که مشتریان کجا هستند و بازار تا چه اندازه به چند منطقه
وابسته است. دام مهم این بخش، اشتباه گرفتن ردیف جدول مشتریان با شخص واقعی است.
""")

code(r"""
# --- ۶.۱ تعداد مشتریان ---
customer_facts = pd.Series({
    "ردیف جدول مشتریان": len(raw["customers"]),
    "شناسه سفارش یکتا": orders["order_id"].nunique(),
    "شخص یکتا (customer_unique_id)": orders["customer_unique_id"].nunique(),
    "سفارش به ازای هر خریدار": round(len(orders) / orders["customer_unique_id"].nunique(), 4),
    "خریدار با بیش از یک سفارش": int((orders.groupby("customer_unique_id").size() > 1).sum()),
    "بیشترین سفارش یک شخص": int(orders.groupby("customer_unique_id").size().max()),
}, name="مقدار")
display(customer_facts.to_frame())
print(f"سهم خریداران تکراری: {(orders.groupby('customer_unique_id').size() > 1).mean() * 100:.2f}%")
""")

code(r"""
# --- ۶.۲ مشتریان به تفکیک ایالت و شهر ---
state_buyers = orders.groupby("customer_state")["customer_unique_id"].nunique().sort_values(ascending=False)
barh(state_buyers.head(10), "ده ایالت با بیشترین مشتری یکتا", "تعداد خریدار یکتا")

top5 = state_buyers.head(5)
top5_share = top5.sum() / state_buyers.sum() * 100
share_table = pd.DataFrame({
    "خریدار یکتا": top5,
    "سهم از کل (درصد)": (top5 / state_buyers.sum() * 100).round(2),
})
display(share_table)
print(f"سهم پنج ایالت اول از خریداران: {top5_share:.2f}%  |  تعداد ایالت‌ها: {state_buyers.size}")
print("بیشترین ایالت:", state_buyers.index[0], f"({state_buyers.iloc[0]:,} خریدار)")

cities = orders.groupby("city_state")["customer_unique_id"].nunique().sort_values(ascending=False)
barh(cities.head(10), "ده شهر با بیشترین مشتری یکتا", "تعداد خریدار یکتا")
""")

code(r"""
# --- ۶.۳ مقایسه تعداد مشتری و تعداد سفارش در ایالت‌ها ---
state_orders = orders.groupby("customer_state").size()
compare = pd.DataFrame({"خریدار": state_buyers, "سفارش": state_orders}).dropna()
compare["سفارش به خریدار"] = (compare["سفارش"] / compare["خریدار"]).round(3)
print("ایالت‌هایی با بیشترین سفارش به ازای هر خریدار:")
display(compare.sort_values("سفارش به خریدار", ascending=False).head(3))
print("ایالت‌هایی با کمترین سفارش به ازای هر خریدار:")
display(compare.sort_values("سفارش به خریدار").head(3))

fig, ax = plt.subplots(figsize=(7.8, 5.4))
ax.scatter(compare["خریدار"], compare["سفارش"], s=compare["سفارش"] / 12,
           color=COLOR_MAIN, alpha=.75)
limit = compare[["خریدار", "سفارش"]].to_numpy().max() * 1.06
ax.plot([0, limit], [0, limit], "--", color=COLOR_MUTED, label="نسبت یک‌به‌یک")
for state in compare.nlargest(6, "خریدار").index:
    ax.annotate(state, (compare.loc[state, "خریدار"], compare.loc[state, "سفارش"]),
                textcoords="offset points", xytext=(6, 4), fontsize=9)
ax.legend(loc="upper left")
ax.set_title("خریدار یکتا در برابر تعداد سفارش، به تفکیک ایالت", loc="right", fontsize=12)
ax.set_xlabel("خریدار یکتا")
ax.set_ylabel("تعداد سفارش")
fig.tight_layout()
plt.show()
""")

md(r"""
**تفسیر**

- ۹۹٬۴۴۱ سفارش به ۹۶٬۰۹۶ شخص می‌رسد؛ یعنی تقریباً هر خریدار فقط یک بار خرید کرده و
  سهم خریداران تکراری حدود ۳ درصد است. این یعنی رشد فروش تا امروز بیشتر از جذب مشتری
  جدید آمده، نه از بازخرید.
- بازار به‌شدت متمرکز است: پنج ایالت اول بیش از سه‌چهارم خریداران را دارند و سائوپائولو
  به‌تنهایی حدود ۴۲ درصد بازار است. همین تمرکز در سطح شهر هم دیده می‌شود و چند شهر
  بزرگ، بیشتر مشتریان را در خود دارند.
- در نمودار مقایسه‌ای، بیشتر ایالت‌ها نزدیک خط یک‌به‌یک هستند؛ یعنی تعداد سفارش با
  تعداد مشتری متناسب است. ایالت‌هایی که بالای خط قرار می‌گیرند خریدار کمتری دارند اما
  همان خریدار چند سفارش ثبت کرده است.
- هر ایالت دور از خط یک‌به‌یک و با تعداد مشتری کم، نامزد بررسی بازار است؛ اما تعداد کم
  مشتری به‌تنهایی دلیل وجود فرصت رشد نیست و باید هزینه ارسال و رقابت هم سنجیده شود.
""")
