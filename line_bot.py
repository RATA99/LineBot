"""
LINE Bot — SET Stock Sniper + AI Agent
ไม่ต้องพิมพ์ตรงๆ AI เข้าใจ natural language
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
from chart import get_chart_url
from flex_menu import make_main_menu, make_symbol_picker, make_tf_picker
from notifier import start_monitor, push_message, add_watchlist, remove_watchlist, get_watchlist
from agent import parse_intent

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

    # ส่งให้ AI Agent ตีความก่อนเสมอ แล้ว execute
    def process():
        intent = parse_intent(text)
        execute_intent(intent, user_id, event)

    # ทำใน thread ป้องกัน timeout 5 วิของ LINE
    threading.Thread(target=process, daemon=True).start()

    # reply ทันทีว่ากำลังคิด (ป้องกัน LINE timeout)
    # แต่ถ้า action เร็ว (menu/popular/help) จะ reply จาก thread แทน
    # ดังนั้น reply token จะถูกใช้ใน thread เท่านั้น

# ─── Intent executor ─────────────────────────────────────────────────────────
def execute_intent(intent: dict, user_id: str, event):
    action  = intent.get("action", "unknown")
    symbol  = intent.get("symbol")
    tf      = intent.get("tf") or "1d"
    conf    = intent.get("confidence", 0)

    # confidence ต่ำเกินไป → ถามใหม่
    if conf < 0.5 and action == "unknown":
        reply_text(event, "ขอโทษครับ ไม่แน่ใจว่าต้องการอะไร 🤔\nลองพิมพ์ใหม่ หรือกด 'เมนู' เพื่อดูตัวเลือก")
        return

    if action == "menu":
        reply_flex(event, make_main_menu(symbol))

    elif action == "popular":
        reply_flex(event, make_symbol_picker())

    elif action == "help":
        reply_text(event, """📈 SET Stock Sniper — AI Agent

พิมพ์อะไรก็ได้ครับ เช่น:
• "ดูกราฟ delta แบบ 1 ชั่วโมง"
• "ptt ราคาเป็นยังไงบ้าง"
• "วิเคราะห์ kbank ให้หน่อย"
• "กราฟ scb ทุก TF เลย"
• "แจ้งเตือนถ้า aot มีสัญญาณ"
• "หุ้นน่าสนใจมีอะไรบ้าง"

ไม่ต้องพิมพ์ตรงๆ AI เข้าใจได้ 🤖""")

    elif action == "price":
        if not symbol:
            reply_text(event, "บอกชื่อหุ้นด้วยนะครับ เช่น 'ราคา DELTA'")
            return
        reply_text(event, get_alert_message(symbol))

    elif action == "analyze":
        if not symbol:
            reply_text(event, "บอกชื่อหุ้นด้วยนะครับ เช่น 'วิเคราะห์ DELTA'")
            return
        reply_text(event, f"🧠 กำลังวิเคราะห์ {symbol}...\nใช้เวลา 15-30 วินาทีครับ")
        def do():
            push_message(user_id, analyze_stock(symbol))
        threading.Thread(target=do, daemon=True).start()

    elif action == "chart":
        if not symbol:
            reply_text(event, "บอกชื่อหุ้นด้วยนะครับ เช่น 'กราฟ DELTA 1h'")
            return
        reply_text(event, f"📊 กำลังสร้างกราฟ {symbol} [{tf.upper()}]...")
        def do():
            url, err = get_chart_url(symbol, tf)
            if err: push_message(user_id, err)
            else:   push_img(user_id, url)
        threading.Thread(target=do, daemon=True).start()

    elif action == "chart_all":
        if not symbol:
            reply_text(event, "บอกชื่อหุ้นด้วยนะครับ เช่น 'กราฟ DELTA ทุก TF'")
            return
        reply_text(event, f"📊 กำลังสร้างกราฟ {symbol} ครบ 5 TF...\nใช้เวลาสักครู่นะครับ")
        def do():
            for t in ["15m", "30m", "1h", "4h", "1d"]:
                url, err = get_chart_url(symbol, t)
                if err: push_message(user_id, f"⚠️ {t}: {err}")
                else:   push_img(user_id, url)
                time.sleep(1.5)
        threading.Thread(target=do, daemon=True).start()

    elif action == "alert_add":
        if not symbol:
            reply_text(event, "บอกชื่อหุ้นด้วยนะครับ เช่น 'แจ้งเตือน DELTA'")
            return
        add_watchlist(symbol, user_id)
        reply_text(event, f"✅ เพิ่ม {symbol} ในรายการแจ้งเตือนแล้วครับ\nจะ push เมื่อสัญญาณเปลี่ยน")

    elif action == "alert_remove":
        if not symbol:
            reply_text(event, "บอกชื่อหุ้นด้วยนะครับ เช่น 'ยกเลิกแจ้งเตือน DELTA'")
            return
        remove_watchlist(symbol, user_id)
        reply_text(event, f"🔕 ลบ {symbol} ออกจากรายการแล้วครับ")

    elif action == "alert_list":
        wl = get_watchlist(user_id)
        msg = "📋 รายการแจ้งเตือน:\n" + "\n".join([f"• {s}" for s in wl]) if wl \
              else "📋 ยังไม่มีหุ้นในรายการครับ"
        reply_text(event, msg)

    else:
        # unknown — แสดงเมนู
        reply_flex(event, make_main_menu())

# ─── Helpers ──────────────────────────────────────────────────────────────────
def reply_text(event, text: str):
    try:
        with ApiClient(configuration) as api:
            MessagingApi(api).reply_message_with_http_info(
                ReplyMessageRequest(reply_token=event.reply_token,
                                    messages=[TextMessage(text=text)]))
    except Exception as e:
        print(f"[reply_text] {e}")

def reply_flex(event, flex: FlexMessage):
    try:
        with ApiClient(configuration) as api:
            MessagingApi(api).reply_message_with_http_info(
                ReplyMessageRequest(reply_token=event.reply_token,
                                    messages=[flex]))
    except Exception as e:
        print(f"[reply_flex] {e}")

def push_img(user_id: str, url: str):
    try:
        with ApiClient(configuration) as api:
            MessagingApi(api).push_message(
                PushMessageRequest(to=user_id,
                                   messages=[ImageMessage(
                                       original_content_url=url,
                                       preview_image_url=url)]))
    except Exception as e:
        print(f"[push_img] {e}")

# ─── Start ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=start_monitor, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
