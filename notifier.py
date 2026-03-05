"""
notifier.py — LINE Push Message auto-alert
ส่ง alert อัตโนมัติผ่าน LINE Messaging API (Push Message)
แทน LINE Notify ที่ปิดบริการแล้ว
"""
import os
import time
import threading
from collections import defaultdict
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    PushMessageRequest, TextMessage
)
from analyzer import get_data, calc_indicators, get_signal

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
CHECK_INTERVAL = 300  # เช็คทุก 5 นาที

# ─── In-memory watchlist & signal cache ───────────────────────────────────────
# { symbol: set(user_id) }
_watchlist: dict = defaultdict(set)
# { symbol: last_signal_str }
_last_signal: dict = {}
_lock = threading.Lock()

# ─── Watchlist management ─────────────────────────────────────────────────────
def add_watchlist(symbol: str, user_id: str):
    with _lock:
        _watchlist[symbol].add(user_id)

def remove_watchlist(symbol: str, user_id: str):
    with _lock:
        _watchlist[symbol].discard(user_id)
        if not _watchlist[symbol]:
            _watchlist.pop(symbol, None)

def get_watchlist(user_id: str) -> list:
    with _lock:
        return [sym for sym, users in _watchlist.items() if user_id in users]

# ─── Push Message sender ──────────────────────────────────────────────────────
def push_message(user_id: str, message: str):
    """Push ข้อความหา user โดยตรงผ่าน LINE Messaging API"""
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("[Push] ไม่พบ LINE_CHANNEL_ACCESS_TOKEN")
        return False
    try:
        configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=message)]
                )
            )
        return True
    except Exception as e:
        print(f"[Push] Error -> {user_id}: {e}")
        return False

def push_to_users(user_ids: set, message: str):
    for uid in user_ids:
        push_message(uid, message)
        time.sleep(0.5)

# ─── Signal checker ───────────────────────────────────────────────────────────
def check_symbol(symbol: str):
    df = get_data(symbol, interval="1d", limit=60)
    if df.empty:
        return None, None

    ind       = calc_indicators(df)
    current_p = df['close'].iloc[-1]
    prev_p    = df['close'].iloc[-2]
    chg_pct   = (current_p - prev_p) / prev_p * 100
    signal    = get_signal(current_p, ind)

    with _lock:
        last = _last_signal.get(symbol)
        if signal == last:
            return None, None
        _last_signal[symbol] = signal

    avg_vol   = df['volume'].tail(20).mean()
    last_vol  = df['volume'].iloc[-1]
    vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1

    msg = (
        f"🔔 สัญญาณเปลี่ยน! {symbol}\n\n"
        f"{signal}\n"
        f"💰 ราคา    : {current_p:,.2f} บาท ({chg_pct:+.2f}%)\n"
        f"📊 Volume  : {vol_ratio:.1f}x avg\n"
        f"📈 EMA 200 : {ind['ema200']:,.2f}\n"
        f"🎯 Fibo 50% : {ind['fib_500']:,.2f}\n"
        f"🎯 Fibo 61.8%: {ind['fib_618']:,.2f}\n\n"
        f"⚠️ ไม่ใช่คำแนะนำการลงทุน"
    )
    return msg, signal

# ─── Background monitor loop ──────────────────────────────────────────────────
def start_monitor():
    print("[Monitor] เริ่ม background monitor (LINE Push Message)...")
    while True:
        try:
            with _lock:
                snapshot = {sym: set(users) for sym, users in _watchlist.items()}

            for symbol, user_ids in snapshot.items():
                if not user_ids:
                    continue
                alert_msg, new_signal = check_symbol(symbol)
                if alert_msg:
                    print(f"[Monitor] {symbol}: {new_signal} -> push {len(user_ids)} คน")
                    push_to_users(user_ids, alert_msg)
                time.sleep(2)

        except Exception as e:
            print(f"[Monitor] Error: {e}")

        time.sleep(CHECK_INTERVAL)
