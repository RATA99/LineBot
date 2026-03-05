"""
agent.py — AI Agent + keyword fallback
"""
import os, json, re
from openai import OpenAI

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

SYSTEM_PROMPT = """You are a Thai stock (SET) chatbot intent parser.
Parse user message and return ONLY a JSON object. No markdown, no explanation, no <think> tags.

Actions: menu, price, analyze, chart, chart_all, alert_add, alert_remove, alert_list, popular, help, unknown

TF mapping: "รายวัน/day/1d/D" → 1d | "4h/4ชม" → 4h | "1h/ชม/hourly" → 1h | "30m/30นาที" → 30m | "15m/15นาที" → 15m

Output format (JSON only):
{"action":"...","symbol":"DELTA","tf":"1d","confidence":0.95}

Examples:
"ดูกราฟ delta ชั่วโมง" → {"action":"chart","symbol":"DELTA","tf":"1h","confidence":0.95}
"ptt ราคาเท่าไร" → {"action":"price","symbol":"PTT","tf":"1d","confidence":0.98}
"วิเคราะห์ kbank" → {"action":"analyze","symbol":"KBANK","tf":"1d","confidence":0.97}
"กราฟ aot ทุก tf" → {"action":"chart_all","symbol":"AOT","tf":"1d","confidence":0.95}
"แจ้งเตือน scb" → {"action":"alert_add","symbol":"SCB","tf":"1d","confidence":0.92}
"สวัสดี" → {"action":"menu","symbol":null,"tf":"1d","confidence":0.99}
"หุ้นน่าสนใจ" → {"action":"popular","symbol":null,"tf":"1d","confidence":0.90}"""

# ─── Keyword fallback (ทำงานแม้ AI fail) ────────────────────────────────────
def keyword_parse(text: str) -> dict | None:
    t = text.lower().strip()

    # extract symbol — หาคำที่เป็น uppercase 2-6 ตัวอักษร
    sym_match = re.search(r'\b([A-Z]{2,6})\b', text.upper())
    symbol = sym_match.group(1) if sym_match else None

    # extract TF
    tf = "1d"
    if re.search(r'15\s*m|15\s*นาที', t):        tf = "15m"
    elif re.search(r'30\s*m|30\s*นาที', t):       tf = "30m"
    elif re.search(r'1\s*h|ชั่วโมง|ชม\b|hourly', t): tf = "1h"
    elif re.search(r'4\s*h|4\s*ชม|4\s*ชั่วโมง', t): tf = "4h"
    elif re.search(r'day|รายวัน|1\s*d\b', t):      tf = "1d"

    # action keywords
    if any(k in t for k in ['สวัสดี','หวัดดี','hello','hi','เมนู','menu','start']):
        return {"action": "menu", "symbol": symbol, "tf": tf, "confidence": 0.99}
    if any(k in t for k in ['ช่วยเหลือ','help','?','วิธีใช้']):
        return {"action": "help", "symbol": None, "tf": tf, "confidence": 0.99}
    if any(k in t for k in ['ยอดนิยม','หุ้นดัง','popular','น่าสนใจ','แนะนำ']) and not symbol:
        return {"action": "popular", "symbol": None, "tf": tf, "confidence": 0.90}
    if any(k in t for k in ['รายการแจ้งเตือน','watchlist','รายการ']) and not any(k in t for k in ['เพิ่ม','แจ้ง']):
        return {"action": "alert_list", "symbol": None, "tf": tf, "confidence": 0.95}
    if any(k in t for k in ['ยกเลิกแจ้งเตือน','หยุดแจ้ง','ลบแจ้ง','unmonitor']):
        return {"action": "alert_remove", "symbol": symbol, "tf": tf, "confidence": 0.92}
    if any(k in t for k in ['แจ้งเตือน','monitor','แจ้งให้รู้','แจ้ง']):
        return {"action": "alert_add", "symbol": symbol, "tf": tf, "confidence": 0.90}
    if any(k in t for k in ['ทุก tf','ทุกtf','all tf','5 tf','ครบ tf','ทุกกราฟ','กราฟทั้งหมด']):
        return {"action": "chart_all", "symbol": symbol, "tf": tf, "confidence": 0.95}
    if any(k in t for k in ['กราฟ','chart','แท่งเทียน','แคนเดิ้ล']):
        return {"action": "chart", "symbol": symbol, "tf": tf, "confidence": 0.93}
    if any(k in t for k in ['วิเคราะห์','analyze','วิเคาระห์','วิเคาะห์','analysis']):
        return {"action": "analyze", "symbol": symbol, "tf": tf, "confidence": 0.95}
    if any(k in t for k in ['ราคา','price','ราคาเท่า','เท่าไร','เป็นยังไง','เป็นไง','อยู่ที่']):
        return {"action": "price", "symbol": symbol, "tf": tf, "confidence": 0.92}

    if any(k in t for k in ['สแกน','scan','breakout','เบรก','เบรคเอ้าท์','วิ่ง','ระเบิด','ปิดทอง','หาหุ้น','หุ้นน่าซื้อ','หุ้นวิ่ง']):
        return {"action": "scan", "symbol": None, "tf": tf, "confidence": 0.92}

    return None  # ไม่ match → ให้ AI ลอง

# ─── AI parse ────────────────────────────────────────────────────────────────
def ai_parse(text: str) -> dict | None:
    if not GROQ_API_KEY:
        return None
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
        res = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": text}
            ],
            max_tokens=150,
            temperature=0.1,
            timeout=10,
            extra_body={"chat_template_kwargs": {"thinking_mode": "off"}},
        )
        raw = res.choices[0].message.content.strip()
        # ลบ <think> blocks
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
        # ลบ markdown backticks
        raw = re.sub(r'```json|```', '', raw).strip()
        # หา JSON
        match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"[Agent/AI] {e}")
    return None

# ─── Main: keyword first, AI fallback ────────────────────────────────────────
def parse_intent(text: str) -> dict:
    # 1. keyword match (เร็ว ไม่พัง)
    result = keyword_parse(text)
    if result:
        print(f"[Agent/KW] {text!r} → {result}")
        return result

    # 2. AI parse (ช้ากว่า แต่เข้าใจ natural language)
    result = ai_parse(text)
    if result:
        print(f"[Agent/AI] {text!r} → {result}")
        return result

    # 3. fallback default
    print(f"[Agent/??] ไม่เข้าใจ: {text!r}")
    return {"action": "unknown", "symbol": None, "tf": "1d", "confidence": 0.0}
