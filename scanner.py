"""
scanner.py - SET Market Scanner
สแกนหาหุ้น Breakout + Volume Surge
"""
import os, json
from openai import OpenAI
from analyzer import get_data, calc_indicators

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

SCAN_UNIVERSE = [
    "DELTA","PTT","AOT","ADVANC","SCB","KBANK","BBL","CPALL",
    "TRUE","GULF","MINT","CPN","PTTEP","IVL","BH","BDMS",
    "HMPRO","LH","MTC","SAWAD","TIDLOR","OSP","GPSC","EGCO",
    "RATCH","BGRIM","EA","WHA","AMATA","STEC","CK","BEM",
    "BTS","VGI","MAJOR","JMT","BAM","RS","WORK","SET50",
]

def scan_one(symbol):
    try:
        df = get_data(symbol, interval="1d", limit=60)
        if df.empty or len(df) < 21:
            return None

        ind = calc_indicators(df)
        cur = df["close"].iloc[-1]
        prv = df["close"].iloc[-2]
        chg = (cur - prv) / prv * 100

        avg_vol = df["volume"].tail(20).mean()
        last_vol = df["volume"].iloc[-1]
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1

        resist = df["close"].iloc[-21:-1].max()
        near_break = cur >= resist * 0.98
        broke_out = cur > resist
        ema_bull = ind["ema50"] > ind["ema200"]

        score = 0
        tags = []

        if vol_ratio >= 2.5:
            score += 45
            tags.append("Volume {:.1f}x".format(vol_ratio))
        elif vol_ratio >= 1.8:
            score += 30
            tags.append("Volume {:.1f}x".format(vol_ratio))
        elif vol_ratio >= 1.4:
            score += 15
            tags.append("Volume {:.1f}x".format(vol_ratio))

        if broke_out:
            score += 40
            tags.append("Breakout")
        elif near_break:
            score += 22
            tags.append("Pre-Breakout")

        if ema_bull:
            score += 15
            tags.append("Uptrend")

        if chg > 1.5:
            score += 10
            tags.append("+{:.1f}%".format(chg))

        if score < 50:
            return None

        return {
            "symbol": symbol,
            "price": cur,
            "chg": chg,
            "vol_ratio": vol_ratio,
            "score": score,
            "tags": tags,
            "resist": resist,
            "fib382": ind["fib_382"],
            "fib500": ind["fib_500"],
            "fib618": ind["fib_618"],
            "ema50": ind["ema50"],
            "ema200": ind["ema200"],
        }
    except Exception as e:
        print("[Scanner] {}: {}".format(symbol, e))
        return None

def build_summary(candidates):
    lines = ["Scan พบ {} ตัว\n".format(len(candidates))]
    icons = {90: "🔴", 70: "🟠", 50: "🟡"}
    for i, c in enumerate(candidates[:10], 1):
        icon = "🔴" if c["score"] >= 90 else "🟠" if c["score"] >= 70 else "🟡"
        lines.append("{} {}. {} {:.2f} ({:+.1f}%)".format(
            icon, i, c["symbol"], c["price"], c["chg"]))
        lines.append("   Vol: {:.1f}x | Score: {}/100".format(c["vol_ratio"], c["score"]))
        lines.append("   " + " | ".join(c["tags"][:3]))
        lines.append("")
    return "\n".join(lines)

def ai_analyze(candidates):
    if not candidates or not GROQ_API_KEY:
        return ""
    top = candidates[:5]
    data = json.dumps([{
        "symbol": c["symbol"],
        "price": round(c["price"], 2),
        "chg": round(c["chg"], 2),
        "vol_ratio": round(c["vol_ratio"], 1),
        "score": c["score"],
        "tags": c["tags"],
        "resist": round(c["resist"], 2),
        "fib382": round(c["fib382"], 2),
        "fib500": round(c["fib500"], 2),
        "fib618": round(c["fib618"], 2),
        "ema200": round(c["ema200"], 2),
    } for c in top], ensure_ascii=False, indent=2)

    prompt = (
        "Role: Senior Quant Trader 30 ปี\n"
        "CRITICAL: R:R < 1:2 ให้ระบุ SKIP เด็ดขาด\n\n"
        "Scan Data:\n" + data + "\n\n"
        "วิเคราะห์แต่ละหุ้น (ภาษาไทย ไม่เกิน 900 คำ):\n"
        "1. Entry Zone (อ้างอิง Fibo/EMA)\n"
        "2. TP1 / TP2\n"
        "3. Stop Loss\n"
        "4. R:R Ratio (ถ้า < 1:2 = SKIP)\n"
        "5. Trigger ที่ต้องรอก่อนเข้า\n\n"
        "สรุปท้าย: ตัวไหน Win Rate สูงสุดและทำไม"
    )
    try:
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEY
        )
        res = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
            temperature=0.2,
            timeout=50,
        )
        return res.choices[0].message.content
    except Exception as e:
        return "AI Error: {}".format(e)

def run_scan():
    candidates = []
    for sym in SCAN_UNIVERSE:
        r = scan_one(sym)
        if r:
            candidates.append(r)
    candidates.sort(key=lambda x: x["score"], reverse=True)
    summary = build_summary(candidates) if candidates else "ไม่พบสัญญาณวันนี้ครับ"
    ai_text = ai_analyze(candidates) if candidates else ""
    return candidates, summary, ai_text
