"""
chart.py — Candlestick + EMA + Fibonacci + Volume + Pattern labels
"""
import os, io, requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
from matplotlib.gridspec import GridSpec
import pandas as pd
import numpy as np
from analyzer import get_data, calc_indicators, get_signal

CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY    = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")

INTERVAL_MAP = {
    "15m": ("15m",  "15 นาที",   100),
    "30m": ("30m",  "30 นาที",   100),
    "1h":  ("60m",  "1 ชั่วโมง", 100),
    "4h":  ("240m", "4 ชั่วโมง", 80),
    "1d":  ("1d",   "รายวัน",    60),
}

BG     = '#0d1117'
PANEL  = '#161b22'
GREEN  = '#26a69a'
RED    = '#ef5350'
GRID   = '#21262d'
TEXT   = '#c9d1d9'
YELLOW = '#FFC107'
BLUE   = '#29B6F6'
ORANGE = '#FF6B35'

# ─── Candle pattern detector ──────────────────────────────────────────────────
def detect_pattern(df: pd.DataFrame) -> list[tuple[int, str, str]]:
    """คืน list ของ (index, pattern_name, color)"""
    patterns = []
    for i in range(2, len(df)):
        o, h, l, c = df['open'].iloc[i], df['high'].iloc[i], df['low'].iloc[i], df['close'].iloc[i]
        po, ph, pl, pc = df['open'].iloc[i-1], df['high'].iloc[i-1], df['low'].iloc[i-1], df['close'].iloc[i-1]
        body = abs(c - o)
        rng  = h - l if h != l else 0.001
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        # Bullish Engulfing
        if pc < po and c > o and c > po and o < pc:
            patterns.append((i, 'Engulf↑', GREEN))
        # Bearish Engulfing
        elif pc > po and c < o and c < po and o > pc:
            patterns.append((i, 'Engulf↓', RED))
        # Hammer (lower wick >= 2x body, small upper wick)
        elif lower_wick >= 2 * body and upper_wick <= body * 0.3 and body > 0:
            patterns.append((i, 'Hammer', GREEN))
        # Shooting Star
        elif upper_wick >= 2 * body and lower_wick <= body * 0.3 and body > 0:
            patterns.append((i, 'Star↓', RED))
        # Doji
        elif body / rng < 0.1:
            patterns.append((i, 'Doji', YELLOW))

    # เอาแค่ 5 อันล่าสุด
    return patterns[-5:]

# ─── Upload Cloudinary ────────────────────────────────────────────────────────
def upload_cloudinary(img_bytes: bytes) -> str | None:
    if not CLOUDINARY_CLOUD_NAME:
        print("[Cloudinary] ไม่พบ CLOUDINARY_CLOUD_NAME")
        return None
    try:
        import hashlib, time as _time
        timestamp  = str(int(_time.time()))
        folder     = "stock_sniper"
        to_sign    = f"folder={folder}&timestamp={timestamp}{CLOUDINARY_API_SECRET}"
        signature  = hashlib.sha1(to_sign.encode()).hexdigest()

        res = requests.post(
            f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/image/upload",
            data={
                "api_key":   CLOUDINARY_API_KEY,
                "timestamp": timestamp,
                "signature": signature,
                "folder":    folder,
            },
            files={"file": ("chart.png", img_bytes, "image/png")},
            timeout=30,
        )
        data = res.json()
        if "secure_url" in data:
            return data["secure_url"]
        print(f"[Cloudinary] Error: {data}")
        return None
    except Exception as e:
        print(f"[Cloudinary] Exception: {e}")
        return None

# ─── Draw Chart ───────────────────────────────────────────────────────────────
def draw_chart(df: pd.DataFrame, symbol: str, tf_label: str, ind: dict) -> bytes:
    fig = plt.figure(figsize=(14, 9), facecolor=BG)
    gs  = GridSpec(4, 1, figure=fig, hspace=0.06,
                   height_ratios=[3.2, 0.8, 0.8, 0.8])

    ax_c  = fig.add_subplot(gs[0])   # Candle + EMA + Fibo
    ax_v  = fig.add_subplot(gs[1])   # Volume
    ax_m  = fig.add_subplot(gs[2])   # MACD (approximated)
    ax_r  = fig.add_subplot(gs[3])   # RSI

    for ax in [ax_c, ax_v, ax_m, ax_r]:
        ax.set_facecolor(PANEL)
        ax.tick_params(colors=TEXT, labelsize=7)
        ax.grid(color=GRID, linewidth=0.4, alpha=0.6)
        for spine in ax.spines.values():
            spine.set_color(GRID)

    n = len(df)
    xs = np.arange(n)

    # ── Candles ──
    for i, row in enumerate(df.itertuples()):
        color = GREEN if row.close >= row.open else RED
        ax_c.plot([i, i], [row.low, row.high], color=color, linewidth=0.7, zorder=2)
        bh = max(abs(row.close - row.open), 0.01)
        by = min(row.close, row.open)
        rect = Rectangle((i - 0.38, by), 0.76, bh,
                          facecolor=color, edgecolor=color,
                          linewidth=0.4, zorder=3)
        ax_c.add_patch(rect)

    # ── EMA ──
    ax_c.plot(xs, df['EMA50'],  color=BLUE,   linewidth=1.1, linestyle='--',
              label='EMA50', alpha=0.9, zorder=4)
    ax_c.plot(xs, df['EMA200'], color=ORANGE, linewidth=1.4,
              label='EMA200', alpha=0.9, zorder=4)

    # ── Fibonacci ──
    fibo_cfg = [
        ('23.6%', ind['fib_236'], '#80CBC4', ':'),
        ('38.2%', ind['fib_382'], '#00E676', '--'),
        ('50.0%', ind['fib_500'], YELLOW,    '--'),
        ('61.8%', ind['fib_618'], RED,       '--'),
        ('78.6%', ind['fib_786'], '#CE93D8', ':'),
    ]
    price_min = df['low'].min()
    price_max = df['high'].max()

    for lbl, val, color, ls in fibo_cfg:
        if price_min * 0.99 <= val <= price_max * 1.01:
            ax_c.axhline(y=val, color=color, linewidth=0.9,
                         linestyle=ls, alpha=0.85, zorder=1)
            ax_c.text(n + 0.3, val, f'Fibo {lbl} {val:,.1f}',
                      color=color, fontsize=6.5, va='center',
                      fontweight='bold')

    # ── Candle Patterns ──
    patterns = detect_pattern(df)
    for idx, name, color in patterns:
        y = df['high'].iloc[idx] * 1.003
        ax_c.annotate(name, xy=(idx, y), fontsize=6, color=color,
                      ha='center', fontweight='bold',
                      bbox=dict(boxstyle='round,pad=0.2', facecolor=PANEL,
                                edgecolor=color, alpha=0.8))

    # ── Signal + Title ──
    current_p = df['close'].iloc[-1]
    prev_p    = df['close'].iloc[-2]
    chg_pct   = (current_p - prev_p) / prev_p * 100
    signal    = get_signal(current_p, ind)
    sig_color = GREEN if 'BULL' in signal else RED if ('BEAR' in signal or 'CRITICAL' in signal) else YELLOW

    ax_c.set_title(
        f'{symbol}  [{tf_label}]   {signal}   {current_p:,.2f} ({chg_pct:+.2f}%)',
        color=sig_color, fontsize=12, fontweight='bold',
        pad=8, loc='left'
    )

    # X ticks
    step   = max(1, n // 8)
    ticks  = list(range(0, n, step))
    labels = [df['time'].iloc[i].strftime('%d/%m\n%H:%M') for i in ticks]
    ax_c.set_xticks(ticks); ax_c.set_xticklabels(labels, color=TEXT, fontsize=6.5)
    ax_c.set_xlim(-1, n + 8)
    ax_c.yaxis.tick_right()
    ax_c.legend(loc='upper left', fontsize=7, facecolor=PANEL,
                labelcolor=TEXT, framealpha=0.8, edgecolor=GRID)

    # ── Volume ──
    avg_vol = df['volume'].mean()
    for i, row in enumerate(df.itertuples()):
        color = GREEN if row.close >= row.open else RED
        ax_v.bar(i, row.volume, color=color, alpha=0.7, width=0.8)
    ax_v.axhline(y=avg_vol, color=YELLOW, linewidth=0.8, linestyle='--', alpha=0.8)
    ax_v.set_xlim(-1, n + 8)
    ax_v.yaxis.tick_right()
    ax_v.set_ylabel('Vol', color=TEXT, fontsize=7)
    ax_v.yaxis.set_label_position('right')
    ax_v.set_xticks([])

    # ── MACD (12/26/9) ──
    ema12  = df['close'].ewm(span=12, adjust=False).mean()
    ema26  = df['close'].ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal_line = macd.ewm(span=9, adjust=False).mean()
    hist   = macd - signal_line

    ax_m.plot(xs, macd,        color=BLUE,   linewidth=0.9, label='MACD')
    ax_m.plot(xs, signal_line, color=ORANGE, linewidth=0.9, label='Signal')
    for i, v in enumerate(hist):
        ax_m.bar(i, v, color=GREEN if v >= 0 else RED, alpha=0.6, width=0.8)
    ax_m.axhline(0, color=GRID, linewidth=0.5)
    ax_m.set_xlim(-1, n + 8)
    ax_m.yaxis.tick_right()
    ax_m.set_ylabel('MACD', color=TEXT, fontsize=7)
    ax_m.yaxis.set_label_position('right')
    ax_m.set_xticks([])
    ax_m.legend(loc='upper left', fontsize=6, facecolor=PANEL,
                labelcolor=TEXT, framealpha=0.7, edgecolor=GRID)

    # ── RSI (14) ──
    delta = df['close'].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))

    ax_r.plot(xs, rsi, color='#AB47BC', linewidth=1.0, label='RSI(14)')
    ax_r.axhline(70, color=RED,   linewidth=0.7, linestyle='--', alpha=0.7)
    ax_r.axhline(30, color=GREEN, linewidth=0.7, linestyle='--', alpha=0.7)
    ax_r.fill_between(xs, rsi, 70, where=(rsi >= 70), alpha=0.15, color=RED)
    ax_r.fill_between(xs, rsi, 30, where=(rsi <= 30), alpha=0.15, color=GREEN)
    ax_r.set_xlim(-1, n + 8)
    ax_r.set_ylim(0, 100)
    ax_r.yaxis.tick_right()
    ax_r.set_ylabel('RSI', color=TEXT, fontsize=7)
    ax_r.yaxis.set_label_position('right')

    step2  = max(1, n // 8)
    ticks2 = list(range(0, n, step2))
    lbl2   = [df['time'].iloc[i].strftime('%d/%m\n%H:%M') for i in ticks2]
    ax_r.set_xticks(ticks2)
    ax_r.set_xticklabels(lbl2, color=TEXT, fontsize=6.5)

    plt.tight_layout(pad=0.8)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=130, facecolor=BG, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.read()

# ─── Public API ───────────────────────────────────────────────────────────────
def get_chart_url(symbol: str, tf_key: str) -> tuple:
    if tf_key not in INTERVAL_MAP:
        return None, f"Timeframe '{tf_key}' ไม่รองรับ\nใช้: 15m, 30m, 1h, 4h, 1d"

    interval, tf_label, limit = INTERVAL_MAP[tf_key]
    df = get_data(symbol, interval=interval, limit=limit)
    if df.empty:
        return None, f"❌ ไม่พบข้อมูล {symbol} ({tf_label})"

    ind = calc_indicators(df)
    df['EMA50']  = df['close'].ewm(span=50,  adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    df = df.reset_index(drop=True)

    try:
        img_bytes = draw_chart(df, symbol, tf_label, ind)
    except Exception as e:
        return None, f"❌ สร้างกราฟไม่ได้: {e}"

    url = upload_cloudinary(img_bytes)
    if not url:
        return None, "❌ Upload ไม่สำเร็จ — เช็ค IMGUR_CLIENT_ID"

    return url, ""
