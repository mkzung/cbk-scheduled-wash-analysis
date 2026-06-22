"""Independently recompute every number cited in post/index.md from the Bybit dumps."""
import numpy as np
import pandas as pd
from cbklib import load

df = load("CBKUSDT", "2026-05")
ctrl = load("GAIBUSDT", "2026-05")
n = len(df)
sec = df.sec.value_counts(normalize=True)
top2 = sorted(sec.index[:2].tolist())
buyshare_sec = df.assign(b=(df.side == "buy").astype(int)).groupby("sec").b.mean()
s_buy = max(top2, key=lambda s: buyshare_sec[s])
s_sell = min(top2, key=lambda s: buyshare_sec[s])
two = df[df.sec.isin(top2)]
two_share = len(two) / n
two_vol = two.notional.sum() / df.notional.sum()
buy_usd = float(df[df.side == "buy"].notional.sum())
sell_usd = float(df[df.side == "sell"].notional.sum())
sec_buy_buy = float(df[(df.sec == s_buy) & (df.side == "buy")].notional.sum())
sec_sell_sell = float(df[(df.sec == s_sell) & (df.side == "sell")].notional.sum())
month_range = df.price.max() / df.price.min() - 1
clip = df.volume.value_counts().iloc[0] / n
csec = float(ctrl.sec.value_counts(normalize=True).iloc[0])
dayshare = df.assign(intwo=df.sec.isin(top2).astype(int)).groupby(df.t.dt.date).intwo.mean()
botv = df[df.sec.isin(top2)].sort_values("t")
gap_med = float(botv.t.diff().dt.total_seconds().dropna().median())
alt = float((botv.side.values[1:] != botv.side.values[:-1]).mean())
ms_v = botv.timestamp % 1000
ms_window = float(ms_v.quantile(0.9) - ms_v.quantile(0.1))
_bbv = df[df.sec.isin(top2)].copy(); _bbv["_h"] = _bbv.t.dt.floor("h")
_hspv = []
for _h, _d in _bbv.groupby("_h"):
    _s = _d[_d.sec == s_sell]; _b = _d[_d.sec == s_buy]
    if len(_s) and len(_b):
        _hspv.append((_b.notional.sum() / _b.volume.sum()) / (_s.notional.sum() / _s.volume.sum()) - 1)
spread_v = float(np.median(_hspv)); spread_pos = float(np.mean([x > 0 for x in _hspv]))
hours_v = int(df[df.sec.isin(top2)].t.dt.hour.nunique())
apr_share = float(load("CBKUSDT", "2026-04").sec.isin(top2).mean())
ctrl2_share = float(load("BOBAUSDT", "2026-05").sec.isin(top2).mean())

print("trades:", n, "| price %.4f..%.4f (month range %.0f%%)" % (df.price.min(), df.price.max(), month_range * 100))
print("modal seconds: sells on :%02d (buyshare %.3f), buys on :%02d (buyshare %.3f), %ds apart"
      % (s_sell, buyshare_sec[s_sell], s_buy, buyshare_sec[s_buy], abs(s_buy - s_sell)))
print("two-second share: %.1f%% of trades, %.1f%% of volume (vs %.1f%% uniform); %.0fx uniform"
      % (two_share * 100, two_vol * 100, 2 / 60 * 100, two_share / (2 / 60)))
print("matched legs: buys on :%02d $%.0f vs sells on :%02d $%.0f" % (s_buy, sec_buy_buy, s_sell, sec_sell_sell))
print("overall balance: buy $%.0f vs sell $%.0f (buyshare %.3f)" % (buy_usd, sell_usd, (df.side == "buy").mean()))
print("no dominant clip: modal size = %.3f%% of trades; control :%02d share %.1f%%" % (clip * 100, int(ctrl.sec.value_counts().index[0]), csec * 100))
print("persistence: two-second share per day %.0f%%..%.0f%% (median %.0f%%)" % (dayshare.min() * 100, dayshare.max() * 100, dayshare.median() * 100))
print("cadence: median inter-trade gap %.0fs, side alternation %.0f%%" % (gap_med, alt * 100))
print("sub-second: trades cluster within a %.0fms window (p10-p90) at the same mark" % ms_window)
print("wash vs MM: buys on :%02d execute %+.2f%% vs sells on :%02d (per-hour median, drift-controlled; positive in %.0f%% of hours => pays spread => loses money)" % (s_buy, spread_v * 100, s_sell, spread_pos * 100))
print("robustness: hours active %d/24 | April :05+:35 share %.1f%% | control BOBA share %.1f%%" % (hours_v, apr_share * 100, ctrl2_share * 100))

assert len(top2) == 2 and abs(s_buy - s_sell) in (30,), "expected two seconds 30s apart"
assert two_share > 0.6, "two-second share too low"
assert buyshare_sec[s_buy] > 0.9 and buyshare_sec[s_sell] < 0.1, "not a clean one-side-per-second split"
assert abs(sec_buy_buy / sec_sell_sell - 1) < 0.2, "the two legs are not matched (not self-wash)"
assert abs(buy_usd / sell_usd - 1) < 0.2, "overall buy/sell not balanced"
assert clip < 0.05, "a dominant clip exists -> that would be clip-wash (see #1180), not timing"
assert csec < 0.1, "control also clusters -> not a clean control"
assert month_range < 0.5, "price moved too much -> that would be a pump, not wash"
assert dayshare.min() > 0.3, "the pattern is not persistent across the month"
assert apr_share > 0.6, "April :05+:35 share too low -> multi-month persistence not confirmed"
assert 85 <= gap_med <= 95, "cadence is not the expected ~90s"
assert alt > 0.8, "sides do not alternate"
assert ms_window < 250, "sub-second timing is not tight"
assert two_vol > 0.5, "two-second volume share too low"
assert df[df.sec == s_buy].volume.nunique() > 1000, "buy-second sizes not varied (would be a fixed clip, not randomised)"
assert spread_v > 0.002 and spread_pos > 0.9, "operator does not consistently pay a spread (drift-controlled) -> not a loss-making wash"
assert hours_v == 24, "bot not active around the clock"
assert apr_share > 0.4, "prior month (April) does not show the same concentration"
assert ctrl2_share < 0.1, "second control (BOBA) also clusters on these seconds"
print("\nALL CHECKS PASS")
