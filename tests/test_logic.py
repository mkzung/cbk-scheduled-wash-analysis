import os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analysis"))
from cbklib import normalize


def test_normalize_misaligned_header():
    # header says id/timestamp/price/volume/side, but the data is ts, price, size, side, dir
    raw = pd.DataFrame({"id": [1777593722668, 1777593722669, 1777593722670],
                        "timestamp": [0.2531, 0.2536, 0.2528],
                        "price": [120.0, 240.5, 95.2],
                        "volume": ["buy", "sell", "buy"],
                        "side": [0, 0, 0]})
    out = normalize(raw, lp=0.253)
    assert list(out.columns) == ["timestamp", "price", "volume", "side"]
    assert out.side.tolist() == ["buy", "sell", "buy"]
    assert out.timestamp.iloc[0] == 1777593722668
    assert abs(out.price.iloc[0] - 0.2531) < 1e-6
    assert abs(out.volume.iloc[0] - 120.0) < 1e-6


def test_normalize_correct_header():
    raw = pd.DataFrame({"timestamp": [1.7e12, 1.7e12, 1.7e12],
                        "price": [0.25, 0.26, 0.24],
                        "volume": [100.0, 200.0, 150.0],
                        "side": ["buy", "sell", "buy"]})
    out = normalize(raw, lp=0.25)
    assert abs(out.price.median() - 0.25) < 1e-3
    assert abs(out.volume.median() - 150.0) < 1


def test_normalize_price_volume_by_magnitude():
    raw = pd.DataFrame({"ts": [1.7e12] * 4, "a": [0.25, 0.26, 0.255, 0.24],
                        "b": [90.0, 120.0, 150.0, 110.0], "sd": ["buy", "sell", "buy", "sell"]})
    out = normalize(raw, lp=0.25)
    assert out.price.max() < 1.0       # picked the small-magnitude column as price
    assert out.volume.median() > 50    # picked the larger column as volume


def test_normalize_raises_without_side():
    raw = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    try:
        normalize(raw, lp=1.0)
    except ValueError:
        return
    assert False, "expected ValueError when no side column is present"


def test_normalize_picks_varying_volume_over_constant_column():
    # a constant numeric column (e.g. a direction flag) sits BEFORE the real size column; volume
    # must be detected as the varying column, never the all-zero flag. Guards the real Bybit layout,
    # whose misaligned dump carries a constant dir column.
    raw = pd.DataFrame({"ts": [1.7e12, 1.7e12 + 1, 1.7e12 + 2, 1.7e12 + 3],
                        "price": [0.25, 0.26, 0.255, 0.24],
                        "flag": [0, 0, 0, 0],
                        "size": [100.0, 150.0, 120.0, 180.0],
                        "sd": ["buy", "sell", "buy", "sell"]})
    out = normalize(raw, lp=0.25)
    assert out.volume.median() > 50                # picked 'size' (varying), not 'flag' (constant zeros)
    assert out.side.tolist() == ["buy", "sell", "buy", "sell"]
