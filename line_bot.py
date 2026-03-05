"""
LINE Bot Webhook Server
รับคำสั่งจาก LINE แล้วส่งบทวิเคราะห์หุ้นกลับ
"""
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os
import threading
from analyzer import analyze_stock, get_alert_message
from notifier import start_monitor

app = Flask(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
LINE_CHANNEL_SECRET      = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler       = WebhookHandler(LINE_CHANNEL_SECRET)

HELP_TEXT = """📈 SET Stock Sniper Bot

คำสั่งที่ใช้ได้:
• วิเคราะห์ [หุ้น] — เช่น "วิเคราะห์ DELTA"
• ราคา [หุ้น] — เช่น "ราคา PTT"
• แจ้งเตือน [หุ้น] — เพิ่มหุ้นในรายการ monitor
• หยุดแจ้งเตือน [หุ้น] — ลบออกจาก monitor
• รายการ — ดูหุ้นที่กำลัง monitor อยู่
• ช่วยเหลือ — แสดงคำสั่งทั้งหมด"""

# ─── Webhook ──────────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
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
    reply   = process_command(text, user_id)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

def process_command(text: str, user_id: str) -> str:
    text_lower = text.lower().strip()

    # วิเคราะห์ [หุ้น]
    if text_lower.startswith("วิเคราะห์") or text_lower.startswith("analyze"):
        parts = text.split()
        if len(parts) < 2:
            return "กรุณาระบุชื่อหุ้น เช่น: วิเคราะห์ DELTA"
        symbol = parts[1].upper()
        return f"🔍 กำลังวิเคราะห์ {symbol}...\n(ใช้เวลาประมาณ 15-30 วินาที)\n\n" + analyze_stock(symbol)

    # ราคา [หุ้น]
    elif text_lower.startswith("ราคา") or text_lower.startswith("price"):
        parts = text.split()
        if len(parts) < 2:
            return "กรุณาระบุชื่อหุ้น เช่น: ราคา PTT"
        symbol = parts[1].upper()
        return get_alert_message(symbol)

    # แจ้งเตือน [หุ้น]
    elif text_lower.startswith("แจ้งเตือน") or text_lower.startswith("monitor"):
        parts = text.split()
        if len(parts) < 2:
            return "กรุณาระบุชื่อหุ้น เช่น: แจ้งเตือน DELTA"
        symbol = parts[1].upper()
        from notifier import add_watchlist
        add_watchlist(symbol, user_id)
        return f"✅ เพิ่ม {symbol} ในรายการแจ้งเตือนแล้วครับ\nจะแจ้งเมื่อสัญญาณเปลี่ยน (BULLISH/BEARISH/CRITICAL)"

    # หยุดแจ้งเตือน [หุ้น]
    elif text_lower.startswith("หยุดแจ้งเตือน") or text_lower.startswith("unmonitor"):
        parts = text.split()
        if len(parts) < 2:
            return "กรุณาระบุชื่อหุ้น เช่น: หยุดแจ้งเตือน DELTA"
        symbol = parts[1].upper()
        from notifier import remove_watchlist
        remove_watchlist(symbol, user_id)
        return f"🔕 ลบ {symbol} ออกจากรายการแจ้งเตือนแล้วครับ"

    # รายการ
    elif text_lower in ["รายการ", "list", "watchlist"]:
        from notifier import get_watchlist
        wl = get_watchlist(user_id)
        if not wl:
            return "📋 ยังไม่มีหุ้นในรายการแจ้งเตือน\nพิมพ์: แจ้งเตือน [ชื่อหุ้น] เพื่อเพิ่ม"
        return "📋 รายการแจ้งเตือนของคุณ:\n" + "\n".join([f"• {s}" for s in wl])

    # ช่วยเหลือ
    elif text_lower in ["ช่วยเหลือ", "help", "?"]:
        return HELP_TEXT

    else:
        return f"ไม่เข้าใจคำสั่ง \"{text}\"\n\n{HELP_TEXT}"

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # เริ่ม background monitor thread
    monitor_thread = threading.Thread(target=start_monitor, daemon=True)
    monitor_thread.start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
