# xauusd-backtest-kit

Pure-Python backtester for a Donchian channel breakout strategy on XAUUSD. Zero dependencies — just `python3`.

## Strategy

- **Enter long** when close breaks above the highest high of the last `N` bars
- **Exit** when close breaks below the lowest low of the last `M` bars (or fixed stop-loss / take-profit)

## Usage

```bash
# generate synthetic data to try it out
python backtest.py --gen-sample 2000 --csv sample.csv

# run backtest on your own OHLC csv (columns: time,open,high,low,close)
python backtest.py --csv XAUUSD_H1.csv --n 20 --m 10

# with stop-loss and per-trade log
python backtest.py --csv XAUUSD_H1.csv --n 20 --m 10 --sl 5.0 --tp 10.0 --trades trades.csv
```

## Output

```
bars: 500  params: n=20 m=10 sl=5.0 tp=None
trades: 7  win rate: 14.3%  profit factor: 0.599
total PnL: -9.52  avg/trade: -1.36  max DD: 23.76
trade log: trades.csv
```

Metrics: trade count, win rate, profit factor, total/average PnL, max drawdown.

> Research tool only — not financial advice.
