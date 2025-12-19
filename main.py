import os
import json
import logging
from datetime import datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from notion_client import Client
import google.generativeai as genai

app = Flask(__name__)

LINE_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_DB_ID = os.environ.get('NOTION_DATABASE_ID')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

if not all([LINE_ACCESS_TOKEN, LINE_SECRET, NOTION_TOKEN, NOTION_DB_ID, GEMINI_KEY]):
    print("⚠️ Warning: กุญแจบางดอกหายไป โปรดเช็คใน Render Environment Variables")

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)
notion = Client(auth=NOTION_TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

def ask_gemini(user_text):
    prompt = f"""
    Role: Personal Assistant.
    Task: Analyze input. If it's a task, extract details for Notion. If chat, reply friendly.
    Current Date: {datetime.now().strftime("%Y-%m-%d")}
    Output: JSON ONLY. Format: {{"type": "task/chat", "reply": "Thai text", "task_data": {{"name": "...", "date": "YYYY-MM-DD", "category": "Work/Personal"}}}}
    Input: "{user_text}"
    """
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"AI Error: {e}")
        return {"type": "chat", "reply": "อารยางงนิดหน่อยขออภัยค่ะ"}

def add_to_notion(data):
    try:
        notion.pages.create(
            parent={"database_id": NOTION_DB_ID},
            properties={
                "Name": {"title": [{"text": {"content": data.get('name', 'Untitled')}}]},
                "Status": {"select": {"name": "To Do"}},
                "Category": {"select": {"name": data.get('category', 'Personal')}},
                "Date": {"date": {"start": data.get('date', datetime.now().strftime("%Y-%m-%d"))}}
            }
        )
        return True
    except Exception as e:
        print(f"Notion Error: {e}")
        return False

@app.route("/", methods=['GET'])
def home():
    return "Jarvis is Running on Render!", 200

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
    user_text = event.message.text
    try:
        ai_res = ask_gemini(user_text)
        reply = ai_res.get('reply', '...')
        
        if ai_res.get('type') == 'task':
            if add_to_notion(ai_res.get('task_data')):
                reply += "\n(บันทึกให้เรียบร้อยค่ะ)"
            else:
                reply += "\n(บันทึกไม่สำเร็จนะคะ)"
                
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    app.run()
