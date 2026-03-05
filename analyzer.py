"""
analyzer.py — Stock analysis engine
ใช้ settrade_v2 + Groq AI วิเคราะห์หุ้น
"""
import os
import json
import pandas as pd
from settrade_v2 import Investor
from openai import OpenAI

# ─── Config ───────────────────────────────────────────────────────────────────
APP_ID       = os.environ.get("APP_ID",       "VMxlV5Hz3BvMkitL")
APP_SECRET   = os.environ.get("APP_SECRET",   "OecHOLQUlbnHevImrX68VPzEOCxqKaBbuatzq88LOmg=")
BROKER_ID    = os.environ.get("BROKER_ID",    "023")
APP_CODE     = os.environ.get("APP_CODE",     "ALGO_EQ")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ─── Settrade ─────────────────────────────────────────────────────────────────
def get_investor():
    return Investor(
        app_id=APP_ID, app_secret=APP_SECRET,
        broker_id=BROKER_ID, app_code=APP_CODE,
        is_auto_queue=False
    )

def get_data(symbol: str, interval: str = "1d", limit: int = 60) -> pd.DataFrame:
    try:
        investor = get_investor()
        market   = investor.MarketData()
        res      = market.get_candlestick(symbol=symbol.upper(), interval=interval, limit=limit)
        if not res:
            return pd.DataFrame()

        data = {k: v for k, v in res.items() if isinstance(v, list)}
        if not data or 'time' not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.columns = [c.lower() for c in df.columns]
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        df = df.sort_values('time').reset_index(drop=True)
        return df
    except Exception as e:
        return pd.DataFrame()

# ─── Indicators ───────────────────────────────────────────────────────────────
def calc_indicators(df: pd.DataFrame) -> dict:
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['EMA50']  = df['close'].ewm(span=50,  adjust=False).mean()

    high_p = df['high'].tail(30).max()
    low_p  = df['low'].tail(30).min()
    diff   = high_p - low_p

    return {
        'ema50':   df['EMA50'].iloc[-1],
        'ema200':  df['EMA200'].iloc[-1],
        'fib_236': low_p + diff * 0.236,
        'fib_382': low_p + diff * 0.382,
        'fib_500': low_p + diff * 0.500,
        'fib_618': low_p + diff * 0.618,
        'fib_786': low_p + diff * 0.786,
        'high_30': high_p,
        'low_30':  low_p,
    }

def get_signal(current_p: float, ind: dict) -> str:
    if current_p < ind['ema200']:
        return "🚨 CRITICAL"
    elif current_p < ind['fib_382']:
        return "📉 BEARISH"
    elif current_p < ind['fib_500']:
        return "⚖️ WATCH"
    elif current_p < ind['fib_618']:
        return "🔍 NEUTRAL"
    elif current_p < ind['fib_786']:
        return "💹 BULLISH"
    else:
        return "🚀 STRONG BULL"

# ─── Quick price summary ───────────────────────────────────────────────────────
def get_alert_message(symbol: str) -> str:
    df = get_data(symbol, interval="1d", limit=60)
    if df.empty:
        return f"❌ ไม่พบข้อมูล {symbol} กรุณาตรวจสอบชื่อหุ้น"

    ind       = calc_indicators(df)
    current_p = df['close'].iloc[-1]
    prev_p    = df['close'].iloc[-2]
    chg_pct   = (current_p - prev_p) / prev_p * 100
    signal    = get_signal(current_p, ind)
    vol       = df['volume'].iloc[-1]
    avg_vol   = df['volume'].tail(20).mean()
    vol_ratio = vol / avg_vol if avg_vol > 0 else 1

    return f"""{signal} — {symbol}

💰 ราคา  : {current_p:,.2f} บาท ({chg_pct:+.2f}%)
📊 Volume : {vol:,.0f} ({vol_ratio:.1f}x avg)
📈 EMA 50 : {ind['ema50']:,.2f}
📉 EMA 200: {ind['ema200']:,.2f}

Fibonacci (30 แท่ง):
• 38.2% = {ind['fib_382']:,.2f}
• 50.0% = {ind['fib_500']:,.2f}
• 61.8% = {ind['fib_618']:,.2f}"""

# ─── Full AI Analysis ─────────────────────────────────────────────────────────
def analyze_stock(symbol: str, interval: str = "1d") -> str:
    df = get_data(symbol, interval=interval, limit=60)
    if df.empty:
        return f"❌ ไม่พบข้อมูล {symbol}"

    ind       = calc_indicators(df)
    current_p = df['close'].iloc[-1]
    prev_p    = df['close'].iloc[-2]
    chg_pct   = (current_p - prev_p) / prev_p * 100
    avg_vol   = df['volume'].tail(20).mean()
    last_vol  = df['volume'].iloc[-1]
    vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1
    last10    = df.tail(10)[['time','open','high','low','close','volume']].to_dict(orient='records')

    if vol_ratio >= 2.0:
        vol_signal = f"🔴 Volume Spike {vol_ratio:.1f}x — Big Player"
    elif vol_ratio >= 1.3:
        vol_signal = f"🟡 Volume สูง {vol_ratio:.1f}x avg"
    else:
        vol_signal = f"⚪ Volume เบาบาง {vol_ratio:.1f}x — Low Volume Rebound"

    ema_signal = "เหนือ EMA 200 ✅" if current_p > ind['ema200'] else "ใต้ EMA 200 ❌"

    prompt = f"""Role: Senior Quant Trader 30 ปี วิเคราะห์หุ้นไทย (SET)
CRITICAL: R:R < 1:2 → SKIP เด็ดขาด | Volume เบาบาง ≠ Smart Money

[INPUT DATA]
Symbol: {symbol} | Price: {current_p:,.2f} ({chg_pct:+.2f}%)
EMA50: {ind['ema50']:,.2f} | EMA200: {ind['ema200']:,.2f} → {ema_signal}
30-Bar High: {ind['high_30']:,.2f} | Low: {ind['low_30']:,.2f}
Fibo: 38.2%={ind['fib_382']:,.2f} | 50%={ind['fib_500']:,.2f} | 61.8%={ind['fib_618']:,.2f}
Volume: {vol_signal}
10 แท่งล่าสุด: {json.dumps(last10, default=str, ensure_ascii=False)}

วิเคราะห์แบบกระชับสำหรับ LINE (ไม่เกิน 400 คำ) ใช้ภาษาไทย:
1. Verdict: BUY/WAIT/SKIP + เหตุผล 3 ข้อ
2. Entry / TP1 / TP2 / SL
3. R:R Ratio (คำนวณให้เห็น)
4. Warning 24 ชม."""

    if not GROQ_API_KEY:
        return "❌ ไม่พบ GROQ_API_KEY"

    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
        res = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user", "content": prompt}],
            timeout=45,
            max_tokens=800,
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"❌ AI Error: {str(e)}"
