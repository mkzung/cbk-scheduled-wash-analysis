"""Shared, key-less loader for the CBK/USDT scheduled-wash analysis (Bybit public spot dumps)."""
import io, gzip, math, os
import requests, pandas as pd

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")


def lastpx(sym, session=None):
    s = session or requests
    j = s.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=%s" % sym, timeout=30).json()
    return float(j["result"]["list"][0]["lastPrice"])


def normalize(df, lp):
    """Map a Bybit spot dump to timestamp/price/volume/side, robust to header misalignment.

    The monthly dumps ship a header that does not line up with the columns, so we detect by
    content: the side column holds buy/sell, the timestamp column is the ms-epoch integer, and
    price versus size are told apart by magnitude against the current last price `lp`.
    """
    side_col = next((c for c in df.columns if df[c].astype(str).str.lower().isin(["buy", "sell"]).mean() > 0.8), None)
    if side_col is None:
        raise ValueError("no buy/sell side column found")
    num = {c: pd.to_numeric(df[c], errors="coerce") for c in df.columns if c != side_col}
    num = {c: s for c, s in num.items() if s.notna().mean() > 0.9}
    ts = next((c for c, s in num.items() if s.median() > 1e11), None)
    rem = [c for c in num if c != ts]
    if ts is None or len(rem) < 2:
        raise ValueError("could not locate timestamp / price / volume columns")
    pc = min(rem, key=lambda c: abs(math.log10(max(num[c].median(), 1e-12)) - math.log10(max(lp, 1e-12))))
    # volume is the most-varied remaining column, never a constant flag (e.g. the dir column);
    # robust to column reordering, unlike taking the first remaining column.
    vc = max((c for c in rem if c != pc), key=lambda c: num[c].nunique())
    return pd.DataFrame({"timestamp": num[ts].astype("int64"), "price": num[pc],
                         "volume": num[vc], "side": df[side_col].astype(str).str.lower()})


def load(sym="CBKUSDT", month="2026-05"):
    os.makedirs(CACHE, exist_ok=True)
    cf = os.path.join(CACHE, "%s_%s.csv.gz" % (sym, month))
    if os.path.exists(cf):
        df = pd.read_csv(cf)
    else:
        s = requests.Session()
        r = s.get("https://public.bybit.com/spot/%s/%s-%s.csv.gz" % (sym, sym, month), timeout=90)
        df = normalize(pd.read_csv(io.BytesIO(gzip.decompress(r.content))), lastpx(sym, s))
        df.to_csv(cf, index=False)
    df["t"] = pd.to_datetime(df["timestamp"] // 1000, unit="s", utc=True)
    df["notional"] = df["price"] * df["volume"]
    df["sec"] = df["t"].dt.second
    return df.sort_values("t").reset_index(drop=True)
