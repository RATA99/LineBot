# 📱 SET Stock Sniper — LINE Bot

วิเคราะห์หุ้นผ่าน LINE ด้วย AI (Groq × Qwen3 32B)

## 🏗️ Architecture

```
LINE ←→ LINE Bot (Webhook) ←→ analyzer.py ←→ Groq AI
                                    ↑
                              settrade_v2 API
                                    
LINE Notify ← notifier.py (background monitor)
```

## 📋 คำสั่งที่ใช้ได้ใน LINE

| คำสั่ง | ตัวอย่าง | ผลลัพธ์ |
|---|---|---|
| วิเคราะห์ [หุ้น] | วิเคราะห์ DELTA | บทวิเคราะห์เต็ม AI |
| ราคา [หุ้น] | ราคา PTT | ราคา + signal + Fibo |
| แจ้งเตือน [หุ้น] | แจ้งเตือน AOT | เพิ่มใน watchlist |
| หยุดแจ้งเตือน [หุ้น] | หยุดแจ้งเตือน AOT | ลบออกจาก watchlist |
| รายการ | รายการ | ดู watchlist |
| ช่วยเหลือ | ช่วยเหลือ | แสดงคำสั่งทั้งหมด |

---

## 🚀 วิธี Deploy บน Railway

### ขั้นที่ 1: เตรียม Keys

**LINE Bot (Messaging API)**
1. ไปที่ https://developers.line.biz
2. Create Provider → Create Channel → Messaging API
3. จด **Channel Secret** + **Channel Access Token**
4. เปิด "Use webhook" และปิด "Auto-reply messages"

**LINE Notify**
1. ไปที่ https://notify-bot.line.me
2. Generate Token → เลือก chat/group ที่ต้องการ
3. จด **Notify Token**

### ขั้นที่ 2: Push ขึ้น GitHub

```bash
git init
git add .
git commit -m "LINE Bot initial"
git remote add origin https://github.com/YOUR/stock-line-bot.git
git push -u origin main
```

### ขั้นที่ 3: Deploy บน Railway

1. ไปที่ https://railway.app → New Project → Deploy from GitHub
2. เลือก repo `stock-line-bot`
3. ไปที่ **Variables** → Add ทั้งหมดนี้:

```
LINE_CHANNEL_SECRET      = (จาก LINE Developers)
LINE_CHANNEL_ACCESS_TOKEN = (จาก LINE Developers)
# LINE_NOTIFY_TOKEN ไม่จำเป็นแล้ว (ปิดบริการ)
GROQ_API_KEY             = gsk_...
APP_ID                   = VMxlV5Hz3BvMkitL
APP_SECRET               = OecHOLQUlbnHevImrX68VPzEOCxqKaBbuatzq88LOmg=
BROKER_ID                = 023
APP_CODE                 = ALGO_EQ
```

4. Deploy → รอ build เสร็จ
5. Copy URL จาก Railway (เช่น `https://stock-bot-xxx.railway.app`)

### ขั้นที่ 4: ตั้ง Webhook ใน LINE

1. ไปที่ LINE Developers → Messaging API
2. Webhook URL: `https://stock-bot-xxx.railway.app/webhook`
3. กด **Verify** → ต้องขึ้น Success
4. เปิด **Use webhook: ON**

### ขั้นที่ 5: ทดสอบ

เพิ่ม LINE Bot เป็นเพื่อน แล้วพิมพ์:
- `ช่วยเหลือ` → ควรได้รับเมนูคำสั่ง
- `ราคา DELTA` → ควรได้ราคา + signal
- `วิเคราะห์ DELTA` → ควรได้บทวิเคราะห์ AI

---

## 🔔 LINE Notify Alert

Bot จะส่ง alert อัตโนมัติทุก 5 นาที เมื่อสัญญาณของหุ้นใน watchlist เปลี่ยน เช่น:
- จาก WATCH → BULLISH
- จาก BULLISH → CRITICAL

ตัวอย่าง alert:
```
🔔 สัญญาณเปลี่ยน! DELTA
💹 BULLISH
💰 ราคา: 261.00 (+2.5%)
📊 Volume: 2.3x avg
🎯 Fibo 50%: 255.00
```
