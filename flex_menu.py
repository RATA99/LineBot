"""
flex_menu.py — LINE Flex Message UI
ปุ่มเมนูที่ trigger state machine รอรับชื่อหุ้นจาก user
"""
from linebot.v3.messaging import FlexMessage, FlexContainer

# ─── Main Menu (ไม่ hardcode symbol) ─────────────────────────────────────────
def make_main_menu(symbol: str = None) -> FlexMessage:
    subtitle = f"หุ้น: {symbol}" if symbol else "กดปุ่มเพื่อเริ่ม"
    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0d1117",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "📈 SET Stock Sniper", "weight": "bold",
                 "size": "xl", "color": "#00E676"},
                {"type": "text", "text": subtitle, "size": "sm", "color": "#888888"},
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "backgroundColor": "#161b22",
            "paddingAll": "14px",
            "contents": [
                # ── Search ──
                _section("🔍 ค้นหาหุ้น"),
                _row([
                    _btn("🔎 ค้นหาหุ้น", "ค้นหา", "primary", "#FF6B35"),
                    _btn("⭐ หุ้นยอดนิยม", "หุ้น", "secondary", "#29B6F6"),
                ]),
                # ── Analyze ──
                _section("📊 วิเคราะห์"),
                _row([
                    _btn("🧠 วิเคราะห์ AI", "วิเคราะห์", "primary", "#FF6B35"),
                    _btn("💰 ดูราคา", "ราคา", "secondary", "#29B6F6"),
                ]),
                # ── Chart ──
                _section("📉 กราฟ"),
                _row([
                    _btn("📊 กราฟ (เลือก TF)", "กราฟ", "secondary", "#26a69a"),
                    _btn("🗂 ครบ 5 TF", "กราฟทั้งหมด", "primary", "#CE93D8"),
                ]),
                # ── Alert ──
                _section("🔔 แจ้งเตือน"),
                _row([
                    _btn("➕ เพิ่มแจ้งเตือน", "แจ้งเตือน", "primary", "#00E676"),
                    _btn("📋 รายการ", "รายการ", "secondary", "#FFC107"),
                ]),
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0d1117",
            "paddingAll": "10px",
            "contents": [{
                "type": "button",
                "action": {"type": "message", "label": "❓ ช่วยเหลือ", "text": "ช่วยเหลือ"},
                "style": "secondary",
                "color": "#21262d",
                "height": "sm"
            }]
        }
    }
    return FlexMessage(alt_text="SET Stock Sniper Menu",
                       contents=FlexContainer.from_dict(bubble))


def make_symbol_picker() -> FlexMessage:
    """Quick pick หุ้นยอดนิยม — กดแล้วแสดงเมนูของหุ้นนั้นเลย"""
    symbols = [
        ("DELTA", "#FF6B35"), ("PTT", "#29B6F6"),   ("AOT", "#00E676"),
        ("ADVANC","#FFC107"), ("SCB", "#CE93D8"),   ("KBANK","#ef5350"),
        ("BBL",  "#80CBC4"), ("CPALL","#FF6B35"),   ("TRUE", "#29B6F6"),
        ("GULF", "#00E676"), ("MINT", "#FFC107"),   ("CPN", "#CE93D8"),
    ]
    rows = []
    for i in range(0, len(symbols), 3):
        chunk = symbols[i:i+3]
        rows.append(_row([_btn(s, f"เมนู {s}", "secondary", c) for s, c in chunk]))

    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0d1117",
            "paddingAll": "14px",
            "contents": [
                {"type": "text", "text": "⭐ หุ้นยอดนิยม", "weight": "bold",
                 "size": "lg", "color": "#FFC107"},
                {"type": "text",
                 "text": "หรือพิมพ์ชื่อหุ้นเองได้เลย เช่น: เมนู DELTA",
                 "size": "xs", "color": "#666666", "wrap": True},
            ]
        },
        "body": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "backgroundColor": "#161b22", "paddingAll": "12px",
            "contents": rows
        }
    }
    return FlexMessage(alt_text="เลือกหุ้น",
                       contents=FlexContainer.from_dict(bubble))


def make_tf_picker(symbol: str) -> FlexMessage:
    """เลือก Timeframe สำหรับหุ้นที่ระบุ"""
    tfs = [
        ("15m", "15 นาที", "#80CBC4"),
        ("30m", "30 นาที", "#26a69a"),
        ("1h",  "1 ชั่วโมง","#29B6F6"),
        ("4h",  "4 ชั่วโมง","#FFC107"),
        ("1d",  "รายวัน",   "#FF6B35"),
    ]
    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0d1117",
            "paddingAll": "14px",
            "contents": [
                {"type": "text", "text": f"📉 เลือก Timeframe — {symbol}",
                 "weight": "bold", "size": "md", "color": "#00E676"},
            ]
        },
        "body": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "backgroundColor": "#161b22", "paddingAll": "12px",
            "contents": [
                _row([_btn(label, f"กราฟ {symbol} {tf}", "secondary", color)
                      for tf, label, color in tfs[:3]]),
                _row([
                    _btn(tfs[3][1], f"กราฟ {symbol} {tfs[3][0]}", "secondary", tfs[3][2]),
                    _btn(tfs[4][1], f"กราฟ {symbol} {tfs[4][0]}", "secondary", tfs[4][2]),
                    _btn("🗂 ทั้งหมด", f"กราฟทั้งหมด {symbol}", "primary", "#CE93D8"),
                ]),
            ]
        }
    }
    return FlexMessage(alt_text=f"เลือก TF — {symbol}",
                       contents=FlexContainer.from_dict(bubble))


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _section(text: str) -> dict:
    return {"type": "text", "text": text, "size": "xs",
            "color": "#555555", "margin": "md"}

def _btn(label: str, msg: str, style: str = "secondary", color: str = "#29B6F6") -> dict:
    return {
        "type": "button",
        "action": {"type": "message", "label": label, "text": msg},
        "style": style,
        "color": color if style == "primary" else "#21262d",
        "height": "sm", "flex": 1
    }

def _row(buttons: list) -> dict:
    return {"type": "box", "layout": "horizontal",
            "spacing": "sm", "contents": buttons}
