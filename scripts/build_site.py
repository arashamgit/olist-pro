"""Build a static showcase site from the generated analysis outputs.

    python scripts/build_site.py [--output site] [--title "..."]
                                [--repo-url URL] [--branch NAME]

The page is plain HTML with the real figures, tables, metrics and the
executive report next to it, so it can be published by GitHub Pages (see
``.github/workflows/pages.yml``) without any Python runtime on the server.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from html import escape
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
TABLES_DIR = REPORTS_DIR / "tables"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
FONT_FILE = PROJECT_ROOT / "assets" / "fonts" / "Vazirmatn-Regular.ttf"
METRICS_FILE = REPORTS_DIR / "metrics.json"
REPORT_MD = REPORTS_DIR / "executive_report.md"
REPORT_PDF = REPORTS_DIR / "executive_report.pdf"

FALLBACK_REPO_URL = "https://github.com/arashamgit/olist-pro"
TITLE = "تحلیل داده‌های فروش و رفتار مشتریان Olist"
SUBTITLE = (
    "گزارش نتایج پروژه <bdi dir=\"ltr\">olist-pro</bdi>؛ همه اعداد از "
    "<bdi dir=\"ltr\">metrics.json</bdi> و خروجی واقعی خط لوله خوانده شده‌اند."
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def git(*args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return completed.stdout.strip()


def repo_url() -> str:
    url = git("remote", "get-url", "origin")
    if not url:
        return FALLBACK_REPO_URL
    if url.startswith("git@") and ":" in url:
        url = "https://" + url.split("@", 1)[1].replace(":", "/", 1)
    return url[:-4] if url.endswith(".git") else url


def current_branch() -> str:
    return git("rev-parse", "--abbrev-ref", "HEAD") or "main"


def number(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f}"


def pick(mapping: dict, path: str, default=None):
    """Read ``a.b.c`` from nested dictionaries without raising."""
    node = mapping
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def card(label: str, value: str, detail: str = "") -> str:
    detail_html = f'<p class="card-detail">{detail}</p>' if detail else ""
    return (
        '<div class="card">'
        f'<p class="card-label">{label}</p>'
        f'<p class="card-value">{value}</p>'
        f"{detail_html}"
        "</div>"
    )


def build_cards(metrics: dict) -> str:
    totals = metrics.get("business_totals", {})
    satisfaction = metrics.get("satisfaction", {})
    delay = metrics.get("delay_vs_satisfaction", {})
    delivery = metrics.get("delivery_duration", {})
    geography = metrics.get("top5_state_share", {})
    categories = metrics.get("category_revenue_top5", {})
    sellers = metrics.get("sellers", {})

    late_share = ""
    if delay.get("n_late") and delivery.get("n_delivered_orders"):
        late_share = number(
            100 * delay["n_late"] / delivery["n_delivered_orders"], 2
        ) + " درصد سفارش‌های تحویل‌شده"

    cards = [
        card("سفارش‌ها", number(totals.get("orders", 0)), "در بازه کامل دیتاست"),
        card("خریداران یکتا", number(totals.get("unique_buyers", 0)),
             "نرخ خرید دوباره " + number(metrics.get("customers", {}).get("repeat_share_pct", 0), 2) + " درصد"),
        card("مبلغ اقلام فروش", number(totals.get("item_revenue_brl", 0), 2) + " رئال",
             "میانگین هر سفارش " + number(totals.get("mean_order_value_brl", 0), 2) + " رئال"),
        card("میانگین امتیاز مشتری", number(satisfaction.get("mean_score", 0), 2) + " از ۵",
             number(satisfaction.get("pct_4_or_5", 0), 2) + " درصد امتیاز ۴ یا ۵"),
        card("میانگین زمان تحویل", number(delivery.get("mean_days", 0), 2) + " روز",
             "میانه " + number(delivery.get("median_days", 0), 2) + " روز"),
        card("سفارش‌های دیرکرددار", number(delay.get("n_late", 0)), late_share),
        card("شکاف امتیاز تأخیر", number(delay.get("score_gap", 0), 2) + " امتیاز",
             number(delay.get("mean_score_late", 0), 2) + " در برابر "
             + number(delay.get("mean_score_on_time_or_early", 0), 2)),
        card("تمرکز جغرافیایی", number(geography.get("top_n_customer_share_pct", 0), 2) + " درصد",
             "سهم پنج ایالت اول از خریداران"),
        card("دسته‌بندی محصول", number(totals.get("product_categories", 0)) + " دسته",
             "سهم پنج دسته اول از درآمد "
             + number(categories.get("top_n_revenue_share_pct", 0), 2) + " درصد"),
        card("فروشندگان", number(sellers.get("n_sellers", 0)),
             "سهم ده فروشنده اول " + number(sellers.get("top10_revenue_share_pct", 0), 2) + " درصد"),
    ]
    return "\n".join(cards)


def build_findings(metrics: dict) -> str:
    totals = metrics.get("business_totals", {})
    satisfaction = metrics.get("satisfaction", {})
    delay = metrics.get("delay_vs_satisfaction", {})
    geography = metrics.get("top5_state_share", {})
    categories = metrics.get("category_revenue_top5", {})
    sellers = metrics.get("seller_low_rating_threshold")

    items = [
        (
            "حجم کسب‌وکار",
            f"مبلغ اقلام فروش {number(totals.get('item_revenue_brl', 0), 2)} رئال در "
            f"{number(totals.get('orders', 0))} سفارش و {number(totals.get('unique_buyers', 0))} "
            "خریدار یکتا؛ میانگین سبد فقط "
            f"{number(metrics.get('customers', {}).get('orders_per_person', 0), 2)} سفارش برای هر خریدار.",
        ),
        (
            "رضایت به‌طور کلی بالا است",
            f"میانگین امتیاز {number(satisfaction.get('mean_score', 0), 2)} از ۵ و "
            f"{number(satisfaction.get('pct_4_or_5', 0), 2)} درصد سفارش‌ها امتیاز ۴ یا ۵ گرفته‌اند.",
        ),
        (
            "تأخیر در تحویل، پرهزینه‌ترین مشکل کیفی",
            f"امتیاز مشتریان دیرکرددار {number(delay.get('mean_score_late', 0), 2)} در برابر "
            f"{number(delay.get('mean_score_on_time_or_early', 0), 2)} گروه به‌موقع؛ "
            f"اختلاف {number(delay.get('score_gap', 0), 2)} امتیاز با "
            f"{number(delay.get('n_late', 0))} سفارش دیرکرددار.",
        ),
        (
            "تمرکز شدید بازار در چند ایالت",
            f"{number(geography.get('top_n_customer_share_pct', 0), 2)} درصد خریداران در پنج ایالت "
            f"({escape(str(geography.get('states', '')))}) هستند؛ رشد باید با برنامه لجستیک همراه باشد.",
        ),
        (
            "تمرکز درآمد در چند دسته",
            f"پنج دسته اول {number(categories.get('top_n_revenue_share_pct', 0), 2)} درصد درآمد را "
            f"می‌سازند؛ آستانه پایش فروشنده پرحجم با امتیاز پایین "
            f"{number(sellers or 0, 2)} رئال است.",
        ),
    ]
    return "\n".join(
        f'<li><h3>{escape(head)}</h3><p>{body}</p></li>' for head, body in items
    )


def build_figures(output_dir: Path) -> str:
    figures = sorted(FIGURES_DIR.glob("fig_*.png"))
    if not figures:
        return '<p class="empty">نموداری یافت نشد؛ ابتدا <bdi dir="ltr">python scripts/run_all.py</bdi> را اجرا کنید.</p>'

    target = output_dir / "figures"
    target.mkdir(parents=True, exist_ok=True)

    blocks: list[str] = []
    for figure in figures:
        shutil.copy2(figure, target / figure.name)
        caption_file = figure.with_suffix(".txt")
        caption = (
            caption_file.read_text(encoding="utf-8").strip()
            if caption_file.exists()
            else figure.stem.replace("_", " ")
        )
        blocks.append(
            '<figure class="figure">'
            f'<img src="figures/{figure.name}" alt="{escape(caption)}" loading="lazy">'
            f"<figcaption>{escape(caption)}</figcaption>"
            "</figure>"
        )
    return "\n".join(blocks)


def build_tables(output_dir: Path) -> str:
    tables = sorted(TABLES_DIR.glob("*.csv"))
    if not tables:
        return '<p class="empty">جدولی یافت نشد.</p>'

    target = output_dir / "tables"
    target.mkdir(parents=True, exist_ok=True)

    rows: list[str] = []
    for table in tables:
        shutil.copy2(table, target / table.name)
        rows.append(
            "<tr>"
            f'<td><a href="tables/{table.name}">{escape(table.name)}</a></td>'
            f"<td>{number(table.stat().st_size / 1024, 1)} کیلوبایت</td>"
            "</tr>"
        )
    return (
        f"<p>مجموعاً {len(tables)} فایل جدول تحلیل در دسترس است.</p>"
        '<table class="tables"><thead><tr><th>فایل</th><th>حجم</th></tr></thead>'
        "<tbody>" + "\n".join(rows) + "</tbody></table>"
    )


def copy_downloads(output_dir: Path) -> list[str]:
    links: list[str] = []
    for source, label in (
        (REPORT_PDF, "گزارش مدیریتی (PDF)"),
        (REPORT_MD, "گزارش مدیریتی (Markdown)"),
        (METRICS_FILE, "شاخص‌های عددی (metrics.json)"),
    ):
        if source.exists():
            shutil.copy2(source, output_dir / source.name)
            links.append(f'<li><a href="{source.name}">{label}</a></li>')
    return links


def build_notebook_links(repo: str, branch: str) -> str:
    notebooks = sorted(NOTEBOOKS_DIR.glob("[0-9][0-9]_*.ipynb"))
    if not notebooks:
        return ""
    rows = "\n".join(
        f'<li><a href="{repo}/blob/{branch}/notebooks/{nb.name}">{escape(nb.stem)}</a></li>'
        for nb in notebooks
    )
    return f'<ul class="notebooks">{rows}</ul>'


def render(
    metrics: dict,
    output_dir: Path,
    title: str,
    subtitle: str,
    repo: str,
    branch: str,
) -> str:
    cards = build_cards(metrics)
    findings = build_findings(metrics)
    figures = build_figures(output_dir)
    tables = build_tables(output_dir)
    downloads = copy_downloads(output_dir)
    notebooks = build_notebook_links(repo, branch)

    font_face = ""
    if FONT_FILE.exists():
        fonts_dir = output_dir / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FONT_FILE, fonts_dir / FONT_FILE.name)
        font_face = (
            "@font-face{font-family:Vazirmatn;src:url('fonts/"
            f"{FONT_FILE.name}') format('truetype');font-display:swap;}}"
        )

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit = git("rev-parse", "--short", "HEAD") or "unknown"
    owner_repo = repo.split("github.com/")[-1]
    codespaces = f"https://codespaces.new/{owner_repo}"
    binder = f"https://mybinder.org/v2/gh/{owner_repo}/{branch}"

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
{font_face}
:root{{--ink:#12263f;--muted:#5b7089;--line:#e2e8f0;--accent:#0f766e;--bg:#f7f9fc;}}
*{{box-sizing:border-box;}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:Vazirmatn,Tahoma,system-ui,sans-serif;line-height:1.9;}}
header{{background:linear-gradient(135deg,#0f766e,#115e59);color:#fff;padding:2.6rem 1.4rem;}}
header .wrap,.page{{max-width:1080px;margin:0 auto;}}
h1{{margin:0 0 .4rem;font-size:1.9rem;}}
header p{{margin:0;opacity:.92;}}
.page{{padding:1.6rem 1.4rem 3rem;}}
h2{{margin:2.4rem 0 .9rem;font-size:1.35rem;border-right:5px solid var(--accent);padding-right:.6rem;}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:.9rem;}}
.card{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:.9rem 1rem;}}
.card-label{{margin:0;color:var(--muted);font-size:.9rem;}}
.card-value{{margin:.25rem 0 0;font-size:1.35rem;font-weight:700;}}
.card-detail{{margin:.35rem 0 0;color:var(--muted);font-size:.83rem;}}
ul.findings{{list-style:none;padding:0;margin:0;display:grid;gap:.9rem;}}
ul.findings li{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:1rem 1.1rem;}}
ul.findings h3{{margin:0 0 .35rem;font-size:1.05rem;color:var(--accent);}}
ul.findings p{{margin:0;}}
.figures{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:1rem;}}
figure{{margin:0;background:#fff;border:1px solid var(--line);border-radius:14px;padding:.7rem;}}
figure img{{width:100%;height:auto;border-radius:10px;display:block;}}
figcaption{{color:var(--muted);font-size:.85rem;padding:.5rem .2rem 0;}}
table.tables{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;font-size:.9rem;}}
table.tables th,table.tables td{{border-bottom:1px solid var(--line);padding:.5rem .7rem;text-align:right;}}
a{{color:var(--accent);}}
.cta{{display:flex;flex-wrap:wrap;gap:.7rem;margin-top:.8rem;}}
.cta a{{display:inline-block;background:#fff;border:1px solid var(--accent);border-radius:999px;padding:.45rem 1rem;text-decoration:none;}}
code{{background:#eef2f7;border-radius:6px;padding:.1rem .4rem;font-family:ui-monospace,Consolas,monospace;direction:ltr;display:inline-block;}}
pre{{background:#12263f;color:#e6edf3;padding:.9rem 1rem;border-radius:12px;overflow-x:auto;direction:ltr;text-align:left;}}
.empty{{color:var(--muted);}}
footer{{color:var(--muted);font-size:.85rem;border-top:1px solid var(--line);margin-top:2.4rem;padding-top:1rem;}}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <h1>{escape(title)}</h1>
    <p>{subtitle}</p>
  </div>
</header>
<main class="page">

  <h2>شاخص‌های کلیدی</h2>
  <div class="cards">
{cards}
  </div>

  <h2>پنج یافته مهم</h2>
  <ul class="findings">
{findings}
  </ul>

  <h2>اجرای کامل پروژه از گیت‌هاب</h2>
  <p>برای اجرای کل خط لوله، آزمون‌ها و نوتبوک‌ها نیازی به نصب چیزی روی رایانه نیست:</p>
  <pre>python scripts/run_all.py</pre>
  <div class="cta">
    <a href="{codespaces}">باز کردن در GitHub Codespaces</a>
    <a href="{binder}">اجرای زنده در Binder</a>
    <a href="{repo}">مخزن پروژه</a>
  </div>

  <h2>دانلود خروجی‌ها</h2>
  <ul>
{chr(10).join(downloads) if downloads else '<li class="empty">خروجی‌ای یافت نشد.</li>'}
  </ul>

  <h2>نوتبوک‌های تحلیل</h2>
  {notebooks or '<p class="empty">نوتبوکی یافت نشد.</p>'}

  <h2>نمودارها</h2>
  <div class="figures">
{figures}
  </div>

  <h2>جدول‌های تحلیل</h2>
  {tables}

  <footer>
    ساخته‌شده با <code>python scripts/build_site.py</code> از خروجی واقعی خط لوله —
    کامیت {escape(commit)} — {generated}
  </footer>
</main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the static results site")
    parser.add_argument("--output", default="site", help="output directory")
    parser.add_argument("--title", default=TITLE)
    parser.add_argument("--subtitle", default=SUBTITLE)
    parser.add_argument("--repo-url", default=None)
    parser.add_argument("--branch", default=None)
    args = parser.parse_args()

    if not METRICS_FILE.exists():
        print(f"missing {METRICS_FILE}; run scripts/run_all.py first")
        return 2

    metrics = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    output_dir = (PROJECT_ROOT / args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    html = render(
        metrics,
        output_dir,
        args.title,
        args.subtitle,
        args.repo_url or repo_url(),
        args.branch or current_branch(),
    )
    (output_dir / "index.html").write_text(html, encoding="utf-8")
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    print(f"site written to {output_dir}")
    print(f"figures: {len(list(FIGURES_DIR.glob('fig_*.png')))}")
    print(f"tables: {len(list(TABLES_DIR.glob('*.csv')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
