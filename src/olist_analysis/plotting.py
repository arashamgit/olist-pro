"""Chart layer.

Every function receives **already computed tables** from
:mod:`olist_analysis.metrics` and only draws them.  That guarantees the picture
and the number can never disagree: the chart is a rendering of the table that
is also written to ``reports/tables/``.

Persian titles and labels are reshaped for Matplotlib through
:func:`olist_analysis.font_utils.t`; when the bundled Vazirmatn font is missing
the charts still render (with unjoined letters) instead of crashing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .config import (  # noqa: E402
    COLOR_ACCENT,
    COLOR_GOOD,
    COLOR_MUTED,
    COLOR_PALETTE,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    FIGURE_DPI,
    FIGURE_SIZE,
    FIGURES_DIR,
)
from .font_utils import persian_font_family, t  # noqa: E402

MIN_FIGURE_DPI = FIGURE_DPI


def setup_style() -> None:
    """Consistent, print-friendly style for every figure."""
    family = persian_font_family()
    plt.rcParams.update(
        {
            "figure.figsize": FIGURE_SIZE,
            "figure.dpi": FIGURE_DPI,
            "savefig.dpi": FIGURE_DPI,
            "savefig.bbox": "tight",
            "font.size": 11,
            "axes.titlesize": 14,
            # the bundled Vazirmatn ships one weight only, so requesting bold
            # would only trigger a "font weight not found" fallback warning
            "axes.titleweight": "normal",
            "axes.labelsize": 11,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "grid.linestyle": "--",
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.unicode_minus": False,
            "legend.frameon": False,
            "figure.autolayout": False,
        }
    )
    if family:
        plt.rcParams["font.family"] = family


def _save(fig, name: str, caption: str = "") -> Path:
    """Persist a figure and close it. Returns the written path.

    Right-to-left housekeeping happens here, in one place, so every chart in the
    project is treated identically:

    * titles are right aligned (the Persian reading direction);
    * tick labels and legend entries are passed through :func:`fa`, because they
      often come straight from a data column and would otherwise be drawn in
      logical rather than visual order.

    Matplotlib shapes Persian glyphs but does **not** apply the Unicode bidi
    algorithm, which is exactly why :func:`fa` is required. This behaviour was
    verified in ``artifacts/rtl_test.png``: the raw string renders with joined
    letters in logical order, while the ``fa``-processed string renders in the
    correct right-to-left visual order.
    """
    for ax in fig.axes:
        title = (
            ax.get_title(loc="center")
            or ax.get_title(loc="left")
            or ax.get_title(loc="right")
        )
        if title:
            # ``set_title(text, loc=...)`` writes one of three *separate* title
            # artists, so the copy already drawn in the centre has to be cleared
            # or the two would be printed on top of each other.
            ax.set_title("", loc="left")
            ax.set_title("", loc="center")
            ax.set_title(title, loc="right")
        for axis in (ax.xaxis, ax.yaxis):
            for tick in axis.get_major_ticks():
                label = tick.label1
                text = label.get_text()
                if text:
                    label.set_text(t(text))
        legend = ax.get_legend()
        if legend is not None:
            for entry in legend.get_texts():
                text = entry.get_text()
                if text:
                    entry.set_text(t(text))

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / f"{name}.png"
    fig.tight_layout()
    fig.savefig(path)
    if caption:
        (FIGURES_DIR / f"{name}.txt").write_text(caption, encoding="utf-8")
    plt.close(fig)
    return path


def _barh(table: pd.DataFrame, label_col: str, value_col: str, title: str, xlabel: str,
          color: str = COLOR_PRIMARY, value_fmt: str = "{:,.0f}", annotate: bool = True):
    fig, ax = plt.subplots()
    ordered = table.iloc[::-1]
    bars = ax.barh(ordered[label_col].astype(str), ordered[value_col], color=color)
    ax.set_title(t(title))
    ax.set_xlabel(t(xlabel))
    ax.set_ylabel("")
    if annotate:
        for bar, value in zip(bars, ordered[value_col]):
            ax.text(
                bar.get_width(),
                bar.get_y() + bar.get_height() / 2,
                "  " + value_fmt.format(value),
                va="center",
                fontsize=9,
            )
    return fig


def _bar(table: pd.DataFrame, label_col: str, value_col: str, title: str, xlabel: str,
         ylabel: str, color=COLOR_PRIMARY, rotate: int = 0):
    fig, ax = plt.subplots()
    ax.bar(table[label_col].astype(str), table[value_col], color=color)
    ax.set_title(t(title))
    ax.set_xlabel(t(xlabel))
    ax.set_ylabel(t(ylabel))
    if rotate:
        plt.setp(ax.get_xticklabels(), rotation=rotate, ha="right")
    return fig


# --------------------------------------------------------------------------- #
# Section 5 - orders and trend
# --------------------------------------------------------------------------- #
def fig_order_status(table: pd.DataFrame) -> Path:
    fig = _bar(
        table, "order_status", "n_orders",
        "توزیع وضعیت سفارشها", "وضعیت سفارش", "تعداد سفارش",
    )
    ax = fig.axes[0]
    total = table["n_orders"].sum()
    for i, (n, pct) in enumerate(zip(table["n_orders"], table["pct_orders"])):
        ax.text(i, n, f"{pct:.2f}%", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, total * 1.08)
    return _save(fig, "fig_01_order_status",
                 "نمودار ۱ - توزیع سفارشها بر اساس وضعیت (n=%s)" % f"{total:,}")


def fig_monthly_orders(table: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    core = table[table["in_core_window"]]
    outside = table[~table["in_core_window"]]
    ax.plot(core["order_month"], core["n_orders"], marker="o", color=COLOR_PRIMARY,
            label="ماههای پنجره تحلیلی")
    ax.plot(core["order_month"], core["n_orders_rolling3"], linestyle="--",
            color=COLOR_ACCENT, label="میانگین متحرک ۳ ماهه")
    if len(outside):
        ax.scatter(outside["order_month"], outside["n_orders"], color=COLOR_MUTED,
                   zorder=3, label="ماههای حاشیه (ناقص)")
    ax.set_title(t("روند ماهانه تعداد سفارشها"))
    ax.set_xlabel(t("ماه"))
    ax.set_ylabel(t("تعداد سفارش"))
    ax.legend()
    peak = core.loc[core["n_orders"].idxmax()]
    ax.annotate(
        f"{peak['purchase_ym']}: {int(peak['n_orders']):,}",
        xy=(peak["order_month"], peak["n_orders"]),
        xytext=(0, 14), textcoords="offset points", ha="center",
        fontsize=9, color=COLOR_ACCENT,
    )
    return _save(fig, "fig_02_monthly_orders",
                 "نمودار ۲ - روند ماهانه سفارشها؛ ماههای حاشیه از تحلیل روند کنار گذاشته شدهاند")


def fig_weekday_orders(table: pd.DataFrame) -> Path:
    fig = _bar(table, "weekday", "n_orders", "تعداد سفارش در روزهای هفته",
               "روز هفته", "تعداد سفارش", color=COLOR_SECONDARY)
    return _save(fig, "fig_03_weekday_orders", "نمودار ۳ - توزیع سفارشها در روزهای هفته")


def fig_top_months(table: pd.DataFrame) -> Path:
    fig = _bar(table, "purchase_ym", "n_orders", "پنج ماه با بیشترین تعداد سفارش",
               "ماه", "تعداد سفارش", color=COLOR_ACCENT)
    return _save(fig, "fig_04_top_months", "نمودار ۴ - پنج ماه پرترافیک")


# --------------------------------------------------------------------------- #
# Section 6 - customers and geography
# --------------------------------------------------------------------------- #
def fig_state_customers(table: pd.DataFrame) -> Path:
    fig = _barh(table, "customer_state", "n_customers",
                "ده ایالت با بیشترین تعداد مشتری", "تعداد مشتری یکتا", color=COLOR_PRIMARY)
    return _save(fig, "fig_05_state_customers",
                 "نمودار ۵ - ده ایالت اول بر اساس تعداد مشتری یکتا (customer_unique_id)")


def fig_top_cities(table: pd.DataFrame) -> Path:
    table = table.copy()
    table["city_state"] = table["customer_city"] + " / " + table["customer_state"]
    fig = _barh(table, "city_state", "n_customers",
                "ده شهر با بیشترین تعداد مشتری", "تعداد مشتری یکتا", color=COLOR_SECONDARY)
    return _save(fig, "fig_06_top_cities", "نمودار ۶ - ده شهر اول بر اساس تعداد مشتری یکتا")


def fig_state_customers_vs_orders(table: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    ax.scatter(table["n_customers"], table["n_orders"], s=60, color=COLOR_PRIMARY, alpha=0.8)
    limit = max(table["n_customers"].max(), table["n_orders"].max()) * 1.05
    ax.plot([0, limit], [0, limit], linestyle="--", color=COLOR_MUTED, label="نسبت ۱ به ۱")
    for _, row in table.head(6).iterrows():
        ax.annotate(row["customer_state"], (row["n_customers"], row["n_orders"]),
                    xytext=(6, 4), textcoords="offset points", fontsize=9)
    ax.set_title(t("مقایسه تعداد مشتری و تعداد سفارش در ایالتها"))
    ax.set_xlabel(t("تعداد مشتری یکتا"))
    ax.set_ylabel(t("تعداد سفارش"))
    ax.legend()
    return _save(fig, "fig_07_state_customers_vs_orders",
                 "نمودار ۷ - رابطه تعداد مشتری و سفارش در هر ایالت؛ فاصله از خط، تفاوت سهم را نشان میدهد")


# --------------------------------------------------------------------------- #
# Section 7 - products
# --------------------------------------------------------------------------- #
def _category_barh(table: pd.DataFrame, value_col: str, title: str, xlabel: str,
                   name: str, fmt: str) -> Path:
    table = table.copy()
    table["label"] = table["category_label"].str.replace("_", " ", regex=False)
    fig = _barh(table, "label", value_col, title, xlabel, color=COLOR_PRIMARY,
                value_fmt=fmt)
    return _save(fig, name, title)


def fig_top_categories_items(table: pd.DataFrame) -> Path:
    return _category_barh(table, "n_items",
                          "ده دستهبندی با بیشترین تعداد اقلام فروختهشده",
                          "تعداد قلم فروختهشده", "fig_08_top_categories_items", "{:,.0f}")


def fig_top_categories_revenue(table: pd.DataFrame) -> Path:
    return _category_barh(table, "revenue",
                          "ده دستهبندی با بیشترین مبلغ فروش",
                          "مبلغ فروش (BRL)", "fig_09_top_categories_revenue", "{:,.0f}")


def fig_category_items_vs_revenue(table: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    ax.scatter(table["n_items"], table["revenue"], s=45, color=COLOR_PRIMARY, alpha=0.75)
    for _, row in table.nlargest(6, "revenue").iterrows():
        ax.annotate(row["category_label"].replace("_", " "), (row["n_items"], row["revenue"]),
                    xytext=(5, 4), textcoords="offset points", fontsize=8)
    ax.set_title(t("رابطه تعداد اقلام فروختهشده و مبلغ فروش دستهبندیها"))
    ax.set_xlabel(t("تعداد قلم فروختهشده"))
    ax.set_ylabel(t("مبلغ فروش (BRL)"))
    return _save(fig, "fig_10_category_items_vs_revenue",
                 "نمودار ۱۰ - دستهبندیهای دور از خط، عملکرد متفاوتی در حجم و مبلغ دارند")


def fig_top_categories_price(table: pd.DataFrame) -> Path:
    return _category_barh(table, "mean_item_price",
                          "پنج دستهبندی با بالاترین متوسط قیمت قلم",
                          "متوسط قیمت قلم (BRL)", "fig_11_top_categories_price", "{:,.0f}")


# --------------------------------------------------------------------------- #
# Section 8 - payments
# --------------------------------------------------------------------------- #
def fig_payment_types(table: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    axes[0].bar(table["payment_type"], table["n_transactions"], color=COLOR_PRIMARY)
    axes[0].set_title(t("تعداد تراکنش هر روش پرداخت"))
    axes[0].set_xlabel(t("روش پرداخت"))
    axes[0].set_ylabel(t("تعداد تراکنش"))
    axes[1].bar(table["payment_type"], table["total_payment_value"], color=COLOR_SECONDARY)
    axes[1].set_title(t("مجموع مبلغ پرداخت هر روش"))
    axes[1].set_xlabel(t("روش پرداخت"))
    axes[1].set_ylabel(t("مجموع مبلغ (BRL)"))
    for ax, column in zip(axes, ["n_transactions", "total_payment_value"]):
        for i, value in enumerate(table[column]):
            ax.text(i, value, f"{value:,.0f}", ha="center", va="bottom", fontsize=8)
    return _save(fig, "fig_12_payment_types",
                 "نمودار ۱۲ - تعداد تراکنش و مجموع مبلغ به تفکیک روش پرداخت")


def fig_installments_distribution(table: pd.DataFrame) -> Path:
    grouped = table.copy()
    grouped["bucket"] = grouped["bucket"].astype(str)
    grouped = grouped.groupby("bucket", as_index=False)["n_transactions"].sum()
    order = [str(i) for i in range(1, 13)] + [">12"]
    grouped["bucket"] = pd.Categorical(grouped["bucket"], categories=order, ordered=True)
    grouped = grouped.sort_values("bucket")
    fig = _bar(grouped, "bucket", "n_transactions", "توزیع تعداد اقساط پرداختها",
               "تعداد اقساط", "تعداد تراکنش", color=COLOR_PRIMARY)
    return _save(fig, "fig_13_installments_distribution",
                 "نمودار ۱۳ - توزیع تعداد اقساط؛ بیش از نیمی از تراکنشها یکقسطی هستند")


def fig_payment_value_vs_installments(table: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    ax.bar(table["value_band"], table["mean_installments"], color=COLOR_PRIMARY)
    ax.set_title(t("میانگین تعداد اقساط در دهکهای مبلغ پرداخت"))
    ax.set_xlabel(t("بازه مبلغ پرداخت (BRL)"))
    ax.set_ylabel(t("میانگین تعداد اقساط"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax2 = ax.twinx()
    ax2.plot(table["value_band"], table["pct_multi_installment"], color=COLOR_ACCENT,
             marker="o", linewidth=2, label="درصد پرداخت چندقسطی")
    ax2.set_ylabel(t("درصد تراکنش چندقسطی"))
    ax2.grid(False)
    ax2.legend(loc="upper left")
    return _save(fig, "fig_14_payment_value_vs_installments",
                 "نمودار ۱۴ - با افزایش مبلغ پرداخت، تعداد اقساط و سهم پرداخت چندقسطی زیاد میشود")


# --------------------------------------------------------------------------- #
# Section 9 - delivery
# --------------------------------------------------------------------------- #
def fig_delivery_histogram(delivered: pd.DataFrame, limit: int = 60) -> Path:
    series = delivered["delivery_days"]
    fig, ax = plt.subplots()
    ax.hist(series.clip(upper=limit), bins=limit, color=COLOR_SECONDARY, edgecolor="white")
    ax.axvline(series.mean(), color=COLOR_ACCENT, linestyle="-", linewidth=2,
               label=f"میانگین = {series.mean():.1f} روز")
    ax.axvline(series.median(), color=COLOR_GOOD, linestyle="--", linewidth=2,
               label=f"میانه = {series.median():.1f} روز")
    ax.set_title(t("توزیع مدت زمان تحویل سفارشها"))
    ax.set_xlabel(t("مدت زمان از ثبت تا تحویل (روز)"))
    ax.set_ylabel(t("تعداد سفارش"))
    ax.legend()
    ax.text(0.98, 0.95, t(f"سفارشهای بیش از {limit} روز: {(series > limit).sum():,}"),
            transform=ax.transAxes, ha="right", va="top", fontsize=9)
    return _save(fig, "fig_15_delivery_histogram",
                 "نمودار ۱۵ - توزیع چوله به راست؛ میانگین بالاتر از میانه است")


def fig_delivery_class(table: pd.DataFrame) -> Path:
    labels = {"early": "زودتر از موعد", "on_time": "دقیقاً بهموقع", "late": "با تأخیر"}
    table = table.copy()
    # raw Persian: t() is applied centrally in _save for tick labels
    table["label"] = table["delivery_class"].map(labels)
    colors = [COLOR_GOOD, COLOR_SECONDARY, COLOR_ACCENT]
    fig, ax = plt.subplots()
    ax.bar(table["label"], table["n_orders"], color=colors)
    for i, (n, pct) in enumerate(zip(table["n_orders"], table["pct_of_delivered"])):
        ax.text(i, n, f"{n:,}\n({pct:.2f}%)", ha="center", va="bottom", fontsize=9)
    ax.set_title(t("طبقهبندی سفارشهای تحویلشده نسبت به تاریخ تخمینی"))
    ax.set_xlabel(t("وضعیت تحویل"))
    ax.set_ylabel(t("تعداد سفارش"))
    ax.set_ylim(0, table["n_orders"].max() * 1.18)
    return _save(fig, "fig_16_delivery_class",
                 "نمودار ۱۶ - تفکیک سفارشهای تحویلشده به زودتر از موعد، بهموقع و دیرکرددار")


def fig_state_delivery(table: pd.DataFrame, min_orders: int = 100, k: int = 10) -> Path:
    eligible = table[table["n_orders"] >= min_orders].head(k).copy()
    fig = _barh(eligible, "customer_state", "mean_delivery_days",
                "ده ایالت با بیشترین میانگین زمان تحویل (حداقل ۱۰۰ سفارش)",
                "میانگین روز تا تحویل", color=COLOR_ACCENT, value_fmt="{:,.1f}")
    ax = fig.axes[0]
    for i, (value, n) in enumerate(zip(eligible["mean_delivery_days"].iloc[::-1],
                                       eligible["n_orders"].iloc[::-1])):
        ax.text(value, i, f"  (n={n:,})", va="center", fontsize=8)
    return _save(fig, "fig_17_state_delivery",
                 "نمودار ۱۷ - میانگین زمان تحویل در ایالتها همراه با حجم نمونه")


def fig_monthly_delivery_trend(table: pd.DataFrame) -> Path:
    core = table[table["in_core_window"]]
    fig, ax = plt.subplots()
    ax.plot(core["order_month"], core["mean_delivery_days"], marker="o",
            color=COLOR_PRIMARY, label="میانگین زمان تحویل (روز)")
    ax.set_title(t("روند میانگین زمان تحویل و نرخ تأخیر در طول زمان"))
    ax.set_xlabel(t("ماه"))
    ax.set_ylabel(t("میانگین زمان تحویل (روز)"))
    ax2 = ax.twinx()
    ax2.plot(core["order_month"], core["pct_late"], marker="s", color=COLOR_ACCENT,
             label="درصد سفارشهای دیرکرددار")
    ax2.set_ylabel(t("درصد سفارشهای دیرکرددار"))
    ax2.grid(False)
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [line.get_label() for line in lines], loc="upper right")
    return _save(fig, "fig_18_monthly_delivery_trend",
                 "نمودار ۱۸ - روند زمانی زمان تحویل و نرخ تأخیر در پنجره تحلیلی")


# --------------------------------------------------------------------------- #
# Section 10 - satisfaction
# --------------------------------------------------------------------------- #
def fig_review_scores(table: pd.DataFrame) -> Path:
    fig = _bar(table, "review_score", "n_reviews", "توزیع امتیازهای ثبتشده مشتریان",
               "امتیاز نظر", "تعداد نظر", color=COLOR_PRIMARY)
    ax = fig.axes[0]
    for i, (n, pct) in enumerate(zip(table["n_reviews"], table["pct_reviews"])):
        ax.text(i, n, f"{pct:.2f}%", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, table["n_reviews"].max() * 1.1)
    return _save(fig, "fig_19_review_scores",
                 "نمودار ۱۹ - توزیع امتیازها؛ ۵ پرتکرارترین و ۱ کمترین رضایت")


def fig_category_scores(best: pd.DataFrame, worst: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, table, title, color in (
        (axes[0], best, "بالاترین میانگین امتیاز", COLOR_GOOD),
        (axes[1], worst, "پایینترین میانگین امتیاز", COLOR_ACCENT),
    ):
        ordered = table.iloc[::-1]
        labels = ordered["category_label"].str.replace("_", " ", regex=False)
        bars = ax.barh(labels, ordered["mean_score"], color=color)
        ax.set_title(t(title))
        ax.set_xlabel(t("میانگین امتیاز"))
        overall = float(table["overall_mean_score"].iloc[0])
        ax.axvline(overall, color=COLOR_MUTED, linestyle="--",
                   label=f"میانگین کل = {overall:.2f}")
        for bar, n in zip(bars, ordered["n_reviews"]):
            ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                    f"  n={int(n):,}", va="center", fontsize=8)
        ax.legend(loc="lower right")
    return _save(fig, "fig_20_category_scores",
                 "نمودار ۲۰ - دستهبندیها با بالاترین و پایینترین میانگین امتیاز (حداقل ۳۰ نظر)")


def fig_monthly_score_trend(table: pd.DataFrame) -> Path:
    core = table[table["in_core_window"]]
    fig, ax = plt.subplots()
    ax.plot(core["order_month"], core["mean_score"], marker="o", color=COLOR_PRIMARY,
            label="میانگین امتیاز")
    ax.set_title(t("روند زمانی میانگین امتیاز مشتریان"))
    ax.set_xlabel(t("ماه"))
    ax.set_ylabel(t("میانگین امتیاز از ۵"))
    ax.set_ylim(1, 5)
    ax2 = ax.twinx()
    ax2.bar(core["order_month"], core["n_reviews"], alpha=0.2, color=COLOR_MUTED,
            label="تعداد نظر")
    ax2.set_ylabel(t("تعداد نظر"))
    ax2.grid(False)
    lines = ax.get_lines() + ax2.patches[:1]
    ax.legend(lines, ["میانگین امتیاز", "تعداد نظر"], loc="lower right")
    return _save(fig, "fig_21_monthly_score_trend",
                 "نمودار ۲۱ - روند میانگین امتیاز مشتریان در پنجره تحلیلی")


# --------------------------------------------------------------------------- #
# Section 11 - delay vs satisfaction
# --------------------------------------------------------------------------- #
def fig_delay_satisfaction(table: pd.DataFrame) -> Path:
    labels = {"on_time_or_early": "بهموقع یا زودتر", "late": "دیرکرددار"}
    data = table.copy()
    # raw Persian: t() is applied centrally in _save for tick labels
    data["label"] = data["group"].map(labels)
    fig, ax = plt.subplots()
    bars = ax.bar(data["label"], data["mean_score"],
                  color=[COLOR_GOOD if g == "on_time_or_early" else COLOR_ACCENT
                         for g in data["group"]])
    for bar, score, n in zip(bars, data["mean_score"], data["n_orders"]):
        ax.text(bar.get_x() + bar.get_width() / 2, score,
                f"{score:.2f}\n(n={n:,})", ha="center", va="bottom", fontsize=10)
    ax.set_title(t("میانگین امتیاز مشتری در سفارشهای بهموقع و دیرکرددار"))
    ax.set_xlabel(t("گروه تحویل"))
    ax.set_ylabel(t("میانگین امتیاز از ۵"))
    ax.set_ylim(0, 5)
    return _save(fig, "fig_22_delay_satisfaction",
                 "نمودار ۲۲ - اختلاف میانگین امتیاز دو گروه تحویل")


def fig_delay_bucket_satisfaction(table: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    bars = ax.bar(table["label"], table["mean_score"], color=COLOR_PALETTE[: len(table)])
    for bar, score, n in zip(bars, table["mean_score"], table["n_orders"]):
        ax.text(bar.get_x() + bar.get_width() / 2, score,
                f"{score:.2f}\n(n={n:,})", ha="center", va="bottom", fontsize=9)
    ax.set_title(t("میانگین امتیاز بر اساس شدت تأخیر"))
    ax.set_xlabel(t("بازه تأخیر"))
    ax.set_ylabel(t("میانگین امتیاز از ۵"))
    ax.set_ylim(0, 5)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    return _save(fig, "fig_23_delay_bucket_satisfaction",
                 "نمودار ۲۳ - هرچه تأخیر شدیدتر، میانگین امتیاز پایینتر")


# --------------------------------------------------------------------------- #
# Section 12 - sellers
# --------------------------------------------------------------------------- #
def fig_top_sellers(table: pd.DataFrame) -> Path:
    data = table.copy()
    data["label"] = data["seller_id"].str.slice(0, 8) + "…"
    fig = _barh(data, "label", "revenue", "ده فروشنده برتر بر اساس مبلغ فروش",
                "مبلغ فروش (BRL)", color=COLOR_PRIMARY, value_fmt="{:,.0f}")
    return _save(fig, "fig_24_top_sellers",
                 "نمودار ۲۴ - ده فروشنده اول بر اساس مبلغ فروش (شناسه فروشنده کوتاه شده است)")


def fig_seller_revenue_vs_score(perf: pd.DataFrame, flagged: pd.DataFrame | None = None,
                                min_reviews: int = 30) -> Path:
    eligible = perf[perf["n_reviews"] >= min_reviews]
    fig, ax = plt.subplots()
    ax.scatter(eligible["revenue"], eligible["mean_score"], s=25, alpha=0.45,
               color=COLOR_PRIMARY, label="فروشنده با حداقل ۳۰ نظر")
    overall = float(perf["overall_mean_score"].iloc[0])
    ax.axhline(overall, color=COLOR_MUTED, linestyle="--",
               label=f"میانگین کل = {overall:.2f}")
    if flagged is not None and len(flagged):
        ax.scatter(flagged["revenue"], flagged["mean_score"], s=90, color=COLOR_ACCENT,
                   zorder=3, label="پرفروش با امتیاز پایین")
        for _, row in flagged.head(5).iterrows():
            ax.annotate(row["seller_id"][:6], (row["revenue"], row["mean_score"]),
                        xytext=(5, 5), textcoords="offset points", fontsize=8,
                        color=COLOR_ACCENT)
    ax.set_xscale("log")
    ax.set_title(t("رابطه مبلغ فروش و میانگین امتیاز فروشندگان"))
    ax.set_xlabel(t("مبلغ فروش (BRL، مقیاس لگاریتمی)"))
    ax.set_ylabel(t("میانگین امتیاز"))
    ax.legend(loc="lower left")
    return _save(fig, "fig_25_seller_revenue_vs_score",
                 "نمودار ۲۵ - فروشندگان پرفروش با امتیاز پایینتر از میانگین کل")


# --------------------------------------------------------------------------- #
# Section 13 - combined analyses
# --------------------------------------------------------------------------- #
def fig_combined_revenue_vs_score(table: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    flagged = table[table["is_high_revenue"] & table["below_average_score"]]
    normal = table[~table.index.isin(flagged.index)]
    ax.scatter(normal["revenue"], normal["mean_score"], s=45, color=COLOR_PRIMARY,
               alpha=0.6, label="سایر دستهبندیها")
    ax.scatter(flagged["revenue"], flagged["mean_score"], s=110, color=COLOR_ACCENT,
               label="مبلغ فروش بالا و امتیاز پایینتر از میانگین")
    overall = float(table["mean_score"].mean())
    ax.axhline(overall, color=COLOR_MUTED, linestyle="--", label=f"میانگین کل = {overall:.2f}")
    for _, row in flagged.iterrows():
        ax.annotate(row["category_label"].replace("_", " "), (row["revenue"], row["mean_score"]),
                    xytext=(6, 4), textcoords="offset points", fontsize=8)
    ax.set_xscale("log")
    ax.set_title(t("دستهبندیهای پرفروش با رضایت پایین"))
    ax.set_xlabel(t("مبلغ فروش (BRL، مقیاس لگاریتمی)"))
    ax.set_ylabel(t("میانگین امتیاز"))
    ax.legend(loc="lower left")
    return _save(fig, "fig_26_combined_revenue_vs_score",
                 "نمودار ۲۶ - تحلیل ترکیبی اول: دستهبندیهای نیازمند بررسی")


def fig_combined_geography_delivery(eligible: pd.DataFrame, thresholds: dict) -> Path:
    fig, ax = plt.subplots()
    normal = eligible[~eligible["needs_attention"]]
    flagged = eligible[eligible["needs_attention"]]
    ax.scatter(normal["mean_delivery_days"], normal["pct_late"], s=normal["n_orders"] / 40,
               color=COLOR_PRIMARY, alpha=0.6, label="سایر ایالتها")
    ax.scatter(flagged["mean_delivery_days"], flagged["pct_late"], s=flagged["n_orders"] / 40,
               color=COLOR_ACCENT, label="کند و پرتأخیر")
    ax.axvline(thresholds["slow_threshold_days"], color=COLOR_MUTED, linestyle="--")
    ax.axhline(thresholds["late_threshold_pct"], color=COLOR_MUTED, linestyle="--")
    for _, row in eligible.iterrows():
        ax.annotate(row["customer_state"], (row["mean_delivery_days"], row["pct_late"]),
                    xytext=(5, 4), textcoords="offset points", fontsize=8)
    ax.set_title(t("عملکرد تحویل ایالتها: زمان تحویل در برابر نرخ تأخیر"))
    ax.set_xlabel(t("میانگین زمان تحویل (روز)"))
    ax.set_ylabel(t("درصد سفارشهای دیرکرددار"))
    ax.legend(loc="upper left")
    return _save(fig, "fig_27_combined_geography_delivery",
                 "نمودار ۲۷ - تحلیل ترکیبی دوم؛ اندازه نقطه نشاندهنده تعداد سفارش است")


def fig_combined_price_vs_score(deciles: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    ax.bar(deciles["price_band"], deciles["mean_score"], color=COLOR_PRIMARY)
    ax.set_title(t("میانگین امتیاز در دهکهای قیمت قلم"))
    ax.set_xlabel(t("دهک قیمت قلم (BRL)"))
    ax.set_ylabel(t("میانگین امتیاز از ۵"))
    ax.set_ylim(3.5, 4.5)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    return _save(fig, "fig_28_combined_price_vs_score",
                 "نمودار ۲۸ - تحلیل ترکیبی سوم: رابطه قیمت و رضایت عملاً وجود ندارد")


def fig_combined_category_revenue_trend(pivot: pd.DataFrame, top_n: int = 5) -> Path:
    reserved = {"total", "purchase_ym"}
    candidates = [c for c in pivot.columns if c not in reserved]
    # keep the legend and the drawing order identical to the revenue ranking
    columns = sorted(candidates, key=lambda c: float(pivot[c].sum()), reverse=True)[:top_n]
    fig, ax = plt.subplots()
    for i, column in enumerate(columns):
        months = pd.PeriodIndex(pivot["purchase_ym"], freq="M").to_timestamp()
        ax.plot(months, pivot[column], marker="o", markersize=3,
                color=COLOR_PALETTE[i % len(COLOR_PALETTE)],
                label=column.replace("_", " "))
    ax.set_title(t("روند مبلغ فروش ماهانه پنج دستهبندی مهم"))
    ax.set_xlabel(t("ماه"))
    ax.set_ylabel(t("مبلغ فروش ماهانه (BRL)"))
    ax.legend(fontsize=9)
    return _save(fig, "fig_29_combined_category_revenue_trend",
                 "نمودار ۲۹ - تحلیل ترکیبی پنجم: رشد دستهبندیهای اصلی در طول زمان")


def fig_combined_seller_satisfaction(perf: pd.DataFrame, candidates: pd.DataFrame) -> Path:
    fig, ax = plt.subplots()
    eligible = perf[perf["meets_min_reviews"]]
    ax.scatter(eligible["n_items"], eligible["mean_score"], s=22, alpha=0.4,
               color=COLOR_PRIMARY, label="فروشنده با حداقل ۳۰ نظر")
    if len(candidates):
        ax.scatter(candidates["n_items"], candidates["mean_score"], s=110,
                   color=COLOR_ACCENT, label="کاندید بررسی بیشتر")
        for _, row in candidates.head(3).iterrows():
            ax.annotate(row["seller_id"][:6], (row["n_items"], row["mean_score"]),
                        xytext=(6, 4), textcoords="offset points", fontsize=8,
                        color=COLOR_ACCENT)
    ax.set_xscale("log")
    ax.set_title(t("عملکرد فروشندگان: حجم فعالیت و رضایت مشتری"))
    ax.set_xlabel(t("تعداد قلم فروختهشده (مقیاس لگاریتمی)"))
    ax.set_ylabel(t("میانگین امتیاز"))
    ax.legend(loc="lower left")
    return _save(fig, "fig_30_combined_seller_satisfaction",
                 "نمودار ۳۰ - تحلیل ترکیبی ششم: فروشندگان با حجم بالا و امتیاز پایین")


def fig_state_late_rate(table: pd.DataFrame, min_orders: int = 100, k: int = 12) -> Path:
    eligible = table[table["n_orders"] >= min_orders].head(k)
    fig = _barh(eligible, "customer_state", "pct_late",
                "ایالتها بر اساس درصد سفارشهای دیرکرددار (حداقل ۱۰۰ سفارش)",
                "درصد سفارشهای دیرکرددار", color=COLOR_ACCENT, value_fmt="{:,.2f}%")
    return _save(fig, "fig_31_state_late_rate",
                 "نمودار ۳۱ - نرخ تأخیر در ایالتها همراه با حجم نمونه")


def figure_paths() -> list[Path]:
    """Every figure currently on disk, sorted - used by the report and the audit."""
    return sorted(FIGURES_DIR.glob("*.png"))


def add_value_labels(ax, values: Iterable[float], fmt: str = "{:,.0f}") -> None:
    """Small helper kept public for notebook use."""
    for i, value in enumerate(values):
        ax.text(i, value, fmt.format(value), ha="center", va="bottom", fontsize=9)


def _unused(table: Sequence) -> None:  # pragma: no cover - documentation only
    _ = np
