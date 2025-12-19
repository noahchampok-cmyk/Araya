import os
import requests
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from notion_client import Client

app = Flask(__name__)

# ตั้งค่า Line Bot
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# ตั้งค่า Notion
notion = Client(auth=os.environ.get('NOTION_TOKEN'))
database_id = os.environ.get('NOTION_DATABASE_ID')

# ฟังก์ชันคุยกับ AI แบบยิงตรง (ไม่ง้อ Library)
def chat_with_gemini(text):
    api_key = os.environ.get('GEMINI_API_KEY')
    # ใช้โมเดล Flash ตัวล่าสุด
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": text}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"ระบบขัดข้องนิดหน่อยค่ะ (Google Error: {response.status_code})"
    except Exception as e:
        return f"ขอโทษค่ะ อารยาป่วย (Error: {str(e)})"

@app.route("/", methods=['GET'])
def hello():
    return "OK", 200

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
    user_msg = event.message.text
    
    # ให้ AI คิดคำตอบ
    ai_reply = chat_with_gemini(user_msg)
    
    # ส่งกลับไปหาผู้ใช้
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_reply)
    )

    # (Optional) ถ้าอยากบันทึกลง Notion ด้วย ให้เปิดบรรทัดล่างนี้
    # save_to_notion(user_msg, ai_reply)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
