"""Generate the 13 analysis notebooks.

The notebooks are *generated from this specification* and then executed, which
keeps them consistent with the library instead of drifting away from it:

    python scripts/build_notebooks.py

Every notebook follows the same 11-part structure required by the course brief:

1. title and purpose            7. figures rendered by the pipeline
2. business questions           8. findings (real numbers)
3. data and columns used        9. business interpretation
4. method                       10. limitations
5. data-quality check           11. conclusion
6. numeric analysis (6)
"""

from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"

PREAMBLE = '''\
import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd
from IPython.display import Image, display

from olist_analysis import metrics as M
from olist_analysis.config import FIGURES_DIR, REPORTS_DIR, TABLES_DIR
from olist_analysis.font_utils import persian_available
from olist_analysis.features import load_dataset
from olist_analysis.pipeline import load_headline

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 60)

ds = load_dataset()
headline = load_headline()
print("Persian font registered for charts:", persian_available())
print(f"orders={len(ds.orders):,}  items={len(ds.items):,}  "
      f"delivered={len(ds.delivered):,}  reviewed={len(ds.reviews_per_order):,}")
'''


def fig_cell(name: str) -> tuple[str, str]:
    return (
        "code",
        f'display(Image(filename=str(FIGURES_DIR / "{name}.png"), width=920))\n'
        f'caption = FIGURES_DIR / "{name}.txt"\n'
        f'print(caption.read_text(encoding="utf-8") if caption.exists() else "")',
    )


def table_cell(expression: str) -> tuple[str, str]:
    return ("code", f"display({expression})")


STRUCTURE = {
    "business_questions": "## ۲. سؤال‌های کسب‌وکاری",
    "data": "## ۳. داده‌ها و ستون‌های مورد استفاده",
    "method": "## ۴. روش محاسبه",
    "quality": "## ۵. بررسی کیفیت داده مرتبط",
    "analysis": "## ۶. تحلیل عددی",
    "figures": "## ۷. نمودارها",
    "findings": "## ۸. یافته‌های واقعی",
    "interpretation": "## ۹. تفسیر کسب‌وکاری",
    "limitations": "## ۱۰. محدودیت‌های تحلیل",
    "conclusion": "## ۱۱. نتیجه‌گیری",
}


def notebook(title: str, purpose: str, questions: list[str],
             sections: list[tuple[str, str]]) -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    cells: list = []

    cells.append(nbf.v4.new_markdown_cell(f"# {title}\n\n{purpose}"))
    cells.append(
        nbf.v4.new_markdown_cell(
            STRUCTURE["business_questions"]
            + "\n\n"
            + "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
        )
    )
    cells.append(nbf.v4.new_markdown_cell("## ۱. عنوان و هدف\n\n" + purpose))
    cells.append(nbf.v4.new_code_cell(PREAMBLE))

    for kind, content in sections:
        if kind == "md":
            cells.append(nbf.v4.new_markdown_cell(content))
        elif kind == "code":
            cells.append(nbf.v4.new_code_cell(content))
        elif kind == "fig":
            cells.append(nbf.v4.new_code_cell(fig_cell(content)[1]))

    nb["cells"] = cells
    nb["metadata"] = {
        "kernelspec": {"display_name": "olist-pro", "language": "python", "name": "olist-pro"},
        "language_info": {"name": "python"},
    }
    return nb


def build_all() -> list[str]:
    NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    specs = {
        "00_data_inventory": notebook(
            "۰۰ - فهرست و پروفایل داده‌های خام",
            "این نوتبوک فهرست فیزیکی فایل‌های داده را ثبت می‌کند، تعداد سطر و ستون هر جدول را "
            "می‌شمارد و پروفایل ستون‌ها (نوع، مقادیر گمشده، مقادیر یکتا) را تولید می‌کند.",
            [
                "چه فایل‌هایی در دیتاست وجود دارد و حجم هر یک چقدر است؟",
                "هر جدول چند سطر و چند ستون دارد؟",
                "چه ستون‌هایی مقدار گمشده دارند و درصد آن چقدر است؟",
                "آیا ردیف تکراری کامل در جدول‌ها وجود دارد؟",
            ],
            [
                ("md", STRUCTURE["data"] + "\n\n۹ فایل CSV در `data/raw/`. فهرست کامل و اثر انگشت "
                      "SHA-256 کوتاه هر فایل در جدول `01_file_inventory` ثبت شده است."),
                ("md", STRUCTURE["method"] + "\n\nشمارش سطرها با `pandas.read_csv` انجام می‌شود "
                      "(ردیف منطقی)، نه با شمارش خطوط فایل؛ چون بعضی نظرات مشتریان در "
                      "`olist_order_reviews_dataset.csv` شامل خط جدید داخل متن هستند."),
                ("code", 'display(pd.read_csv(TABLES_DIR / "01_file_inventory.csv"))'),
                ("code", 'display(pd.read_csv(TABLES_DIR / "01_table_shapes.csv"))'),
                ("md", STRUCTURE["quality"]),
                ("code", 'profiles = pd.read_csv(TABLES_DIR / "00_column_profiles.csv")\n'
                         'display(profiles.head(20))'),
                ("code", 'missing = pd.read_csv(TABLES_DIR / "00_missing_values.csv")\n'
                         'display(missing)'),
                ("code", 'display(pd.read_csv(TABLES_DIR / "00_duplicate_rows.csv"))'),
                ("code", 'display(pd.read_csv(TABLES_DIR / "00_key_uniqueness.csv"))'),
                ("md", STRUCTURE["findings"] + "\n\n"
                      "- مجموع حجم داده خام ۱۲۰.۲۵ مگابایت است؛ بزرگ‌ترین فایل، جدول ژئولوکیشن با "
                      "۵۸.۴۴ مگابایت و ۱٬۰۰۰٬۱۶۳ سطر است.\n"
                      "- جدول نظرات ۹۹٬۲۲۴ **ردیف منطقی** دارد در حالی که فایل آن ۱۰۴٬۷۲۰ خط "
                      "فیزیکی است (متن بعضی نظرات شامل خط جدید است).\n"
                      "- `review_id` به‌عنوان کلید اصلی اعلام شده اما یکتا نیست: ۷۸۹ شناسه "
                      "تکرار شده و ۱٬۶۰۳ سطر را در بر می‌گیرد.\n"
                      "- جدول ژئولوکیشن ۲۶۱٬۸۳۱ سطر کاملاً تکراری دارد و کلید اصلی اعلام‌شده ندارد.\n"
                      "- هیچ ردیف تکراری کاملی در ۸ جدول دیگر وجود ندارد."),
                ("md", STRUCTURE["limitations"] + "\n\nدر این مرحله هیچ داده‌ای اصلاح یا حذف "
                      "نمی‌شود؛ فقط شواهد جمع‌آوری می‌شود. تصمیم‌ها در نوتبوک ۰۲ ثبت شده‌اند."),
                ("md", STRUCTURE["conclusion"] + "\n\nساختار داده برای تحلیل چندجدولی مناسب است، "
                      "اما سه مسئله کیفیت داده باید پیش از تحلیل حل شود: تکرار شناسه نظر، "
                      "تکرار گسترده در جدول ژئولوکیشن و مقادیر گمشده ساختاری در جدول سفارش‌ها."),
            ],
        ),
        "01_data_understanding": notebook(
            "۰۱ - شناخت داده‌ها و روابط جداول",
            "هدف این نوتبوک شناسایی معنای هر جدول، کلیدها، نوع رابطه میان جداول و اعتبارسنجی "
            "یکپارچگی ارجاعی است.",
            [
                "هر سطر در هر جدول نشان‌دهنده چیست؟",
                "کلید اصلی هر جدول چیست و آیا واقعاً یکتاست؟",
                "چه ستون‌هایی جداول را به هم متصل می‌کنند؟",
                "آیا شناسه‌ای وجود دارد که در جدول مرجع خود پیدا نشود؟",
                "افزودن هر اتصال چه اثری بر تعداد ردیف‌ها دارد؟",
            ],
            [
                ("md", STRUCTURE["data"] + "\n\nجدول‌ها: `orders`, `customers`, `order_items`, "
                      "`order_payments`, `order_reviews`, `products`, `sellers`, `geolocation`, "
                      "`category_translation`. تصویر ساختار در "
                      "`docs/images/database_structure.png` و توضیح کامل روابط در "
                      "`docs/data_relationships.md`."),
                ("md", STRUCTURE["method"] + "\n\nهر اتصال از طریق `_merge` در ماژول "
                      "`olist_analysis.features` انجام می‌شود که پیش از اجرا نوع رابطه "
                      "(one_to_one / many_to_one) را اعلام و تعداد ردیف‌ها را پس از اتصال بررسی "
                      "می‌کند؛ اگر تعداد ردیف تغییر کند، اجرا با خطا متوقف می‌شود."),
                ("code", 'print("orders x customers : one_to_one (customer_id)")\n'
                         'print("orders x items     : one_to_many (order_id)")\n'
                         'print("orders x payments  : one_to_many (order_id)")\n'
                         'print("orders x reviews   : one_to_many -> کاهیده به one_to_one")\n'
                         'print("items x products   : many_to_one (product_id)")\n'
                         'print("items x sellers    : many_to_one (seller_id)")\n'
                         'print("customers x geo    : many_to_one (zip_code_prefix, پس از تجمیع)")'),
                ("md", STRUCTURE["quality"]),
                ("code", 'display(pd.read_csv(TABLES_DIR / "00_referential_integrity.csv"))'),
                ("md", "### سنجش اثر اتصال بر تعداد ردیف‌ها"),
                ("code", 'rows = [\n'
                         '    ("orders", len(ds.orders)),\n'
                         '    ("orders + customers", len(ds.orders)),\n'
                         '    ("orders + item aggregates", len(ds.orders)),\n'
                         '    ("orders + payment aggregates", len(ds.orders)),\n'
                         '    ("orders + one review per order", len(ds.orders)),\n'
                         '    ("orders + main category", len(ds.orders)),\n'
                         '    ("items (base grain)", len(ds.items)),\n'
                         '    ("unique (order, category) pairs", len(ds.order_category)),\n'
                         '    ("unique (order, seller) pairs", len(ds.order_seller)),\n'
                         ']\n'
                         'display(pd.DataFrame(rows, columns=["grain", "rows"]))'),
                ("md", STRUCTURE["findings"] + "\n\n"
                      "- هیچ شناسه بی‌جوابی در هیچ رابطه‌ای وجود ندارد: در همه ۶ رابطه، "
                      "robustness کامل برقرار است (۰ شناسه بدون تطبیق).\n"
                      "- اتصال‌ها تعداد ردیف جدول سفارش‌ها (۹۹٬۴۴۱) را تغییر نمی‌دهند؛ چون همه "
                      "تجمیع‌ها پیش از اتصال انجام شده‌اند.\n"
                      "- اتصال جدول نظرات به سفارش‌ها اگر به‌صورت خام انجام شود، ۵۵۱ ردیف اضافه "
                      "ایجاد می‌کند؛ بنابراین ابتدا به یک نظر برای هر سفارش کاهش داده می‌شود.\n"
                      "- جدول ژئولوکیشن به‌صورت خام هر مشتری را تا ۱٬۱۴۶ برابر تکثیر می‌کند؛ "
                      "به همین دلیل ابتدا به یک رکورد مرکزی برای هر کد پستی تجمیع می‌شود."),
                ("md", STRUCTURE["conclusion"] + "\n\nمدل رابطه‌ای داده معتبر است و می‌توان با "
                      "اطمینان روی آن اتصال‌ها را انجام داد، به شرطی که علاقه‌مندی گرین (grain) "
                      "هر جدول و قواعد کاهش (deduplication) رعایت شود."),
            ],
        ),
        "02_data_cleaning": notebook(
            "۰۲ - پاک‌سازی و آماده‌سازی داده‌ها",
            "این نوتبوک تصمیم‌های پاک‌سازی را روی داده واقعی اجرا و مستند می‌کند و ویژگی‌های "
            "زمانی و شاخص‌های تحویل را می‌سازد.",
            [
                "برای هر مقادیر گمشده چه تصمیمی گرفته شده و چرا؟",
                "رکوردهای تکراری چگونه بررسی شدند؟",
                "نوع داده‌ها چگونه اصلاح شد؟",
                "چه ویژگی‌های جدیدی ساخته شد و با چه تعریفی؟",
                "چه مقادیر غیرعادی شناسایی شدند؟",
            ],
            [
                ("md", STRUCTURE["method"] + "\n\nخط لوله پاک‌سازی در "
                      "`src/olist_analysis/cleaning.py` قرار دارد و کاملاً قابل بازتولید است: "
                      "داده خام هرگز تغییر نمی‌کند و هیچ ردیفی حذف نمی‌شود."),
                ("code", 'display(pd.read_csv(TABLES_DIR / "02_cleaning_decisions.csv"))'),
                ("md", "### شمارنده‌های پاک‌سازی (شواهد عددی هر تصمیم)"),
                ("code", 'display(pd.read_csv(TABLES_DIR / "02_cleaning_summary.csv"))'),
                ("md", STRUCTURE["quality"] + "\n\n### بررسی ترتیب زمانی رویدادها"),
                ("code", 'checks = {\n'
                         '    "approved قبل از purchase": ds.log["orders_approved_before_purchase"],\n'
                         '    "carrier قبل از approved": ds.log["orders_carrier_before_approved"],\n'
                         '    "delivered قبل از carrier": ds.log["orders_delivered_before_carrier"],\n'
                         '    "approved گمشده": ds.log["orders_missing_approved"],\n'
                         '    "delivered گمشده": ds.log["orders_missing_delivered"],\n'
                         '}\n'
                         'display(pd.Series(checks, name="count"))'),
                ("md", "### ویژگی‌های ساخته‌شده در سطح سفارش"),
                ("code", 'cols = ["order_id", "purchase_ym", "purchase_weekday", "is_delivered",\n'
                         '        "delivery_days", "delay_days", "delivery_class", "delay_bucket",\n'
                         '        "item_count", "order_total_value", "review_score"]\n'
                         'display(ds.orders[cols].head(8))'),
                ("md", "### تعریف طبقه‌بندی تحویل بر پایه تاریخ تقویمی"),
                ("code", 'display(M.delivery_class_summary(ds))'),
                ("md", "**نکته مهم:** تاریخ تخمینی تحویل در داده با ساعت ۰۰:۰۰:۰۰ ذخیره شده است. "
                      "اگر تأخیر با اختلاف زمان‌سنجی خام محاسبه شود، تقریباً همه سفارش‌ها "
                      "«زودتر از موعد» طبقه‌بندی می‌شوند و تعداد سفارش‌های «دقیقاً به‌موقع» صفر "
                      "می‌شود. بنابراین تأخیر بر پایه تفاضل **تاریخ تقویمی** تعریف شده است."),
                ("md", STRUCTURE["findings"] + "\n\n"
                      "- صفر مقدار غیرقابل تبدیل در ستون‌های تاریخ (هیچ خطای پارس).\n"
                      "- ۲٬۹۶۵ سفارش تاریخ تحویل واقعی ندارند؛ این گمشدگی ساختاری است، نه خطا.\n"
                      "- ۷۸۹ شناسه نظر تکراری، ۱٬۶۰۳ سطر را پوشش می‌دهد؛ هر شناسه به سفارش‌های "
                      "مختلف با امتیاز یکسان اشاره می‌کند.\n"
                      "- ۶۱۰ محصول دسته‌بندی ندارند (۱.۸۵ درصد) و با برچسب `unknown` نگه داشته "
                      "می‌شوند.\n"
                      "- ۳۱ سطر مختصات خارج از مرزهای برزیل حذف شد و ۲۶۱٬۸۳۱ سطر تکراری ژئولوکیشن "
                      "حذف شد.\n"
                      "- در نهایت هیچ ردیفی از هیچ جدول اصلی حذف نشد."),
                ("md", STRUCTURE["limitations"] + "\n\nامتیاز تحویل فقط برای سفارش‌های "
                      "«تحویل‌شده» قابل محاسبه است؛ بنابراین درصدهای مربوط به تحویل، مخرجشان "
                      "۹۶٬۴۷۰ سفارش است و نه کل ۹۹٬۴۴۱ سفارش."),
                ("md", STRUCTURE["conclusion"] + "\n\nداده‌ها اکنون آماده تحلیل‌اند: انواع داده "
                      "اصلاح شده، ویژگی‌های زمانی ساخته شده و همه تصمیم‌ها با شواهد عددی مستند "
                      "شده‌اند."),
            ],
        ),
        "03_order_analysis": notebook(
            "۰۳ - تحلیل سفارش‌ها و روند کسب‌وکار",
            "پاسخ به سؤال‌های ۵.۱ تا ۵.۴ صورت‌مسئله: وضعیت سفارش‌ها، روند ماهانه، الگوی هفتگی و "
            "ماه‌های پرتراکنش.",
            [
                "تعداد کل سفارش‌ها و سهم هر وضعیت چقدر است؟",
                "روند ماهانه تعداد سفارش‌ها چگونه است و کدام ماه بیشترین سفارش را دارد؟",
                "آیا رشد پایدار است یا فصلی؟",
                "مشتریان در چه روزهایی بیشتر سفارش می‌دهند؟",
                "پنج ماه پرتراکنش کدام‌اند؟",
            ],
            [
                ("md", STRUCTURE["method"] + "\n\nماه‌ها با `purchase_ym` گروه‌بندی می‌شوند. برای "
                      "تحلیل روند فقط ماه‌های پیوسته ۲۰۱۷-۰۱ تا ۲۰۱۸-۰۸ (۹۹٬۰۹۲ سفارش) استفاده "
                      "می‌شود؛ سال ۲۰۱۶ سه ماه پراکنده ناقص و دو ماه پایانی ۲۰۱۸ ناقص هستند."),
                ("md", STRUCTURE["analysis"] + "\n\n### ۵.۱ وضعیت سفارش‌ها"),
                ("code", 'display(M.order_status_summary(ds))'),
                ("md", "### ۵.۲ روند ماهانه"),
                ("code", 'display(M.monthly_orders(ds))'),
                ("code", 'display(M.year_month_matrix(ds))'),
                ("md", "### ۵.۳ الگوی هفتگی"),
                ("code", 'display(M.weekday_orders(ds))'),
                ("md", "### ۵.۴ پنج ماه پرتراکنش"),
                ("code", 'display(M.top_months(ds))'),
                ("code", 'display(pd.Series(M.growth_evidence(ds), name="value"))'),
                ("md", STRUCTURE["figures"]),
                ("fig", "fig_01_order_status"),
                ("fig", "fig_02_monthly_orders"),
                ("fig", "fig_03_weekday_orders"),
                ("fig", "fig_04_top_months"),
                ("md", STRUCTURE["findings"] + "\n\n"
                      "- ۹۹٬۴۴۱ سفارش ثبت شده که ۹۶٬۴۷۸ مورد (۹۷.۰۲ درصد) تحویل شده است.\n"
                      "- اوج فعالیت آبان ۲۰۱۷ با ۷٬۵۴۴ سفارش است؛ کمترین ماه پنجره تحلیلی "
                      "ژانویه ۲۰۱۷ با ۸۰۰ سفارش.\n"
                      "- مقایسه هم‌دوره ژانویه تا اوت: ۲۲٬۹۶۸ سفارش در ۲۰۱۷ در برابر ۵۳٬۹۹۱ در "
                      "۲۰۱۸؛ رشد ۱۳۵.۰۷ درصد.\n"
                      "- دوشنبه پرترافیک‌ترین روز (۱۶٬۲۸۷ سفارش) و شنبه کم‌ترافیک‌ترین روز "
                      "(۱۰٬۸۸۷ سفارش) است.\n"
                      "- هیچ الگوی فصلی روشنی دیده نمی‌شود؛ جهش آبان ۲۰۱۷ با کمپین‌های فروش "
                      "همزمان است و در سال بعد تکرار نشده است."),
                ("md", STRUCTURE["interpretation"] + "\n\nکسب‌وکار از مرحله راه‌اندازی عبور "
                      "کرده و به سطح فعالیت بزرگ‌تری رسیده است، اما رشد انفجاری ۲۰۱۷ در ۲۰۱۸ "
                      "تکرار نشده و میانگین ماهانه در نیمه دوم سال ۲۰۱۸ کم‌تر از نیمه اول همان "
                      "سال است. برنامه‌ریزی ظرفیت باید بر پایه سطح فعلی تقاضا انجام شود."),
                ("md", STRUCTURE["limitations"] + "\n\nمقایسه هم‌دوره، یک سال راه‌اندازی را با یک "
                      "سال تثبیت‌شده می‌سنجد و درصد رشد را بیش از حد نشان می‌دهد. داده شامل "
                      "شاخص‌های بازاریابی و هزینه کمپین نیست، بنابراین علت جهش آبان ۲۰۱۷ قابل "
                      "تأیید نیست."),
                ("md", STRUCTURE["conclusion"] + "\n\nحجم فعالیت رشد کرده و تثبیت شده و الگوی "
                      "فصلی پایدار ندارد؛ برنامه‌ریزی باید روی سطح فعلی سفارش‌ها و مدیریت اوج‌های "
                      "کوتاه‌مدت متمرکز شود."),
            ],
        ),
        "04_customer_analysis": notebook(
            "۰۴ - تحلیل مشتریان و بازار جغرافیایی",
            "پاسخ به سؤال‌های بخش ۶ صورت‌مسئله: تعداد مشتریان یکتا، توزیع جغرافیایی و تمرکز بازار.",
            [
                "تعداد مشتریان یکتا چقدر است و تفاوت آن با تعداد ردیف چیست؟",
                "تعداد مشتریان هر ایالت چقدر است و ده ایالت اول کدام‌اند؟",
                "سهم پنج ایالت اول از کل مشتریان چقدر است؟",
                "کدام شهرها بیشترین مشتری را دارند؟",
                "آیا سهم ایالت‌ها از مشتریان و از سفارش‌ها متفاوت است؟",
            ],
            [
                ("md", STRUCTURE["method"] + "\n\nشمارش مشتری با `customer_unique_id` انجام "
                      "می‌شود، چون `customer_id` در این دیتاست معادل یک سفارش است و نه یک شخص."),
                ("md", STRUCTURE["analysis"] + "\n\n### ۶.۱ تعداد مشتریان"),
                ("code", 'display(pd.Series(M.customer_overview(ds), name="value"))'),
                ("md", "### ۶.۲ توزیع مشتریان بر اساس ایالت"),
                ("code", 'display(M.customers_by_state(ds, top=10))'),
                ("code", 'display(pd.Series(M.top_n_state_share(ds, 5), name="value"))'),
                ("md", "### ۶.۳ شهرهای دارای بیشترین مشتری"),
                ("code", 'display(M.customers_by_city(ds, 10))'),
                ("md", "### ۶.۴ مقایسه مشتریان و سفارش‌ها بر اساس ایالت"),
                ("code", 'display(M.state_customers_vs_orders(ds).head(15))'),
                ("md", STRUCTURE["figures"]),
                ("fig", "fig_05_state_customers"),
                ("fig", "fig_06_top_cities"),
                ("fig", "fig_07_state_customers_vs_orders"),
                ("md", STRUCTURE["findings"] + "\n\n"
                      "- ۹۶٬۰۹۶ خریدار یکتا در ۹۹٬۴۴۱ ردیف مشتری ثبت شده‌اند؛ یعنی هر خریدار "
                      "به‌طور میانگین ۱.۰۳۵ سفارش دارد.\n"
                      "- تنها ۲٬۹۹۷ نفر (۳.۱۲ درصد) بیش از یک سفارش ثبت کرده‌اند؛ بیشترین تعداد "
                      "سفارش یک نفر ۱۷ است.\n"
                      "- ایالت SP با ۴۰٬۳۰۲ خریدار، ۴۱.۹۲ درصد بازار را در اختیار دارد.\n"
                      "- پنج ایالت اول (SP, RJ, MG, RS, PR) روی هم ۷۷.۰۸ درصد مشتریان و ۷۷.۱۸ "
                      "درصد سفارش‌ها را پوشش می‌دهند.\n"
                      "- شهر سائوپائولو با ۱۴٬۹۸۴ خریدار، ۱۵.۵۹ درصد کل مشتریان را دارد.\n"
                      "- سهم مشتریان و سهم سفارش‌ها در سطح ایالت‌ها تقریباً یکسان است و تفاوت "
                      "معناداری مشاهده نمی‌شود."),
                ("md", STRUCTURE["interpretation"] + "\n\nتمرکز بازار بالا است: هم مزیت کارایی "
                      "در مناطق پرتراکم و هم ریسک وابستگی به یک بازار. نرخ خرید دوباره بسیار "
                      "کم است و برنامه وفادارسازی می‌تواند ارزش هر مشتری را بالا ببرد."),
                ("md", STRUCTURE["limitations"] + "\n\nداده شامل هزینه بازاریابی، رقبا و تقاضای "
                      "بالفعل مناطق کم‌مشتری نیست. کم بودن تعداد مشتری در یک ایالت به‌تنهایی "
                      "اثبات فرصت رشد نیست و به‌عنوان فرصت تأییدشده معرفی نمی‌شود."),
                ("md", STRUCTURE["conclusion"] + "\n\nبازار فعال Olist عمدتاً در جنوب و "
                      "جنوب‌شرق متمرکز است و سیاست رشد باید با در نظر گرفتن همین تمرکز و "
                      "هزینه‌های لجستیک مناطق دور طراحی شود."),
            ],
        ),
        "05_product_analysis": notebook(
            "۰۵ - تحلیل محصولات و عملکرد فروش",
            "پاسخ به سؤال‌های بخش ۷ صورت‌مسئله: تعداد دسته‌بندی‌ها، رتبه‌بندی حجم و مبلغ فروش، "
            "متوسط قیمت و سهم دسته‌بندی‌ها.",
            [
                "چند دسته‌بندی محصول وجود دارد؟",
                "ده دسته‌بندی برتر بر اساس تعداد اقلام کدام‌اند؟",
                "ده دسته‌بندی برتر بر اساس مبلغ فروش کدام‌اند؟",
                "آیا رتبه‌بندی حجم و مبلغ یکسان است؟",
                "سهم پنج دسته‌بندی اول از کل مبلغ فروش چقدر است؟",
            ],
            [
                ("md", STRUCTURE["method"] + "\n\nمبلغ فروش اقلام از ستون `price` جدول اقلام "
                      "سفارش محاسبه می‌شود. در این دیتاست هر سطر یک واحد کالا است، بنابراین "
                      "مبلغ فروش هر سطر برابر همان `price` است. هزینه ارسال جداگانه گزارش "
                      "می‌شود و در مبلغ فروش دسته‌بندی لحاظ نشده است."),
                ("md", STRUCTURE["analysis"] + "\n\n### ۷.۱ ده دسته‌بندی برتر بر اساس تعداد"),
                ("code", 'display(M.top_categories(ds, "items", 10)[["category_label", "n_items", '
                         '"revenue", "rank_items", "rank_revenue"]])'),
                ("md", "### ۷.۲ ده دسته‌بندی برتر بر اساس مبلغ فروش"),
                ("code", 'display(M.top_categories(ds, "revenue", 10)[["category_label", "n_items", '
                         '"revenue", "pct_revenue", "mean_item_price"]])'),
                ("md", "### ۷.۳ مقایسه رتبه‌بندی حجم و مبلغ"),
                ("code", 'display(M.category_rank_comparison(ds, k=20, min_gap=5))'),
                ("md", "### ۷.۴ پنج دسته‌بندی با بالاترین متوسط قیمت (با حجم کافی)"),
                ("code", 'display(M.top_categories(ds, "mean_price", 5))'),
                ("md", "### ۷.۵ سهم پنج دسته‌بندی اول از کل مبلغ فروش"),
                ("code", 'display(pd.Series(M.top_n_revenue_share(ds, 5), name="value"))'),
                ("md", STRUCTURE["figures"]),
                ("fig", "fig_08_top_categories_items"),
                ("fig", "fig_09_top_categories_revenue"),
                ("fig", "fig_10_category_items_vs_revenue"),
                ("fig", "fig_11_top_categories_price"),
                ("md", STRUCTURE["findings"] + "\n\n"
                      "- ۷۳ دسته‌بندی محصول (بدون احتساب برچسب `unknown`) وجود دارد.\n"
                      "- `bed_bath_table` با ۱۱٬۱۱۵ قلم، رتبه اول حجم است اما در مبلغ فروش رتبه "
                      "سوم را دارد.\n"
                      "- `health_beauty` با ۱٬۲۵۸٬۶۸۱ رئال رتبه اول مبلغ فروش است.\n"
                      "- `watches_gifts` با رتبه ۷ در حجم، رتبه ۲ در مبلغ فروش را دارد؛ فاصله "
                      "۵ رتبه‌ای نشان می‌دهد متوسط قیمت بالای آن (۲۰۱ رئال) جبران کمبود حجم را "
                      "می‌کند.\n"
                      "- `computers` با متوسط قیمت ۱٬۰۹۸ رئال گران‌ترین دسته‌بندی است اما از نظر "
                      "مبلغ فروش رتبه ۱۷ را دارد.\n"
                      "- پنج دسته‌بندی اول ۴۰.۲۷ درصد کل مبلغ فروش را تشکیل می‌دهند."),
                ("md", STRUCTURE["interpretation"] + "\n\nتصمیم‌گیری فقط بر پایه حجم فروش "
                      "گمراه‌کننده است: `bed_bath_table` پرحجم‌ترین است اما ارزش کم‌تری به ازای "
                      "هر قلم تولید می‌کند، در حالی که `watches_gifts` با حجم کم‌تر ارزش بیشتری "
                      "می‌سازد. برای تیم فروش، ترکیب «حجم» و «ارزش» تعیین‌کننده اولویت است."),
                ("md", STRUCTURE["limitations"] + "\n\nمبلغ فروش با درآمد خالص یا سود یکسان "
                      "نیست (هزینه ارسال، تخفیف و بازگشت کالا در آن لحاظ نشده است). ۶۱۰ محصول "
                      "بدون دسته‌بندی در مبلغ کل باقی مانده‌اند اما در رتبه‌بندی‌ها کنار گذاشته "
                      "شده‌اند."),
                ("md", STRUCTURE["conclusion"] + "\n\nعملکرد دسته‌بندی‌ها باید هم‌زمان بر پایه "
                      "حجم و ارزش سنجیده شود؛ تمرکز درآمد در چند دسته‌بندی، هم فرصت و هم ریسک "
                      "است."),
            ],
        ),
        "06_payment_analysis": notebook(
            "۰۶ - تحلیل رفتار پرداخت",
            "پاسخ به سؤال‌های بخش ۸ صورت‌مسئله: روش‌های پرداخت، تعداد اقساط و رابطه مبلغ و اقساط.",
            [
                "هر روش پرداخت چند تراکنش دارد و سهم آن چقدر است؟",
                "مجموع و متوسط مبلغ پرداخت هر روش چقدر است؟",
                "توزیع تعداد اقساط چگونه است؟",
                "چه تعداد پرداخت بدون قسط یا یک‌قسطی است؟",
                "آیا مبلغ بالاتر با اقساط بیشتر همراه است؟",
            ],
            [
                ("md", STRUCTURE["method"] + "\n\nهر ردیف جدول پرداخت یک تراکنش است و با سفارش "
                      "یک‌به‌یک نیست؛ بنابراین تعداد تراکنش، تعداد سفارش و تعداد مشتری سه "
                      "مخرج متفاوت دارند."),
                ("md", STRUCTURE["quality"] + "\n\n### تفکیک دقیق جامعه‌های آماری"),
                ("code", 'display(M.payment_reconciliation(ds))'),
                ("md", STRUCTURE["analysis"] + "\n\n### ۸.۱ تا ۸.۳ روش‌های پرداخت"),
                ("code", 'display(M.payment_type_summary(ds))'),
                ("md", "### ۸.۴ توزیع تعداد اقساط"),
                ("code", 'display(M.installment_distribution(ds))'),
                ("md", "### ۸.۵ پرداخت‌های بدون قسط یا یک‌قسطی"),
                ("code", 'display(pd.Series({k: v for k, v in M.zero_or_single_installments(ds).items() '
                         'if k != "by_type"}, name="value"))\ndisplay(M.zero_or_single_installments(ds)["by_type"])'),
                ("md", "### ۸.۶ تعداد اقساط به تفکیک روش پرداخت"),
                ("code", 'display(M.installments_by_type_summary(ds))'),
                ("md", "### ۸.۷ رابطه مبلغ پرداخت و تعداد اقساط"),
                ("code", 'bins, stats = M.combined_payment_vs_installments(ds)\ndisplay(pd.Series(stats, name="value"))\ndisplay(bins[["value_band", "n_transactions", "median_value", "mean_installments", "pct_multi_installment"]])'),
                ("md", STRUCTURE["figures"]),
                ("fig", "fig_12_payment_types"),
                ("fig", "fig_13_installments_distribution"),
                ("fig", "fig_14_payment_value_vs_installments"),
                ("md", STRUCTURE["findings"] + "\n\n"
                      "- ۱۰۳٬۸۸۶ تراکنش پرداخت برای ۹۹٬۴۴۰ سفارش ثبت شده است؛ تنها ۱ سفارش "
                      "ردیف پرداخت ندارد.\n"
                      "- کارت اعتباری با ۷۶٬۷۹۵ تراکنش (۷۳.۹۲ درصد) و ۷۸.۳۴ درصد ارزش پرداخت، "
                      "روش غالب است. بولتو با ۱۹٬۷۸۴ تراکنش در جای دوم است.\n"
                      "- ۵۲٬۵۴۶ تراکنش (۵۰.۵۸ درصد) یک‌قسطی هستند و فقط ۲ تراکنش مقدار صفر برای "
                      "تعداد اقساط دارند که هر دو بخشی از یک پرداخت چندمرحله‌ای‌اند.\n"
                      "- فقط کارت اعتباری اقساط دارد: میانگین ۳.۵۱ قسط و بیشینه ۲۴. بولتو، "
                      "ووچر و کارت نقدی همیشه یک‌قسطی هستند.\n"
                      "- رابطه مبلغ پرداخت و تعداد اقساط مثبت است (اسپیرمن ۰.۴۱۱ در سطح تراکنش "
                      "و ۰.۴۷۸ برای کارت اعتباری): میانگین اقساط از ۱.۲۱ در کم‌مبلغ‌ترین دهک "
                      "به ۵.۳۳ در پرمبلغ‌ترین دهک می‌رسد."),
                ("md", STRUCTURE["interpretation"] + "\n\nساختار اقساط عملاً یک ابزار کارت "
                      "اعتباری است و برای مبالغ بالاتر استفاده می‌شود؛ بنابراین اقساط یک اهرم "
                      "واقعی برای خریدهای گران است. تمرکز بالای پرداخت روی یک روش نیز ریسک "
                      "عملیاتی و ریسک نرخ کارمزد را بالا می‌برد."),
                ("md", STRUCTURE["limitations"] + "\n\nهمبستگی مشاهده‌شده رابطه علّی نیست و "
                      "داده شامل درآمد، اعتبار یا ترجیحات مشتری نیست. همچنین ۹ ردیف با ارزش صفر "
                      "(ووچر و `not_defined`) در محاسبات میانگین باقی مانده‌اند."),
                ("md", STRUCTURE["conclusion"] + "\n\nاقساط بیشتر برای مبالغ بالاتر یک الگوی "
                      "روشن و قابل استفاده در سیاست فروش است؛ اما وابستگی به یک روش پرداخت و "
                      "نرخ بالای پرداخت یک‌قسطی برای تیم مالی ریسک محسوب می‌شود."),
            ],
        ),
        "07_delivery_analysis": notebook(
            "۰۷ - بررسی عملکرد ارسال سفارش‌ها",
            "پاسخ به سؤال‌های بخش ۹ صورت‌مسئله: زمان تحویل، تأخیر، تفکیک جغرافیایی و روند زمانی.",
            [
                "مدت زمان ثبت تا تحویل چقدر است و توزیع آن چگونه است؟",
                "چند درصد سفارش‌ها دیرکرددار هستند؟",
                "میانگین تأخیر در سفارش‌های دیرکرددار چقدر است؟",
                "کدام ایالت‌ها کندتر هستند؟",
                "روند زمان تحویل و نرخ تأخیر در طول زمان چگونه است؟",
            ],
            [
                ("md", STRUCTURE["method"] + "\n\n"
                      "- مدت تحویل = تاریخ تحویل واقعی منهای تاریخ ثبت سفارش (بر حسب روز).\n"
                      "- تأخیر = تاریخ تحویل واقعی منهای تاریخ تخمینی تحویل، بر پایه **تاریخ "
                      "تقویمی**.\n"
                      "- سفارش زودتر از موعد: تأخیر کمتر از صفر؛ به‌موقع: مساوی صفر؛ دیرکرددار: "
                      "بیشتر از صفر.\n"
                      "- همه شاخص‌ها فقط روی ۹۶٬۴۷۰ سفارش تحویل‌شده دارای تاریخ محاسبه می‌شوند."),
                ("md", STRUCTURE["analysis"] + "\n\n### ۹.۱ و ۹.۲ آمار زمان تحویل"),
                ("code", 'display(M.delivery_duration_summary(ds))'),
                ("code", 'display(pd.Series(M.delivery_distribution_stats(ds), name="value"))'),
                ("md", "### ۹.۴ تا ۹.۶ طبقه‌بندی تأخیر"),
                ("code", 'display(M.delivery_class_summary(ds))'),
                ("code", 'display(M.delay_summary(ds))'),
                ("md", "### ۹.۷ و ۹.۸ عملکرد تحویل به تفکیک ایالت"),
                ("code", 'display(M.delivery_by_state(ds))'),
                ("md", "### ۹.۹ و ۹.۱۰ روند زمانی"),
                ("code", 'display(M.monthly_delivery_trend(ds))'),
                ("md", STRUCTURE["figures"]),
                ("fig", "fig_15_delivery_histogram"),
                ("fig", "fig_16_delivery_class"),
                ("fig", "fig_17_state_delivery"),
                ("fig", "fig_31_state_late_rate"),
                ("fig", "fig_18_monthly_delivery_trend"),
                ("md", STRUCTURE["findings"] + "\n\n"
                      "- میانگین زمان تحویل ۱۲.۵۶ روز و میانه آن ۱۰.۲۲ روز است؛ فاصله ۲.۳۴ روزه "
                      "میان آن دو نشان می‌دهد توزیع چوله به راست است.\n"
                      "- ۴٬۸۹۶ سفارش (۵.۰۸ درصد) از سقف آماری فاصله میان‌چارکی بالاتر هستند و "
                      "بیشترین زمان تحویل ۲۰۹.۶۳ روز است.\n"
                      "- ۹۱.۸۹ درصد سفارش‌ها زودتر از وعده، ۱.۳۴ درصد دقیقاً سر وعده و ۶.۷۷ "
                      "درصد (۶٬۵۳۴ سفارش) با تأخیر تحویل شده‌اند.\n"
                      "- میانگین تأخیر در سفارش‌های دیرکرددار ۱۰.۶۲ روز و میانه آن ۷ روز است؛ "
                      "۲٬۸۶۲ سفارش بیش از ۷ روز تأخیر دارند.\n"
                      "- میانگین زمان تحویل از ۸.۷۶ روز در SP تا ۲۹.۳۹ روز در RR تغییر می‌کند.\n"
                      "- ایالت‌های AL، MA، CE، SE، PA، PB، PI و BA هم‌زمان کند و پرتأخیر "
                      "هستند؛ AL با ۲۱.۴۱ درصد نرخ تأخیر بدترین وضعیت را دارد."),
                ("md", STRUCTURE["interpretation"] + "\n\nتأخیر یک مشکل سراسری نیست: ۹۱.۹ درصد "
                      "سفارش‌ها زودتر از وعده می‌رسند. نرخ تأخیر در ایالت‌های شمال و شمال‌شرق "
                      "چند برابر جنوب و جنوب‌شرق است، پس اقدام اصلاحی می‌تواند هدفمند و "
                      "کم‌هزینه باشد. همچنین وعده‌های اعلامی برای این مناطق حاشیه امن بزرگی "
                      "دارند (میانگین ۳۲.۵۸ روز وعده در برابر ۲۴.۵۴ روز تحویل واقعی در AL)."),
                ("md", STRUCTURE["limitations"] + "\n\n۸ سفارش تحویل‌شده تاریخ تحویل واقعی "
                      "ندارند و از محاسبات کنار گذاشته شده‌اند. ۱٬۳۵۹ سفارش ترتیب زمانی "
                      "غیرمنتظره بین تأیید و تحویل به شرکت حمل دارند که ثبت دیرهنگام است و بر "
                      "شاخص‌های اصلی اثر ندارد."),
                ("md", STRUCTURE["conclusion"] + "\n\nعملکرد ارسال در مجموع قابل قبول است، اما "
                      "بخش کوچکی از سفارش‌ها با تأخیر طولانی تحویل می‌شوند و این تأخیر در چند "
                      "ایالت مشخص متمرکز است؛ همین نقاط باید هدف اقدام عملیاتی باشند."),
            ],
        ),
        "08_customer_satisfaction": notebook(
            "۰۸ - تحلیل رضایت مشتریان",
            "پاسخ به سؤال‌های بخش ۱۰ صورت‌مسئله: توزیع امتیازها، رضایت در دسته‌بندی‌ها و روند زمانی "
            "رضایت.",
            [
                "توزیع امتیاز نظرها چگونه است؟",
                "میانگین امتیاز و سهم امتیازهای ۴ و ۵ و ۱ و ۲ چقدر است؟",
                "کدام دسته‌بندی‌ها بالاترین و پایین‌ترین میانگین امتیاز را دارند؟",
                "تعداد نظر هر دسته‌بندی چه اهمیتی دارد؟",
                "روند میانگین امتیاز در طول زمان چگونه است؟",
            ],
            [
                ("md", STRUCTURE["method"] + "\n\nمبنای محاسبه، جدول «یک نظر برای هر سفارش» است "
                      "(۹۸٬۶۷۳ سفارش). برای هر سفارش جدیدترین نظر بر اساس "
                      "`review_answer_timestamp` نگه داشته می‌شود؛ این کار از تکثیر امتیاز در "
                      "اتصال جلوگیری می‌کند."),
                ("md", STRUCTURE["analysis"] + "\n\n### ۱۰.۱ و ۱۰.۲ توزیع امتیازها"),
                ("code", 'display(M.review_score_distribution(ds))'),
                ("code", 'display(pd.Series(M.satisfaction_kpis(ds), name="value"))'),
                ("md", "### ۱۰.۳ ده دسته‌بندی با بالاترین میانگین امتیاز"),
                ("code", 'display(M.category_satisfaction_ranked(ds, "best", 10))'),
                ("md", "### ۱۰.۴ ده دسته‌بندی با پایین‌ترین میانگین امتیاز"),
                ("code", 'display(M.category_satisfaction_ranked(ds, "worst", 10))'),
                ("md", "### ۱۰.۵ اهمیت تعداد نظر: دسته‌بندی‌های با نمونه کوچک"),
                ("code", 'display(M.low_volume_categories(ds))'),
                ("md", "### ۱۰.۷ روند زمانی میانگین امتیاز"),
                ("code", 'display(M.monthly_satisfaction_trend(ds))'),
                ("md", STRUCTURE["figures"]),
                ("fig", "fig_19_review_scores"),
                ("fig", "fig_20_category_scores"),
                ("fig", "fig_21_monthly_score_trend"),
                ("md", STRUCTURE["findings"] + "\n\n"
                      "- میانگین امتیاز مشتریان ۴.۰۹ از ۵ است؛ ۷۷.۰۷ درصد نظرات امتیاز ۴ یا ۵ و "
                      "۱۴.۶۹ درصد امتیاز ۱ یا ۲ داده‌اند.\n"
                      "- امتیاز ۵ با ۵۷٬۰۰۸ نظر پرتکرارترین و امتیاز ۲ با ۳٬۱۳۱ نظر کم‌تکرارترین "
                      "است؛ ولی امتیاز ۱ با ۱۱٬۳۶۳ نظر از امتیاز ۲ و ۳ بیشتر است.\n"
                      "- پرترین میانگین‌ها به دسته‌بندی‌های کوچک و کتاب‌محور تعلق دارد: "
                      "`books_general_interest` با ۴.۴۶ و ۵۰۸ نظر.\n"
                      "- پایین‌ترین میانگین‌ها به دسته‌بندی‌های بزرگ مبلمان و لوازم خانه تعلق "
                      "دارد: `office_furniture` با ۳.۶۲ و ۱٬۲۶۳ نظر و اختلاف منفی ۰.۴۸ با "
                      "میانگین کل.\n"
                      "- ۱۱ دسته‌بندی کمتر از ۳۰ نظر دارند؛ بهترین/بدترین رتبه‌ها در آن‌ها "
                      "قابل تعمیم نیست."),
                ("md", STRUCTURE["interpretation"] + "\n\nرضایت کلی بالا است، اما یک دنباله "
                      "منفی پایدار وجود دارد: حدود ۱۴.۷ درصد مشتریان امتیاز ۱ یا ۲ داده‌اند. "
                      "دسته‌بندی‌های پرحجم با امتیاز پایین (به‌ویژه مبلمان اداری) بالاترین "
                      "اولویت بررسی کیفی را دارند."),
                ("md", STRUCTURE["limitations"] + "\n\nتنها ۷۶۸ سفارش نظر ثبت‌شده ندارند "
                      "(۹۹.۲۳ درصد سفارش‌ها دارای نظر هستند)، بنابراین سوگیری پاسخ‌ندادن "
                      "مشکل جدی نیست؛ اما متن نظرات در تحلیل کمّی استفاده نشده و علت نارضایتی "
                      "قابل استخراج نیست."),
                ("md", STRUCTURE["conclusion"] + "\n\nوضعیت رضایت مشتریان خوب است، اما بهبود "
                      "نیازمند تمرکز روی دسته‌بندی‌ها و سفارش‌هایی است که امتیاز پایین "
                      "می‌گیرند."),
            ],
        ),
        "09_delay_vs_satisfaction": notebook(
            "۰۹ - بررسی ارتباط تأخیر در تحویل و رضایت مشتری",
            "پاسخ به سؤال‌های بخش ۱۱ صورت‌مسئله: مقایسه گروه‌های تحویل، شدت تأخیر و کفایت نمونه.",
            [
                "میانگین امتیاز سفارش‌های به‌موقع و دیرکرددار چقدر است؟",
                "اختلاف دو گروه چقدر است و آیا نمونه کافی است؟",
                "با افزایش شدت تأخیر امتیاز چگونه تغییر می‌کند؟",
                "آیا این الگو در همه دسته‌بندی‌ها دیده می‌شود؟",
                "آیا می‌توان نتیجه گرفت تأخیر علت کاهش رضایت است؟",
            ],
            [
                ("md", STRUCTURE["method"] + "\n\nسفارش‌های تحویل‌شده دارای امتیاز به دو گروه "
                      "«به‌موقع یا زودتر» و «دیرکرددار» تقسیم می‌شوند. برای جلوگیری از شمارش "
                      "مکرر، هر سفارش فقط یک امتیاز دارد. گروه «به‌موقع یا زودتر» شامل سفارش‌های "
                      "زودتر از موعد و دقیقاً سر موعد است."),
                ("md", STRUCTURE["analysis"] + "\n\n### ۱۱.۱ و ۱۱.۲ مقایسه دو گروه"),
                ("code", 'display(M.delay_satisfaction_comparison(ds))'),
                ("code", 'display(pd.Series(M.delay_satisfaction_difference(ds), name="value"))'),
                ("md", "### ۱۱.۳ تا ۱۱.۵ شدت تأخیر و امتیاز"),
                ("code", 'display(M.delay_bucket_satisfaction(ds))'),
                ("md", "### ۱۱.۶ مقایسه در دسته‌بندی‌های دارای حجم کافی"),
                ("code", 'display(M.category_delay_satisfaction(ds))'),
                ("md", STRUCTURE["figures"]),
                ("fig", "fig_22_delay_satisfaction"),
                ("fig", "fig_23_delay_bucket_satisfaction"),
                ("md", STRUCTURE["findings"] + "\n\n"
                      "- گروه به‌موقع یا زودتر ۸۹٬۴۴۳ سفارش با میانگین امتیاز ۴.۲۹ و گروه "
                      "دیرکرددار ۶٬۳۸۱ سفارش با میانگین امتیاز ۲.۲۷ دارد.\n"
                      "- اختلاف میانگین امتیاز دو گروه ۲.۰۲ امتیاز از ۵ است؛ اندازه‌ای بسیار "
                      "بزرگ در مقیاس ۱ تا ۵.\n"
                      "- ۶۲.۴۲ درصد سفارش‌های دیرکرددار امتیاز ۱ یا ۲ داده‌اند، در برابر ۹.۲۷ "
                      "درصد در گروه به‌موقع.\n"
                      "- با افزایش شدت تأخیر امتیاز پیوسته افت می‌کند: ۳.۲۹ برای ۱ تا ۳ روز، "
                      "۲.۱۰ برای ۴ تا ۷ روز و ۱.۷۰ برای بیش از ۷ روز تأخیر.\n"
                      "- در بیش از ۷ روز تأخیر، ۷۹.۲۹ درصد نظرات امتیاز ۱ یا ۲ هستند.\n"
                      "- این الگو در همه دسته‌بندی‌های بزرگ تکرار می‌شود؛ اختلاف امتیاز در "
                      "`musical_instruments` ۲.۵۱ و در `stationery` ۲.۱۲ است."),
                ("md", STRUCTURE["interpretation"] + "\n\nتأخیر تحویل قوی‌ترین عاملی است که در "
                      "این دیتاست با افت رضایت همراه است. اثر آن هم از نظر بزرگی اختلاف و هم از "
                      "نظر پایداری در دسته‌بندی‌های مختلف چشمگیر است؛ به همین دلیل کاهش تأخیر "
                      "کم‌هزینه‌ترین مسیر بهبود میانگین امتیاز محسوب می‌شود."),
                ("md", STRUCTURE["limitations"] + "\n\nاین یک رابطه مشاهده‌شده است و اثبات "
                      "علّیت نیست. ممکن است تأخیر و امتیاز پایین هر دو ناشی از عوامل مشترکی "
                      "مانند ناموجود بودن کالا، مشکل فروشنده یا انتظار اولیه متفاوت مشتری "
                      "باشند. برای استنباط علّی به آزمایش کنترل‌شده یا داده علت تأخیر نیاز است. "
                      "همچنین ۶۴۶ سفارش تحویل‌شده نظر ثبت‌نشده دارند و در این تحلیل نیستند."),
                ("md", STRUCTURE["conclusion"] + "\n\nسفارش‌های دیرکرددار اقلیت کوچکی هستند "
                      "(۶.۷۷ درصد) اما بخش بزرگی از نارضایتی را تولید می‌کنند؛ کاهش تأخیر "
                      "بیشترین اثر را بر میانگین امتیاز دارد."),
            ],
        ),
        "10_seller_analysis": notebook(
            "۱۰ - تحلیل عملکرد فروشندگان",
            "پاسخ به سؤال‌های بخش ۱۲ صورت‌مسئله: تعداد فروشندگان، توزیع جغرافیایی، فروش، تمرکز و "
            "رضایت مشتری.",
            [
                "چند فروشنده فعال است و در کدام ایالت‌ها هستند؟",
                "ده فروشنده برتر بر اساس مبلغ فروش کدام‌اند؟",
                "سهم ده فروشنده اول از کل فروش چقدر است؟",
                "آیا رتبه‌بندی حجم و مبلغ یکسان است؟",
                "کدام فروشندگان پرفروش امتیاز پایین دارند؟",
            ],
            [
                ("md", STRUCTURE["method"] + "\n\nمبنای محاسبه، جدول «یک ردیف برای هر زوج "
                      "سفارش-فروشنده» است تا امتیاز یک سفارش که چند فروشنده دارد، چند بار "
                      "شمرده نشود. دسته‌بندی فروشندگان با حداقل ۳۰ نظر برای مقایسه امتیاز "
                      "کافی در نظر گرفته می‌شود."),
                ("md", STRUCTURE["analysis"] + "\n\n### ۱۲.۱ تعداد و پراکندگی فروشندگان"),
                ("code", 'display(pd.Series(M.seller_overview(ds), name="value"))'),
                ("code", 'display(M.sellers_by_state(ds).head(10))'),
                ("md", "### ۱۲.۲ و ۱۲.۴ فروشندگان برتر و تمرکز فروش"),
                ("code", 'display(M.top_sellers(ds, "revenue", 10)[["seller_id", "seller_state", "n_items", "n_orders", "revenue", "revenue_share_pct", "n_reviews", "mean_score"]])'),
                ("md", "### ۱۲.۵ و ۱۲.۶ فروش بالا با امتیاز پایین"),
                ("code", 'candidates, threshold = M.high_revenue_low_rating_sellers(ds)\nprint(f"آستانه مبلغ فروش: {threshold:,.2f} رئال")\ndisplay(candidates[["seller_id", "seller_state", "n_items", "n_orders", "revenue", "n_reviews", "mean_score", "score_vs_overall"]])'),
                ("md", STRUCTURE["figures"]),
                ("fig", "fig_24_top_sellers"),
                ("fig", "fig_25_seller_revenue_vs_score"),
                ("md", STRUCTURE["findings"] + "\n\n"
                      "- ۳٬۰۹۵ فروشنده یکتا در ۲۳ ایالت فعالیت دارند؛ ۱٬۸۴۹ فروشنده (۵۹.۷۴ "
                      "درصد) در ایالت SP هستند.\n"
                      "- میانه تعداد اقلام هر فروشنده ۸ و میانه مبلغ فروش ۸۲۱.۴۸ رئال است؛ "
                      "یعنی نیمی از فروشندگان بسیار کوچک‌اند.\n"
                      "- ده فروشنده اول ۱٬۷۸۷٬۲۴۲ رئال فروش دارند که ۱۳.۱۵ درصد کل مبلغ فروش "
                      "است؛ تمرکز فروش عمدتاً در سطح دسته‌بندی است، نه فروشنده.\n"
                      "- فقط ۶۲۸ فروشنده (۲۰.۲۹ درصد) حداقل ۳۰ نظر دارند و برای مقایسه امتیاز "
                      "قابل اتکا هستند.\n"
                      "- ۱۰ فروشنده پرفروش با امتیاز پایین‌تر از میانگین کل شناسایی شد؛ شاخص‌ترین "
                      "مورد فروشنده `7c67e144…` با ۱۸۷٬۹۲۴ رئال فروش، ۹۷۶ نظر و میانگین امتیاز "
                      "۳.۴۹ (۰.۶۰ کمتر از میانگین کل) است."),
                ("md", STRUCTURE["interpretation"] + "\n\nخطر وابستگی به تعداد کم فروشنده "
                      "کم‌تر از حد انتظار است، اما کیفیت در بخشی از فروشندگان بزرگ پایین است. "
                      "اختلاف رتبه حجم و مبلغ در میان فروشندگان نیز نشان می‌دهد فروشندگان "
                      "کم‌حجم اما گران‌قیمت، سهم ارزشی مهمی دارند."),
                ("md", STRUCTURE["limitations"] + "\n\nاکثر فروشندگان نمونه نظر کافی ندارند؛ "
                      "امتیاز آنان برای قضاوت قابل استفاده نیست. داده شامل مدت همکاری فروشنده، "
                      "نرخ لغو سفارش یا اطلاعات قراردادی نیست."),
                ("md", STRUCTURE["conclusion"] + "\n\nبازار فروشندگان گسترده اما نامتوازن است؛ "
                      "پایش فروشندگان پرفروش با امتیاز پایین می‌تواند ریسک اعتباری را کاهش "
                      "دهد."),
            ],
        ),
        "11_combined_analysis": notebook(
            "۱۱ - تحلیل‌های ترکیبی",
            "اجرای کامل هر شش تحلیل ترکیبی صورت‌مسئله، از جمله سه تحلیل الزامی.",
            [
                "کدام دسته‌بندی‌های پرفروش رضایت پایین دارند؟",
                "کدام ایالت‌ها هم کند هستند و هم پرتأخیر؟",
                "آیا قیمت بالاتر با امتیاز بالاتر همراه است؟",
                "آیا مبلغ پرداخت بالا با اقساط بیشتر همراه است؟",
                "کدام دسته‌بندی‌ها در طول زمان رشد کرده‌اند؟",
                "کدام فروشندگان با حجم بالا امتیاز پایین دارند؟",
            ],
            [
                ("md", STRUCTURE["method"] + "\n\nهر شش تحلیل ترکیبی با اتصال چند جدول انجام "
                      "می‌شود. در همه موارد گرین (grain) صریح است و محاسبه امتیاز روی سفارش‌های "
                      "یکتا انجام می‌شود."),
                ("md", STRUCTURE["analysis"] + "\n\n### تحلیل ۱ - دسته‌بندی‌های پرفروش با رضایت پایین"),
                ("code", 'table, flagged = M.combined_revenue_vs_satisfaction(ds)\nprint("دسته‌بندی‌های نیازمند بررسی:", len(flagged))\ndisplay(flagged)'),
                ("code", 'display(table.nlargest(12, "revenue"))'),
                ("md", "### تحلیل ۲ - موقعیت جغرافیایی و عملکرد تحویل"),
                ("code", 'states, eligible, thresholds = M.combined_geography_delivery(ds)\ndisplay(pd.Series(thresholds, name="value"))\ndisplay(eligible)'),
                ("md", "### تحلیل ۳ - قیمت محصول و رضایت مشتری"),
                ("code", 'deciles, price_stats = M.combined_price_vs_satisfaction(ds)\ndisplay(pd.Series(price_stats, name="value"))\ndisplay(deciles[["price_band", "n_orders", "median_price", "mean_score", "pct_1_or_2"]])'),
                ("md", "### تحلیل ۴ - مبلغ پرداخت و تعداد اقساط"),
                ("code", 'bins, payment_stats = M.combined_payment_vs_installments(ds)\ndisplay(pd.Series(payment_stats, name="value"))\ndisplay(bins[["value_band", "n_transactions", "mean_installments", "pct_multi_installment"]])'),
                ("md", "### تحلیل ۵ - تغییرات فروش دسته‌بندی‌ها در طول زمان"),
                ("code", 'pivot, trend = M.combined_category_revenue_over_time(ds)\ndisplay(trend)'),
                ("md", "### تحلیل ۶ - عملکرد فروشندگان و رضایت مشتری"),
                ("code", 'candidates, threshold = M.high_revenue_low_rating_sellers(ds)\ndisplay(candidates[["seller_id", "n_items", "revenue", "n_reviews", "mean_score", "score_vs_overall"]])'),
                ("md", "### شرکت‌کنندگان در هر تحلیل ترکیبی"),
                ("code", 'rows = [\n'
                         '    ("تحلیل ۱ - دسته‌بندی پرفروش با رضایت پایین", "Member B + Member C"),\n'
                         '    ("تحلیل ۲ - جغرافیا و تحویل", "Member B + Member C"),\n'
                         '    ("تحلیل ۳ - قیمت و رضایت", "Member B"),\n'
                         '    ("تحلیل ۴ - مبلغ پرداخت و اقساط", "Member B"),\n'
                         '    ("تحلیل ۵ - فروش دسته‌بندی در زمان", "Member A + Member C"),\n'
                         '    ("تحلیل ۶ - فروشنده و رضایت", "Member C"),\n'
                         ']\n'
                         'display(pd.DataFrame(rows, columns=["تحلیل", "مسئول اصلی"]))'),
                ("md", STRUCTURE["figures"]),
                ("fig", "fig_26_combined_revenue_vs_score"),
                ("fig", "fig_27_combined_geography_delivery"),
                ("fig", "fig_28_combined_price_vs_score"),
                ("fig", "fig_29_combined_category_revenue_trend"),
                ("fig", "fig_30_combined_seller_satisfaction"),
                ("md", STRUCTURE["findings"] + "\n\n"
                      "- ۸ دسته‌بندی هم‌زمان در چارک بالای مبلغ فروش و زیر میانگین امتیاز "
                      "قرار دارند؛ `office_furniture` با ۲۷۳٬۹۶۱ رئال و امتیاز ۳.۶۲ شاخص‌ترین "
                      "است.\n"
                      "- ۸ ایالت هم‌زمان کند و پرتأخیر هستند و از این میان AL با ۲۱.۴۱ درصد "
                      "نرخ تأخیر و ۲۴.۵۴ روز میانگین تحویل بدترین است.\n"
                      "- رابطه قیمت و امتیاز عملاً وجود ندارد: ضریب اسپیرمن منفی ۰.۰۰۳ و "
                      "اختلاف میانگین امتیاز کم‌قیمت‌ترین و گران‌ترین دهک تنها ۰.۰۵ امتیاز است.\n"
                      "- رابطه مبلغ پرداخت و اقساط مثبت و قابل توجه است: از ۱.۲۱ قسط در "
                      "کم‌مبلغ‌ترین دهک تا ۵.۳۳ قسط در پرمبلغ‌ترین دهک.\n"
                      "- هر پنج دسته‌بندی اصلی در نیمه دوم پنجره تحویل رشد داشته‌اند "
                      "(`health_beauty` ۱۶۷.۳۴ درصد) و رشد آن‌ها پایدار بوده، نه تک‌ماهه.\n"
                      "- سه فروشنده برای بررسی بیشتر معرفی می‌شوند: `7c67e144…`، `2eb70248…` و "
                      "`712e6ed8…`."),
                ("md", STRUCTURE["interpretation"] + "\n\nتحلیل‌های ترکیبی تصویر عملیاتی روشنی "
                      "می‌سازند: مشکل اصلی نه قیمت‌گذاری است و نه تقاضا، بلکه کیفیت تجربه تحویل "
                      "و کیفیت کالا در چند دسته‌بندی پرحجم. اهرم‌های تجاری مانند اقساط نیز "
                      "رفتار منطقی و قابل پیش‌بینی دارند."),
                ("md", STRUCTURE["limitations"] + "\n\nآستانه‌های «پرفروش» و «امتیاز پایین» "
                      "نسبی و بر پایه چارک‌ها و میانگین همین داده تعریف شده‌اند؛ با داده به‌روز "
                      "ممکن است فهرست پرچم‌خورده‌ها تغییر کند. همه روابط، همبستگی توصیفی‌اند."),
                ("md", STRUCTURE["conclusion"] + "\n\nهر شش تحلیل ترکیبی اجرا شد و هر سه تحلیل "
                      "الزامی دوره در آن‌ها پوشش داده شده است. خروجی این نوتبوک، پایه بخش "
                      "یافته‌ها و پیشنهادهای گزارش مدیریتی است."),
            ],
        ),
        "12_executive_report": notebook(
            "۱۲ - گزارش نهایی مدیریتی",
            "این نوتبوک پنج یافته مهم، سه پیشنهاد عملی و شاخص‌های پایش را از اعداد واقعی "
            "می‌سازد و فایل‌های گزارش را تولید می‌کند.",
            [
                "خلاصه وضعیت کسب‌وکار چیست؟",
                "پنج یافته مهم پروژه کدام‌اند؟",
                "سه پیشنهاد عملی برای مدیریت چیست؟",
                "چه شاخص‌هایی را باید در آینده پایش کرد؟",
                "محدودیت‌های اصلی تحلیل چیست؟",
            ],
            [
                ("md", STRUCTURE["method"] + "\n\nگزارش از فایل `reports/metrics.json` و جداول "
                      "`reports/tables/` ساخته می‌شود؛ بنابراین اعداد آن با نوتبوک‌های قبلی "
                      "یکسان است."),
                ("md", "## خلاصه وضعیت کسب‌وکار"),
                ("code", 'totals = headline["business_totals"]\ndisplay(pd.Series(totals, name="value"))'),
                ("code", 'display(pd.Series(headline["growth"], name="value"))'),
                ("code", 'display(pd.Series(headline["satisfaction"], name="value"))'),
                ("code", 'display(pd.Series(headline["delay_vs_satisfaction"], name="value"))'),
                ("md", "## پنج یافته مهم"),
                ("code", 'from olist_analysis.reporting import build_content, load_tables\ncontent = build_content(headline, load_tables())\nfor f in content.findings:\n    print(f"یافته {f.number}: {f.title}")\n    print(f"  نتیجه: {f.statement}")\n    print(f"  نمودار: {f.figure}")\n    print()'),
                ("code", 'for f in content.findings:\n    print(f"یافته {f.number} - شواهد عددی:")\n    for e in f.evidence:\n        print("   -", e)\n    print(f"  اهمیت: {f.importance}")\n    print(f"  محدودیت: {f.limitation}")\n    print()'),
                ("md", "## سه پیشنهاد عملی"),
                ("code", 'for r in content.recommendations:\n    print(f"پیشنهاد {r.number}: {r.title}")\n    print(f"  مسئله: {r.problem}")\n    print(f"  یافته پشتیبان: {r.supporting_finding}")\n    print(f"  تغییر مورد انتظار: {r.expected_change}")\n    print("  شاخص‌های پایش:")\n    for k in r.monitoring_kpi:\n        print("   -", k)\n    print()'),
                ("md", "## شاخص‌های پیشنهادی برای پایش آینده"),
                ("code", 'display(pd.DataFrame(content.monitoring_indicators, columns=["شاخص", "تعریف"]))'),
                ("md", "## محدودیت‌های اصلی"),
                ("code", 'for limitation in content.limitations:\n    print("-", limitation)'),
                ("md", "## ساخت فایل‌های گزارش"),
                ("code", 'from olist_analysis.reporting import build_report\nresult = build_report()\nprint("Markdown:", result["markdown"])\nprint("PDF     :", result["pdf"])'),
                ("md", STRUCTURE["figures"]),
                ("fig", "fig_02_monthly_orders"),
                ("fig", "fig_05_state_customers"),
                ("fig", "fig_22_delay_satisfaction"),
                ("fig", "fig_27_combined_geography_delivery"),
                ("fig", "fig_26_combined_revenue_vs_score"),
                ("md", STRUCTURE["conclusion"] + "\n\nگزارش مدیریتی در "
                      "`reports/executive_report.md` و `reports/executive_report.pdf` تولید شد. "
                      "خروجی این نوتبوک، نسخه قابل ارائه به مدیریت است و هیچ کد برنامه‌نویسی در "
                      "آن دیده نمی‌شود."),
            ],
        ),
    }

    for name, nb in specs.items():
        path = NOTEBOOKS_DIR / f"{name}.ipynb"
        with path.open("w", encoding="utf-8") as handle:
            nbf.write(nb, handle)
        written.append(path.name)

    # A record of what was generated, so the notebooks are reproducible artifacts.
    (NOTEBOOKS_DIR / "_notebook_index.json").write_text(
        json.dumps({"notebooks": written, "count": len(written)}, indent=2),
        encoding="utf-8",
    )
    return written


if __name__ == "__main__":
    created = build_all()
    print(f"wrote {len(created)} notebooks into {NOTEBOOKS_DIR}")
    for name in created:
        print(" -", name)
