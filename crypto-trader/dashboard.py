#!/usr/bin/env python3
"""
Crypto Trader Dashboard — run with: python3 -m streamlit run dashboard.py
"""
from __future__ import annotations  # lazy annotations — keeps `X | None` etc. safe on Python 3.9

import sqlite3
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import streamlit as st
import pandas as pd
import altair as alt

sys.path.insert(0, os.path.dirname(__file__))

ROOT = Path(__file__).parent
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE_PATH = ROOT / ".env.example"

# signal → color
C_BUY, C_SELL, C_HOLD = "#16c784", "#ea3943", "#f0b90b"
SIGNAL_COLORS = {"BUY": C_BUY, "SELL": C_SELL, "HOLD": C_HOLD}

st.set_page_config(
    page_title="Crypto Trader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── global styling ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
  .block-container { padding-top: 2.2rem; max-width: 1280px; }
  #MainMenu, footer { visibility: hidden; }

  /* hero header */
  .hero {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1.1rem 1.4rem; border-radius: 16px; margin-bottom: 1.4rem;
    background: linear-gradient(120deg, #1e2530 0%, #11151c 100%);
    border: 1px solid rgba(255,255,255,0.06);
  }
  .hero-title { font-size: 1.45rem; font-weight: 600; margin: 0; letter-spacing: -0.01em; }
  .hero-sub { color: #8a94a6; font-size: 0.86rem; margin-top: 2px; }
  .hero-price { font-size: 1.9rem; font-weight: 700; line-height: 1; }
  .hero-price-label { color: #8a94a6; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; text-align: right; }

  .pill { display: inline-flex; align-items: center; gap: 6px; padding: 3px 11px;
          border-radius: 999px; font-size: 0.74rem; font-weight: 600; }
  .pill-live { background: rgba(22,199,132,0.14); color: #16c784; }
  .pill-off  { background: rgba(138,148,166,0.14); color: #8a94a6; }
  .pill-danger { background: rgba(234,57,67,0.16); color: #ea3943; border: 1px solid rgba(234,57,67,0.35); }
  .pill-warn { background: rgba(240,185,11,0.14); color: #f0b90b; }
  .dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
  .dot-live { background: #16c784; box-shadow: 0 0 0 3px rgba(22,199,132,0.22); }
  .dot-off  { background: #8a94a6; }

  /* metric cards */
  .mcard { background: #161b22; border: 1px solid rgba(255,255,255,0.06);
           border-radius: 14px; padding: 1rem 1.15rem; height: 100%; }
  .mcard-label { color: #8a94a6; font-size: 0.74rem; text-transform: uppercase;
                 letter-spacing: 0.06em; margin-bottom: 6px; }
  .mcard-value { font-size: 1.7rem; font-weight: 700; line-height: 1; }
  .mcard-sub { font-size: 0.78rem; margin-top: 6px; color: #8a94a6; }

  /* signal chip */
  .schip { display: inline-flex; align-items: center; gap: 7px; padding: 5px 13px;
           border-radius: 10px; font-weight: 700; font-size: 1.05rem; }

  /* last-signal panel */
  .lspanel { background: #161b22; border: 1px solid rgba(255,255,255,0.06);
             border-radius: 14px; padding: 1.15rem 1.3rem; }
  .ls-row { display: flex; justify-content: space-between; padding: 5px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; }
  .ls-row:last-child { border-bottom: none; }
  .ls-k { color: #8a94a6; }
  .ls-v { font-weight: 600; }

  section[data-testid="stSidebar"] { background: #0d1117; }
  div[data-testid="stMetricValue"] { font-size: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ── env helpers ────────────────────────────────────────────────────────────────

def load_env_file() -> dict:
    path = ENV_PATH if ENV_PATH.exists() else ENV_EXAMPLE_PATH
    entries = {}
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        entries[k.strip()] = v.strip()
    return entries


def save_env_file(values: dict):
    ENV_PATH.write_text("\n".join(f"{k}={v}" for k, v in values.items()) + "\n")


def check_env_complete() -> tuple[bool, list[str]]:
    required = ["BINANCE_API_KEY", "BINANCE_API_SECRET"]
    if not ENV_PATH.exists():
        return False, required
    env = load_env_file()
    missing = [k for k in required if not env.get(k)]
    return len(missing) == 0, missing


# ── data helpers ───────────────────────────────────────────────────────────────

def _db_mtime() -> float:
    db = ROOT / "data" / "trades.db"
    return db.stat().st_mtime if db.exists() else 0.0


@st.cache_data(show_spinner=False)
def _load_trades_cached(mtime: float, n: int) -> list[dict]:
    db = ROOT / "data" / "trades.db"
    if not db.exists():
        return []
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM trades ORDER BY ts DESC LIMIT ?", (n,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def load_trades(n: int = 500) -> list[dict]:
    # cache key includes the DB file mtime — invalidates the moment a run writes
    return _load_trades_cached(_db_mtime(), n)


@st.cache_data(show_spinner=False)
def _csv_export(mtime: float) -> str:
    return pd.DataFrame(_load_trades_cached(mtime, 100000)).to_csv(index=False)


@st.cache_data(ttl=30)
def live_price(symbol: str) -> Optional[float]:
    try:
        from src import market
        return market.get_price(symbol)
    except Exception:
        return None


def asset_info(symbol: str) -> dict:
    from src.assets import get_asset
    return get_asset(symbol)


def run_script(args: list[str], extra_env: Optional[dict] = None) -> tuple[int, str]:
    """Run a pipeline script in-process; returns (returncode, cleaned output).

    Subprocesses forked from Streamlit segfault on macOS (fork-safety),
    so scripts execute via runpy inside this process instead. src.* modules
    are purged first so every run re-reads .env — account/config changes
    apply immediately, no restart needed.
    """
    import io, contextlib, re, runpy, traceback

    script, argv = args[0], args[1:]
    buf = io.StringIO()
    old_argv = sys.argv
    old_env = {k: os.environ.get(k) for k in (extra_env or {})}
    os.environ.update(extra_env or {})
    for m in [m for m in list(sys.modules) if m == "src" or m.startswith("src.")]:
        del sys.modules[m]
    rc = 0
    try:
        sys.argv = [script] + argv
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            runpy.run_path(str(ROOT / script), run_name="__main__")
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception:
        buf.write(traceback.format_exc())
        rc = 1
    finally:
        sys.argv = old_argv
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    out = buf.getvalue()
    out = re.sub(r"\x1b\[[0-9;]*m", "", out)  # strip ANSI colors
    noise = ("NotOpenSSLWarning", "warnings.warn", "urllib3")
    out = "\n".join(l for l in out.splitlines() if not any(n in l for n in noise))
    try:  # persist for debugging — survives page reloads
        (ROOT / "data").mkdir(exist_ok=True)
        (ROOT / "data" / "last_run.log").write_text(f"cmd: {args}\nrc: {rc}\n\n{out}")
    except OSError:
        pass
    return rc, out


def routine_status() -> tuple[str, str]:
    """(pill css class, label) for the Claude Routine heartbeat.
    execute_signal.py touches data/routine_heartbeat.txt on every routine run."""
    hb = ROOT / "data" / "routine_heartbeat.txt"
    if not hb.exists():
        return "pill-off", "Routine: no runs yet"
    try:
        last = datetime.fromisoformat(hb.read_text().strip())
        mins = (datetime.now(timezone.utc) - last).total_seconds() / 60
    except Exception:
        return "pill-off", "Routine: unknown"
    if mins <= 20:
        return "pill-live", f"Routine ✓ {mins:.0f}m ago"
    if mins <= 60:
        return "pill-warn", f"Routine ⚠ {mins:.0f}m ago"
    return "pill-danger", f"Routine stopped — last ran {mins/60:.1f}h ago"


def remember_run(label: str, rc: int, out: str):
    st.session_state["last_output"] = out
    st.session_state["last_rc"] = rc
    st.session_state["last_run"] = label
    st.session_state["just_ran"] = True


# ── sidebar ────────────────────────────────────────────────────────────────────

env_ok, missing_keys = check_env_complete()
env_vals = load_env_file()
is_testnet = env_vals.get("BINANCE_TESTNET", "true").lower() == "true"
cur_ticker = env_vals.get("TICKER", "BTCUSDT")
cur_asset = asset_info(cur_ticker)
is_stock = cur_asset["kind"] == "stock"

with st.sidebar:
    st.markdown("### 📈 Crypto Trader")
    mode_pill = ('<span class="pill pill-live">🧪 TESTNET — paper money</span>' if is_testnet
                 else '<span class="pill pill-danger">🔴 LIVE — real money</span>')
    st.markdown(mode_pill, unsafe_allow_html=True)
    thr_lbl = float(env_vals.get("SIGNAL_CONFIDENCE_THRESHOLD") or 0.65)
    paper_note = " · 📄 paper-only" if is_stock else ""
    st.caption(f"{cur_asset['icon']} **{cur_asset['name']}** ({cur_ticker}){paper_note} · threshold **{thr_lbl:.0%}**")
    if not env_ok:
        st.warning("⚠️ No API keys — add them in **Settings**. Dry-run & simulation work without keys.")
    st.divider()

    st.markdown("#### Run pipeline")
    dry_run = st.toggle("Dry-run mode", value=True,
                        help="On: signal is logged, no order placed. Off: places a market order on the selected account.")
    live_confirmed = True
    if not dry_run and not is_testnet:
        st.error("**LIVE account** — turning dry-run off places orders with real funds.")
        live_confirmed = st.checkbox("I understand this trades real money")
    can_run = (dry_run or env_ok) and live_confirmed
    if st.button("▶ Run now", width="stretch", type="primary", disabled=not can_run):
        extra = {"ALLOW_LIVE_TRADING": "true"} if (not dry_run and not is_testnet and live_confirmed) else None
        with st.spinner("Fetching headlines & analyzing (~10s)..."):
            rc, out = run_script(["main.py"] + (["--dry-run"] if dry_run else []), extra_env=extra)
        remember_run("Pipeline " + datetime.now(timezone.utc).strftime("%H:%M:%S UTC"), rc, out)
        st.rerun()
    if not env_ok and not dry_run:
        st.caption("Placing orders needs API keys — set them in Settings.")

    st.divider()
    st.markdown("#### Simulation")
    cycles = st.slider("Cycles", 5, 100, 20)
    wipe = st.checkbox("Wipe existing log first", value=True,
                       help="Unchecked: append mock cycles to the current trade log")
    if st.button("▶ Run simulation", width="stretch"):
        with st.spinner(f"Simulating {cycles} cycles..."):
            rc, out = run_script(["simulate.py", "--cycles", str(cycles)] + ([] if wipe else ["--append"]))
        remember_run(f"Simulation ({cycles} cycles)", rc, out)
        st.rerun()

    st.divider()
    auto = st.toggle("Auto-refresh (30s)", value=False)
    if st.button("🔄 Refresh now", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    if "last_run" in st.session_state:
        st.caption(f"Last run: {st.session_state['last_run']}")

if auto:
    st.markdown("<meta http-equiv='refresh' content='30'>", unsafe_allow_html=True)


# ── tabs ───────────────────────────────────────────────────────────────────────

tab_dashboard, tab_settings = st.tabs(["📊 Dashboard", "⚙️ Settings"])


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

with tab_dashboard:
    trades = load_trades()

    # one-shot result banner for the run that just finished
    if st.session_state.pop("just_ran", False):
        rc = st.session_state.get("last_rc", 0)
        if rc == 0:
            newest = trades[0] if trades else None
            detail = (f" — latest signal: **{newest['signal']}** ({newest['confidence']:.0%}, {newest['status']})"
                      if newest else "")
            st.success(f"✅ {st.session_state['last_run']} completed{detail}")
        else:
            st.error(f"❌ {st.session_state['last_run']} failed — output below.")
            st.code(st.session_state.get("last_output", ""), language="bash")

    if not trades:
        st.info("👋 **Welcome!** Nothing logged yet. Try the demo below — no API keys needed — "
                "or run the real pipeline in dry-run from the sidebar. Add Binance keys in **Settings** when ready.")
        if st.button("▶ Run a 20-cycle demo simulation", type="primary"):
            with st.spinner("Simulating 20 cycles..."):
                rc, out = run_script(["simulate.py", "--cycles", "20"])
            remember_run("Demo simulation (20 cycles)", rc, out)
            st.rerun()
        st.stop()

    # ── hero header ──
    price = live_price(cur_ticker)
    rt_cls, rt_txt = routine_status()
    price_html = f"${price:,.2f}" if price else "—"
    acct_pill = ('<span class="pill pill-warn">📄 PAPER — stock</span>' if is_stock
                 else ('<span class="pill pill-live">🧪 TESTNET</span>' if is_testnet
                       else '<span class="pill pill-danger">🔴 LIVE</span>'))

    st.markdown(f"""
    <div class="hero">
      <div>
        <div class="hero-title">{cur_asset['icon']} {cur_asset['name']} sentiment trader</div>
        <div class="hero-sub">
          {acct_pill}
          &nbsp;<span class="pill {rt_cls}">{rt_txt}</span>
          &nbsp;·&nbsp; {len(trades)} signals logged
        </div>
      </div>
      <div>
        <div class="hero-price-label">{cur_ticker} live</div>
        <div class="hero-price">{price_html}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── derived stats ──
    total    = len(trades)
    buys     = sum(1 for t in trades if t["signal"] == "BUY")
    sells    = sum(1 for t in trades if t["signal"] == "SELL")
    holds    = sum(1 for t in trades if t["signal"] == "HOLD")
    acted    = sum(1 for t in trades if t["status"] in ("FILLED", "DRY_RUN"))
    avg_conf = sum(t["confidence"] for t in trades) / total
    act_rate = acted / total if total else 0

    def mcard(label, value, sub="", color="#e6e9ef"):
        return f"""<div class="mcard"><div class="mcard-label">{label}</div>
        <div class="mcard-value" style="color:{color}">{value}</div>
        <div class="mcard-sub">{sub}</div></div>"""

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(mcard("Total signals", total, "all-time"), unsafe_allow_html=True)
    c2.markdown(mcard("Buy", buys, f"{buys/total:.0%} of signals", C_BUY), unsafe_allow_html=True)
    c3.markdown(mcard("Sell", sells, f"{sells/total:.0%} of signals", C_SELL), unsafe_allow_html=True)
    c4.markdown(mcard("Acted on", acted, f"{act_rate:.0%} act rate"), unsafe_allow_html=True)
    c5.markdown(mcard("Avg confidence", f"{avg_conf:.0%}", "across all"), unsafe_allow_html=True)

    st.write("")

    # ── paper portfolio (current asset only — assets don't share a position) ──
    from src.trader.portfolio import replay
    pf = replay(trades, ticker=cur_ticker)

    st.markdown(f"##### Paper portfolio — {cur_asset['name']}")
    if pf["equity_curve"]:
        pnl = pf["total_pnl"]
        pnl_col = C_BUY if pnl >= 0 else C_SELL
        pnl_sign = "+" if pnl >= 0 else "−"
        win_txt = f"{pf['win_rate']:.0%} ({pf['wins']}/{pf['closed']})" if pf["win_rate"] is not None else "no closed trades yet"
        unreal = pf["unrealized"]
        unreal_col = C_BUY if unreal >= 0 else C_SELL

        p1, p2, p3, p4 = st.columns(4)
        p1.markdown(mcard("Equity", f"${pf['equity']:,.0f}", f"start ${pf['starting_usdt']:,.0f}"), unsafe_allow_html=True)
        p2.markdown(mcard("Total PnL", f"{pnl_sign}${abs(pnl):,.2f}", f"{pf['total_pnl_pct']:+.2f}%", pnl_col), unsafe_allow_html=True)
        p3.markdown(mcard("Win rate", win_txt.split(" ")[0] if pf["win_rate"] is not None else "—", win_txt if pf["win_rate"] is not None else "close a position first"), unsafe_allow_html=True)
        p4.markdown(mcard("Open position", f"{pf['open_qty']:.5f}" if pf["open_qty"] else "flat",
                          f"unrealized {'+' if unreal >= 0 else '−'}${abs(unreal):,.2f}" if pf["open_qty"] else "no exposure",
                          unreal_col if pf["open_qty"] else "#e6e9ef"), unsafe_allow_html=True)

        eq_df = pd.DataFrame(pf["equity_curve"])
        eq_df["ts"] = pd.to_datetime(eq_df["ts"])
        eq_color = C_BUY if pnl >= 0 else C_SELL
        area = alt.Chart(eq_df).mark_area(
            line={"color": eq_color, "strokeWidth": 1.8},
            color=alt.Gradient(
                gradient="linear",
                stops=[alt.GradientStop(color="transparent", offset=0),
                       alt.GradientStop(color=eq_color + "44", offset=1)],
                x1=1, x2=1, y1=1, y2=0,
            ),
        ).encode(
            x=alt.X("ts:T", title=None, axis=alt.Axis(format="%H:%M", grid=False)),
            y=alt.Y("equity:Q", title="USDT", scale=alt.Scale(zero=False),
                    axis=alt.Axis(grid=True, gridOpacity=0.08)),
            tooltip=[alt.Tooltip("ts:T", format="%b %d %H:%M"),
                     alt.Tooltip("equity:Q", format=",.2f"),
                     alt.Tooltip("price:Q", format=",.2f")],
        ).properties(height=170).configure_view(strokeWidth=0)
        st.altair_chart(area, use_container_width=True)
    else:
        st.caption("No acted-on trades yet — the portfolio replay starts once BUY/SELL signals clear the threshold.")

    st.write("")

    # ── signal quality scorecard ──
    from src.trader.scorecard import evaluate
    sc = evaluate(trades)
    sc_rows = []
    for hname, h in sc["horizons"].items():
        if h["BUY"]["total"] + h["SELL"]["total"] == 0:
            continue
        sc_rows.append({
            "Horizon": hname,
            "Overall": f"{h['overall_accuracy']:.0%}" if h["overall_accuracy"] is not None else "—",
            "BUY accuracy": f"{h['BUY']['accuracy']:.0%}" if h["BUY"]["accuracy"] is not None else "—",
            "BUY calls": h["BUY"]["total"],
            "BUY avg move": f"{h['BUY']['avg_move_pct']:+.2f}%" if h["BUY"]["avg_move_pct"] is not None else "—",
            "SELL accuracy": f"{h['SELL']['accuracy']:.0%}" if h["SELL"]["accuracy"] is not None else "—",
            "SELL calls": h["SELL"]["total"],
            "SELL avg move": f"{h['SELL']['avg_move_pct']:+.2f}%" if h["SELL"]["avg_move_pct"] is not None else "—",
        })
    st.markdown("##### Signal quality — was the analyzer right?")
    if sc_rows:
        st.dataframe(pd.DataFrame(sc_rows), width="stretch", hide_index=True)
        st.caption("A BUY is correct if price was higher N later; a SELL if lower. "
                   "Above ~55% overall and the signal has edge; near 50% it's a coin flip. "
                   f"{sc['pending']} signal/horizon pairs still waiting for enough later data.")
    else:
        st.caption("Needs more history — signals are scored against the price 1h/4h/24h after each call.")

    st.write("")

    # ── ML learning panel ──
    from src.ml.learner import stats as ml_stats
    ms = ml_stats()
    st.markdown("##### 🧠 Machine learning — learning from its own trades")
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(mcard("Outcomes learned", ms["total"],
                      f"goes active at {ms['min_samples']}"), unsafe_allow_html=True)
    acc_txt = f"{ms['recent_accuracy']:.0%}" if ms["recent_accuracy"] is not None else "—"
    acc_col = C_BUY if (ms["recent_accuracy"] or 0) >= 0.55 else "#e6e9ef"
    m2.markdown(mcard("Prediction accuracy", acc_txt, "last 50 outcomes", acc_col), unsafe_allow_html=True)
    gate_on = env_vals.get("ML_GATE", "true").lower() == "true"
    m3.markdown(mcard("Gate", "ACTIVE" if (ms["active"] and gate_on) else ("observing" if gate_on else "off"),
                      f"vetoes below {float(env_vals.get('ML_MIN_PROB') or 0.35):.0%}",
                      C_BUY if (ms["active"] and gate_on) else "#8a94a6"), unsafe_allow_html=True)
    base_txt = f"{ms['base_rate']:.0%}" if ms["base_rate"] is not None else "—"
    m4.markdown(mcard("Signal win rate", base_txt, "share of past signals that paid"), unsafe_allow_html=True)
    if ms["total"]:
        w = ms["weights"]
        learned = ", ".join(f"{k} {'+' if v >= 0 else '−'}{abs(v):.2f}"
                            for k, v in sorted(w.items(), key=lambda kv: -abs(kv[1])) if k != "bias")
        st.caption(f"Learned weights (what the model currently believes matters): {learned}. "
                   "Positive = that feature makes a signal more likely to profit. "
                   "The model retrains itself on every run as signal outcomes mature (~4h), "
                   "and its memory persists in `data/model.json` across restarts and log wipes.")
    else:
        st.caption("Cold start — the model trains itself automatically as signals mature (~4h after each call). "
                   "Run a simulation with 30+ cycles to bootstrap it with paper outcomes.")

    st.write("")

    # ── charts ──
    col_left, col_right = st.columns([1.9, 1])

    df = pd.DataFrame([{
        "time": pd.to_datetime(t["ts"]),
        "price": t["price"],
        "confidence": round(t["confidence"] * 100, 1),
        "signal": t["signal"],
        "status": t["status"],
        "reasoning": t["reasoning"] or "",
    } for t in reversed(trades[-60:])])

    sig_scale = alt.Scale(domain=["BUY", "SELL", "HOLD"], range=[C_BUY, C_SELL, C_HOLD])

    with col_left:
        st.markdown("##### Price & signal markers")
        price_df = df[df["price"].notna()]
        if not price_df.empty:
            line = alt.Chart(price_df).mark_line(color="#3b82f6", strokeWidth=1.6).encode(
                x=alt.X("time:T", title=None, axis=alt.Axis(format="%H:%M", grid=False)),
                y=alt.Y("price:Q", title="USDT", scale=alt.Scale(zero=False),
                        axis=alt.Axis(grid=True, gridOpacity=0.08)),
            )
            pts = alt.Chart(price_df[price_df["signal"] != "HOLD"]).mark_point(
                size=85, filled=True, opacity=0.95).encode(
                x="time:T", y="price:Q",
                color=alt.Color("signal:N", scale=sig_scale, legend=alt.Legend(orient="top", title=None)),
                shape=alt.Shape("signal:N", scale=alt.Scale(domain=["BUY", "SELL"], range=["triangle-up", "triangle-down"]), legend=None),
                tooltip=[alt.Tooltip("time:T", format="%b %d %H:%M"), "signal", "confidence", "reasoning"],
            )
            st.altair_chart((line + pts).properties(height=240).configure_view(strokeWidth=0), use_container_width=True)
        else:
            st.caption("No price data yet.")

        st.markdown("##### Confidence per signal")
        bars = alt.Chart(df).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X("time:T", title=None, axis=alt.Axis(format="%H:%M", grid=False)),
            y=alt.Y("confidence:Q", title="%", scale=alt.Scale(domain=[0, 100]),
                    axis=alt.Axis(grid=True, gridOpacity=0.08)),
            color=alt.Color("signal:N", scale=sig_scale, legend=None),
            tooltip=[alt.Tooltip("time:T", format="%b %d %H:%M"), "signal", "confidence", "status"],
        ).properties(height=160).configure_view(strokeWidth=0)
        st.altair_chart(bars, use_container_width=True)

    with col_right:
        st.markdown("##### Signal split")
        split_df = pd.DataFrame({"signal": ["BUY", "SELL", "HOLD"], "count": [buys, sells, holds]})
        donut = alt.Chart(split_df).mark_arc(innerRadius=58, cornerRadius=3).encode(
            theta=alt.Theta("count:Q"),
            color=alt.Color("signal:N", scale=sig_scale, legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["signal", "count"],
        ).properties(height=220).configure_view(strokeWidth=0)
        st.altair_chart(donut, use_container_width=True)

        latest = trades[0]
        lsig = latest["signal"]
        lcol = SIGNAL_COLORS.get(lsig, "#8a94a6")
        arrow = "▲" if lsig == "BUY" else ("▼" if lsig == "SELL" else "■")
        price_str = f"${latest['price']:,.2f}" if latest["price"] else "—"
        ts_str = latest["ts"][:16].replace("T", " ")
        st.markdown(f"""
        <div class="lspanel">
          <div class="mcard-label">Latest signal</div>
          <div style="margin:8px 0 12px;">
            <span class="schip" style="background:{lcol}22; color:{lcol};">{arrow} {lsig}</span>
          </div>
          <div class="ls-row"><span class="ls-k">Confidence</span><span class="ls-v">{latest['confidence']:.0%}</span></div>
          <div class="ls-row"><span class="ls-k">Price</span><span class="ls-v">{price_str}</span></div>
          <div class="ls-row"><span class="ls-k">Status</span><span class="ls-v" style="color:{lcol}">{latest['status']}</span></div>
          <div class="ls-row"><span class="ls-k">Time</span><span class="ls-v">{ts_str}</span></div>
          <div style="margin-top:10px; color:#8a94a6; font-size:0.82rem; line-height:1.4;">{latest['reasoning'] or ''}</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.markdown("##### Trade log")

    f1, f2, f3 = st.columns([2, 2, 1])
    sig_filter = f1.multiselect("Signal", ["BUY", "SELL", "HOLD"], default=["BUY", "SELL", "HOLD"])
    status_opts = sorted({t["status"] for t in trades})
    status_filter = f2.multiselect("Status", status_opts, default=status_opts)
    show_n = f3.number_input("Rows", min_value=5, max_value=200, value=25, step=5)

    filtered = [t for t in trades if t["signal"] in sig_filter and t["status"] in status_filter][:show_n]

    if filtered:
        log_df = pd.DataFrame([{
            "Time": t["ts"][:19].replace("T", " "),
            "Asset": t["ticker"],
            "Signal": t["signal"],
            "Conf": t["confidence"],
            "Price": t["price"],
            "Status": t["status"],
            "Reasoning": (t["reasoning"] or "")[:70],
        } for t in filtered])

        def color_signal(v):
            return f"color: {SIGNAL_COLORS.get(v, '#e6e9ef')}; font-weight: 700;"

        def shade_conf(v):
            # green background that deepens with confidence — no matplotlib needed
            if pd.isna(v):
                return ""
            alpha = 0.10 + 0.45 * float(v)
            return f"background-color: rgba(22,199,132,{alpha:.2f}); font-weight: 600;"

        styled = (log_df.style
                  .map(color_signal, subset=["Signal"])
                  .map(shade_conf, subset=["Conf"])
                  .format({"Conf": "{:.0%}", "Price": lambda v: f"${v:,.2f}" if pd.notna(v) else "—"}))
        st.dataframe(styled, width="stretch", hide_index=True,
                     column_config={"Conf": st.column_config.Column(width="small")})
    else:
        st.caption("No trades match the current filters.")

    st.download_button(
        "⬇ Export full trade log (CSV)",
        data=_csv_export(_db_mtime()),
        file_name=f"trades_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

    if "last_output" in st.session_state:
        failed = st.session_state.get("last_rc", 0) != 0
        with st.expander(("❌ " if failed else "") + f"Pipeline output — {st.session_state.get('last_run', '')}",
                         expanded=failed):
            st.code(st.session_state["last_output"], language="bash")


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

with tab_settings:
    st.markdown("### API keys & configuration")

    if st.session_state.pop("settings_saved", False):
        st.success("✅ Saved — applies from the next run, no restart needed.")

    if not ENV_PATH.exists():
        st.info("No `.env` file found — fill in the form below to create one.")

    current = load_env_file()

    st.info(
        "**No API keys needed for Claude or news.** Analysis runs inside your Claude Routine — "
        "Claude is the engine. News comes from free RSS feeds (CoinDesk, CoinTelegraph, Decrypt, "
        "Bitcoin Magazine) + Reddit. You only need free Binance testnet keys.",
        icon="ℹ️",
    )

    st.markdown("#### Account")
    acct = st.radio(
        "Trading account",
        ["🧪 Testnet — paper money", "🔴 Live — real money"],
        index=0 if current.get("BINANCE_TESTNET", "true").lower() == "true" else 1,
        horizontal=True,
        label_visibility="collapsed",
    )
    use_testnet = acct.startswith("🧪")
    if not use_testnet:
        st.error(
            "**Live account selected — orders use real funds.** Two extra protections stay on: "
            "dry-run is the default for every run, and turning it off requires a confirmation "
            "checkbox in the sidebar before any order is sent. Live keys come from binance.com, "
            "not the testnet site."
        )

    st.markdown("#### Binance API keys")
    a, b = st.columns(2)
    key_ph = "Testnet key" if use_testnet else "Live key (binance.com)"
    binance_key = a.text_input("API Key", value=current.get("BINANCE_API_KEY", ""), type="password",
                                placeholder=key_ph)
    binance_secret = b.text_input("API Secret", value=current.get("BINANCE_API_SECRET", ""), type="password",
                                   placeholder=key_ph.replace("key", "secret"))
    if use_testnet:
        st.caption("Get free testnet keys at [testnet.binance.vision](https://testnet.binance.vision/) → "
                   "Log in with GitHub → Generate HMAC_SHA256 Key. Testnet and live keys are different — "
                   "switching account means swapping keys too.")
    else:
        st.caption("Live keys: binance.com → API Management. Enable spot trading only; never enable withdrawals. "
                   "Testnet and live keys are different — switching account means swapping keys too.")

    st.markdown("#### Asset")
    from src.assets import ASSETS
    asset_opts = list(ASSETS.keys())
    cur_sym = current.get("TICKER", "BTCUSDT")
    if cur_sym not in asset_opts:
        asset_opts.insert(0, cur_sym)
    ticker = st.selectbox(
        "Asset to trade",
        asset_opts,
        index=asset_opts.index(cur_sym),
        format_func=lambda s: f"{ASSETS.get(s, {}).get('icon', '•')} "
                              f"{ASSETS.get(s, {}).get('name', s)}  ({s})"
                              + ("  — 📄 paper only" if ASSETS.get(s, {}).get("kind") == "stock" else ""),
    )
    sel_kind = ASSETS.get(ticker, {}).get("kind", "crypto")
    if sel_kind == "stock":
        st.info("📄 **Stocks are paper-only.** Prices come from Yahoo Finance, news from "
                "Yahoo/Google feeds — signals, paper portfolio, scorecard and ML all work, "
                "but no real orders are ever placed (Binance can't trade stocks).", icon="ℹ️")
    else:
        st.caption("Crypto trades on the selected Binance account (testnet/live).")

    st.markdown("#### Trading config")
    c, d, e = st.columns(3)
    c.text_input("Ticker (from Asset above)", value=ticker, disabled=True)
    threshold = d.number_input("Confidence threshold", 0.0, 1.0,
                                value=float(current.get("SIGNAL_CONFIDENCE_THRESHOLD", "0.65")),
                                step=0.05, format="%.2f", help="Signals below this are skipped")
    max_order = e.number_input("Max order (USDT)", 1.0,
                                value=float(current.get("MAX_ORDER_USDT", "100")), step=10.0)

    st.markdown("#### Risk management")
    r1, r2, r3 = st.columns(3)
    max_open = r1.number_input("Max exposure (USDT)", 1.0,
                               value=float(current.get("MAX_OPEN_USDT", "300")), step=50.0,
                               help="BUY signals are vetoed once this much is already in the position")
    stop_loss = r2.number_input("Stop-loss (%)", 0.0, 50.0,
                                value=float(current.get("STOP_LOSS_PCT", "2.5")), step=0.5,
                                help="Force-sell if the position drops this far below cost basis. 0 = off")
    take_profit = r3.number_input("Take-profit (%)", 0.0, 100.0,
                                  value=float(current.get("TAKE_PROFIT_PCT", "4")), step=0.5,
                                  help="Force-sell once the position is up this much — banks winners "
                                       "before sentiment noise gives them back. 0 = off")
    r4, r5 = st.columns(2)
    trend_filter = r4.toggle("Trend filter",
                             value=current.get("TREND_FILTER", "true").lower() == "true",
                             help="Veto BUY signals when price is below its 20-period (15m) moving average")
    adaptive_thr = r5.toggle("Adaptive thresholds",
                             value=current.get("ADAPTIVE_THRESHOLD", "true").lower() == "true",
                             help="Raise the confidence bar +15% for a side (BUY/SELL) while its rolling "
                                  "4h scorecard accuracy is under 50%")
    st.caption(f"Reward/risk shape: take-profit {take_profit:.1f}% vs stop-loss {stop_loss:.1f}% "
               f"≈ {take_profit/stop_loss if stop_loss else 0:.1f}:1 — "
               f"breakeven win rate ≈ {stop_loss/(stop_loss+take_profit)*100 if (stop_loss+take_profit) else 0:.0f}% before fees.")

    st.markdown("#### Machine learning")
    ml1, ml2, ml3 = st.columns(3)
    ml_gate = ml1.toggle("ML gate",
                         value=current.get("ML_GATE", "true").lower() == "true",
                         help="Once trained on 20+ outcomes, the learner vetoes low-probability "
                              "signals and scales order size by predicted edge")
    ml_min_prob = ml2.number_input("Veto below P(profit)", 0.05, 0.95,
                                   value=float(current.get("ML_MIN_PROB", "0.35")), step=0.05,
                                   format="%.2f")
    if ml3.button("🧹 Reset learning", help="Delete data/model.json — the model starts from scratch"):
        from src.ml import learner as _learner
        _learner.reset()
        st.success("Model reset — learning starts over from the next matured signal.")

    st.markdown("#### Alerts (optional)")
    g, h = st.columns(2)
    slack_url = g.text_input("Slack Webhook URL", value=current.get("SLACK_WEBHOOK_URL", ""),
                              placeholder="https://hooks.slack.com/services/...")
    alert_email = h.text_input("Alert Email", value=current.get("ALERT_EMAIL", ""),
                                placeholder="you@example.com")
    i, j = st.columns(2)
    sendgrid_key = i.text_input("SendGrid API Key", value=current.get("SENDGRID_API_KEY", ""),
                                 type="password", placeholder="SG....")
    from_email = j.text_input("From Email", value=current.get("FROM_EMAIL", ""),
                               placeholder="noreply@yourdomain.com")

    st.write("")
    s1, s2 = st.columns(2)
    if s1.button("💾 Save settings", type="primary", width="stretch"):
        new_env = {
            "BINANCE_API_KEY": binance_key,
            "BINANCE_API_SECRET": binance_secret,
            "BINANCE_TESTNET": "true" if use_testnet else "false",
            "TICKER": ticker,
            "SIGNAL_CONFIDENCE_THRESHOLD": f"{threshold:.2f}",
            "MAX_ORDER_USDT": str(max_order),
            "MAX_OPEN_USDT": str(max_open),
            "STOP_LOSS_PCT": str(stop_loss),
            "TAKE_PROFIT_PCT": str(take_profit),
            "TREND_FILTER": "true" if trend_filter else "false",
            "ADAPTIVE_THRESHOLD": "true" if adaptive_thr else "false",
            "ML_GATE": "true" if ml_gate else "false",
            "ML_MIN_PROB": f"{ml_min_prob:.2f}",
        }
        if slack_url:    new_env["SLACK_WEBHOOK_URL"] = slack_url
        if alert_email:  new_env["ALERT_EMAIL"] = alert_email
        if sendgrid_key: new_env["SENDGRID_API_KEY"] = sendgrid_key
        if from_email:   new_env["FROM_EMAIL"] = from_email
        save_env_file(new_env)
        st.session_state["settings_saved"] = True
        st.rerun()

    if s2.button("🔌 Test connections", width="stretch"):
        with st.spinner("Testing connections..."):
            rc, out = run_script(["check_connection.py"])
        (st.success if rc == 0 else st.error)(
            "All connections OK" if rc == 0 else "One or more connections failed")
        st.code(out, language="bash")
