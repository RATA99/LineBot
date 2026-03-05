"""
agent.py — AI Agent สำหรับ LINE Bot
ใช้ Qwen3 ตีความ intent จาก natural language แล้ว execute
"""
import os, json, re
from openai import OpenAI

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

SYSTEM_PROMPT = """คุณคือ AI Agent ผู้ช่วยวิเคราะห์หุ้นไทย (SET)
รับข้อความภาษาไทย/อังกฤษจาก user แล้วแปลงเป็น JSON action

Action ที่รองรับ:
- menu: แสดงเมนูหลัก (ไม่ต้องมี symbol ก็ได้)
- price: ดูราคา + signal
- analyze: วิเคราะห์ AI เต็มรูปแบบ
- chart: ดูกราฟ (ต้องมี tf = 15m/30m/1h/4h/1d)
- chart_all: กราฟครบ 5 TF
- alert_add: เพิ่มแจ้งเตือน
- alert_remove: ลบแจ้งเตือน
- alert_list: ดูรายการแจ้งเตือน
- popular: หุ้นยอดนิยม
- help: ช่วยเหลือ
- unknown: ไม่เข้าใจ

กฎ:
- symbol ให้ใช้ชื่อหุ้น SET ตัวพิมพ์ใหญ่ เช่น DELTA, PTT, AOT, KBANK
- tf ให้เลือกที่ใกล้เคียงที่สุด: 15m, 30m, 1h, 4h, 1d
  - "รายวัน/day/daily/D" → 1d
  - "4 ชั่วโมง/4H" → 4h
  - "1 ชั่วโมง/ชม/hourly/1H/H" → 1h
  - "30 นาที/30m" → 30m
  - "15 นาที/15m" → 15m
- ถ้าไม่ระบุ TF ให้ใช้ 1d เป็น default
- ถ้าไม่ระบุ symbol ให้ symbol = null

ตอบเป็น JSON เท่านั้น ห้าม markdown ห้าม backtick:
{"action": "...", "symbol": "...", "tf": "...", "confidence": 0.9, "reason": "..."}

ตัวอย่าง:
User: "ดูกราฟ delta แบบรายชั่วโมง" → {"action":"chart","symbol":"DELTA","tf":"1h","confidence":0.95,"reason":"ต้องการกราฟ 1H"}
User: "ptt ราคาเป็นยังไง" → {"action":"price","symbol":"PTT","tf":"1d","confidence":0.98,"reason":"ถามราคา"}
User: "วิเคราะห์ kbank ให้หน่อย" → {"action":"analyze","symbol":"KBANK","tf":"1d","confidence":0.97,"reason":"ต้องการวิเคราะห์"}
User: "กราฟ scb ทุก tf เลย" → {"action":"chart_all","symbol":"SCB","tf":"1d","confidence":0.95,"reason":"ต้องการครบ 5 TF"}
User: "แจ้งเตือนด้วย ถ้า delta วิ่ง" → {"action":"alert_add","symbol":"DELTA","tf":"1d","confidence":0.90,"reason":"ต้องการ monitor"}
User: "หุ้นน่าสนใจมีอะไรบ้าง" → {"action":"popular","symbol":null,"tf":null,"confidence":0.85,"reason":"ถามหุ้นยอดนิยม"}
User: "สวัสดี" → {"action":"menu","symbol":null,"tf":null,"confidence":0.99,"reason":"ทักทาย"}"""

def parse_intent(user_text: str) -> dict:
    """ส่งข้อความไปให้ AI ตีความ → คืน dict action"""
    if not GROQ_API_KEY:
        return {"action": "unknown", "symbol": None, "tf": "1d", "confidence": 0}
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
        res = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_text}
            ],
            max_tokens=200,
            temperature=0.1,  # ต้องการ consistent ไม่ creative
            timeout=15,
            extra_body={"thinking": {"type": "disabled"}},  # ปิด thinking mode เพื่อความเร็ว
        )
        raw = res.choices[0].message.content.strip()
        # ลบ <think>...</think> ถ้ามี
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
        # parse JSON
        return json.loads(raw)
    except json.JSONDecodeError:
        # ลอง extract JSON จาก response
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return {"action": "unknown", "symbol": None, "tf": "1d", "confidence": 0}
    except Exception as e:
        print(f"[Agent] Error: {e}")
        return {"action": "unknown", "symbol": None, "tf": "1d", "confidence": 0}
