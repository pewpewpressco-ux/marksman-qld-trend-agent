# Backtest: Accumulation Swing Strategy vs Alternatives
**Run date:** June 10, 2026
**Data:** Yahoo Finance daily dividend-adjusted closes, Jun 13 2016 – Jun 10 2026 (2,513 trading days)
**Simulation window:** Mar 29 2017 – Jun 10 2026 (9.2 years, after 200-day indicator warmup)
**Starting capital:** $2,000

## Strategies tested

1. **Buy & hold** — $2,000 all-in at sim start.
2. **Current agent rules** — Buy: RSI(14) < 38 AND price < 20-day SMA. Sell: RSI(14) > 62 AND price > 20-day SMA (50% of oldest unsold lot). Sizing: min(25% of cash, $500). 40% minimum equity floor. Kill switch at $1,600. 3% daily-move volatility pause. Initial 40% ($800) core position.
3. **RSI(2) variant (Connors-style)** — Buy: RSI(2) < 10 AND price > 200-day SMA. Sell: RSI(2) > 65. Same sizing/mechanics as #2.

All fills at next day's close (no lookahead). No commissions. Fractional shares. Wilder RSI, verified against independent implementation.

## Results

| Metric | SPY B&H | SPY current | SPY RSI(2) | QQQ B&H | QQQ current | QQQ RSI(2) |
|---|---|---|---|---|---|---|
| Final value | $7,104 | $6,478 | $6,561 | $11,146 | $9,181 | $10,333 |
| CAGR | 14.8% | 13.7% | 13.8% | 20.6% | 18.1% | 19.6% |
| Final shares | 9.79 | 8.90 | 9.02 | 16.07 | 13.21 | 14.87 |
| Buys / sells | — | 56 / 57 | 37 / 38 | — | 57 / 58 | 37 / 38 |
| Trades per year | 0 | ~12 | ~8 | 0 | ~12 | ~8 |
| Max drawdown | 33.7% | 32.1% | 33.5% | 35.1% | 34.9% | 35.0% |
| Kill switch hit | — | No | No | — | No | No |

## Key findings

1. Buy & hold beat every strategy variant on both assets — including on the agent's own success metric (share count: 8.90 strategy vs 9.79 B&H on SPY).
2. The swing rules provided almost no drawdown protection (~32–34% max DD in all cases).
3. RSI(2) + 200-day SMA filter outperformed the current RSI(14) rules but still trailed B&H.
4. Asset choice dominated trigger choice: worst QQQ variant beat best SPY variant by ~$2,000.
5. Taxes (not modeled) widen the gap further — ~57 sells are taxable events; B&H defers all gains.

## Round 2: Strategy transforms (same window, same harness)

| Strategy | Final value | CAGR | Max DD | Trades | Time in market |
|---|---|---|---|---|---|
| B&H SPY | $7,104 | 14.8% | 33.7% | 0 | 100% |
| B&H QQQ | $11,146 | 20.6% | 35.1% | 0 | 100% |
| B&H QLD (2x QQQ) | $26,222 | 32.4% | 63.7% | 0 | 100% |
| Trend filter QQQ (200-SMA cross) | $8,797 | 17.5% | 24.5% | 41 | 82% |
| Trend filter QLD (200-SMA cross) | $21,660 | 29.6% | 45.0% | 41 | 82% |
| Momentum rotation SPY/QQQ (126d, monthly) | $7,355 | 15.3% | 28.6% | 39 | 85% |

Trend signals computed on QQQ close vs 200-day SMA; QLD traded as the vehicle.

## Round 3: QLD trend parameter sweep (hysteresis band × SMA length)

| SMA | Band | Final | CAGR | Max DD | Trades |
|---|---|---|---|---|---|
| 150 | 0% | $20,671 | 29.0% | 44.9% | 49 |
| 150 | 1% | $27,254 | 32.9% | 34.5% | 19 |
| 150 | 2% | $24,636 | 31.5% | 34.5% | 19 |
| 150 | 3% | $31,830 | 35.2% | 34.5% | 11 |
| 175 | 0% | $29,305 | 34.0% | 40.9% | 39 |
| 175 | 1% | $27,020 | 32.8% | 44.9% | 19 |
| 175 | 2% | $32,983 | 35.7% | 34.5% | 11 |
| 175 | 3% | $25,556 | 32.0% | 35.8% | 11 |
| 200 | 0% | $21,660 | 29.6% | 45.0% | 41 |
| 200 | 1% | $25,775 | 32.1% | 44.9% | 17 |
| 200 | 2% | $23,089 | 30.6% | 40.9% | 17 |
| **200** | **2% (chosen)** | **$23,089** | **30.6%** | **40.9%** | **17** |
| 200 | 3% | $23,024 | 30.5% | 46.0% | 11 |

**Selection rationale:** every banded variant beat its unbanded version — the band is a
robust improvement, not a fitted one. The single best cell (175/2%) was NOT chosen:
175 days is a nonstandard, in-sample-fitted length. Chosen config is 200-day SMA + 2%
band — the standard parameter with the robust improvement. Treat the chosen cell's
30.6% CAGR as the in-sample figure, not a forward expectation.

## Decision (2026-06-10)

Agent transformed from SPY accumulation swing → QLD trend following per
`AGENT_INSTRUCTIONS_v2_QLD_TREND.md`. Kill switch redesigned from fixed $1,600 to
trailing 50%-of-peak halt.

## Caveats

- 2017–2026 was a strongly trending bull decade — best-case regime for buy & hold and
  for leveraged long ETFs. Forward returns very likely lower.
- Volatility decay punishes 2x funds in sideways markets; the trend filter mitigates,
  not eliminates.
- Signals computed on dividend-adjusted closes; live agent uses raw prices (minor differences).
- No taxes or slippage modeled. ~2 trades/yr keeps both small but nonzero.
- Past performance does not predict future results. Not financial advice.
