# Crypto Trader

Automated BTC sentiment trader: free news feeds → Claude analysis → paper trades on Binance testnet, with a Streamlit dashboard and a 15-minute Claude Routine.

**No paid APIs.** News comes from RSS (CoinDesk, CoinTelegraph, Decrypt, Bitcoin Magazine) + Reddit; analysis runs inside your Claude Routine. The only credentials needed are free [Binance testnet keys](https://testnet.binance.vision/).

## Quick start

```bash
pip3 install -r requirements.txt
python3 -m streamlit run dashboard.py     # open http://localhost:8501
```

Enter your Binance testnet keys in the **Settings** tab (writes `.env`), then run a simulation or the live pipeline from the sidebar.

## How it works

```
RSS + Reddit headlines ──> sentiment analysis ──> BUY/SELL/HOLD + confidence
                                                        │
                                  below threshold ── SKIPPED (logged only)
                                  above threshold ── DRY_RUN / testnet order
                                                        │
                                              SQLite trade log (data/trades.db)
                                                        │
                                    dashboard PnL replay + equity curve
```

Two analysis paths:

| Path | Engine | Trigger |
|---|---|---|
| **Scheduled** | Claude Routine reads headlines and reasons about them | every 15 min (`crypto-trader-pipeline` routine) |
| **Manual** | Keyword heuristic (`src/sentiment/analyzer.py`) — instant, offline | `python3 main.py --dry-run` or dashboard "Run now" |

## Commands

| Command | What it does |
|---|---|
| `python3 main.py --dry-run` | Full pipeline once, no orders placed |
| `python3 simulate.py --cycles 20` | Populate the trade log with mock-scenario data |
| `python3 fetch_headlines.py` | Print live headlines as JSON (used by the Routine) |
| `python3 execute_signal.py --signal BUY --confidence 0.8 --reasoning "..." --dry-run` | Log/execute one signal (used by the Routine) |
| `python3 pnl.py` | Terminal PnL dashboard with paper-portfolio replay |
| `python3 show_trades.py [n]` | Recent signals table |
| `python3 check_connection.py` | Verify Binance testnet + news feeds |
| `python3 -m pytest tests/ -q` | Smoke tests (no network, no keys) |

## Testnet vs Live account

Switch accounts in **Settings → Account** (writes `BINANCE_TESTNET` to `.env`; applies on the next run, no restart). The sidebar and hero always show which account is active — green 🧪 TESTNET or red 🔴 LIVE.

Live orders are gated three deep, all of which must be deliberately passed:
1. Account set to **Live** in Settings (red warning shown)
2. **Dry-run toggled off** in the sidebar (defaults to on, every session)
3. The **"I understand this trades real money"** checkbox confirmed — this sets a per-run `ALLOW_LIVE_TRADING` latch; without it the executor refuses the order and logs `BLOCKED_LIVE`

Testnet and live keys are different credentials: testnet keys come from [testnet.binance.vision](https://testnet.binance.vision/), live keys from binance.com (spot trading only — never enable withdrawals).

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `BINANCE_API_KEY` / `BINANCE_API_SECRET` | — | Keys for the selected account (testnet and live keys differ) |
| `BINANCE_TESTNET` | `true` | `true` = paper trading on testnet; switch via Settings → Account |
| `TICKER` | `BTCUSDT` | Trading pair |
| `SIGNAL_CONFIDENCE_THRESHOLD` | `0.65` | Signals below this are logged as SKIPPED |
| `MAX_ORDER_USDT` | `100` | Max position size per signal (scaled down by confidence) |
| `MAX_OPEN_USDT` | `300` | Exposure cap — BUYs are vetoed (`VETOED_RISK`) beyond this |
| `STOP_LOSS_PCT` | `5` | Force-sell when the position is down this % from cost basis (0 = off) |
| `TREND_FILTER` | `true` | Veto BUYs (`VETOED_TREND`) when price is below the 20-period SMA |
| `FEE_RATE` | `0.001` | Taker fee applied in the paper-PnL replay |
| `TICKER` | `BTCUSDT` | Asset to trade — crypto (`BTCUSDT`, `ETHUSDT`…) or stock (`AAPL`, `GOOGL`…) |
| `ML_GATE` | `true` | Let the trained model veto (`VETOED_ML`) and size trades |
| `ML_MIN_PROB` | `0.35` | Veto signals the model scores below this probability |
| `SLACK_WEBHOOK_URL`, `ALERT_EMAIL`, `SENDGRID_API_KEY`, `FROM_EMAIL` | — | Optional alerts on BUY/SELL |

## Project layout

```
dashboard.py            Streamlit GUI (dashboard + settings/.env editor)
main.py                 Standalone pipeline (offline keyword analyzer)
fetch_headlines.py      Headlines as JSON — step 1 of the Claude Routine
execute_signal.py       Log/execute a signal — step 3 of the Claude Routine
simulate.py             Mock-data simulation runner
pnl.py, show_trades.py  Terminal viewers
src/
  config.py             All env config
  sentiment/scraper.py  RSS + Reddit headline fetcher (no keys)
  sentiment/analyzer.py Keyword sentiment heuristic (offline fallback)
  trader/binance_client.py  Testnet client, market orders
  trader/db.py          SQLite trade log
  trader/portfolio.py   Paper-PnL replay (equity curve, win rate)
  trader/executor.py    Threshold check → order/log
  alerts.py             Slack / SendGrid notifications
tests/test_smoke.py     Import, analyzer, portfolio, and Py3.9-safety tests
```

## Assets — crypto and stocks

Pick the asset in **Settings → Asset**: Bitcoin, Ethereum, Solana (crypto, traded on Binance testnet/live) or Apple, Alphabet, Microsoft, Tesla (stocks). Stocks are **paper-only**: prices come from Yahoo Finance's free endpoints, news from Yahoo Finance + Google News RSS — signals, paper portfolio, scorecard and ML all work, but no real orders are ever placed. The registry lives in `src/assets.py`; adding an asset is one dict entry.

## Machine learning — the system learns from its own trades

`src/ml/learner.py` is an online logistic regression (pure Python, no heavy deps) that predicts **P(this signal will be profitable)** from decision-time features: confidence, signal direction, trend, and volatility.

- **It trains itself on every run**: signals whose outcome has matured (price known ~4h later) become labeled examples; weights update by SGD.
- **Learning persists** in `data/model.json` — across restarts, sessions, and even trade-log wipes.
- **Cold start is safe**: until 20 outcomes are learned the model only observes. After that, the gate vetoes signals scoring below `ML_MIN_PROB` (`VETOED_ML`) and scales order size by predicted edge.
- The dashboard's 🧠 panel shows outcomes learned, prediction accuracy, and the learned weights in plain language. **Settings → Reset learning** wipes the model.

Note: simulations also feed the learner (useful for demos). Reset the model before relying on it for real signals.

## Risk rules & signal quality

Every order — manual or routine — passes through the same executor pipeline:

1. **Stop-loss / take-profit**: forced SELL when the position is down `STOP_LOSS_PCT` (2.5%) or up `TAKE_PROFIT_PCT` (4%) from cost basis. The 1.6:1 reward/risk shape makes the strategy profitable from a ~42% win rate after fees — expectancy over win rate.
2. **Adaptive thresholds**: while a side's rolling 4h scorecard accuracy is under 50% (min 10 calls), its confidence bar rises +15%. The losing side has to earn its way back.
3. **Trend filter**: BUY signals are vetoed while price is below its 20-period (15m) moving average.
4. **Exposure cap**: BUYs are vetoed once `MAX_OPEN_USDT` is already at risk.
5. **Confidence sizing**: order notional = `MAX_ORDER_USDT × confidence × ML edge`.

The **Signal quality** scorecard (dashboard + `pnl.py`) scores every BUY/SELL against the price 1h/4h/24h later — above ~55% overall accuracy the signal has edge; near 50% it's a coin flip and the analyzer needs work before anything else matters.

The dashboard's routine pill reads `data/routine_heartbeat.txt`, written by `execute_signal.py` on every routine run — it shows "Routine ✓ 12m ago" or warns when the schedule has stopped.

## Gotchas

- **Python 3.9 compatibility:** every module carries `from __future__ import annotations`; without it, `X | None` annotations crash at import time. A smoke test enforces this.
- The Claude Routine always runs with `--dry-run`. Remove the flag in the routine prompt only when you deliberately want live testnet orders.
- Paper PnL sizes DRY_RUN trades at `MAX_ORDER_USDT` notional since no real fill quantity exists.
