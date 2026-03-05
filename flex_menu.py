"""
flex_menu.py — LINE Flex Message สำหรับ interactive UI
"""
from linebot.v3.messaging import FlexMessage, FlexContainer

def make_main_menu(symbol: str = "DELTA") -> FlexMessage:
    """เมนูหลัก — เลือกหุ้นและ action"""
    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{
                "type": "text",
                "text": "📈 SET Stock Sniper",
                "weight": "bold",
                "size": "xl",
                "color": "#00E676"
            }, {
                "type": "text",
                "text": f"หุ้นที่เลือก: {symbol}",
                "size": "sm",
                "color": "#aaaaaa"
            }],
            "backgroundColor": "#0d1117",
            "paddingAll": "16px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "backgroundColor": "#161b22",
            "contents": [
                _section_title("🔍 วิเคราะห์"),
                _btn_row([
                    _btn("📊 บทวิเคราะห์ AI", f"วิเคราะห์ {symbol}", "primary", "#FF6B35"),
                    _btn("💰 ราคา + Signal", f"ราคา {symbol}", "secondary", "#29B6F6"),
                ]),
                _section_title("📉 กราฟ"),
                _btn_row([
                    _btn("15m", f"กราฟ {symbol} 15m", "secondary", "#26a69a"),
                    _btn("30m", f"กราฟ {symbol} 30m", "secondary", "#26a69a"),
                    _btn("1H",  f"กราฟ {symbol} 1h",  "secondary", "#26a69a"),
                ]),
                _btn_row([
                    _btn("4H",  f"กราฟ {symbol} 4h",  "secondary", "#FFC107"),
                    _btn("Day", f"กราฟ {symbol} 1d",  "secondary", "#FFC107"),
                    _btn("All 5 TF", f"กราฟทั้งหมด {symbol}", "primary", "#CE93D8"),
                ]),
                _section_title("🔔 แจ้งเตือน"),
                _btn_row([
                    _btn("➕ เพิ่มแจ้งเตือน", f"แจ้งเตือน {symbol}", "primary",  "#00E676"),
                    _btn("➖ ยกเลิก",         f"หยุดแจ้งเตือน {symbol}", "secondary", "#ef5350"),
                ]),
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [{
                "type": "button",
                "action": {
                    "type": "message",
                    "label": "📋 รายการแจ้งเตือนของฉัน",
                    "text": "รายการ"
                },
                "style": "secondary",
                "color": "#21262d",
                "height": "sm"
            }],
            "backgroundColor": "#0d1117",
            "paddingAll": "10px"
        }
    }
    return FlexMessage(alt_text=f"Stock Sniper — {symbol}", contents=FlexContainer.from_dict(bubble))


def make_symbol_picker() -> FlexMessage:
    """Quick pick หุ้นยอดนิยม"""
    symbols = [
        ("DELTA", "#FF6B35"), ("PTT", "#29B6F6"),   ("AOT", "#00E676"),
        ("ADVANC", "#FFC107"), ("SCB", "#CE93D8"),  ("KBANK", "#ef5350"),
        ("BBL", "#80CBC4"),   ("CPALL", "#FF6B35"),  ("TRUE", "#29B6F6"),
        ("GULF", "#00E676"),
    ]
    rows = []
    for i in range(0, len(symbols), 3):
        chunk = symbols[i:i+3]
        rows.append(_btn_row([
            _btn(s, f"เมนู {s}", "secondary", c) for s, c in chunk
        ]))

    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{
                "type": "text",
                "text": "🏦 เลือกหุ้น",
                "weight": "bold",
                "size": "lg",
                "color": "#00E676"
            }, {
                "type": "text",
                "text": "หรือพิมพ์: เมนู [ชื่อหุ้น]",
                "size": "xs",
                "color": "#666666"
            }],
            "backgroundColor": "#0d1117",
            "paddingAll": "14px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "backgroundColor": "#161b22",
            "contents": rows
        }
    }
    return FlexMessage(alt_text="เลือกหุ้น", contents=FlexContainer.from_dict(bubble))


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _section_title(text: str) -> dict:
    return {
        "type": "text",
        "text": text,
        "size": "xs",
        "color": "#666666",
        "margin": "md"
    }

def _btn(label: str, msg: str, style: str = "secondary", color: str = "#29B6F6") -> dict:
    return {
        "type": "button",
        "action": {"type": "message", "label": label, "text": msg},
        "style": style,
        "color": color if style == "primary" else "#21262d",
        "height": "sm",
        "flex": 1
    }

def _btn_row(buttons: list) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "contents": buttons
    }
