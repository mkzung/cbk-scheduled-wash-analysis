"""Build a self-contained dark-theme dashboard (index.html + dashboard.html) for the CBK post.

Embeds the four figures as base64 so the page is a single file with no external assets, reads the
computed numbers from findings.json, and reconstructs a sample-minute tape from the cached dump.
"""
import os, sys, json, base64
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import pandas as pd
from cbklib import load

F = json.load(open(os.path.join(ROOT, "findings.json")))


def b64(name):
    with open(os.path.join(ROOT, "post", name), "rb") as f:
        return base64.b64encode(f.read()).decode()


fig = {n: b64(n) for n in ["price-volume.png", "second-of-minute.png", "buysell-by-second.png", "persistence.png"]}


def usd(x):
    return "$%.1fM" % (x / 1e6) if x >= 1e6 else ("$%.1fk" % (x / 1e3) if x >= 1e3 else "$%.0f" % x)


# sample-minute tape: the bot's :05 / :35 trades across a few consecutive minutes
df = load("CBKUSDT", "2026-05")
s_sell, s_buy = F["sec_sell"], F["sec_buy"]
w0 = pd.Timestamp("2026-05-15 12:00", tz="UTC")
win = df[(df.t >= w0) & (df.t < w0 + pd.Timedelta(minutes=20)) & (df.sec.isin([s_sell, s_buy]))].copy()
win = win.sort_values("t").head(14)
rows = "".join(
    '<tr><td class="txt">%s</td><td class="txt %s">%s</td><td class="num">%.6f</td><td class="num">%s</td></tr>'
    % (r.t.strftime("%H:%M:%S"), "buy" if r.side == "buy" else "sell", r.side, r.price, usd(r.notional))
    for _, r in win.iterrows())
sell_pct = (1 - F["sec_sell_buyshare"]) * 100

CSS = """
:root{--bg:#0e1116;--panel:#161b22;--panel-2:#1c232c;--border:#2d333b;--text:#e6edf3;--muted:#8b949e;
--accent:#58a6ff;--accent-2:#f0883e;--good:#3fb950;--bad:#f85149;--warn:#d29922;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;}
*,*::before,*::after{box-sizing:border-box;}
body{background:var(--bg);color:var(--text);font-family:var(--sans);margin:0;line-height:1.55;}
a{color:var(--accent);text-decoration:none;} a:hover{text-decoration:underline;}
header{border-bottom:1px solid var(--border);padding:32px 48px;background:linear-gradient(180deg,#161b22 0%,#0e1116 100%);}
header h1{margin:0 0 8px 0;font-size:24px;font-weight:600;}
header .meta{color:var(--muted);font-size:14px;}
main{padding:28px 48px;max-width:1180px;margin:0 auto;}
.lead{font-size:16px;margin:0 0 24px 0;} .lead strong{color:var(--accent-2);}
.grid{display:grid;gap:16px;grid-template-columns:repeat(3,1fr);}
@media(max-width:900px){.grid{grid-template-columns:1fr;}main,header{padding:20px 16px;}}
.stat{background:var(--panel);border:1px solid var(--border);padding:18px 20px;border-radius:10px;}
.stat .label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:0.4px;}
.stat .value{font-size:26px;font-weight:700;margin-top:4px;font-family:var(--mono);}
.stat .sub{color:var(--muted);font-size:12px;margin-top:4px;}
.stat.bad .value{color:var(--bad);} .stat.good .value{color:var(--good);} .stat.warn .value{color:var(--warn);} .stat.accent .value{color:var(--accent-2);}
section{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:22px 26px;margin:18px 0;}
section h2{margin:0 0 6px 0;font-size:18px;font-weight:600;}
section .sub{color:var(--muted);font-size:14px;margin-bottom:14px;}
.figure{background:white;border:1px solid var(--border);border-radius:8px;padding:8px;margin:6px 0;text-align:center;}
.figure img{max-width:100%;height:auto;display:block;margin:0 auto;}
table{width:100%;border-collapse:collapse;margin:6px 0;font-size:13.5px;}
th,td{border-bottom:1px solid var(--border);text-align:left;padding:7px 12px;}
th{color:var(--muted);font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:0.4px;}
td.num{font-family:var(--mono);text-align:right;} td.txt{font-family:var(--mono);}
td.buy{color:var(--good);} td.sell{color:var(--bad);}
.keyfindings{background:linear-gradient(135deg,#1c232c 0%,#161b22 100%);border-left:3px solid var(--accent-2);}
.keyfindings h2{color:var(--accent-2);}
footer{color:var(--muted);font-size:13px;padding:22px 48px;border-top:1px solid var(--border);margin-top:28px;}
"""

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>CBK/USDT scheduled wash, May 2026 | Market Health</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{CSS}</style></head><body>
<header>
  <h1>CBK/USDT: wash trading on a fixed clock</h1>
  <div class="meta">Submission to the DN Institute Market Manipulation Wiki (issue #277) |
    <a href="https://github.com/mkzung/cbk-scheduled-wash-analysis">github.com/mkzung/cbk-scheduled-wash-analysis</a> | Max Gorbuk<br>
    Free, key-less Bybit public spot dumps | {F["n_trades"]:,} trades | May 2026</div>
</header>
<main>
<p class="lead">CBK (Cobak Token) churned about <strong>{usd(F["month_usd"])}</strong> in May 2026 with no pump or sustained trend,
yet <strong>{F["two_sec_trade_share"]*100:.0f}%</strong> of its trades fired on just two seconds of the minute,
one all sells (:{F["sec_sell"]:02d}), the other all buys (:{F["sec_buy"]:02d}). A self-trading bot firing every
{int(round(F["median_gap_s"]))} seconds, alternating side, randomising size to defeat clip detection but not its schedule.</p>

<div class="grid">
  <div class="stat accent"><div class="label">Trades on two seconds</div><div class="value">{F["two_sec_trade_share"]*100:.0f}%</div><div class="sub">on :{F["sec_sell"]:02d} (sells) and :{F["sec_buy"]:02d} (buys)</div></div>
  <div class="stat warn"><div class="label">Trade cadence</div><div class="value">{int(round(F["median_gap_s"]))}s</div><div class="sub">one trade every {int(round(F["median_gap_s"]))}s, alternating buy/sell</div></div>
  <div class="stat bad"><div class="label">Second :{F["sec_sell"]:02d}</div><div class="value">{sell_pct:.0f}% sells</div><div class="sub">{usd(F["sec_sell_sell_usd"])} sold on this second</div></div>
  <div class="stat good"><div class="label">Second :{F["sec_buy"]:02d}</div><div class="value">{F["sec_buy_buyshare"]*100:.0f}% buys</div><div class="sub">{usd(F["sec_buy_buy_usd"])} bought 30s later</div></div>
  <div class="stat accent"><div class="label">No pump</div><div class="value">~flat</div><div class="sub">{usd(F["month_usd"])} churned; price range-bound ({F["month_range_pct"]*100:.0f}%)</div></div>
  <div class="stat warn"><div class="label">Always on</div><div class="value">{F["day_two_sec_med"]*100:.0f}%</div><div class="sub">median daily share, every day of May</div></div>
</div>

<section class="keyfindings"><h2>What the data says</h2>
<ol>
<li><b>A scheduler, not demand.</b> {F["two_sec_trade_share"]*100:.0f}% of all trades and {F["two_sec_vol_share"]*100:.0f}% of volume land on :{F["sec_sell"]:02d} and :{F["sec_buy"]:02d}, about {F["ratio_vs_uniform"]:.0f}x a uniform clock: one trade every {int(round(F["median_gap_s"]))} seconds, alternating side, each within a ~{int(F["ms_window_ms"])}ms sub-second window. Two unrelated controls (GAIB, BOBA) stay flat near the 1.7% uniform line, so this is specific to CBK.</li>
<li><b>Two-sided self-wash.</b> Second :{F["sec_sell"]:02d} is {sell_pct:.0f}% sells, second :{F["sec_buy"]:02d} is {F["sec_buy_buyshare"]*100:.0f}% buys; the {int(round(F["median_gap_s"]))}-second cadence lands each side on its own second. The legs match: {usd(F["sec_buy_buy_usd"])} bought vs {usd(F["sec_sell_sell_usd"])} sold.</li>
<li><b>Almost no net position, and it loses money.</b> Over the month buying ({usd(F["buy_usd"])}) and selling ({usd(F["sell_usd"])}) are within about 4%. It pays the spread each round trip (buys ~{F["spread_paid_pct"]*100:.1f}% above its sells), so it loses money rather than earning it like a real market maker: turnover without exposure.</li>
<li><b>It hides its size, not its clock.</b> The most common trade size is just {F["modal_clip_share"]*100:.1f}% of trades ({F["size_nunique_at_buy"]:,} distinct sizes on the buy second), so it slips past clip and first-digit detection, but time-of-trade catches it.</li>
<li><b>Read it as a flag, not a verdict</b>: the time-of-trade and buy/sell signatures of a scheduled wash bot, not an attribution of intent.</li>
</ol></section>

<section><h2>Volume without a pump</h2>
<div class="sub">Daily close and daily volume. The price drifts in a band and ends near where it started while {usd(F["month_usd"])} churns: no directional move, just turnover.</div>
<div class="figure"><img src="data:image/png;base64,{fig['price-volume.png']}" alt="price and volume"></div></section>

<section><h2>The tell: two seconds of the minute</h2>
<div class="sub">An organic market spreads trades across all 60 seconds (the control stays near 1.7%). CBK puts {F["two_sec_trade_share"]*100:.0f}% on :{F["sec_sell"]:02d} and :{F["sec_buy"]:02d}.</div>
<div class="figure"><img src="data:image/png;base64,{fig['second-of-minute.png']}" alt="second of minute distribution"></div></section>

<section><h2>Two-sided self-wash</h2>
<div class="sub">Buy share by second. Second :{F["sec_sell"]:02d} is almost all sells, second :{F["sec_buy"]:02d} almost all buys; a {int(round(F["median_gap_s"]))}-second alternating bot lands each side on its own second.</div>
<div class="figure"><img src="data:image/png;base64,{fig['buysell-by-second.png']}" alt="buy share by second"></div></section>

<section><h2>Always on</h2>
<div class="sub">Share of each day's trades on the two seconds, every day of May, in all 24 hours. Never below 47%, median {F["day_two_sec_med"]*100:.0f}%, against a 3.3% uniform expectation; the same signature also runs in April.</div>
<div class="figure"><img src="data:image/png;base64,{fig['persistence.png']}" alt="daily persistence"></div></section>

<section><h2>The clock on the tape</h2>
<div class="sub">The bot's trades on :{F["sec_sell"]:02d} (sell) and :{F["sec_buy"]:02d} (buy) over a sample window on 2026-05-15: one trade every {int(round(F["median_gap_s"]))} seconds, alternating a sell on :{F["sec_sell"]:02d} and a buy on :{F["sec_buy"]:02d}.</div>
<table><thead><tr><th>time (UTC)</th><th>side</th><th>price</th><th>size (USD)</th></tr></thead><tbody>{rows}</tbody></table></section>

<footer>Data: Bybit public spot trade dumps (public.bybit.com/spot/CBKUSDT/), May 2026, free and key-less.
Control: GAIB/USDT. Reproducible: see the companion repository.</footer>
</main></body></html>"""

for name in ("index.html", "dashboard.html"):
    open(os.path.join(ROOT, name), "w").write(HTML)
print("wrote index.html + dashboard.html (%d bytes), %d tape rows" % (len(HTML), len(win)))
