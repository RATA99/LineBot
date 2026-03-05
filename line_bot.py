"""
LINE Bot Webhook Server — SET Stock Sniper
รับคำสั่งผ่าน LINE Flex Message + ส่งกราฟและบทวิเคราะห์
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

from analyzer import analyze_stock, get_alert_message
from chart import get_chart_url, INTERVAL_MAP
from flex_menu import make_main_menu, make_symbol_picker
from notifier import start_monitor, push_message, add_watchlist, remove_watchlist, get_watchlist

app = Flask(__name__)

LINE_CHANNEL_SECRET       = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler       = WebhookHandler(LINE_CHANNEL_SECRET)

# ─── Webhook ──────────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body      = request.get_data(as_text=True)
    app.logger.info(f"Webhook | sig: {signature[:10]}...")
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

# ─── Message Handler ──────────────────────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text    = event.message.text.strip()
    user_id = event.source.user_id
    process_command(text, user_id, event)

# ─── Reply helpers ────────────────────────────────────────────────────────────
def reply_text(event, text: str):
    with ApiClient(configuration) as api:
        MessagingApi(api).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=text)]
            )
        )

def reply_flex(event, flex: FlexMessage):
    with ApiClient(configuration) as api:
        MessagingApi(api).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[flex]
            )
        )

def reply_image(event, url: str):
    with ApiClient(configuration) as api:
        MessagingApi(api).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[ImageMessage(
                    original_content_url=url,
                    preview_image_url=url
                )]
            )
        )

def push_image(user_id: str, url: str):
    with ApiClient(configuration) as api:
        MessagingApi(api).push_message(
            PushMessageRequest(
                to=user_id,
                messages=[ImageMessage(
                    original_content_url=url,
                    preview_image_url=url
                )]
            )
        )

# ─── Command processor ────────────────────────────────────────────────────────
def process_command(text: str, user_id: str, event):
    t = text.strip().lower()
    parts = text.strip().split()

    # ── เมนูหลัก ──
    if t in ["เมนู", "menu", "start", "สวัสดี", "hi", "hello"]:
        reply_flex(event, make_main_menu())
        return

    if t.startswith("เมนู ") and len(parts) >= 2:
        symbol = parts[1].upper()
        reply_flex(event, make_main_menu(symbol))
        return

    # ── เลือกหุ้น ──
    if t in ["หุ้น", "เลือกหุ้น", "stock"]:
        reply_flex(event, make_symbol_picker())
        return

    # ── ราคา ──
    if t.startswith("ราคา") or t.startswith("price"):
        if len(parts) < 2:
            reply_text(event, "กรุณาระบุชื่อหุ้น เช่น: ราคา DELTA")
            return
        symbol = parts[1].upper()
        reply_text(event, get_alert_message(symbol))
        return

    # ── วิเคราะห์ ──
    if t.startswith("วิเคราะห์") or t.startswith("analyze"):
        if len(parts) < 2:
            reply_text(event, "กรุณาระบุชื่อหุ้น เช่น: วิเคราะห์ DELTA")
            return
        symbol = parts[1].upper()
        reply_text(event, f"🧠 กำลังวิเคราะห์ {symbol}...\nใช้เวลา 15-30 วินาที")
        # push ผลลัพธ์หลังจาก reply แล้ว
        def do_analyze():
            result = analyze_stock(symbol)
            push_message(user_id, result)
        threading.Thread(target=do_analyze, daemon=True).start()
        return

    # ── กราฟ TF เดียว ──
    if t.startswith("กราฟ") or t.startswith("chart"):
        if len(parts) < 2:
            reply_text(event, "เช่น: กราฟ DELTA 1d\nTF: 15m, 30m, 1h, 4h, 1d")
            return
        symbol = parts[1].upper()
        tf     = parts[2].lower() if len(parts) >= 3 else "1d"

        reply_text(event, f"📊 กำลังสร้างกราฟ {symbol} [{tf.upper()}]...")
        def do_chart():
            url, err = get_chart_url(symbol, tf)
            if err:
                push_message(user_id, err)
            else:
                push_image(user_id, url)
        threading.Thread(target=do_chart, daemon=True).start()
        return

    # ── กราฟทั้งหมด 5 TF ──
    if t.startswith("กราฟทั้งหมด") or t.startswith("allchart"):
        if len(parts) < 2:
            reply_text(event, "เช่น: กราฟทั้งหมด DELTA")
            return
        symbol = parts[1].upper()
        reply_text(event, f"📊 กำลังสร้างกราฟ {symbol} ครบ 5 TF...\n(15m / 30m / 1H / 4H / Day)\nใช้เวลาสักครู่นะครับ")
        def do_all_charts():
            for tf in ["15m", "30m", "1h", "4h", "1d"]:
                url, err = get_chart_url(symbol, tf)
                if err:
                    push_message(user_id, f"⚠️ {tf}: {err}")
                else:
                    push_image(user_id, url)
                time.sleep(1.5)
        threading.Thread(target=do_all_charts, daemon=True).start()
        return

    # ── แจ้งเตือน ──
    if t.startswith("แจ้งเตือน") or t.startswith("monitor"):
        if len(parts) < 2:
            reply_text(event, "เช่น: แจ้งเตือน DELTA")
            return
        symbol = parts[1].upper()
        add_watchlist(symbol, user_id)
        reply_text(event, f"✅ เพิ่ม {symbol} ในรายการแจ้งเตือนแล้วครับ\nจะ push เมื่อสัญญาณเปลี่ยน")
        return

    if t.startswith("หยุดแจ้งเตือน") or t.startswith("unmonitor"):
        if len(parts) < 2:
            reply_text(event, "เช่น: หยุดแจ้งเตือน DELTA")
            return
        symbol = parts[1].upper()
        remove_watchlist(symbol, user_id)
        reply_text(event, f"🔕 ลบ {symbol} ออกจากรายการแล้วครับ")
        return

    if t in ["รายการ", "list", "watchlist"]:
        wl = get_watchlist(user_id)
        if not wl:
            reply_text(event, "📋 ยังไม่มีหุ้นในรายการ\nพิมพ์: แจ้งเตือน [หุ้น]")
        else:
            reply_text(event, "📋 รายการแจ้งเตือน:\n" + "\n".join([f"• {s}" for s in wl]))
        return

    # ── ช่วยเหลือ ──
    if t in ["ช่วยเหลือ", "help", "?"]:
        reply_text(event, """📈 SET Stock Sniper

คำสั่งทั้งหมด:
• เมนู [หุ้น] — เมนูปุ่มกด เช่น: เมนู DELTA
• หุ้น — เลือกหุ้นจากลิสต์
• ราคา [หุ้น] — ราคา + signal
• วิเคราะห์ [หุ้น] — บทวิเคราะห์ AI
• กราฟ [หุ้น] [TF] — กราฟ TF เดียว
  TF: 15m, 30m, 1h, 4h, 1d
• กราฟทั้งหมด [หุ้น] — ครบ 5 TF
• แจ้งเตือน [หุ้น] — เพิ่ม watchlist
• หยุดแจ้งเตือน [หุ้น] — ลบออก
• รายการ — ดู watchlist""")
        return

    # ── default ──
    reply_flex(event, make_main_menu())

# ─── Start ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=start_monitor, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
