import os
import json
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# ตั้งค่า LINE (ดึงจาก Render)
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# ฟังก์ชันคุยกับ AI (แบบยิงตรง 100% ไม่ผ่าน Library)
def chat_with_gemini(text):
    api_key = os.environ.get('GEMINI_API_KEY')
    # ใช้ URL มาตรฐานของ Google (Stable Version)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    data = {
        "contents": [{
            "parts": [{"text": text}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        # กรณีสำเร็จ (200 OK)
        if response.status_code == 200:
            result = response.json()
            # แกะกล่องเอาคำตอบ
            return result['candidates'][0]['content']['parts'][0]['text']
        
        # กรณี Google ปฏิเสธ (เช่น กุญแจผิด)
        else:
            print(f"Google Error: {response.text}") # ปริ้นท์ลง Log ให้เราเห็น
            return f"ระบบขัดข้อง: {response.status_code} (ลองเช็ค API Key อีกทีนะคะ)"
            
    except Exception as e:
        print(f"System Error: {str(e)}")
        return "ขอโทษค่ะ ระบบประมวลผลมีปัญหาชั่วคราว"

@app.route("/", methods=['GET'])
def hello():
    return "Status: OK (Bot is running)", 200

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text.strip()
    
    # ส่งข้อความไปถาม AI
    ai_reply = chat_with_gemini(user_msg)
    
    # ตอบกลับทาง LINE
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_reply)
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
