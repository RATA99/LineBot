"""
LINE Bot - SET Stock Sniper + AI Agent + Market Scanner
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
from scanner import run_scan

app = Flask(__name__)

LINE_CHANNEL_SECRET       = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler       = WebhookHandler(LINE_CHANNEL_SECRET)

# ─── Webhook ──────────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    if not signature:
        abort(400)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        app.logger.error("Invalid signature: {}".format(e))
        abort(400)
    return "OK"

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "SET Stock Sniper Bot"}

# ─── Message Handler ──────────────────────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id
    def process():
        intent = parse_intent(text)
        execute_intent(intent, user_id, event)
    threading.Thread(target=process, daemon=True).start()

# ─── Intent Executor ─────────────────────────────────────────────────────────
def execute_intent(intent, user_id, event):
    action = intent.get("action", "unknown")
    symbol = intent.get("symbol")
    tf     = intent.get("tf") or "1d"
    conf   = intent.get("confidence", 0)

    if conf < 0.5 and action == "unknown":
        reply_text(event, "ไม่แน่ใจครับ ลองพิมพ์ใหม่ หรือพิมพ์ 'เมนู'")
        return

    if action == "menu":
        reply_flex(event, make_main_menu(symbol))

    elif action == "popular":
        reply_flex(event, make_symbol_picker())

    elif action == "help":
        reply_text(event,
            "SET Stock Sniper - AI Agent\n\n"
            "พิมพ์อะไรก็ได้ เช่น:\n"
            "- ดูกราฟ delta ชั่วโมง\n"
            "- ptt ราคาเท่าไร\n"
            "- วิเคราะห์ kbank\n"
            "- สแกนหาหุ้น breakout\n"
            "- กราฟ scb ทุก tf\n"
            "- แจ้งเตือน aot\n"
            "- หุ้นยอดนิยม"
        )

    elif action == "scan":
        reply_text(event, "Scanning SET market... ใช้เวลา 30-60 วินาทีครับ")
        def do_scan():
            try:
                candidates, summary, ai_text = run_scan()
                if not candidates:
                    push_message(user_id, "ไม่พบสัญญาณ Breakout วันนี้ครับ")
                    return
                push_message(user_id, summary)
                if ai_text:
                    header = "=== AI Entry/Exit Analysis ===\n\n"
                    push_message(user_id, header + ai_text)
            except Exception as e:
                push_message(user_id, "Scan Error: {}".format(e))
        threading.Thread(target=do_scan, daemon=True).start()

    elif action == "price":
        if not symbol:
            reply_text(event, "บอกชื่อหุ้นด้วยครับ เช่น ราคา DELTA")
            return
        reply_text(event, get_alert_message(symbol))

    elif action == "analyze":
        if not symbol:
            reply_text(event, "บอกชื่อหุ้นด้วยครับ เช่น วิเคราะห์ DELTA")
            return
        reply_text(event, "กำลังวิเคราะห์ {}... ใช้เวลา 15-30 วินาทีครับ".format(symbol))
        def do():
            push_message(user_id, analyze_stock(symbol))
        threading.Thread(target=do, daemon=True).start()

    elif action == "chart":
        if not symbol:
            reply_text(event, "บอกชื่อหุ้นด้วยครับ เช่น กราฟ DELTA 1h")
            return
        reply_text(event, "กำลังสร้างกราฟ {} [{}]...".format(symbol, tf.upper()))
        def do():
            url, err = get_chart_url(symbol, tf)
            if err:
                push_message(user_id, err)
            else:
                push_img(user_id, url)
        threading.Thread(target=do, daemon=True).start()

    elif action == "chart_all":
        if not symbol:
            reply_text(event, "บอกชื่อหุ้นด้วยครับ เช่น กราฟ DELTA ทุก TF")
            return
        reply_text(event, "กำลังสร้างกราฟ {} ครบ 5 TF...".format(symbol))
        def do():
            for t in ["15m", "30m", "1h", "4h", "1d"]:
                url, err = get_chart_url(symbol, t)
                if err:
                    push_message(user_id, "{}: {}".format(t, err))
                else:
                    push_img(user_id, url)
                time.sleep(1.5)
        threading.Thread(target=do, daemon=True).start()

    elif action == "alert_add":
        if not symbol:
            reply_text(event, "บอกชื่อหุ้นด้วยครับ เช่น แจ้งเตือน DELTA")
            return
        add_watchlist(symbol, user_id)
        reply_text(event, "เพิ่ม {} ในรายการแจ้งเตือนแล้วครับ".format(symbol))

    elif action == "alert_remove":
        if not symbol:
            reply_text(event, "บอกชื่อหุ้นด้วยครับ เช่น ยกเลิกแจ้งเตือน DELTA")
            return
        remove_watchlist(symbol, user_id)
        reply_text(event, "ลบ {} ออกจากรายการแล้วครับ".format(symbol))

    elif action == "alert_list":
        wl = get_watchlist(user_id)
        if wl:
            msg = "รายการแจ้งเตือน:\n" + "\n".join(["- " + s for s in wl])
        else:
            msg = "ยังไม่มีหุ้นในรายการครับ"
        reply_text(event, msg)

    else:
        reply_flex(event, make_main_menu())

# ─── Reply Helpers ────────────────────────────────────────────────────────────
def reply_text(event, text):
    try:
        with ApiClient(configuration) as api:
            MessagingApi(api).reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=text)]
                )
            )
    except Exception as e:
        print("reply_text error: {}".format(e))

def reply_flex(event, flex):
    try:
        with ApiClient(configuration) as api:
            MessagingApi(api).reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[flex]
                )
            )
    except Exception as e:
        print("reply_flex error: {}".format(e))

def push_img(user_id, url):
    try:
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
    except Exception as e:
        print("push_img error: {}".format(e))

# ─── Start ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=start_monitor, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
