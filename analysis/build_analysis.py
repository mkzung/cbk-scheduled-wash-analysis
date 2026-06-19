"""Reconstruct the CBK/USDT scheduled wash bot (May 2026) from free Bybit public spot dumps.

Computes every figure cited in post/index.md into findings.json, writes processed datasets to
../data, and renders the figures into ../post. Key-less and deterministic. See cbklib.py.
"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cbklib import load

HERE = os.path.dirname(os.path.abspath(__file__))
POST = os.path.join(HERE, "..", "post"); os.makedirs(POST, exist_ok=True)
DATA = os.path.join(HERE, "..", "data"); os.makedirs(DATA, exist_ok=True)
ACC, CTL, GREY, BUY, SELL = "#d9480f", "#1c7ed6", "#adb5bd", "#2f9e44", "#e03131"

df = load("CBKUSDT", "2026-05")
ctrl = load("GAIBUSDT", "2026-05")   # a comparably active low-cap pair, organic timing control
n = len(df)

sec = df.sec.value_counts(normalize=True)
top2 = sorted(sec.index[:2].tolist())                       # the two dominant seconds, e.g. [5, 35]
buyshare_sec = df.assign(b=(df.side == "buy").astype(int)).groupby("sec").b.mean()
s_buy = max(top2, key=lambda s: buyshare_sec[s])            # the second that is almost all buys
s_sell = min(top2, key=lambda s: buyshare_sec[s])           # the second that is almost all sells
two = df[df.sec.isin(top2)]

g = df.set_index("t").resample("1D").agg(o=("price", "first"), h=("price", "max"), l=("price", "min"),
                                         c=("price", "last"), v=("notional", "sum")).dropna()
dayshare = df.assign(intwo=df.sec.isin(top2).astype(int)).groupby(df.t.dt.date).intwo.mean()
csec = ctrl.sec.value_counts(normalize=True)
# cadence: the bot's trades on the two seconds fire on a fixed period, alternating side
_bot = df[df.sec.isin(top2)].sort_values("t")
_gaps = _bot.t.diff().dt.total_seconds().dropna()
median_gap_s = float(_gaps.median())
alternation_share = float((_bot.side.values[1:] != _bot.side.values[:-1]).mean())
# sub-second precision: the bot's trades land at a near-constant millisecond offset in the second
_ms = _bot.timestamp % 1000
ms_median = float(_ms.median()); ms_window_ms = float(_ms.quantile(0.9) - _ms.quantile(0.1))
# wash vs market-maker: the operator buys above its own sells (pays the spread) -> loses money.
# Spread is measured per-hour and then median-aggregated, so the month's price drift cannot inflate it.
_sells = df[df.sec == s_sell]; _buys = df[df.sec == s_buy]
_bb = df[df.sec.isin(top2)].copy(); _bb["_h"] = _bb.t.dt.floor("h")
_hsp = []
for _h, _d in _bb.groupby("_h"):
    _s = _d[_d.sec == s_sell]; _b = _d[_d.sec == s_buy]
    if len(_s) and len(_b):
        _hsp.append((_b.notional.sum() / _b.volume.sum()) / (_s.notional.sum() / _s.volume.sum()) - 1)
spread_paid_pct = float(np.median(_hsp))
spread_hours_positive = float(np.mean([x > 0 for x in _hsp]))
est_wash_cost_usd = spread_paid_pct * min(_sells.notional.sum(), _buys.notional.sum()) + (_sells.notional.sum() + _buys.notional.sum()) * 0.001
hours_active = int(_bot.t.dt.hour.nunique())
# robustness: same signature the prior month + a second, unrelated low-cap control
apr_two_sec_share = float(load("CBKUSDT", "2026-04").sec.isin(top2).mean())
control2_two_sec_share = float(load("BOBAUSDT", "2026-05").sec.isin(top2).mean())

F = dict(
    symbol="CBKUSDT", month="2026-05", n_trades=int(n),
    price_min=round(float(df.price.min()), 6), price_max=round(float(df.price.max()), 6),
    max_daily_range_pct=round(float((g.h / g.l - 1).max()), 3),
    month_range_pct=round(float(df.price.max() / df.price.min() - 1), 3),
    net_change_pct=round(float(g.c.iloc[-1] / g.c.iloc[0] - 1), 3),
    month_usd=round(float(df.notional.sum()), 0), median_daily_usd=round(float(g.v.median()), 0),
    sec_buy=int(s_buy), sec_sell=int(s_sell), gap_seconds=int(abs(s_buy - s_sell)),
    median_gap_s=round(median_gap_s, 1), alternation_share=round(alternation_share, 3),
    ms_median=round(ms_median, 0), ms_window_ms=round(ms_window_ms, 0),
    spread_paid_pct=round(spread_paid_pct, 4), spread_hours_positive=round(spread_hours_positive, 3), est_wash_cost_usd=round(est_wash_cost_usd, 0), hours_active=hours_active,
    apr_two_sec_share=round(apr_two_sec_share, 3), control2_sym="BOBAUSDT", control2_two_sec_share=round(control2_two_sec_share, 3),
    sec_buy_share=round(float(sec[s_buy]), 3), sec_sell_share=round(float(sec[s_sell]), 3),
    two_sec_trade_share=round(float(len(two) / n), 3),
    two_sec_vol_share=round(float(two.notional.sum() / df.notional.sum()), 3),
    sec_buy_buyshare=round(float(buyshare_sec[s_buy]), 3), sec_sell_buyshare=round(float(buyshare_sec[s_sell]), 3),
    sec_buy_buy_usd=round(float(df[(df.sec == s_buy) & (df.side == "buy")].notional.sum()), 0),
    sec_sell_sell_usd=round(float(df[(df.sec == s_sell) & (df.side == "sell")].notional.sum()), 0),
    overall_buyshare=round(float((df.side == "buy").mean()), 3),
    buy_usd=round(float(df[df.side == "buy"].notional.sum()), 0), sell_usd=round(float(df[df.side == "sell"].notional.sum()), 0),
    modal_clip_share=round(float(df.volume.value_counts().iloc[0] / n), 3),
    size_nunique_at_buy=int(df[df.sec == s_buy].volume.nunique()),
    control_sym="GAIBUSDT", control_modal_sec_share=round(float(csec.iloc[0]), 3), uniform_sec_share=round(1 / 60, 4),
    ratio_vs_uniform=round(float((len(two) / n) / (2 / 60)), 1),
    days=int(len(dayshare)), day_two_sec_min=round(float(dayshare.min()), 3),
    day_two_sec_med=round(float(dayshare.median()), 3), day_two_sec_max=round(float(dayshare.max()), 3))
json.dump(F, open(os.path.join(HERE, "..", "findings.json"), "w"), indent=2)
for k, v in F.items():
    print("%-24s %s" % (k, v))

# committed processed datasets
sectbl = pd.DataFrame({"trades": df.sec.value_counts().sort_index(),
                       "share": df.sec.value_counts(normalize=True).sort_index()})
sectbl.index.name = "second_of_minute"; sectbl.round(6).to_csv(os.path.join(DATA, "second_of_minute_distribution.csv"))
bys = pd.DataFrame({"trades": df.groupby("sec").size(),
                    "buyshare": buyshare_sec,
                    "buy_usd": df[df.side == "buy"].groupby("sec").notional.sum(),
                    "sell_usd": df[df.side == "sell"].groupby("sec").notional.sum()}).fillna(0.0)
bys.index.name = "second_of_minute"; bys.round(4).to_csv(os.path.join(DATA, "buysell_by_second.csv"))
g.round(8).to_csv(os.path.join(DATA, "daily_ohlcv.csv"))
dayshare.rename("two_second_share").round(4).to_csv(os.path.join(DATA, "daily_two_second_share.csv"))
print("wrote 4 processed datasets to", os.path.abspath(DATA))

# fig 1: second-of-minute distribution, CBK vs control vs uniform
allsec = pd.Series(0.0, index=range(60)); allsec.update(sec * 100)
csec_full = pd.Series(0.0, index=range(60)); csec_full.update(csec * 100)
fig, ax = plt.subplots(figsize=(9, 4))
ax.bar(allsec.index, allsec.values, color=ACC, width=0.9, label="CBK/USDT")
ax.plot(csec_full.index, csec_full.values, color=CTL, lw=1.4, label="GAIB/USDT (control)")
ax.axhline(100 / 60, ls="--", color="grey", lw=1, label="uniform (1.67%)")
ax.set_xlabel("second of the minute (UTC)"); ax.set_ylabel("share of trades (%)")
ax.set_title("CBK/USDT puts %.0f%% of trades on two seconds (:%02d and :%02d); an organic market is flat"
             % (F["two_sec_trade_share"] * 100, s_sell, s_buy))
ax.legend(); fig.tight_layout(); fig.savefig(os.path.join(POST, "second-of-minute.png"), dpi=120); plt.close()

# fig 2: buy share by second of minute
bsx = buyshare_sec.reindex(range(60)) * 100
colors = [SELL if (s == s_sell) else (BUY if s == s_buy else GREY) for s in range(60)]
fig, ax = plt.subplots(figsize=(9, 4))
ax.bar(range(60), bsx.fillna(0).values, color=colors, width=0.9)
ax.axhline(50, ls="--", color="grey", lw=1, label="balanced (50%)")
ax.set_xlabel("second of the minute (UTC)"); ax.set_ylabel("buy share (%)")
ax.set_title("Two-sided self-wash: a %ds-cadence bot, sells on :%02d and buys on :%02d" % (int(round(median_gap_s)), s_sell, s_buy))
ax.legend(loc="upper left"); fig.tight_layout(); fig.savefig(os.path.join(POST, "buysell-by-second.png"), dpi=120); plt.close()

# fig 3: persistence across the month
dd = dayshare.copy(); dd.index = pd.to_datetime(dd.index)
fig, ax = plt.subplots(figsize=(9, 4))
ax.bar(dd.index, dd.values * 100, color=ACC, width=0.7)
ax.axhline(dd.median() * 100, ls="--", color="black", lw=1, label="median %.0f%%" % (dd.median() * 100))
ax.axhline(100 * 2 / 60, ls=":", color="grey", lw=1, label="uniform, 2 of 60 sec (3.3%)")
ax.set_ylabel("daily trades on :%02d + :%02d (%%)" % (s_sell, s_buy)); ax.set_xlabel("day (UTC), May 2026")
ax.set_title("Always on: %.0f to %.0f%% of each day's trades land on the same two seconds"
             % (dd.min() * 100, dd.max() * 100))
ax.legend(loc="lower right"); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(os.path.join(POST, "persistence.png"), dpi=120); plt.close()

# fig 4: volume without price (wash, not pump)
fig, ax1 = plt.subplots(figsize=(9, 4)); ax2 = ax1.twinx()
ax2.bar(g.index, g.v, width=0.7, color=GREY, alpha=0.55); ax2.set_ylabel("daily volume (USD)")
ax1.plot(g.index, g.c, color=ACC, lw=1.8); ax1.set_ylabel("CBK/USDT close (USDT)")
ax1.set_xlabel("day (UTC), May 2026")
ax1.set_title("Volume without a pump: about $%.0fk churned; price range-bound in a %.0f%% band"
              % (df.notional.sum() / 1e3, F["month_range_pct"] * 100))
ax1.set_zorder(2); ax1.patch.set_visible(False); fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(os.path.join(POST, "price-volume.png"), dpi=120); plt.close()
print("wrote 4 figures to", os.path.abspath(POST))
