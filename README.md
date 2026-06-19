# Wash trading on a fixed clock: CBK/USDT (May 2026)

![python](https://img.shields.io/badge/python-3.10+-3776ab?logo=python&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-5%2F5_pass-3fb950)
![reproducible](https://img.shields.io/badge/numbers-verify.py_reproduces-3fb950)
![data](https://img.shields.io/badge/data-free_%2F_key--less-3fb950)
[![tests](https://github.com/mkzung/cbk-scheduled-wash-analysis/actions/workflows/test.yml/badge.svg)](https://github.com/mkzung/cbk-scheduled-wash-analysis/actions/workflows/test.yml)

Market-health analysis for the DN Institute wiki (Market Manipulation challenge, issue #277).
CBK/USDT churned about $448k on Bybit spot in May 2026 with no pump or sustained trend, but 75% of
its trades fired on just two seconds of the minute, one all sells (:05), the other all buys (:35).
A self-trading bot firing every 90 seconds, alternating side, randomising size to defeat clip
detection but not its schedule.

**Live dashboard:** https://mkzung.github.io/cbk-scheduled-wash-analysis/

## Finding

- 36,890 trades, May 2026; price drifts in a 17% band and ends near where it started (no pump), about $448k churned.
- 74.6% of trades and 59.6% of volume on two seconds, :05 and :35, about 22x a uniform clock.
- Fixed cadence: one trade every 90 seconds (median), alternating buy and sell, each landing within a ~130ms sub-second window; 90s is 1.5 minutes, so consecutive trades fall alternately on :05 (sells) and :35 (buys).
- Second :05 is 98.8% sells, second :35 is 99.4% buys; the legs match ($133.1k sold vs $129.7k bought).
- Over the month buying ($228.6k) and selling ($219.7k) are within about 4%: almost no net position, the signature of a wash.
- Not a market maker: drift-controlled, it buys about 0.4% above its own sells (positive in nearly every hour) and pays fees, so it loses several hundred dollars in May. It pays the spread instead of earning it; the loss is the cost of faking volume.
- No dominant clip (most common size 0.5% of trades; 2,287 distinct sizes on the buy second): it evades clip and first-digit detection.
- Persistent: 47 to 91% of each day's trades on the two seconds (median 79%), all 31 days, in all 24 hours; the same signature runs in April too. Two unrelated controls (GAIB, BOBA) stay near 3% on these seconds, so it is CBK-specific, not a venue artifact.
- Read this as a flag, not a verdict.

## Layout

    post/index.md                 the wiki submission (Hugo page bundle)
    post/*.png                    4 figures referenced by index.md
    data/*.csv                    processed datasets (second-of-minute dist, buy/sell by second, daily OHLCV, daily share)
    analysis/cbklib.py            shared key-less Bybit loader (header-robust)
    analysis/build_analysis.py    compute findings.json and render the 4 figures
    analysis/verify.py            independently recompute the numbers and assert the headline ones
    dashboard/build_dashboard.py  render the self-contained index.html / dashboard.html
    tests/test_logic.py           loader unit tests
    findings.json                 the computed numbers
    index.html, dashboard.html    self-contained dashboard (GitHub Pages)

## Reproduce

    pip install -r requirements.txt
    python analysis/build_analysis.py     # findings.json + datasets + 4 figures
    python analysis/verify.py             # independent recompute, asserts the headline numbers
    python dashboard/build_dashboard.py   # regenerate the dashboard
    pytest -q

Data source: Bybit public spot trade dumps (public.bybit.com/spot/CBKUSDT/, plus GAIBUSDT as an
organic-timing control), May 2026, free and key-less.

## Submission

The article in post/ goes to 1712n/dn-institute as
content/research/market-health/posts/2026-05-31-cbk-scheduled-wash/, with a review request to the
issue assignee.
