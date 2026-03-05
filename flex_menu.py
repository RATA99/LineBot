"""
flex_menu.py — LINE Flex Message UI (Carousel style)
"""
from linebot.v3.messaging import FlexMessage, FlexContainer

# ─── Main Menu ────────────────────────────────────────────────────────────────
def make_main_menu(symbol: str = None) -> FlexMessage:
    subtitle = f"📌 หุ้น: {symbol}" if symbol else "พิมพ์ชื่อหุ้น หรือเลือกจากเมนู"
    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0d1117",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "📈 SET Stock Sniper",
                 "weight": "bold", "size": "xl", "color": "#00E676"},
                {"type": "text", "text": subtitle,
                 "size": "sm", "color": "#888888", "wrap": True},
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "backgroundColor": "#161b22",
            "paddingAll": "14px",
            "contents": [
                # ── ค้นหา ──
                _full_btn("🔎  ค้นหาหุ้น  (พิมพ์ชื่อใดก็ได้)", "ค้นหา", "#FF6B35"),
                _full_btn("⭐  หุ้นยอดนิยม", "หุ้น", "#FFC107"),
                _divider(),
                # ── วิเคราะห์ ──
                _label("📊 วิเคราะห์"),
                _full_btn("🔥  SCAN หาหุ้น Breakout + Volume", "สแกน", "#ef5350"),
                _two_btn("🧠 AI วิเคราะห์", "วิเคราะห์", "#FF6B35",
                         "💰 ดูราคา",      "ราคา",      "#29B6F6"),
                _divider(),
                # ── กราฟ ──
                _label("📉 กราฟ"),
                _two_btn("📊 กราฟ (เลือก TF)", "กราฟ",        "#26a69a",
                         "🗂 ครบ 5 TF",       "กราฟทั้งหมด", "#CE93D8"),
                _divider(),
                # ── แจ้งเตือน ──
                _label("🔔 แจ้งเตือน"),
                _two_btn("➕ เพิ่มแจ้งเตือน", "แจ้งเตือน", "#00E676",
                         "📋 รายการ",         "รายการ",    "#888888"),
            ]
        },
        "footer": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#0d1117", "paddingAll": "10px",
            "contents": [{
                "type": "button",
                "action": {"type": "message", "label": "❓ วิธีใช้", "text": "ช่วยเหลือ"},
                "style": "secondary", "color": "#21262d", "height": "sm"
            }]
        }
    }
    return FlexMessage(alt_text="SET Stock Sniper",
                       contents=FlexContainer.from_dict(bubble))


# ─── Symbol Picker — Carousel (1 แถว 3 ตัว ไม่ตัดคำ) ─────────────────────────
def make_symbol_picker() -> FlexMessage:
    groups = [
        [("DELTA","#FF6B35"), ("PTT",  "#29B6F6"), ("AOT",  "#00E676")],
        [("ADVANC","#FFC107"),("SCB",  "#CE93D8"), ("KBANK","#ef5350")],
        [("BBL",  "#80CBC4"), ("CPALL","#FF6B35"), ("TRUE", "#29B6F6")],
        [("GULF", "#00E676"), ("MINT", "#FFC107"), ("CPN",  "#CE93D8")],
    ]

    bubbles = []
    for group in groups:
        rows = []
        for sym, color in group:
            rows.append({
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "margin": "sm",
                "contents": [
                    {
                        "type": "button",
                        "action": {"type": "message",
                                   "label": sym,
                                   "text": f"เมนู {sym}"},
                        "style": "primary",
                        "color": color,
                        "height": "sm",
                    },
                    {
                        "type": "button",
                        "action": {"type": "message",
                                   "label": f"📊 กราฟ {sym}",
                                   "text": f"กราฟ {sym} 1d"},
                        "style": "secondary",
                        "color": "#21262d",
                        "height": "sm",
                    },
                ]
            })

        bubbles.append({
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#0d1117", "paddingAll": "10px",
                "contents": [{"type": "text", "text": "⭐ หุ้นยอดนิยม",
                               "weight": "bold", "size": "md", "color": "#FFC107"}]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#161b22", "paddingAll": "10px",
                "spacing": "sm",
                "contents": rows
            }
        })

    carousel = {"type": "carousel", "contents": bubbles}
    return FlexMessage(alt_text="หุ้นยอดนิยม",
                       contents=FlexContainer.from_dict(carousel))


# ─── TF Picker ────────────────────────────────────────────────────────────────
def make_tf_picker(symbol: str) -> FlexMessage:
    tfs = [
        ("15m","15 นาที",  "#80CBC4"),
        ("30m","30 นาที",  "#26a69a"),
        ("1h", "1 ชั่วโมง","#29B6F6"),
        ("4h", "4 ชั่วโมง","#FFC107"),
        ("1d", "รายวัน",   "#FF6B35"),
    ]
    rows = []
    for tf, label, color in tfs:
        rows.append({
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "margin": "sm",
            "contents": [
                {
                    "type": "button",
                    "action": {"type": "message",
                               "label": f"📊 {label}",
                               "text": f"กราฟ {symbol} {tf}"},
                    "style": "primary",
                    "color": color,
                    "height": "sm",
                    "flex": 1
                }
            ]
        })

    # ปุ่ม All TF
    rows.append({
        "type": "box",
        "layout": "horizontal",
        "margin": "md",
        "contents": [{
            "type": "button",
            "action": {"type": "message",
                       "label": f"🗂  ครบทุก TF ({symbol})",
                       "text": f"กราฟทั้งหมด {symbol}"},
            "style": "primary",
            "color": "#CE93D8",
            "height": "sm",
        }]
    })

    bubble = {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#0d1117", "paddingAll": "12px",
            "contents": [
                {"type": "text", "text": "📉 เลือก Timeframe",
                 "weight": "bold", "size": "md", "color": "#00E676"},
                {"type": "text", "text": f"หุ้น: {symbol}",
                 "size": "sm", "color": "#888888"},
            ]
        },
        "body": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#161b22", "paddingAll": "12px",
            "contents": rows
        }
    }
    return FlexMessage(alt_text=f"เลือก TF — {symbol}",
                       contents=FlexContainer.from_dict(bubble))


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _label(text: str) -> dict:
    return {"type": "text", "text": text, "size": "sm",
            "color": "#aaaaaa", "margin": "sm"}

def _divider() -> dict:
    return {"type": "separator", "margin": "sm", "color": "#21262d"}

def _full_btn(label: str, msg: str, color: str) -> dict:
    return {
        "type": "button",
        "action": {"type": "message", "label": label, "text": msg},
        "style": "primary", "color": color, "height": "sm", "margin": "sm"
    }

def _two_btn(l1, m1, c1, l2, m2, c2) -> dict:
    return {
        "type": "box", "layout": "horizontal", "spacing": "sm", "margin": "xs",
        "contents": [
            {"type": "button",
             "action": {"type": "message", "label": l1, "text": m1},
             "style": "primary", "color": c1, "height": "sm", "flex": 1},
            {"type": "button",
             "action": {"type": "message", "label": l2, "text": m2},
             "style": "primary", "color": c2, "height": "sm", "flex": 1},
        ]
    }
