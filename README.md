# Marksman — QLD Trend Agent (public release)

A human-gated, Claude + Robinhood trend-following agent. It holds **QLD** (2x Nasdaq-100)
when **QQQ** closes above its 200-day SMA × 1.02, holds cash when QQQ closes below
200-day SMA × 0.98, and does nothing in between. A 2% hysteresis band kills whipsaw.
Expected activity: ~1–3 trades/year. Almost every run logs one line: `HOLD`.

This is the sanitized release that accompanies the r/AIportfolio writeup. Share it, fork it,
try to break it — that's the point.

## What's in here

| File | What it is |
|---|---|
| `STRATEGY_SPEC.md` | The full ruleset the agent runs — state machine, execution rules, risk controls, pre-report integrity checks. The source of truth. |
| `BACKTEST_RESULTS.md` | All three backtest rounds: B&H vs swing variants, strategy transforms, and the SMA-length × hysteresis-band parameter sweep that selected 200/2%. |
| `log_writer.py` | Deterministic log writer + integrity validator. Exists because hand-composed log lines kept truncating; this makes one record → one validated, fsync'd line. |
| `qqq_price_history.csv` | 240 rows of raw (non-adjusted) QQQ closes — the local price cache, enough to recompute the 200-day SMA without re-pulling history. |
| `sample_log_redacted.txt` | A few real run lines showing the log format. Dollar values redacted. |

## How the signal works

1. Pull the **prior trading day's settled QQQ close** (never a last-trade or estimate).
2. SMA200 = mean of the last 200 raw closes. Upper band = SMA200 × 1.02, lower = × 0.98.
3. State machine (always exactly one state):
   - **OUT** and QQQ close > upper band → BUY signal (deploy 100% of cash into QLD).
   - **IN** and QQQ close < lower band → SELL signal (liquidate all QLD).
   - Otherwise → HOLD.
4. Trailing drawdown halt: if account value < 50% of all-time high, liquidate and stop.

**The signal is always computed on QQQ, never on QLD.** Leveraged-ETF prices decay, so
their moving averages are unreliable — QQQ tells you the trend; QLD is only the vehicle.

## Reproducing the backtest

The backtest *harness* is intentionally not included — the sim was run ad hoc, not from a
committed script — but it's reproducible from the spec. Parameters used: fills at next
day's close (no lookahead), no commissions, fractional shares, Wilder RSI (for the swing
variants), dividend-adjusted closes for the sim. Note the live agent uses **raw** closes,
a minor difference. The `qqq_price_history.csv` here is raw closes for the live cache, not
the adjusted series the sim used.

## What was deliberately removed

This is a scrubbed copy of a live trading agent. Removed before release: brokerage account
numbers, the mobile-notification (ntfy) topic, personal file paths, and the live
scheduled-task definition. Don't expect it to run as-is — it's the strategy and mechanics,
not a turnkey bot wired to someone's account.

## Caveats (don't skip these)

2017–2026 was the best decade leveraged long ETFs have ever had — forward returns will very
likely be lower. Volatility decay grinds 2x funds in sideways markets. A 40–50% drawdown is
an **expected** event under this strategy, not a malfunction. The chosen 200/2% config posts
30.6% CAGR **in-sample** — treat that as a backtest figure, not a forward expectation. This
was $2k of play money. Past performance does not predict future results. Not financial advice.
