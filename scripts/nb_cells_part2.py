"""Cells: products, payments, delivery, satisfaction, delay vs satisfaction, sellers."""

CELLS = []


def md(text):
    CELLS.append(("md", text))


def code(text):
    CELLS.append(("code", text))


# --------------------------------------------------------------------------- #
md(r"""
## بخش ۷ — تحلیل محصولات و عملکرد فروش

تیم فروش می‌خواهد بداند تقاضا روی کدام دسته‌بندی‌ها متمرکز است و مبلغ فروش در کدام
دسته‌بندی‌ها بیشتر است. تفاوت این دو فهرست، همان جایی است که تصمیم‌گیری فقط بر پایه
تعداد فروش گمراه‌کننده می‌شود.
""")

code(r"""
# --- ۷.۱ تعداد اقلام فروخته‌شده در هر دسته‌بندی ---
category = (items.groupby("category_label")
            .agg(n_items=("order_item_id", "count"),
                 revenue=("price", "sum"),
                 mean_price=("price", "mean"),
                 mean_freight=("freight_value", "mean"))
            .reset_index())
category = category[category["category_label"] != "unknown"]
print("تعداد دسته‌بندی دارای فروش:", len(category))
print("مجموع اقلام فروخته‌شده:", f"{category['n_items'].sum():,}")

by_items = category.nlargest(10, "n_items").set_index("category_label")["n_items"].sort_values()
barh(by_items, "ده دسته‌بندی با بیشترین تعداد قلم فروخته‌شده", "تعداد قلم")
display(category.nlargest(5, "n_items").set_index("category_label")[["n_items", "revenue"]].round(2))
""")

code(r"""
# --- ۷.۲ مبلغ فروش و مقایسه رتبه‌ها ---
by_revenue = category.nlargest(10, "revenue").set_index("category_label")["revenue"].sort_values()
barh(by_revenue, "ده دسته‌بندی با بیشترین مبلغ فروش (BRL)", "مبلغ فروش، BRL")

category["rank_items"] = category["n_items"].rank(ascending=False, method="min").astype(int)
category["rank_revenue"] = category["revenue"].rank(ascending=False, method="min").astype(int)
category["rank_gap"] = category["rank_items"] - category["rank_revenue"]
gap = category.reindex(category["rank_gap"].abs().nlargest(8).index)
print("دسته‌بندی‌هایی که رتبه تعداد با رتبه مبلغ فاصله زیادی دارند:")
display(gap[["category_label", "n_items", "revenue", "rank_items", "rank_revenue", "rank_gap"]]
        .sort_values("rank_gap").set_index("category_label").round(2))
""")

code(r"""
# --- ۷.۳ متوسط قیمت و سهم از فروش ---
pricey = category[category["n_items"] >= 100].nlargest(5, "mean_price")
barh(pricey.set_index("category_label")["mean_price"].sort_values(),
     "پنج دسته‌بندی با بالاترین متوسط قیمت (حداقل ۱۰۰ قلم)", "متوسط قیمت، BRL",
     figsize=(9.4, 3.8))
print("آیا این دسته‌بندی‌ها در فهرست پرفروش‌ترین‌ها هم هستند؟")
display(pricey[["category_label", "mean_price", "n_items", "rank_items"]].set_index("category_label").round(2))

top5_revenue = category.nlargest(5, "revenue")
share = top5_revenue["revenue"].sum() / category["revenue"].sum() * 100
top5_table = top5_revenue.assign(سهم_درصد=(top5_revenue["revenue"] / category["revenue"].sum() * 100).round(2))
display(top5_table[["category_label", "revenue", "سهم_درصد"]].set_index("category_label"))
print(f"سهم پنج دسته‌بندی اول از مبلغ فروش: {share:.2f}%  |  مبلغ کل: {category['revenue'].sum():,.2f} BRL")
""")

code(r"""
# --- ۷.۴ تعداد قلم در برابر مبلغ فروش ---
fig, ax = plt.subplots(figsize=(8.4, 5.4))
ax.scatter(category["n_items"], category["revenue"], s=30, alpha=.7, color=COLOR_MAIN)
ax.set_xscale("log")
ax.set_yscale("log")
for name in category.nlargest(5, "revenue")["category_label"]:
    row = category[category["category_label"] == name].iloc[0]
    ax.annotate(name.replace("_", " "), (row["n_items"], row["revenue"]), fontsize=8,
                textcoords="offset points", xytext=(4, 4))
ax.set_title("تعداد قلم فروخته‌شده در برابر مبلغ فروش، به تفکیک دسته‌بندی", loc="right", fontsize=12)
ax.set_xlabel("تعداد قلم (مقیاس لگاریتمی)")
ax.set_ylabel("مبلغ فروش، BRL (مقیاس لگاریتمی)")
fig.tight_layout()
plt.show()

above = category[(category["rank_items"] <= 10) & (category["rank_revenue"] > 15)]
print("دسته‌بندی‌های پرتعداد با مبلغ فروش پایین‌تر:")
display(above[["category_label", "n_items", "revenue", "rank_revenue"]].set_index("category_label"))
""")

md(r"""
**تفسیر**

- ۷۳ دسته‌بندی دارای فروش داریم. پرتعدادترین دسته‌بندی `bed_bath_table` است، اما در
  مبلغ فروش جایگاه اول را ندارد؛ دسته‌بندی‌هایی مثل `health_beauty` و `watches_gifts`
  با تعداد کمتر، مبلغ بیشتری تولید می‌کنند.
- مقایسه رتبه‌ها نشان می‌دهد چند دسته‌بندی با حجم بالا در مبلغ فروش جایگاه پایین‌تری
  دارند؛ یعنی قیمت واحد پایین‌تری دارند و حاشیه کمتری روی هر قلم می‌سازند. تصمیم
  بازاریابی برای این گروه باید بر «افزایش سبد خرید» متمرکز باشد، نه تخفیف حجمی.
- دسته‌بندی‌های گران‌قیمت لزوماً پرفروش نیستند و برخی حتی در ۱۰ دسته‌بندی اول حجم هم
  قرار نمی‌گیرند؛ این گروه برای فروش مکمل و لوازم جانبی مناسب‌ترند.
- پنج دسته‌بندی اول حدود ۴۰ درصد مبلغ فروش را می‌سازند. این تمرکز یعنی هر اختلال در
  تأمین یا قیمت همین چند دسته‌بندی، مستقیماً روی درآمد اثر می‌گذارد.

**نکته روش‌شناسی:** مبلغ فروش از ستون `price` جدول اقلام محاسبه شده و هزینه ارسال
(`freight_value`) را شامل نمی‌شود؛ پس با درآمد خالص شرکت یکی نیست.
""")

# --------------------------------------------------------------------------- #
md(r"""
## بخش ۸ — تحلیل رفتار پرداخت مشتریان

در این بخش دو نکته روش‌شناختی مهم است: هر ردیف جدول پرداخت یک تراکنش است، نه یک سفارش؛
و مبلغ پرداخت‌شده با مبلغ اقلام یکی نیست، چون هزینه ارسال هم پرداخت می‌شود.
""")

code(r"""
# --- ۸.۱ روش‌های پرداخت ---
payments = raw["payments"].copy()
payment_facts = pd.Series({
    "ردیف پرداخت (تراکنش)": len(payments),
    "سفارش یکتا با پرداخت": payments["order_id"].nunique(),
    "سفارش در جدول سفارش": len(orders),
    "مجموع مبلغ پرداخت‌شده (BRL)": f"{payments['payment_value'].sum():,.2f}",
    "مجموع مبلغ اقلام (BRL)": f"{items['price'].sum():,.2f}",
    "مجموع هزینه ارسال (BRL)": f"{items['freight_value'].sum():,.2f}",
}, name="مقدار")
display(payment_facts.to_frame())

by_type = (payments.groupby("payment_type")
           .agg(تراکنش=("payment_value", "size"),
                مبلغ_کل=("payment_value", "sum"),
                میانگین=("payment_value", "mean")))
by_type["سهم_تراکنش_درصد"] = (by_type["تراکنش"] / len(payments) * 100).round(2)
by_type["سهم_مبلغ_درصد"] = (by_type["مبلغ_کل"] / payments["payment_value"].sum() * 100).round(2)
display(by_type.sort_values("تراکنش", ascending=False).round(2))

fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
ordered = by_type.sort_values("تراکنش", ascending=False)
labels = [name.replace("_", " ") for name in ordered.index]
axes[0].bar(labels, ordered["تراکنش"], color=COLOR_MAIN)
axes[0].set_title("تعداد تراکنش", loc="right")
axes[1].bar(labels, ordered["مبلغ_کل"], color="#7FA8C9")
axes[1].set_title("مجموع مبلغ، BRL", loc="right")
for axis in axes:
    axis.tick_params(axis="x", rotation=20)
fig.suptitle("روش‌های پرداخت: تعداد تراکنش و مبلغ کل", x=0.99, ha="right", fontsize=12)
fig.tight_layout()
plt.show()
""")

code(r"""
# --- ۸.۲ توزیع تعداد اقساط ---
installments = payments["payment_installments"].value_counts().sort_index()
installments.index = installments.index.astype(int)
install_table = pd.DataFrame({
    "اقساط": installments.index,
    "تراکنش": installments.values,
    "درصد": (installments.values / len(payments) * 100).round(2),
}).set_index("اقساط")
display(install_table)

share_single = (payments["payment_installments"] <= 1).mean() * 100
print(f"پرداخت بدون قسط یا یک‌قسطی: {share_single:.2f}%")
print("پرداخت با صفر قسط:", int((payments["payment_installments"] == 0).sum()), "تراکنش")
print("پرتکرارترین تعداد اقساط:", int(installments.idxmax()), f"({installments.max():,} تراکنش)")
print("بیشترین تعداد اقساط ثبت‌شده:", int(installments.index.max()))

bars(installments[installments.index <= 12].rename("تراکنش"),
     "توزیع تعداد اقساط (تا ۱۲ قسط)", "تعداد تراکنش")
""")

code(r"""
# --- ۸.۳ رابطه مبلغ پرداخت و تعداد اقساط ---
payment_rho = payments[["payment_value", "payment_installments"]].corr(method="spearman").iloc[0, 1]
payments["value_decile"] = pd.qcut(payments["payment_value"], 10, duplicates="drop")
deciles = (payments.groupby("value_decile", observed=True)
           .agg(تراکنش=("payment_value", "size"),
                میانگین_اقساط=("payment_installments", "mean"),
                چندقسطی_درصد=("payment_installments", lambda series: (series > 1).mean() * 100)))
deciles["بازه مبلغ"] = [f"{interval.left:,.0f} تا {interval.right:,.0f}" for interval in deciles.index]
display(deciles.reset_index(drop=True).set_index("بازه مبلغ").round(2))
print(f"همبستگی اسپیرمن مبلغ پرداخت و تعداد اقساط: {payment_rho:.4f}")

card_only = payments[payments["payment_type"] == "credit_card"]
card_rho = card_only[["payment_value", "payment_installments"]].corr(method="spearman").iloc[0, 1]
print(f"همین همبستگی فقط در کارت اعتباری: {card_rho:.4f}")

by_type_installments = (payments.groupby("payment_type")
                        .agg(میانگین_اقساط=("payment_installments", "mean"),
                             چندقسطی_درصد=("payment_installments", lambda series: (series > 1).mean() * 100)))
display(by_type_installments.round(2).sort_values("میانگین_اقساط", ascending=False))

fig, ax = plt.subplots(figsize=(10.4, 4.6))
ax.plot(deciles["بازه مبلغ"], deciles["میانگین_اقساط"], marker="o", color=COLOR_MAIN,
        label="میانگین تعداد اقساط")
ax.set_ylabel("میانگین تعداد اقساط")
ax2 = ax.twinx()
ax2.bar(deciles["بازه مبلغ"], deciles["چندقسطی_درصد"], alpha=.25, color=COLOR_ACCENT,
        label="سهم پرداخت چندقسطی (درصد)")
ax2.set_ylabel("درصد پرداخت‌های چندقسطی")
ax2.grid(False)
ax.set_title("مبلغ پرداخت و رفتار اقساط در دهک‌های مبلغ", loc="right", fontsize=12)
ax.set_xlabel("دهک مبلغ پرداخت، BRL")
ax.tick_params(axis="x", rotation=35)
ax.legend(loc="upper left")
ax2.legend(loc="lower right")
fig.tight_layout()
plt.show()
""")

md(r"""
**تفسیر**

- کارت اعتباری با فاصله زیاد پرکاربردترین روش است و پس از آن بولتو (رسید بانکی) قرار
  دارد. کارت اعتباری هم از نظر تعداد و هم از نظر مبلغ، ستون اصلی پرداخت‌هاست؛ بنابراین
  هر اختلال در درگاه کارت، مستقیماً فروش را متوقف می‌کند.
- حدود نیمی از تراکنش‌ها یک‌قسطی یا بدون قسط هستند و پرتکرارترین حالت یک قسط است. پس
  فرهنگ خرید اقساطی وجود دارد، اما اکثریت هنوز یک‌جا پرداخت می‌کنند.
- رابطه مبلغ و تعداد اقساط مثبت و متوسط است (اسپیرمن حدود ۰٫۴۱ در کل تراکنش‌ها و
  بالاتر در کارت اعتباری). از دهک کم‌مبلغ به دهک پرمبلغ، میانگین اقساط و سهم پرداخت
  چندقسطی به‌طور پیوسته بالا می‌رود؛ این رابطه گام‌به‌گام است، نه پرشی.
- جمع مبلغ پرداخت‌ها از جمع مبلغ اقلام بیشتر است و اختلاف تقریباً برابر مجموع هزینه
  ارسال است؛ این تطبیق نشان می‌دهد محاسبه مبلغ در دو جدول سازگار است.
""")

# --------------------------------------------------------------------------- #
md(r"""
## بخش ۹ — بررسی عملکرد ارسال سفارش‌ها

دو شاخص متفاوت داریم و نباید با هم اشتباه شوند: **مدت تحویل** (فاصله ثبت تا تحویل) و
**تأخیر** (تحویل واقعی نسبت به تاریخ تخمینی). ممکن است سفارشی ۲۰ روز طول بکشد اما
زودتر از موعد برسد.
""")

code(r"""
# --- ۹.۱ مدت زمان تحویل ---
duration = delivered["delivery_days"]
distribution = pd.Series({
    "تعداد سفارش": len(duration),
    "میانگین (روز)": round(duration.mean(), 2),
    "میانه (روز)": round(duration.median(), 2),
    "کمینه (روز)": round(duration.min(), 2),
    "بیشینه (روز)": round(duration.max(), 2),
    "صدک ۹۰ (روز)": round(duration.quantile(.90), 2),
    "صدک ۹۹ (روز)": round(duration.quantile(.99), 2),
    "چولگی": round(duration.skew(), 2),
}, name="مقدار")
display(distribution.to_frame())
print(f"اختلاف میانگین و میانه: {duration.mean() - duration.median():.2f} روز")

fig, ax = plt.subplots(figsize=(10.4, 4.6))
ax.hist(duration.clip(upper=60), bins=40, color=COLOR_MAIN, alpha=.85)
ax.axvline(duration.mean(), color=COLOR_ACCENT, linestyle="--", label=f"میانگین {duration.mean():.1f} روز")
ax.axvline(duration.median(), color="#2E8B57", linestyle="--", label=f"میانه {duration.median():.1f} روز")
ax.legend()
ax.set_title("توزیع زمان تحویل (برش در ۶۰ روز برای خوانایی)", loc="right", fontsize=12)
ax.set_xlabel("زمان تحویل، روز")
ax.set_ylabel("تعداد سفارش")
fig.tight_layout()
plt.show()
print(f"تحویل تا ۷ روز: {(duration <= 7).mean() * 100:.2f}%  |  بیش از ۳۰ روز: {(duration > 30).mean() * 100:.2f}%")
""")

code(r"""
# --- ۹.۲ مقایسه تحویل با تاریخ تخمینی ---
CLASS_FA = {"early": "زودتر از موعد", "on_time": "به‌موقع", "late": "دیرکرددار"}
class_table = delivered["delivery_class"].value_counts().rename_axis("طبقه").to_frame("تعداد")
class_table["درصد"] = (class_table["تعداد"] / len(delivered) * 100).round(2)
class_table.index = [CLASS_FA[key] for key in class_table.index]
display(class_table)
bars(class_table["تعداد"], "وضعیت تحویل نسبت به تاریخ تخمینی", "تعداد سفارش")

late_orders = delivered[delivered["delivery_class"] == "late"]
late_facts = pd.Series({
    "سفارش دیرکرددار": len(late_orders),
    "سهم از تحویل‌شده (درصد)": round(len(late_orders) / len(delivered) * 100, 2),
    "میانگین تأخیر (روز)": round(late_orders["delay_days"].mean(), 2),
    "میانه تأخیر (روز)": float(late_orders["delay_days"].median()),
    "تأخیر بیش از ۷ روز": int((late_orders["delay_days"] > 7).sum()),
    "تأخیر بیش از ۱۵ روز": int((late_orders["delay_days"] > 15).sum()),
}, name="مقدار")
display(late_facts.to_frame())

bucket_counts = delivered["delay_bucket"].value_counts().reindex(BUCKET_ORDER)
bucket_counts.index = [BUCKET_FA[key] for key in bucket_counts.index]
bars(bucket_counts, "توزیع سفارش‌ها بر اساس شدت تأخیر", "تعداد سفارش", rotate=15)
""")

code(r"""
# --- ۹.۳ عملکرد جغرافیایی و روند زمانی ---
state_delivery = (delivered.groupby("customer_state")
                  .agg(سفارش=("order_id", "size"),
                       میانگین_روز=("delivery_days", "mean"),
                       نرخ_تأخیر_درصد=("delivery_class", lambda series: (series == "late").mean() * 100),
                       میانگین_تأخیر=("delay_days", lambda series: series[series > 0].mean())))
eligible_states = state_delivery[state_delivery["سفارش"] >= 100].copy()
print("ایالت با حداقل ۱۰۰ سفارش:", len(eligible_states), "از", len(state_delivery))

slow_states = eligible_states.nlargest(10, "میانگین_روز").sort_values("میانگین_روز")
fig, ax = plt.subplots(figsize=(9.8, 4.8))
ax.barh(slow_states.index, slow_states["میانگین_روز"], color=COLOR_MAIN)
for row, state in enumerate(slow_states.index):
    value = slow_states.loc[state, "میانگین_روز"]
    count = int(slow_states.loc[state, "سفارش"])
    ax.text(value, row, f"  {value:.1f} روز (n={count:,})", va="center", fontsize=9)
ax.set_title("ده ایالت با بیشترین میانگین زمان تحویل", loc="right", fontsize=12)
ax.set_xlabel("میانگین زمان تحویل، روز")
ax.margins(x=0.24)
fig.tight_layout()
plt.show()

late_states = eligible_states.nlargest(10, "نرخ_تأخیر_درصد").sort_values("نرخ_تأخیر_درصد")
barh(late_states["نرخ_تأخیر_درصد"], "ده ایالت با بالاترین نرخ تأخیر",
     "درصد سفارش‌های دیرکرددار", fmt="{:.1f}%")
print("بدترین ایالت از نظر نرخ تأخیر:", late_states.index[-1],
      f"({late_states['نرخ_تأخیر_درصد'].iloc[-1]:.1f}% از {int(late_states['سفارش'].iloc[-1]):,} سفارش)")
""")

code(r"""
# --- ۹.۴ روند ماهانه زمان تحویل و نرخ تأخیر ---
monthly_delivery = (delivered.groupby("purchase_ym")
                    .agg(میانگین_روز=("delivery_days", "mean"),
                         نرخ_تأخیر_درصد=("delivery_class", lambda series: (series == "late").mean() * 100))
                    .reset_index())
monthly_delivery["ماه"] = pd.to_datetime(monthly_delivery["purchase_ym"] + "-01")
trend_delivery = monthly_delivery[(monthly_delivery["purchase_ym"] >= CORE_START)
                                  & (monthly_delivery["purchase_ym"] <= CORE_END)]

fig, ax = plt.subplots(figsize=(10.8, 4.6))
ax.plot(trend_delivery["ماه"], trend_delivery["میانگین_روز"], marker="o", color=COLOR_MAIN,
        label="میانگین زمان تحویل (روز)")
ax.set_ylabel("میانگین زمان تحویل، روز")
ax2 = ax.twinx()
ax2.plot(trend_delivery["ماه"], trend_delivery["نرخ_تأخیر_درصد"], marker="s",
         color=COLOR_ACCENT, label="نرخ تأخیر (درصد)")
ax2.set_ylabel("درصد سفارش‌های دیرکرددار")
ax2.grid(False)
ax.set_title("روند زمان تحویل و نرخ تأخیر", loc="right", fontsize=12)
ax.set_xlabel("ماه")
ax.legend(loc="upper left")
ax2.legend(loc="upper right")
fig.tight_layout()
plt.show()

first_quarter = trend_delivery.head(3)
last_quarter = trend_delivery.tail(3)
print(f"میانگین زمان تحویل سه ماه اول: {first_quarter['میانگین_روز'].mean():.1f} روز"
      f" | سه ماه آخر: {last_quarter['میانگین_روز'].mean():.1f} روز")
print(f"نرخ تأخیر سه ماه اول: {first_quarter['نرخ_تأخیر_درصد'].mean():.2f}%"
      f" | سه ماه آخر: {last_quarter['نرخ_تأخیر_درصد'].mean():.2f}%")
""")

md(r"""
**تفسیر**

- میانگین زمان تحویل حدود ۱۲٫۶ روز و میانه حدود ۱۰٫۲ روز است. اختلاف ۲٫۴ روزه میان
  این دو و چولگی مثبت نشان می‌دهد توزیع راست‌چوله است: بیشتر سفارش‌ها در محدوده ۶ تا
  ۱۶ روز می‌رسند و دنباله‌ای از سفارش‌های بسیار دیرآمده وجود دارد که میانگین را بالا
  می‌کشد. برای گزارش عملکرد، میانه تصویر واقعی‌تری از تجربه مشتری معمولی می‌دهد.
- حدود ۲۷ درصد سفارش‌ها در ۷ روز اول می‌رسند، اما ۴٫۷ درصد بیش از ۳۰ روز طول می‌کشند؛
  همین گروه کوچک است که تجربه بد می‌سازد.
- بیشتر سفارش‌ها زودتر از تاریخ تخمینی می‌رسند و تنها ۶٫۸ درصد دیرکردارند. این دیرکرد
  اما روی رضایت اثر نامتناسبی می‌گذارد (بخش بعدی).
- دیرکرد یک مشکل سراسری نیست: در چند ایالت شمال و شمال‌شرق نرخ تأخیر و میانگین زمان
  تحویل هر دو بالاتر است. تفاوت جغرافیایی، اثر مستقیم فاصله از مراکز توزیع و کیفیت
  حمل‌ونقل محلی است.
- روند ماهانه نشان می‌دهد زمان تحویل و نرخ تأخیر حرکت هم‌جهت دارند؛ ماه‌هایی که حجم
  سفارش بالا رفته، هر دو شاخص بدتر شده‌اند. یعنی ظرفیت عملیات در اوج تقاضا کشش کافی
  ندارد.
""")

# --------------------------------------------------------------------------- #
md(r"""
## بخش ۱۰ — تحلیل رضایت مشتریان

امتیاز نظرها بین ۱ تا ۵ است. چون چند نظر برای یک سفارش وجود دارد، پیش از محاسبه
میانگین، نظرات را در سطح سفارش یکتا کردیم.
""")

code(r"""
# --- ۱۰.۱ توزیع امتیازها و شاخص‌های کلی ---
scored = orders[orders["review_score"].notna()].copy()
overall_score = scored["review_score"].mean()
score_counts = scored["review_score"].value_counts().sort_index()
score_table = pd.DataFrame({
    "امتیاز": score_counts.index.astype(int),
    "تعداد": score_counts.values,
    "درصد": (score_counts.values / len(scored) * 100).round(2),
}).set_index("امتیاز")
display(score_table)

score_kpi = pd.Series({
    "سفارش دارای نظر": len(scored),
    "میانگین امتیاز": round(overall_score, 4),
    "میانه امتیاز": float(scored["review_score"].median()),
    "درصد امتیاز ۴ و ۵": round((scored["review_score"] >= 4).mean() * 100, 2),
    "درصد امتیاز ۱ و ۲": round((scored["review_score"] <= 2).mean() * 100, 2),
    "درصد امتیاز ۱": round((scored["review_score"] == 1).mean() * 100, 2),
}, name="مقدار")
display(score_kpi.to_frame())

bars(score_table["تعداد"], "توزیع امتیاز نظرات مشتریان", "تعداد نظر")
""")

code(r"""
# --- ۱۰.۲ رضایت به تفکیک دسته‌بندی ---
cat_sat = (order_category.groupby("category_label")
           .agg(نظر=("review_score", "count"),
                میانگین_امتیاز=("review_score", "mean"),
                مبلغ_فروش=("revenue", "sum")))
cat_sat = cat_sat[cat_sat["نظر"] >= 30]
print("دسته‌بندی با حداقل ۳۰ نظر:", len(cat_sat), "از", category.shape[0])

best = cat_sat.nlargest(10, "میانگین_امتیاز").sort_values("میانگین_امتیاز")
worst = cat_sat.nsmallest(10, "میانگین_امتیاز").sort_values("میانگین_امتیاز")
fig, axes = plt.subplots(1, 2, figsize=(13, 4.9), sharex=True)
for axis, frame, color, title in [
    (axes[0], best, "#2E8B57", "ده دسته‌بندی با بالاترین میانگین امتیاز"),
    (axes[1], worst, COLOR_ACCENT, "ده دسته‌بندی با پایین‌ترین میانگین امتیاز"),
]:
    axis.barh([name.replace("_", " ") for name in frame.index], frame["میانگین_امتیاز"], color=color)
    axis.axvline(overall_score, color=COLOR_MUTED, linestyle="--")
    axis.set_title(title, loc="right", fontsize=11)
    axis.set_xlim(1, 5)
    axis.margins(x=0.16)
fig.suptitle(f"میانگین امتیاز دسته‌بندی‌ها (خط‌چین: میانگین کل {overall_score:.2f})",
             x=0.99, ha="right", fontsize=12)
fig.tight_layout()
plt.show()

print("کمترین تعداد نظر در این فهرست:", int(min(best["نظر"].min(), worst["نظر"].min())))
display(pd.concat([best.head(3), worst.head(3)])[["نظر", "میانگین_امتیاز"]].round(2))

low_volume = (order_category.groupby("category_label")
              .agg(نظر=("review_score", "count"), میانگین_امتیاز=("review_score", "mean")))
low_volume = low_volume[low_volume["نظر"] < 30].sort_values("میانگین_امتیاز")
print("نمونه دسته‌بندی‌هایی با کمتر از ۳۰ نظر که در فهرست بالا و پایین قرار می‌گرفتند:")
display(pd.concat([low_volume.tail(3), low_volume.head(3)]).round(2))
""")

code(r"""
# --- ۱۰.۳ روند زمانی رضایت و مقایسه با فروش ---
monthly_score = (scored.groupby("purchase_ym")
                 .agg(میانگین_امتیاز=("review_score", "mean"), نظر=("review_score", "size"))
                 .reset_index())
monthly_score["ماه"] = pd.to_datetime(monthly_score["purchase_ym"] + "-01")
score_trend = monthly_score[(monthly_score["purchase_ym"] >= CORE_START)
                            & (monthly_score["purchase_ym"] <= CORE_END)]

fig, ax = plt.subplots(figsize=(10.8, 4.6))
ax.plot(score_trend["ماه"], score_trend["میانگین_امتیاز"], marker="o", color=COLOR_MAIN,
        label="میانگین امتیاز ماهانه")
ax.axhline(overall_score, color=COLOR_MUTED, linestyle="--", label=f"میانگین کل {overall_score:.2f}")
ax.set_ylim(3, 5)
ax.set_ylabel("میانگین امتیاز")
ax.set_xlabel("ماه")
ax2 = ax.twinx()
ax2.bar(score_trend["ماه"], score_trend["نظر"], width=18, alpha=.2, color=COLOR_ACCENT,
        label="تعداد نظر")
ax2.set_ylabel("تعداد نظر")
ax2.grid(False)
ax.set_title("روند ماهانه رضایت مشتری", loc="right", fontsize=12)
ax.legend(loc="lower left")
ax2.legend(loc="lower right")
fig.tight_layout()
plt.show()

rev_score = cat_sat.copy()
rev_score["رتبه_مبلغ"] = rev_score["مبلغ_فروش"].rank(ascending=False, method="min").astype(int)
high_revenue = rev_score[rev_score["رتبه_مبلغ"] <= 10].sort_values("مبلغ_فروش", ascending=False)
risky = high_revenue[high_revenue["میانگین_امتیاز"] < overall_score]
print("ده دسته‌بندی پرفروش و میانگین امتیازشان:")
display(high_revenue[["نظر", "میانگین_امتیاز", "مبلغ_فروش"]].round(2))
print(f"از این ده مورد، {len(risky)} دسته‌بندی زیر میانگین کل هستند:")
display(risky[["میانگین_امتیاز", "مبلغ_فروش"]].round(2))
""")

md(r"""
**تفسیر**

- توزیع امتیازها دوقطبی است: حدود ۵۸ درصد امتیاز ۵ و در همان حال ۱۱٫۵ درصد امتیاز ۱.
  میانگین ۴٫۰۹ و میانه ۵ است، اما این میانگین بالا نباید تصویر را خوش‌بینانه کند؛
  تجربه بخشی از مشتریان واقعاً بد بوده است.
- ۷۷ درصد نظرات ۴ یا ۵ و حدود ۱۵ درصد ۱ یا ۲ هستند. برای پایش تجربه مشتری، درصد
  امتیازهای پایین شاخص حساس‌تری از میانگین است، چون میانگین با حجم امتیازهای ۵ پنهان
  می‌شود.
- روند ماهانه نسبتاً پایدار است و نوسان شدیدی ندارد؛ افت‌های مقطعی بیشتر در ماه‌های
  پرحجم دیده می‌شود که با افزایش زمان تحویل هم‌زمان است.
- در میان ده دسته‌بندی پرفروش، چند مورد میانگین امتیاز پایین‌تر از کل دارند. این‌ها
  دقیقاً همان جایی هستند که بهبود کیفیت، بیشترین اثر مالی را دارد.
- دسته‌بندی‌هایی که در فهرست بدترین‌ها هستند اما تعداد نظر کمی دارند، نباید با همین
  میانگین قضاوت شوند؛ به همین دلیل حداقل ۳۰ نظر گذاشتیم و تعداد نظر را کنار نتیجه
  نگه داشتیم.
""")

# --------------------------------------------------------------------------- #
md(r"""
## بخش ۱۱ — ارتباط تأخیر در تحویل و رضایت مشتری

فرضیه تیم تجربه مشتری این است که تأخیر، رضایت را کاهش می‌دهد. برای آزمون آن، امتیاز
سفارش‌های به‌موقع و دیرکردار را مقایسه می‌کنیم و بعد شدت تأخیر را هم بررسی می‌کنیم.
""")

code(r"""
# --- ۱۱.۱ مقایسه دو گروه ---
reviewed = scored[scored["delivery_class"].notna()].copy()
reviewed["گروه"] = np.where(reviewed["delivery_class"] == "late", "late", "on_time")

comparison = (reviewed.groupby("گروه")
              .agg(سفارش=("review_score", "size"), میانگین_امتیاز=("review_score", "mean"))
              .reindex(["on_time", "late"]))
comparison.index = ["به‌موقع یا زودتر", "با تأخیر"]
comparison["سهم_از_نظرات_درصد"] = (comparison["سفارش"] / len(reviewed) * 100).round(2)
display(comparison.round(3))

score_gap = (comparison.loc["به‌موقع یا زودتر", "میانگین_امتیاز"]
             - comparison.loc["با تأخیر", "میانگین_امتیاز"])
print(f"اختلاف میانگین امتیاز: {score_gap:.2f}")
bars(comparison["میانگین_امتیاز"], "میانگین امتیاز در سفارش‌های به‌موقع و دیرکردار",
     "میانگین امتیاز", fmt="{:.2f}")
""")

code(r"""
# --- ۱۱.۲ شدت تأخیر ---
bucket_satisfaction = (reviewed.groupby("delay_bucket")
                       .agg(سفارش=("review_score", "size"), میانگین_امتیاز=("review_score", "mean"))
                       .reindex(BUCKET_ORDER))
bucket_satisfaction.index = [BUCKET_FA[key] for key in bucket_satisfaction.index]
display(bucket_satisfaction.round(3))

fig, ax = plt.subplots(figsize=(9.8, 4.5))
positions = range(len(bucket_satisfaction))
ax.bar(positions, bucket_satisfaction["میانگین_امتیاز"],
       color=["#2E8B57", "#E0A800", "#E67E22", COLOR_ACCENT])
for position, (count, value) in enumerate(zip(bucket_satisfaction["سفارش"],
                                             bucket_satisfaction["میانگین_امتیاز"])):
    ax.text(position, value, f"{value:.2f}\n(n={int(count):,})", ha="center", va="bottom", fontsize=9)
ax.set_xticks(list(positions))
ax.set_xticklabels(bucket_satisfaction.index)
ax.set_ylim(0, 5)
ax.set_title("میانگین امتیاز بر اساس شدت تأخیر", loc="right", fontsize=12)
ax.set_ylabel("میانگین امتیاز")
ax.margins(y=0.18)
fig.tight_layout()
plt.show()

print("افت امتیاز از به‌موقع به بیش از ۷ روز:",
      f"{bucket_satisfaction.iloc[0, 1] - bucket_satisfaction.iloc[-1, 1]:.2f}")
""")

code(r"""
# --- ۱۱.۳ تفاوت میان دسته‌بندی‌ها ---
reviewed_categories = order_category[order_category["review_score"].notna()
                                    & order_category["delivery_class"].notna()].copy()
reviewed_categories["گروه"] = np.where(reviewed_categories["delivery_class"] == "late", "late", "on_time")
pivot = reviewed_categories.pivot_table(index="category_label", columns="گروه",
                                        values="review_score", aggfunc=["size", "mean"])
pivot.columns = [f"{stat}_{group}" for stat, group in pivot.columns]
pivot = pivot.rename(columns={"size_on_time": "ن_به‌موقع", "size_late": "ن_با_تأخیر",
                              "mean_on_time": "امتیاز_به‌موقع", "mean_late": "امتیاز_با_تأخیر"})
pivot = pivot.dropna()
pivot = pivot[(pivot["ن_به‌موقع"] >= 30) & (pivot["ن_با_تأخیر"] >= 30)]
pivot["اختلاف"] = pivot["امتیاز_به‌موقع"] - pivot["امتیاز_با_تأخیر"]
print("دسته‌بندی با حداقل ۳۰ سفارش در هر گروه:", len(pivot))
display(pivot.sort_values("ن_با_تأخیر", ascending=False).head(8).round(2))

fig, ax = plt.subplots(figsize=(9.6, 4.8))
plotted = pivot.sort_values("اختلاف", ascending=False).head(10)
ax.barh([name.replace("_", " ") for name in plotted.index], plotted["اختلاف"], color=COLOR_MAIN)
ax.set_title("افت امتیاز در اثر تأخیر، به تفکیک دسته‌بندی", loc="right", fontsize=12)
ax.set_xlabel("اختلاف امتیاز (به‌موقع منهای دیرکردار)")
ax.margins(x=0.14)
fig.tight_layout()
plt.show()
print("همه دسته‌بندی‌ها افت امتیاز دارند؟", bool((pivot["اختلاف"] > 0).all()))
print("بیشترین افت:", f"{pivot['اختلاف'].max():.2f}", "در", pivot["اختلاف"].idxmax())
""")

md(r"""
**تفسیر تحلیلی**

- اختلاف امتیاز دو گروه حدود ۲ واحد از ۵ است (۴٫۲۹ در برابر ۲٫۲۷)؛ این بزرگ‌ترین
  شکافی است که در کل پروژه دیدیم و با نمونه‌ای چند ده‌هزارتایی پشتیبانی می‌شود. فرضیه
  تیم تجربه مشتری با داده سازگار است.
- رابطه با شدت تأخیر یکنوا نیست: در بازه ۱ تا ۳ روز افت ملایم است، از ۴ روز به بعد
  افت تندتر می‌شود و در بیش از ۷ روز به کمترین مقدار می‌رسد. یعنی «کمی دیر رسیدن»
  تقریباً بخشوده می‌شود، اما «دیر رسیدن طولانی» نه.
- در همه دسته‌بندی‌هایی که نمونه کافی دارند، امتیاز گروه دیرکردار پایین‌تر است؛ پس این
  الگو به یک محصول یا یک فروشنده خاص محدود نیست.
- **محدودیت مهم:** این یک تحلیل مشاهده‌ای است. تأخیر با عوامل دیگری مثل ایالت دور،
  فروشنده ضعیف یا انتظار بالا هم‌بسته است و ممکن است بخشی از افت امتیاز به همان عوامل
  مربوط باشد. برای اثبات علیت به آزمون کنترل‌شده یا تحلیل با کنترل متغیرهای همراه
  نیاز است؛ داده فعلی فقط هم‌بستگی قوی نشان می‌دهد.
""")

# --------------------------------------------------------------------------- #
md(r"""
## بخش ۱۲ — تحلیل عملکرد فروشندگان

پرسش مدیریت: فروش چقدر متمرکز است و آیا فروشندگان بزرگ، مشتریان را هم راضی نگه
می‌دارند.
""")

code(r"""
# --- ۱۲.۱ تعداد و پراکندگی فروشندگان ---
seller_state = raw["sellers"].set_index("seller_id")["seller_state"]
seller_perf = (order_seller.groupby("seller_id")
               .agg(اقلام=("n_items", "sum"),
                    مبلغ_فروش=("revenue", "sum"),
                    نظر=("review_score", "count"),
                    میانگین_امتیاز=("review_score", "mean")))
seller_perf["ایالت"] = seller_state.reindex(seller_perf.index)

seller_facts = pd.Series({
    "فروشنده یکتا": len(seller_perf),
    "ایالت دارای فروشنده": seller_perf["ایالت"].nunique(),
    "میانه اقلام هر فروشنده": float(seller_perf["اقلام"].median()),
    "میانه مبلغ فروش هر فروشنده (BRL)": float(seller_perf["مبلغ_فروش"].median()),
    "فروشنده با حداقل ۳۰ نظر": int((seller_perf["نظر"] >= 30).sum()),
}, name="مقدار")
display(seller_facts.to_frame())

barh(seller_perf["ایالت"].value_counts().head(10), "ده ایالت با بیشترین تعداد فروشنده", "تعداد فروشنده")
""")

code(r"""
# --- ۱۲.۲ فروش فروشندگان ---
top_sellers = seller_perf.nlargest(10, "مبلغ_فروش").sort_values("مبلغ_فروش")
fig, ax = plt.subplots(figsize=(9.8, 4.6))
ax.barh([f"…{seller[-6:]}" for seller in top_sellers.index], top_sellers["مبلغ_فروش"], color=COLOR_MAIN)
for row, value in enumerate(top_sellers["مبلغ_فروش"]):
    ax.text(value, row, f"  {value:,.0f}", va="center", fontsize=9)
ax.set_title("ده فروشنده با بیشترین مبلغ فروش", loc="right", fontsize=12)
ax.set_xlabel("مبلغ فروش، BRL")
ax.margins(x=0.2)
fig.tight_layout()
plt.show()

top10_revenue = top_sellers["مبلغ_فروش"].sum()
total_revenue = seller_perf["مبلغ_فروش"].sum()
print(f"سهم ده فروشنده اول از مبلغ فروش: {top10_revenue / total_revenue * 100:.2f}%")
print(f"سهم ده فروشنده اول از تعداد اقلام: {top_sellers['اقلام'].sum() / seller_perf['اقلام'].sum() * 100:.2f}%")
print(f"میانه سهم هر فروشنده از فروش: {seller_perf['مبلغ_فروش'].median() / total_revenue * 100:.4f}%")

seller_perf["رتبه_اقلام"] = seller_perf["اقلام"].rank(ascending=False, method="min").astype(int)
seller_perf["رتبه_مبلغ"] = seller_perf["مبلغ_فروش"].rank(ascending=False, method="min").astype(int)
seller_perf["اختلاف_رتبه"] = seller_perf["رتبه_اقلام"] - seller_perf["رتبه_مبلغ"]
movers = seller_perf.reindex(seller_perf["اختلاف_رتبه"].abs().nlargest(5).index)
print("فروشندگانی که رتبه اقلام و رتبه مبلغشان فاصله زیادی دارد:")
display(movers[["اقلام", "مبلغ_فروش", "میانگین_امتیاز", "رتبه_اقلام", "رتبه_مبلغ", "اختلاف_رتبه"]].round(2))
""")

code(r"""
# --- ۱۲.۳ فروش در برابر رضایت ---
scored_sellers = seller_perf[(seller_perf["نظر"] >= 30) & seller_perf["میانگین_امتیاز"].notna()].copy()
threshold = scored_sellers["مبلغ_فروش"].quantile(0.75)
scored_sellers["پرچم"] = ((scored_sellers["مبلغ_فروش"] >= threshold)
                          & (scored_sellers["میانگین_امتیاز"] < overall_score))
flagged = scored_sellers[scored_sellers["پرچم"]].sort_values("مبلغ_فروش", ascending=False)

print(f"فروشنده با حداقل ۳۰ نظر: {len(scored_sellers)}")
print(f"آستانه فروش (چارک سوم): {threshold:,.2f} BRL")
print(f"فروشنده پرفروش با امتیاز زیر میانگین: {len(flagged)}")
display(flagged[["اقلام", "مبلغ_فروش", "نظر", "میانگین_امتیاز"]].head(5).round(2))

fig, ax = plt.subplots(figsize=(10.2, 5.4))
ax.scatter(scored_sellers["مبلغ_فروش"].clip(lower=1), scored_sellers["میانگین_امتیاز"],
           s=22, alpha=.45, color=COLOR_MAIN, label="فروشنده")
ax.scatter(flagged["مبلغ_فروش"], flagged["میانگین_امتیاز"], s=55, color=COLOR_ACCENT,
           label="پرفروش با امتیاز پایین")
ax.axhline(overall_score, color=COLOR_MUTED, linestyle="--", label=f"میانگین کل {overall_score:.2f}")
ax.set_xscale("log")
ax.set_title("مبلغ فروش و میانگین امتیاز فروشندگان (حداقل ۳۰ نظر)", loc="right", fontsize=12)
ax.set_xlabel("مبلغ فروش، BRL (مقیاس لگاریتمی)")
ax.set_ylabel("میانگین امتیاز")
ax.legend(loc="lower left")
fig.tight_layout()
plt.show()
""")

md(r"""
**تفسیر**

- ۳٬۰۹۵ فروشنده در ۲۳ ایالت فعال‌اند، اما میانه فروش هر فروشنده حدود ۸۲۱ دلار است؛
  یعنی توده فروشندگان بسیار کوچک‌اند و بخش زیادی از فروش به گروه کوچکی از فروشندگان
  بزرگ می‌رسد. ده فروشنده اول حدود ۱۳ درصد فروش و ۱۰ درصد اقلام را در اختیار دارند.
- رتبه‌بندی بر اساس تعداد اقلام با رتبه‌بندی بر اساس مبلغ یکسان نیست؛ برخی فروشندگان
  با حجم بالا، قیمت واحد پایین دارند و در مبلغ جایگاه پایین‌تری می‌گیرند.
- در نمودار فروش-امتیاز، بیشتر فروشندگان بزرگ در محدوده امتیاز بالا هستند؛ اما گروهی
  هم هستند که فروش بالا و امتیاز زیر میانگین دارند. تعداد نظر این گروه را کنار نتیجه
  آوردیم تا مقایسه بر پایه نمونه کوچک انجام نشود.
- فروشندگانی که در ناحیه پرچم قرار می‌گیرند، نامزد بررسی کیفیت بسته‌بندی و زمان ارسال
  هستند؛ چون هر امتیاز پایین آن‌ها روی برند پلتفرم هم اثر می‌گذارد.
""")
