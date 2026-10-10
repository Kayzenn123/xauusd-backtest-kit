#!/usr/bin/env python3
"""XAUUSD Donchian-breakout backtester — pure Python, no dependencies.

Reads an OHLC CSV (columns: time,open,high,low,close) and simulates a
Donchian channel breakout strategy:

  - LONG when close breaks above the highest high of the last N bars
  - Exit when close breaks below the lowest low of the last M bars
    (or an optional fixed stop-loss in price units)

Outputs a metrics summary plus an optional per-trade CSV log.

Usage:
    python backtest.py --csv XAUUSD_H1.csv --n 20 --m 10
    python backtest.py --csv XAUUSD_H1.csv --n 20 --m 10 --sl 5.0 --trades trades.csv
    python backtest.py --gen-sample 2000 --csv sample.csv   # make synthetic data

This is a research tool, not financial advice.
"""

import argparse
import csv
import math
import random
import sys


def load_ohlc(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                rows.append({
                    "time": r["time"],
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                })
            except (KeyError, ValueError):
                continue
    if len(rows) < 2:
        raise SystemExit(f"not enough valid rows in {path}")
    return rows


def backtest(rows, n=20, m=10, stop_loss=None, risk_reward_tp=None):
    """Run the breakout simulation. Returns (trades, equity_curve)."""
    trades = []
    equity = 0.0
    equity_curve = []
    position = None  # dict(entry_time, entry_price)

    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    closes = [r["close"] for r in rows]

    for i in range(n, len(rows)):
        upper = max(highs[i - n:i])
        lower = min(lows[i - m:i])
        price = closes[i]
        t = rows[i]["time"]

        if position is None:
            if price > upper:
                position = {"entry_time": t, "entry_price": price}
        else:
            exit_price, reason = None, ""
            if stop_loss is not None and price <= position["entry_price"] - stop_loss:
                exit_price, reason = position["entry_price"] - stop_loss, "stop"
            elif risk_reward_tp is not None and price >= position["entry_price"] + risk_reward_tp:
                exit_price, reason = position["entry_price"] + risk_reward_tp, "tp"
            elif price < lower:
                exit_price, reason = price, "channel"
            if exit_price is not None:
                pnl = exit_price - position["entry_price"]
                equity += pnl
                trades.append({
                    "entry_time": position["entry_time"],
                    "exit_time": t,
                    "entry": round(position["entry_price"], 2),
                    "exit": round(exit_price, 2),
                    "pnl": round(pnl, 2),
                    "reason": reason,
                })
                position = None
        equity_curve.append(equity)

    return trades, equity_curve


def metrics(trades, equity_curve):
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    peak, max_dd = 0.0, 0.0
    for e in equity_curve:
        peak = max(peak, e)
        max_dd = max(max_dd, peak - e)
    total = sum(t["pnl"] for t in trades)
    return {
        "trades": len(trades),
        "win_rate": round(100 * len(wins) / len(trades), 1) if trades else 0.0,
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss else float("inf"),
        "total_pnl": round(total, 2),
        "avg_pnl": round(total / len(trades), 2) if trades else 0.0,
        "max_drawdown": round(max_dd, 2),
    }


def gen_sample(path, bars=2000, start=2650.0, seed=42):
    rnd = random.Random(seed)
    price = start
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close"])
        for i in range(bars):
            o = price
            drift = rnd.gauss(0.15, 2.2)
            c = max(1.0, o + drift)
            h = max(o, c) + abs(rnd.gauss(0, 1.2))
            l = min(o, c) - abs(rnd.gauss(0, 1.2))
            w.writerow([f"2026-01-{(i // 24) % 28 + 1:02d} {(i % 24):02d}:00",
                        round(o, 2), round(h, 2), round(l, 2), round(c, 2)])
            price = c
    print(f"sample written: {path} ({bars} bars)")


def main():
    ap = argparse.ArgumentParser(description="XAUUSD Donchian breakout backtester")
    ap.add_argument("--csv", help="OHLC csv: time,open,high,low,close")
    ap.add_argument("--n", type=int, default=20, help="donchian entry lookback (default 20)")
    ap.add_argument("--m", type=int, default=10, help="donchian exit lookback (default 10)")
    ap.add_argument("--sl", type=float, default=None, help="stop-loss in price units")
    ap.add_argument("--tp", type=float, default=None, help="take-profit in price units")
    ap.add_argument("--trades", help="write per-trade CSV here")
    ap.add_argument("--gen-sample", type=int, metavar="BARS",
                    help="generate synthetic CSV with BARS bars and exit")
    args = ap.parse_args()

    if args.gen_sample:
        out = args.csv or "sample_xauusd.csv"
        gen_sample(out, args.gen_sample)
        return
    if not args.csv:
        ap.error("--csv is required (or use --gen-sample)")

    rows = load_ohlc(args.csv)
    trades, curve = backtest(rows, n=args.n, m=args.m,
                             stop_loss=args.sl, risk_reward_tp=args.tp)
    m = metrics(trades, curve)
    print(f"bars: {len(rows)}  params: n={args.n} m={args.m} sl={args.sl} tp={args.tp}")
    print(f"trades: {m['trades']}  win rate: {m['win_rate']}%  "
          f"profit factor: {m['profit_factor']}")
    print(f"total PnL: {m['total_pnl']}  avg/trade: {m['avg_pnl']}  "
          f"max DD: {m['max_drawdown']}")

    if args.trades and trades:
        with open(args.trades, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(trades[0].keys()))
            w.writeheader()
            w.writerows(trades)
        print(f"trade log: {args.trades}")


if __name__ == "__main__":
    main()
