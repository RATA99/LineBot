"""
LINE Bot — SET Stock Sniper
State machine รอรับชื่อหุ้นจาก user แทน hardcode
"""
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, PushMessageRequest,
    TextMessage, ImageMessage, FlexMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os, threading, time
from collections import defaultdict

from analyzer import analyze_stock, get_alert_message
from chart import get_chart_url
from flex_menu import make_main_menu, make_symbol_picker, make_tf_picker
from notifier import start_monitor, push_message, add_watchlist, remove_watchlist, get_watchlist

app = Flask(__name__)

LINE_CHANNEL_SECRET       = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler       = WebhookHandler(LINE_CHANNEL_SECRET)

# ─── User state machine ───────────────────────────────────────────────────────
# { user_id: {"waiting": str, "tf": str} }
_state: dict = defaultdict(dict)

WAIT_MENU     = "menu"
WAIT_PRICE    = "price"
WAIT_ANALYZE  = "analyze"
WAIT_CHART    = "chart"
WAIT_ALLCHART = "allchart"
WAIT_ALERT    = "alert"
WAIT_SEARCH   = "search"   # ค้นหาและแสดงเมนูของหุ้นนั้น

# ─── Webhook ──────────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body      = request.get_data(as_text=True)
    if not signature:
        abort(400)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        app.logger.error(f"Invalid signature: {e}")
        abort(400)
    return "OK"

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "SET Stock Sniper Bot"}

# ─── Message handler ──────────────────────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text    = event.message.text.strip()
    user_id = event.source.user_id
    t       = text.lower()

    # ── ถ้ากำลังรอชื่อหุ้น ──────────────────────────────────────────────────
    state = _state.get(user_id, {})
    waiting = state.get("waiting")

    if waiting:
        # ยกเลิก state ถ้า user พิมพ์ command ใหม่
        is_new_cmd = any(t.startswith(k) for k in [
            "เมนู","menu","หุ้น","ราคา","วิเคราะห์","กราฟ",
            "แจ้งเตือน","หยุดแจ้งเตือน","รายการ","ช่วยเหลือ",
            "ค้นหา","start","help"
        ])
        if not is_new_cmd:
            # รับเป็นชื่อหุ้น
            symbol = text.upper().strip()
            _state[user_id] = {}
            handle_symbol_input(event, user_id, symbol, waiting, state.get("tf","1d"))
            return

    process_command(text, user_id, event)

# ─── Handle symbol input จาก state ──────────────────────────────────────────
def handle_symbol_input(event, user_id, symbol, waiting, tf):
    if waiting == WAIT_SEARCH or waiting == WAIT_MENU:
        reply_flex(event, make_main_menu(symbol))

    elif waiting == WAIT_PRICE:
        reply_text(event, get_alert_message(symbol))

    elif waiting == WAIT_ANALYZE:
        reply_text(event, f"🧠 กำลังวิเคราะห์ {symbol}...\nใช้เวลา 15-30 วินาทีครับ")
        def do():
            push_message(user_id, analyze_stock(symbol))
        threading.Thread(target=do, daemon=True).start()

    elif waiting == WAIT_CHART:
        reply_flex(event, make_tf_picker(symbol))

    elif waiting == WAIT_ALLCHART:
        reply_text(event, f"📊 กำลังสร้างกราฟ {symbol} ครบ 5 TF...\nใช้เวลาสักครู่นะครับ")
        def do():
            for t in ["15m","30m","1h","4h","1d"]:
                url, err = get_chart_url(symbol, t)
                if err: push_message(user_id, f"⚠️ {t}: {err}")
                else:   push_img(user_id, url)
                time.sleep(1.5)
        threading.Thread(target=do, daemon=True).start()

    elif waiting == WAIT_ALERT:
        add_watchlist(symbol, user_id)
        reply_text(event, f"✅ เพิ่ม {symbol} ในรายการแจ้งเตือนแล้วครับ\nจะ push เมื่อสัญญาณเปลี่ยน")

# ─── Main command router ──────────────────────────────────────────────────────
def process_command(text: str, user_id: str, event):
    parts = text.strip().split()
    t     = text.strip().lower()

    # เมนู / start
    if t in ["เมนู","menu","start","สวัสดี","hi","hello"]:
        reply_flex(event, make_main_menu())
        return

    if t.startswith("เมนู ") and len(parts) >= 2:
        reply_flex(event, make_main_menu(parts[1].upper()))
        return

    # ค้นหาหุ้น → รอรับ input
    if t in ["ค้นหา","search"]:
        _state[user_id] = {"waiting": WAIT_SEARCH}
        reply_text(event, "🔎 พิมพ์ชื่อหุ้นที่ต้องการครับ\nเช่น: DELTA, PTT, AOT")
        return

    # หุ้นยอดนิยม
    if t in ["หุ้น","เลือกหุ้น","stock"]:
        reply_flex(event, make_symbol_picker())
        return

    # ราคา
    if t in ["ราคา","price"]:
        _state[user_id] = {"waiting": WAIT_PRICE}
        reply_text(event, "💰 พิมพ์ชื่อหุ้นครับ เช่น: DELTA")
        return
    if (t.startswith("ราคา ") or t.startswith("price ")) and len(parts) >= 2:
        reply_text(event, get_alert_message(parts[1].upper()))
        return

    # วิเคราะห์
    if t in ["วิเคราะห์","analyze"]:
        _state[user_id] = {"waiting": WAIT_ANALYZE}
        reply_text(event, "🧠 พิมพ์ชื่อหุ้นที่ต้องการวิเคราะห์ครับ เช่น: DELTA")
        return
    if (t.startswith("วิเคราะห์ ") or t.startswith("analyze ")) and len(parts) >= 2:
        symbol = parts[1].upper()
        reply_text(event, f"🧠 กำลังวิเคราะห์ {symbol}...\nใช้เวลา 15-30 วินาทีครับ")
        def do():
            push_message(user_id, analyze_stock(symbol))
        threading.Thread(target=do, daemon=True).start()
        return

    # กราฟ
    if t in ["กราฟ","chart"]:
        _state[user_id] = {"waiting": WAIT_CHART}
        reply_text(event, "📊 พิมพ์ชื่อหุ้นที่ต้องการดูกราฟครับ เช่น: DELTA")
        return
    if (t.startswith("กราฟ ") or t.startswith("chart ")) and len(parts) >= 2:
        symbol = parts[1].upper()
        tf     = parts[2].lower() if len(parts) >= 3 else None
        if not tf:
            reply_flex(event, make_tf_picker(symbol))
            return
        reply_text(event, f"📊 กำลังสร้างกราฟ {symbol} [{tf.upper()}]...")
        def do():
            url, err = get_chart_url(symbol, tf)
            if err: push_message(user_id, err)
            else:   push_img(user_id, url)
        threading.Thread(target=do, daemon=True).start()
        return

    # กราฟทั้งหมด
    if t in ["กราฟทั้งหมด","allchart"]:
        _state[user_id] = {"waiting": WAIT_ALLCHART}
        reply_text(event, "🗂 พิมพ์ชื่อหุ้นสำหรับกราฟครบ 5 TF ครับ เช่น: DELTA")
        return
    if (t.startswith("กราฟทั้งหมด ") or t.startswith("allchart ")) and len(parts) >= 2:
        symbol = parts[1].upper()
        reply_text(event, f"📊 กำลังสร้างกราฟ {symbol} ครบ 5 TF...")
        def do():
            for tf2 in ["15m","30m","1h","4h","1d"]:
                url, err = get_chart_url(symbol, tf2)
                if err: push_message(user_id, f"⚠️ {tf2}: {err}")
                else:   push_img(user_id, url)
                time.sleep(1.5)
        threading.Thread(target=do, daemon=True).start()
        return

    # แจ้งเตือน
    if t in ["แจ้งเตือน","monitor"]:
        _state[user_id] = {"waiting": WAIT_ALERT}
        reply_text(event, "🔔 พิมพ์ชื่อหุ้นที่ต้องการแจ้งเตือนครับ เช่น: DELTA")
        return
    if t.startswith("แจ้งเตือน ") and len(parts) >= 2:
        symbol = parts[1].upper()
        add_watchlist(symbol, user_id)
        reply_text(event, f"✅ เพิ่ม {symbol} ในรายการแล้วครับ")
        return

    if t.startswith("หยุดแจ้งเตือน ") and len(parts) >= 2:
        symbol = parts[1].upper()
        remove_watchlist(symbol, user_id)
        reply_text(event, f"🔕 ลบ {symbol} ออกจากรายการแล้วครับ")
        return

    if t in ["รายการ","list","watchlist"]:
        wl = get_watchlist(user_id)
        msg = "📋 รายการแจ้งเตือน:\n" + "\n".join([f"• {s}" for s in wl]) if wl \
              else "📋 ยังไม่มีหุ้นในรายการ\nพิมพ์ 'แจ้งเตือน' เพื่อเพิ่ม"
        reply_text(event, msg)
        return

    if t in ["ช่วยเหลือ","help","?"]:
        reply_text(event, """📈 SET Stock Sniper

คำสั่ง:
• เมนู — เมนูหลัก (ปุ่ม)
• ค้นหา — ค้นหาหุ้น (พิมพ์ชื่อ)
• หุ้น — หุ้นยอดนิยม (ปุ่ม)
• ราคา — ดูราคา + Signal
• วิเคราะห์ — AI วิเคราะห์
• กราฟ — กราฟ (เลือก TF)
• กราฟทั้งหมด — ครบ 5 TF
• แจ้งเตือน — เพิ่ม watchlist
• รายการ — ดู watchlist

💡 พิมพ์คำสั่ง แล้วบอกชื่อหุ้นในขั้นถัดไปได้เลยครับ""")
        return

    # default — แสดงเมนู
    reply_flex(event, make_main_menu())

# ─── Reply helpers ────────────────────────────────────────────────────────────
def reply_text(event, text: str):
    with ApiClient(configuration) as api:
        MessagingApi(api).reply_message_with_http_info(
            ReplyMessageRequest(reply_token=event.reply_token,
                                messages=[TextMessage(text=text)]))

def reply_flex(event, flex: FlexMessage):
    with ApiClient(configuration) as api:
        MessagingApi(api).reply_message_with_http_info(
            ReplyMessageRequest(reply_token=event.reply_token,
                                messages=[flex]))

def push_img(user_id: str, url: str):
    with ApiClient(configuration) as api:
        MessagingApi(api).push_message(
            PushMessageRequest(to=user_id,
                               messages=[ImageMessage(original_content_url=url,
                                                      preview_image_url=url)]))

# ─── Start ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=start_monitor, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
