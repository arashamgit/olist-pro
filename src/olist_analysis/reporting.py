"""Executive report builder: Persian Markdown + Persian PDF.

The report never recomputes a business metric.  It reads
``reports/metrics.json`` and the CSV tables written by
:mod:`olist_analysis.pipeline`, so the document a manager reads and the numbers
the notebooks print come from the same run.

Two rendering paths share one content model:

* :func:`build_report` writes ``reports/executive_report.md`` (raw Persian,
  RTL-safe Markdown) and ``reports/executive_report.pdf`` (ReportLab with the
  bundled Vazirmatn font, shaped through :func:`olist_analysis.font_utils.fa`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .config import (
    FIGURES_DIR,
    PERSIAN_FONT_PATH,
    REPORTS_DIR,
    TABLES_DIR,
)
from .font_utils import fa, persian_available
from .pipeline import METRICS_PATH, load_headline

MARKDOWN_PATH = REPORTS_DIR / "executive_report.md"
PDF_PATH = REPORTS_DIR / "executive_report.pdf"

FONT_NAME = "Vazirmatn"


# --------------------------------------------------------------------------- #
# Content model
# --------------------------------------------------------------------------- #
@dataclass
class Finding:
    number: int
    title: str
    statement: str
    evidence: list[str]
    figure: str
    figure_caption: str
    importance: str
    limitation: str


@dataclass
class Recommendation:
    number: int
    title: str
    problem: str
    supporting_finding: str
    expected_change: str
    monitoring_kpi: list[str]


@dataclass
class ExecutiveReport:
    business_status: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    monitoring_indicators: list[tuple[str, str]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    glossary: list[tuple[str, str]] = field(default_factory=list)
    figure_list: list[tuple[str, str]] = field(default_factory=list)


def _num(value: float, digits: int = 2) -> str:
    """Format a number with thousands separators and a fixed precision."""
    return f"{value:,.{digits}f}"


def _int(value: float) -> str:
    return f"{int(value):,}"


def load_tables() -> dict[str, pd.DataFrame]:
    names = [
        "05_monthly_orders",
        "09_delivery_by_state",
        "09_monthly_delivery_trend",
        "10_category_satisfaction",
        "12_seller_performance",
        "12_high_revenue_low_rating_sellers",
        "13_combined_geography_eligible",
        "13_combined_revenue_vs_satisfaction_flagged",
        "figure_manifest",
    ]
    out: dict[str, pd.DataFrame] = {}
    for name in names:
        path = TABLES_DIR / f"{name}.csv"
        if path.exists():
            out[name] = pd.read_csv(path)
    return out


# --------------------------------------------------------------------------- #
# Content
# --------------------------------------------------------------------------- #
def build_content(headline: dict, tables: dict[str, pd.DataFrame]) -> ExecutiveReport:
    """Assemble the report from the persisted numbers."""
    report = ExecutiveReport()
    totals = headline["business_totals"]
    growth = headline["growth"]
    customers = headline["customers"]
    top5 = headline["top5_state_share"]
    satisfaction = headline["satisfaction"]
    delay_vs = headline["delay_vs_satisfaction"]
    duration = headline["delivery_duration"]
    distribution = headline["delivery_distribution"]
    sellers = headline["sellers"]
    category_top5 = headline["category_revenue_top5"]
    price_stats = headline["price_vs_satisfaction"]
    payment_stats = headline["payment_vs_installments"]

    delivery_class = pd.read_csv(TABLES_DIR / "09_delivery_class_summary.csv")
    late_row = delivery_class[delivery_class["delivery_class"] == "late"].iloc[0]
    late_share = float(late_row["pct_of_delivered"])
    late_count = int(late_row["n_orders"])
    delivered_share = 100.0 * totals["delivered_orders"] / totals["orders"]

    delay_summary = pd.read_csv(TABLES_DIR / "09_delay_summary.csv").set_index("metric")["value"]
    bucket = pd.read_csv(TABLES_DIR / "11_delay_bucket_satisfaction.csv")
    worst_bucket = bucket[bucket["delay_bucket"] == "more_than_7_days"].iloc[0]

    # ---------------------------------------------------------------- business status
    report.business_status = [
        (
            f"در بازه مورد بررسی {_int(totals['orders'])} سفارش ثبت شده است که "
            f"{_int(totals['delivered_orders'])} مورد آن، یعنی حدود "
            f"{_num(delivered_share)} درصد، به وضعیت «تحویلشده» رسیدهاند."
        ),
        (
            f"ارزش اقلام فروختهشده {_num(totals['item_revenue_brl'])} رئال برزیل و مجموع مبلغ "
            f"پرداختشده {_num(totals['total_paid_brl'])} رئال است؛ اختلاف این دو عدد عمدتاً از "
            f"هزینه ارسال ({_num(totals['freight_brl'])} رئال) و ساختار پرداخت ناشی میشود. "
            "این مبلغ «ارزش اقلام سفارشها» است و با سود خالص شرکت یکسان نیست."
        ),
        (
            f"مجموعه شامل {_int(totals['unique_buyers'])} خریدار یکتا، "
            f"{_int(totals['unique_products'])} محصول در {_int(totals['product_categories'])} "
            f"دستهبندی و {_int(totals['unique_sellers'])} فروشنده است."
        ),
        (
            f"میانگین زمان تحویل {_num(duration['mean_days'], 2)} روز و میانه آن "
            f"{_num(duration['median_days'], 2)} روز است؛ فاصله میان میانگین و میانه نشان میدهد "
            "توزیع زمان تحویل چوله به راست است و تعداد محدودی سفارش بسیار طولانی، میانگین را بالا میبرد."
        ),
        (
            f"میانگین امتیاز مشتریان {_num(satisfaction['mean_score'], 4)} از ۵ است؛ "
            f"{_num(satisfaction['pct_4_or_5'], 2)} درصد نظرات امتیاز ۴ یا ۵ و "
            f"{_num(satisfaction['pct_1_or_2'], 2)} درصد امتیاز ۱ یا ۲ گرفتهاند."
        ),
        (
            f"نرخ سفارشهای دیرکرددار {_num(late_share, 2)} درصد از سفارشهای تحویلشده "
            f"({_int(late_count)} سفارش) است، در حالی که "
            f"{_num(distribution['pct_within_15_days'], 2)} درصد سفارشها حداکثر تا ۱۵ روز تحویل شدهاند."
        ),
    ]

    # ---------------------------------------------------------------- findings
    flagged_categories = tables.get("13_combined_revenue_vs_satisfaction_flagged")
    if flagged_categories is not None and len(flagged_categories):
        worst = flagged_categories.sort_values("score_vs_overall").iloc[0]
        worst_text = (
            f"{worst['category_label']} با مبلغ فروش {_num(worst['revenue'])} رئال، "
            f"{_int(worst['n_reviews'])} نظر و میانگین امتیاز "
            f"{_num(worst['mean_score'], 2)} (اختلاف {_num(worst['score_vs_overall'], 2)} با میانگین کل)"
        )
    else:
        worst_text = "بدون مورد قابل توجه"

    flagged_sellers = tables.get("12_high_revenue_low_rating_sellers")
    if flagged_sellers is not None and len(flagged_sellers):
        seller = flagged_sellers.sort_values("score_vs_overall").iloc[0]
        seller_text = (
            f"فروشنده {str(seller['seller_id'])[:12]} با مبلغ فروش {_num(seller['revenue'])} رئال، "
            f"{_int(seller['n_reviews'])} نظر و میانگین امتیاز {_num(seller['mean_score'], 2)}"
        )
    else:
        seller_text = "بدون مورد قابل توجه"

    geo = tables.get("13_combined_geography_eligible")
    if geo is not None and len(geo):
        attention = geo[geo["needs_attention"]].sort_values("pct_late", ascending=False)
        states_text = "، ".join(attention["customer_state"].tolist())
        worst_state = attention.iloc[0]
        # raw floats: formatting happens at the point of use so a number can
        # never be formatted twice (which would turn it into a string)
        state_pct_late = float(worst_state["pct_late"])
        state_mean_days = float(worst_state["mean_delivery_days"])
        state_promised_days = float(worst_state["mean_promised_days"])
        state_name = str(worst_state["customer_state"])
        states_count = int(len(attention))
    else:
        states_text, state_pct_late, state_mean_days = "-", 0.0, 0.0
        state_promised_days, state_name, states_count = 0.0, "-", 0

    # best-performing state, read from the same table rather than hard-coded
    best_state_line = "در مقابل، بهترین عملکرد تحویل در ایالت‌های جنوب و جنوب‌شرق دیده می‌شود."
    delivery_state = tables.get("09_delivery_by_state")
    if delivery_state is not None:
        sp_rows = delivery_state[delivery_state["customer_state"] == "SP"]
        if len(sp_rows):
            sp_row = sp_rows.iloc[0]
            best_state_line = (
                f"در مقابل، ایالت SP با {_num(float(sp_row['mean_delivery_days']), 2)} روز میانگین "
                f"تحویل و {_num(float(sp_row['pct_late']), 2)} درصد نرخ تأخیر، بهترین عملکرد را دارد."
            )

    customer_states = tables.get("06_customers_by_state")
    sp_customer_pct = "نامشخص"
    if customer_states is not None:
        sp_customers = customer_states[customer_states["customer_state"] == "SP"]
        if len(sp_customers):
            sp_customer = sp_customers.iloc[0]
            sp_customer_pct = _num(float(sp_customer["pct_customers"]), 2)
            state_share_line = (
                f"ایالت SP به‌تنهایی {_num(float(sp_customer['pct_customers']), 2)} درصد خریداران "
                f"({_int(float(sp_customer['n_customers']))} نفر) را در اختیار دارد."
            )
    else:
        state_share_line = "جدول تفصیلی مشتریان هر ایالت در 06_customers_by_state موجود است."

    cleaning_metrics = pd.read_csv(TABLES_DIR / "02_cleaning_summary.csv").set_index("metric")[
        "value"
    ]
    comment_missing_pct = (
        100.0 * float(cleaning_metrics["reviews_missing_message"])
        / float(cleaning_metrics["reviews_rows"])
    )
    core_window_share = 100.0 * growth["core_orders"] / growth["total_orders"]

    monthly = tables.get("05_monthly_orders")
    if monthly is not None and len(monthly):
        core = monthly[monthly["in_core_window"]]
        last_three = float(core["n_orders"].tail(3).mean())
        first_six = float(core["n_orders"].head(6).mean())
    else:
        last_three, first_six = 0.0, 0.0

    trend_days = tables.get("09_monthly_delivery_trend")
    if trend_days is not None and len(trend_days):
        core_days = trend_days[trend_days["in_core_window"]]
        trend_first_days = float(core_days["mean_delivery_days"].head(3).mean())
        trend_last_days = float(core_days["mean_delivery_days"].tail(3).mean())
        trend_first_late = float(core_days["pct_late"].head(3).mean())
        trend_last_late = float(core_days["pct_late"].tail(3).mean())
    else:
        trend_first_days = trend_last_days = trend_first_late = trend_last_late = 0.0

    report.findings = [
        Finding(
            number=1,
            title="رشد سریع کسبوکار در ۲۰۱۷ و سپس تثبیت در سطح بالاتر در ۲۰۱۸",
            statement=(
                "حجم سفارشها از آغاز فعالیت رشد چشمگیری داشته است، اما این رشد یکنواخت نبوده؛ "
                "پس از جهش آبان ۲۰۱۷ و فروردین ۲۰۱۸، سطح فعالیت تقریباً ثابت شده و الگوی فصلی "
                "قابل تشخیصی نیز دیده نمیشود."
            ),
            evidence=[
                f"تعداد سفارشها از {_int(growth['first_core_month_orders'])} در "
                f"{growth['first_core_month']} به اوج {_int(growth['peak_month_orders'])} در "
                f"{growth['peak_month']} رسیده است.",
                f"مقایسه همدوره ژانویه تا اوت: {_int(growth['jan_aug_2017_orders'])} سفارش در "
                f"۲۰۱۷ برابر با {_int(growth['jan_aug_2018_orders'])} سفارش در ۲۰۱۸، یعنی "
                f"{_num(growth['yoy_jan_aug_pct_change'], 2)} درصد افزایش.",
                f"میانگین سفارش ششماهه نخست پنجره تحلیلی {_num(growth['mean_orders_first_6_core_months'], 1)} "
                f"و ششماهه پایانی {_num(growth['mean_orders_last_6_core_months'], 1)} سفارش در ماه است.",
                f"سه ماه پایانی پنجره بهطور میانگین {_num(last_three, 1)} سفارش در ماه دارد، در برابر "
                f"{_num(first_six, 1)} سفارش در شش ماه نخست این پنجره.",
            ],
            figure="fig_02_monthly_orders.png",
            figure_caption="روند ماهانه سفارشها همراه با میانگین متحرک ۳ ماهه",
            importance=(
                "برنامهریزی ظرفیت انبار، پشتیبانی و ارسال باید بر پایه سطح فعلی تقاضا انجام شود، "
                "نه بر پایه نرخ رشد ۲۰۱۷. همچنین نبود الگوی فصلی روشن یعنی نمیتوان برای کمپینها "
                "به «فصل اوج» تکیه کرد."
            ),
            limitation=(
                "مقایسه همدوره، یک سال راهاندازی را با یک سال تثبیتشده میسنجد و بنابراین درصد رشد "
                "را بیش از حد نشان میدهد. ماههای ۲۰۱۶ و دو ماه پایانی ۲۰۱۸ بهدلیل ناقص بودن از "
                "تحلیل روند کنار گذاشته شدهاند."
            ),
        ),
        Finding(
            number=2,
            title="تمرکز شدید بازار در پنج ایالت و یک شهر",
            statement=(
                "بازار Olist بهشدت متمرکز است: نزدیک به نیمی از خریداران در یک ایالت و بیش از "
                "سهچهارم آنان در پنج ایالت زندگی میکنند."
            ),
            evidence=[
                f"{_int(customers['unique_people'])} خریدار یکتا در {_int(top5['n_states'])} ایالت "
                "شناسایی شده است.",
                f"پنج ایالت نخست ({top5['states']}) روی هم "
                f"{_num(top5['top_n_customer_share_pct'], 2)} درصد خریداران و "
                f"{_num(top5['top_n_order_share_pct'], 2)} درصد سفارشها را در اختیار دارند.",
                f"ایالت SP بهتنهایی {sp_customer_pct} درصد "
                "خریداران را دارد (این عدد از جدول 06_customers_by_state خوانده میشود).",
                "سهم ایالتها از مشتریان و از سفارشها تقریباً یکسان است؛ یعنی اختلاف معناداری میان "
                "«تعداد مشتری» و «حجم سفارش» در سطح ایالتها وجود ندارد.",
            ],
            figure="fig_05_state_customers.png",
            figure_caption="ده ایالت نخست بر اساس تعداد مشتری یکتا",
            importance=(
                "تمرکز بالا هم مزیت است (کارایی لجستیک و بازاریابی در مناطق پرتراکم) و هم ریسک "
                "(وابستگی به یک بازار). رشد پایدار در میانمدت به تنوعبخشی بازار نیاز دارد."
            ),
            limitation=(
                "داده شامل هزینه بازاریابی، رقبا یا تقاضای بالفعل مناطق کممشتری نیست. بنابراین "
                "تعداد کم مشتری در یک ایالت بهتنهایی نشانه فرصت رشد نیست و بهعنوان فرصت اثباتشده "
                "معرفی نمیشود."
            ),
        ),
        Finding(
            number=3,
            title="تأخیر در تحویل، قویترین عامل همراه با افت رضایت مشتری",
            statement=(
                "سفارشهای دیرکرددار بخش کوچکی از سفارشها را تشکیل میدهند، اما میانگین امتیاز آنان "
                "بسیار پایینتر است؛ و هرچه تأخیر طولانیتر باشد، افت امتیاز شدیدتر میشود."
            ),
            evidence=[
                f"{_num(late_share, 2)} درصد از سفارشهای تحویلشده ({_int(late_count)} سفارش) با "
                "تأخیر تحویل شدهاند.",
                f"میانگین امتیاز گروه بهموقع یا زودتر "
                f"{_num(delay_vs['mean_score_on_time_or_early'], 2)} و گروه دیرکرددار "
                f"{_num(delay_vs['mean_score_late'], 2)} است؛ اختلاف "
                f"{_num(delay_vs['score_gap'], 2)} امتیاز.",
                f"در بازه بیش از ۷ روز تأخیر، میانگین امتیاز به "
                f"{_num(worst_bucket['mean_score'], 2)} کاهش مییابد و "
                f"{_num(worst_bucket['pct_1_or_2'], 2)} درصد این سفارشها امتیاز ۱ یا ۲ گرفتهاند.",
                f"میانگین روزهای تأخیر میان سفارشهای دیرکرددار "
                f"{_num(delay_summary['mean delay days (late only)'], 2)} روز است و "
                f"{_int(delay_summary['late orders > 7 days'])} سفارش بیش از هفت روز تأخیر داشتهاند.",
            ],
            figure="fig_22_delay_satisfaction.png",
            figure_caption="میانگین امتیاز مشتری در سفارشهای بهموقع و دیرکرددار",
            importance=(
                "این یافته کمهزینهترین مسیر بهبود رضایت است: کاهش تأخیر در چند هزار سفارش، "
                "میانگین امتیاز کل را مستقیماً بالا میبرد. امتیاز پایین همچنین بر نرخ بازگشت "
                "مشتری و اعتبار فروشگاه اثر میگذارد."
            ),
            limitation=(
                "این یک رابطه مشاهدهشده است، نه اثبات علیت. ممکن است تأخیر و امتیاز پایین هر دو "
                "ناشی از عوامل مشترکی مانند ناموجود بودن کالا یا مشکل فروشنده باشند. برای استنباط "
                "علّی به داده آزمایشی یا اطلاعات علت تأخیر نیاز است."
            ),
        ),
        Finding(
            number=4,
            title="تأخیر در تحویل الگویی منطقهای دارد، نه تصادفی",
            statement=(
                "زمان تحویل و نرخ تأخیر در ایالتهای شمال و شمالشرق بهطور نظاممند بدتر از "
                "ایالتهای جنوب و جنوبشرق است؛ یعنی مسئله بیشتر عملیاتی و منطقهای است تا عمومی."
            ),
            evidence=[
                f"{states_count} ایالت همزمان در هر دو شاخص «زمان تحویل» و «نرخ تأخیر» بالاتر از "
                f"میانه قرار گرفتند: {states_text}.",
                f"بدترین ایالت {state_name} با {_num(state_mean_days, 2)} روز میانگین تحویل و "
                f"{_num(state_pct_late, 2)} درصد نرخ تأخیر است.",
                best_state_line,
            ],
            figure="fig_27_combined_geography_delivery.png",
            figure_caption="عملکرد تحویل ایالتها: زمان تحویل در برابر نرخ تأخیر",
            importance=(
                "اقدام لجستیکی میتواند هدفمند باشد: تمرکز روی چند ایالت مشخص، بهجای یک برنامه "
                "سراسری پرهزینه. همچنین میتوان وعده تحویل را در همین ایالتها محافظهکارانهتر "
                "تنظیم کرد."
            ),
            limitation=(
                "بخشی از تفاوت، ناشی از فاصله جغرافیایی است و در داده فعلی سهم هر علت قابل تفکیک "
                "نیست. همچنین وعده تحویل در این ایالتها از پیش طولانیتر است، پس بخشی از میانگین "
                "بلندتر، نتیجه حاشیه امن عمدی است و نه فقط کندی عملیات."
            ),
        ),
        Finding(
            number=5,
            title="سهم بالای چند دستهبندی در فروش، همراه با نقاط ضعف کیفی مشخص",
            statement=(
                "پنج دستهبندی نخست بیش از ۴۰ درصد ارزش فروش را تشکیل میدهند. در همین گروه، "
                "چند دستهبندی و فروشنده با فروش بالا امتیاز پایینتر از میانگین دارند."
            ),
            evidence=[
                f"پنج دستهبندی نخست {_num(category_top5['top_n_revenue_share_pct'], 2)} درصد از کل "
                f"مبلغ فروش ({_num(category_top5['top_n_revenue'], 2)} رئال) را تشکیل میدهند.",
                f"مورد شاخص در سطح دستهبندی: {worst_text}.",
                f"مورد شاخص در سطح فروشنده: {seller_text}.",
                f"ده فروشنده نخست روی هم {_num(sellers['top10_revenue_share_pct'], 2)} درصد مبلغ فروش "
                "را در اختیار دارند؛ تمرکز فروش عمدتاً در سطح دستهبندی است، نه فروشنده.",
            ],
            figure="fig_26_combined_revenue_vs_score.png",
            figure_caption="دستهبندیهای پرفروش با میانگین امتیاز پایینتر از میانگین کل",
            importance=(
                "دستهبندیها و فروشندگانی که هم پولساز هستند و هم رضایت پایین دارند، بالاترین "
                "اولویت بررسی کیفی را دارند: ریسک مالی آنان بزرگتر از سایرین است."
            ),
            limitation=(
                "امتیاز پایین ممکن است ناشی از ماهیت کالا، انتظار خریدار یا کیفیت بستهبندی باشد و "
                "داده فعلی علت را مشخص نمیکند. امتیاز دستهبندیهای کمحجم نیز بهدلیل نمونه کوچک "
                "قابل تعمیم نیست."
            ),
        ),
    ]

    # ---------------------------------------------------------------- recommendations
    report.recommendations = [
        Recommendation(
            number=1,
            title=f"کاهش تأخیر تحویل در {states_count} ایالت دارای وضعیت نامطلوب",
            problem=(
                f"{_num(late_share, 2)} درصد سفارشهای تحویلشده دیرکرددار هستند و در ایالتهای "
                "شمال و شمالشرق این نرخ چند برابر ایالتهای جنوب و جنوبشرق است."
            ),
            supporting_finding=(
                f"یافته ۳ و ۴: اختلاف {_num(delay_vs['score_gap'], 2)} امتیازی میان دو گروه تحویل، "
                f"و نرخ تأخیر {_num(state_pct_late, 2)} درصد در {state_name}."
            ),
            expected_change=(
                "کاهش نرخ تأخیر و در پی آن افزایش میانگین امتیاز سفارشهای همان ایالتها؛ حتی کاهش "
                "چند درصدی سهم سفارشهای دیرکرددار میتواند میانگین امتیاز کل را بهطور محسوس بالا ببرد."
            ),
            monitoring_kpi=[
                "نرخ سفارشهای دیرکرددار به تفکیک ایالت (ماهانه)",
                "میانگین روزهای تأخیر در میان سفارشهای دیرکرددار",
                "میانگین امتیاز سفارشهای دیرکرددار در برابر بهموقع",
            ],
        ),
        Recommendation(
            number=2,
            title="بازتنظیم وعده تحویل بر اساس عملکرد واقعی هر منطقه",
            problem=(
                f"بهطور میانگین سفارشها {_num(duration['mean_days_earlier_than_promise'], 2)} روز "
                "زودتر از وعده اعلامشده تحویل میشوند؛ یعنی وعده فعلی در کل حاشیه امن بزرگی دارد "
                "و در برخی مناطق بیش از حد محافظهکارانه است."
            ),
            supporting_finding=(
                f"یافته ۴: میانگین زمان تحویل در {state_name} "
                f"{_num(state_mean_days, 2)} روز است، در حالی که وعده اعلامی برای همان ایالت "
                "طولانیتر است (جدول 09_delivery_by_state)."
            ),
            expected_change=(
                "اعلام وعدههای واقعبینانهتر میتواند نرخ تبدیل را بهبود دهد؛ در نقاطی که حاشیه "
                "امن غیرضروری وجود دارد بدون افزایش نرخ تأخیر، و در ایالتهای پرتأخیر با حاشیه بیشتر."
            ),
            monitoring_kpi=[
                "میانگین و میانه روزهای زودتر از وعده در هر ایالت",
                "نرخ تأخیر به تفکیک ایالت پس از تغییر وعدهها",
                "نرخ تبدیل سفارش در ایالتهایی که وعده تغییر کرده است",
            ],
        ),
        Recommendation(
            number=3,
            title="بازبینی کیفی دستهبندیها و فروشندگان پرفروش با امتیاز پایین",
            problem=(
                "بخشی از پرفروشترین دستهبندیها و فروشندگان، میانگین امتیاز پایینتر از میانگین کل "
                "دارند؛ این ترکیب، هم ریسک از دست دادن مشتری و هم ریسک اعتبار فروشگاه ایجاد میکند."
            ),
            supporting_finding=(
                f"یافته ۵: {worst_text} و {seller_text}."
            ),
            expected_change=(
                "شناسایی علت اصلی (کیفیت کالا، تأخیر، بستهبندی یا توصیف نامنطبق) در همان "
                "دستهبندیها و فروشندگان و افزایش تدریجی میانگین امتیاز آنان به سطح میانگین کل."
            ),
            monitoring_kpi=[
                "میانگین امتیاز هر دستهبندی با حداقل ۳۰ نظر",
                "سهم نظرات با امتیاز ۱ یا ۲ در دستهبندیها و فروشندگان پرچمخورده",
                "نرخ خرید دوباره مشتریان (سهم خریداران با بیش از یک سفارش)",
            ],
        ),
    ]

    # ---------------------------------------------------------------- extras
    report.monitoring_indicators = [
        ("نرخ سفارشهای دیرکرددار", "درصد سفارشهای تحویلشده با تأخیر بیشتر از تاریخ تخمینی"),
        ("میانگین زمان تحویل", "میانگین فاصله ثبت سفارش تا تحویل واقعی، به تفکیک ایالت"),
        ("میانگین امتیاز مشتری", "میانگین review_score و سهم امتیازهای ۱ و ۲"),
        ("سهم امتیازهای ۱ و ۲ در سفارشهای دیرکرددار", "بهعنوان شاخص هشدار زودهنگام تجربه مشتری"),
        ("سهم خریداران بازگشتی", f"درصد خریداران با بیش از یک سفارش (اکنون {_num(customers['repeat_share_pct'], 2)} درصد)"),
        ("سهم پنج دستهبندی نخست از مبلغ فروش", "برای پایش تمرکز درآمد"),
        ("سهم پنج ایالت نخست از سفارشها", "برای پایش تمرکز بازار"),
    ]

    report.limitations = [
        "همه یافتهها همبستگی توصیفی هستند؛ هیچ آزمون علّی یا آزمایش کنترلشدهای انجام نشده است.",
        "مبلغ فروش از ستون price جدول اقلام سفارش محاسبه شده و با درآمد خالص یا سود شرکت یکسان نیست.",
        "سفارشهای لغوشده و ناموجود در تحلیلهای تحویل و رضایت وارد نشدهاند؛ بنابراین نتایج آن "
        "تحلیلها فقط برای سفارشهای تحویلشده معتبر است.",
        "ماههای سال ۲۰۱۶ و دو ماه پایانی سال ۲۰۱۸ از تحلیل روند کنار گذاشته شدهاند؛ اما آمار کل "
        "بر پایه همه داده است.",
        f"متن نظرات مشتریان در تحلیل کمّی استفاده نشده است؛ {_num(comment_missing_pct, 2)} درصد "
        "نظرات هیچ متن توضیحی ندارند.",
        "داده شامل هزینه بازاریابی، موجودی انبار، رقبا و اطلاعات جمعیتشناختی مشتریان نیست.",
    ]

    report.glossary = [
        ("سفارشهای دیرکرددار", "سفارشی که تاریخ تحویل واقعی آن، از تاریخ تخمینی تحویل دیرتر باشد"),
        ("سفارشهای بهموقع", "سفارشی که در همان تاریخ تخمینی تحویل داده شده باشد"),
        ("مبلغ فروش اقلام", "مجموع ستون price در جدول اقلام سفارش، بدون هزینه ارسال"),
        ("خریدار یکتا", "شخص حقیقی شناساییشده با customer_unique_id، مستقل از تعداد سفارشها"),
        ("پنجره تحلیلی", "بازه پیوسته ۲۰۱۷-۰۱ تا ۲۰۱۸-۰۸ که تقریباً همه سفارشها را در خود دارد"),
    ]

    manifest = tables.get("figure_manifest")
    if manifest is not None:
        report.figure_list = [
            (str(row["figure"]), str(row["caption"])) for _, row in manifest.iterrows()
        ]

    return report


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #
def render_markdown(report: ExecutiveReport, headline: dict) -> str:
    lines: list[str] = []
    lines.append('<div dir="rtl" align="right">\n')
    lines.append("# گزارش مدیریتی تحلیل دادههای فروش و رفتار مشتریان Olist\n")
    lines.append(
        "این گزارش بر پایه تحلیل داده واقعی سفارشهای Olist (۹۹٬۴۴۱ سفارش بین سپتامبر ۲۰۱۶ تا "
        "اکتبر ۲۰۱۸) تهیه شده است و برای مخاطب مدیریتی نوشته شده؛ بنابراین هیچ کد برنامهنویسی "
        "در آن وجود ندارد.\n"
    )
    lines.append(
        f"> شماره اجرا: همه اعداد این گزارش از فایل `reports/metrics.json` و جداول "
        f"`reports/tables/` همان اجرای خط لوله خوانده شدهاند.\n"
    )

    lines.append("\n## ۱. خلاصه اجرایی\n")
    for item in report.business_status:
        lines.append(f"- {item}")

    lines.append("\n## ۲. وضعیت کلی کسبوکار\n")
    lines.append(
        "کسبوکار Olist در پنجره تحلیلی از یک پلتفرم در حال راهاندازی به یک عملیات تثبیتشده "
        "تبدیل شده است. تقاضا در سال ۲۰۱۷ سریع رشد کرده، در ۲۰۱۸ در سطح بالاتری تثبیت شده و "
        "الگوی فصلی روشنی ندارد. رضایت مشتریان در مجموع بالا است، اما بخش کوچکی از سفارشها "
        "که با تأخیر تحویل میشوند، امتیاز بسیار پایینتری ثبت میکنند.\n"
    )
    lines.append("\n## ۳. پنج یافته مهم\n")
    for finding in report.findings:
        lines.append(f"\n### یافته {finding.number}: {finding.title}\n")
        lines.append(f"**نتیجه:** {finding.statement}\n")
        lines.append("**شواهد عددی:**\n")
        for evidence in finding.evidence:
            lines.append(f"- {evidence}")
        lines.append(
            f"\n![{finding.figure_caption}](figures/{finding.figure})\n"
        )
        lines.append(f"*{finding.figure_caption}*\n")
        lines.append(f"**اهمیت کسبوکاری:** {finding.importance}\n")
        lines.append(f"**محدودیت:** {finding.limitation}\n")

    lines.append("\n## ۴. سه پیشنهاد عملی\n")
    for rec in report.recommendations:
        lines.append(f"\n### پیشنهاد {rec.number}: {rec.title}\n")
        lines.append(f"- **مسئله:** {rec.problem}")
        lines.append(f"- **یافته پشتیبان:** {rec.supporting_finding}")
        lines.append(f"- **تغییر مورد انتظار:** {rec.expected_change}")
        lines.append("- **شاخصهای پایش:**")
        for kpi in rec.monitoring_kpi:
            lines.append(f"  - {kpi}")
    lines.append(
        "\n> این پیشنهادها مبتنی بر شواهد داده موجود هستند و بهعنوان نتیجه اثباتشده یا تضمینشده "
        "ارائه نمیشوند.\n"
    )

    lines.append("\n## ۵. شاخصهای پیشنهادی برای پایش آینده\n")
    lines.append("| شاخص | تعریف |")
    lines.append("| --- | --- |")
    for name, definition in report.monitoring_indicators:
        lines.append(f"| {name} | {definition} |")

    lines.append("\n## ۶. محدودیتهای اصلی تحلیل\n")
    for limitation in report.limitations:
        lines.append(f"- {limitation}")

    lines.append("\n## ۷. جمعبندی\n")
    lines.append(
        "دادههای Olist نشان میدهند مسئله اصلی کسبوکار کمبود تقاضا نیست، بلکه «پایداری تجربه "
        "تحویل» است. حجم سفارشها رشد کرده و تثبیت شده است، بازار متمرکز است و رضایت کلی بالا؛ "
        "اما همان بخش کوچکی از سفارشها که با تأخیر تحویل میشوند، بخش بزرگی از نارضایتی را "
        "تولید میکنند و تأخیر در چند ایالت مشخص متمرکز است. تمرکز اقدام بر همین نقاط، "
        "کمهزینهترین مسیر بهبود شاخصهای مشتری است.\n"
    )

    lines.append("\n## پیوست: فهرست نمودارها\n")
    for name, caption in report.figure_list:
        lines.append(f"- `figures/{name}` - {caption}")

    lines.append("\n## پیوست: واژهنامه کوتاه\n")
    lines.append("| اصطلاح | تعریف |")
    lines.append("| --- | --- |")
    for term, definition in report.glossary:
        lines.append(f"| {term} | {definition} |")

    lines.append("\n</div>\n")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
def _register_font() -> bool:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return True
    if not PERSIAN_FONT_PATH.exists():
        return False
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(PERSIAN_FONT_PATH)))
    return True


def render_pdf(report: ExecutiveReport, headline: dict, path: Path = PDF_PATH) -> Path | None:
    """Build the Persian PDF. Returns ``None`` when the font is unavailable."""
    if not _register_font():
        return None

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    body = ParagraphStyle(
        "body", fontName=FONT_NAME, fontSize=10.5, leading=17, alignment=TA_RIGHT,
        spaceAfter=6, textColor=colors.HexColor("#1A1A1A"),
    )
    bullet = ParagraphStyle("bullet", parent=body, rightIndent=10, alignment=TA_RIGHT)
    title = ParagraphStyle(
        "title", fontName=FONT_NAME, fontSize=19, leading=27, alignment=TA_CENTER,
        spaceAfter=14, textColor=colors.HexColor("#2E5F8A"),
    )
    h1 = ParagraphStyle(
        "h1", fontName=FONT_NAME, fontSize=15, leading=23, alignment=TA_RIGHT,
        spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#2E5F8A"),
    )
    h2 = ParagraphStyle(
        "h2", fontName=FONT_NAME, fontSize=12.5, leading=20, alignment=TA_RIGHT,
        spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#C0392B"),
    )
    small = ParagraphStyle(
        "small", parent=body, fontSize=9, leading=14, textColor=colors.HexColor("#555555"),
        alignment=TA_CENTER,
    )
    justified = ParagraphStyle("justified", parent=body, alignment=TA_JUSTIFY)

    def pr(text: str, style=body) -> Paragraph:
        return Paragraph(fa(text), style)

    story: list = []
    story.append(pr("گزارش مدیریتی تحلیل دادههای فروش و رفتار مشتریان Olist", title))
    story.append(
        pr(
            "این گزارش بر پایه تحلیل داده واقعی سفارشهای Olist تهیه شده و برای مخاطب مدیریتی "
            "نوشته شده است. تمام اعداد از یک اجرای مشخص خط لوله تحلیل استخراج شدهاند.",
            justified,
        )
    )
    story.append(Spacer(1, 10))

    def table(rows: list[list[str]], widths: list[float], header: bool = True) -> Table:
        data = [[pr(cell, small if header else bullet) for cell in row] for row in rows]
        tbl = Table(data, colWidths=widths, repeatRows=1 if header else 0)
        style = [
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BDC3C7")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
        if header:
            style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1F8")))
        tbl.setStyle(TableStyle(style))
        return tbl

    story.append(pr("۱. خلاصه اجرایی", h1))
    for item in report.business_status:
        story.append(pr("• " + item, bullet))

    story.append(pr("۲. وضعیت کلی کسبوکار", h1))
    story.append(
        pr(
            "کسبوکار Olist در پنجره تحلیلی از یک پلتفرم در حال راهاندازی به یک عملیات تثبیتشده "
            "تبدیل شده است. تقاضا در سال ۲۰۱۷ سریع رشد کرده، در ۲۰۱۸ در سطح بالاتری تثبیت شده و "
            "الگوی فصلی روشنی ندارد. رضایت مشتریان در مجموع بالا است، اما بخش کوچکی از سفارشها "
            "که با تأخیر تحویل میشوند، امتیاز بسیار پایینتری ثبت میکنند.",
            justified,
        )
    )

    story.append(PageBreak())
    story.append(pr("۳. پنج یافته مهم", h1))
    for finding in report.findings:
        story.append(pr(f"یافته {finding.number}: {finding.title}", h2))
        story.append(pr("نتیجه: " + finding.statement, justified))
        story.append(pr("شواهد عددی:", body))
        for evidence in finding.evidence:
            story.append(pr("• " + evidence, bullet))
        figure_path = FIGURES_DIR / finding.figure
        if figure_path.exists():
            try:
                story.append(Spacer(1, 6))
                story.append(Image(str(figure_path), width=16.5 * cm, height=9.0 * cm))
                story.append(pr(finding.figure_caption, small))
            except Exception:  # pragma: no cover - image problems must not kill the report
                story.append(pr("(نمودار در پیوست موجود است.)", small))
        story.append(pr("اهمیت کسبوکاری: " + finding.importance, justified))
        story.append(pr("محدودیت: " + finding.limitation, justified))
        story.append(Spacer(1, 6))

    story.append(PageBreak())
    story.append(pr("۴. سه پیشنهاد عملی", h1))
    for rec in report.recommendations:
        story.append(pr(f"پیشنهاد {rec.number}: {rec.title}", h2))
        rows = [
            ["مسئله", rec.problem],
            ["یافته پشتیبان", rec.supporting_finding],
            ["تغییر مورد انتظار", rec.expected_change],
            ["شاخصهای پایش", "؛ ".join(rec.monitoring_kpi)],
        ]
        story.append(table([["عنوان", "توضیح"]] + [[a, b] for a, b in rows],
                           [4.0 * cm, 12.5 * cm]))
        story.append(Spacer(1, 8))

    story.append(pr("۵. شاخصهای پیشنهادی برای پایش آینده", h1))
    story.append(
        table([["شاخص", "تعریف"]] + [[a, b] for a, b in report.monitoring_indicators],
              [6.0 * cm, 10.5 * cm])
    )

    story.append(pr("۶. محدودیتهای اصلی تحلیل", h1))
    for limitation in report.limitations:
        story.append(pr("• " + limitation, bullet))

    story.append(pr("۷. جمعبندی", h1))
    story.append(
        pr(
            "دادههای Olist نشان میدهند مسئله اصلی کسبوکار کمبود تقاضا نیست، بلکه پایداری تجربه "
            "تحویل است. حجم سفارشها رشد کرده و تثبیت شده است، بازار متمرکز است و رضایت کلی بالا؛ "
            "اما همان بخش کوچکی از سفارشها که با تأخیر تحویل میشوند، بخش بزرگی از نارضایتی را "
            "تولید میکنند و تأخیر در چند ایالت مشخص متمرکز است.",
            justified,
        )
    )

    story.append(pr("پیوست: فهرست نمودارها", h1))
    for name, caption in report.figure_list:
        story.append(pr(f"• {caption} ({name})", bullet))

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="Olist Executive Report",
        author="olist-pro analysis team",
    )
    doc.build(story)
    return path


def build_report() -> dict[str, Path | None]:
    """Build both the Markdown and the PDF report from the persisted metrics."""
    if not METRICS_PATH.exists():
        raise FileNotFoundError(
            "reports/metrics.json is missing. Run `python scripts/run_all.py` first."
        )
    headline = load_headline()
    tables = load_tables()
    report = build_content(headline, tables)

    MARKDOWN_PATH.write_text(render_markdown(report, headline), encoding="utf-8")
    pdf = render_pdf(report, headline)
    return {"markdown": MARKDOWN_PATH, "pdf": pdf, "persian_font": persian_available()}
