from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextSendMessage, 
    TemplateSendMessage, ButtonsTemplate, MessageAction
)
from datetime import datetime
import random
from typing import Tuple, Dict
import requests
from bs4 import BeautifulSoup

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)

# 用於存儲用戶當前題目和答案的字典
user_sessions: Dict[str, Dict] = {}

def generate_question() -> Tuple[str, int]:
    """生成一個隨機算術題目和其答案"""
    attempts = 0
    max_attempts = 100
    
    while attempts < max_attempts:
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        num3 = random.randint(1, 9)
        
        operators = ['+', '-', '*', '/']
        operator1 = random.choice(operators)
        operator2 = random.choice(operators)

        expression = f"{num1} {operator1} {num2} {operator2} {num3}"
        
        try:
            correct_answer = eval(expression)
            if correct_answer == int(correct_answer) and -1000 <= correct_answer <= 1000:
                return expression, int(correct_answer)
        except (ZeroDivisionError, SyntaxError):
            pass
        
        attempts += 1
    
    return "2 + 3 + 4", 9

def check_answer(user_answer: str, correct_answer: int) -> str:
    """檢查用戶的答案"""
    try:
        user_answer = int(user_answer.strip())
    except ValueError:
        return "請輸入有效的整數答案。"
    
    if user_answer == correct_answer:
        return "很棒，正確 ~ \n要繼續練習嗎？"
    else:
        return f"錯誤，加油，再想想 ~\n正確答案是: {correct_answer}\n要繼續練習嗎？"

def read(word):
    """查詢中文字的注音"""
    try:
        url = f'https://dict.revised.moe.edu.tw/search.jsp?md=1&word={word}#searchL'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 找到包含注音的單元格
        phonetic_td = soup.find('td', class_='ph')
        
        if phonetic_td:
            # 獲取所有注音碼和聲調
            result = []
            for ib in phonetic_td.find_all('ib'):
                phonetic = ''
                code = ib.find('code')
                if code:
                    phonetic = code.text.strip()
                sup = ib.find('sup')
                if sup:
                    phonetic += sup.text.strip()
                if phonetic:
                    result.append(phonetic)
            
            if result:
                phonetic_str = " ".join(result)
                return f"{word}=>{phonetic_str}"
        
        return '查無此字'
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return f'發生錯誤: {str(e)}'

def index(request):
    return HttpResponse("Hello Line Bot works~!")

@csrf_exempt
def callback(request):
    if request.method == 'POST':
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')
        try:
            events = parser.parse(body, signature)
        except InvalidSignatureError:
            return HttpResponseForbidden()
        except LineBotApiError:
            return HttpResponseBadRequest()

        for event in events:
            if isinstance(event, MessageEvent):
                user_id = event.source.user_id
                user_message = event.message.text.strip()
                
                # 檢查是否是查詢注音的指令
                if user_message.startswith('查注音'):
                    # 提取要查詢的中文字
                    word = user_message[3:].strip()
                    if word:
                        result = read(word)
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=result)
                        )
                    else:
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="請在「查注音」後面輸入要查詢的中文字")
                        )
                    return HttpResponse()
                
                # 檢查是否是算術練習相關的指令
                elif user_message.lower() in ['開始', '練習', 'start', 'y', '是']:
                    # 生成新題目
                    expression, answer = generate_question()
                    user_sessions[user_id] = {
                        'answer': answer,
                        'question': expression
                    }
                    
                    # 發送題目給用戶
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"請計算：{expression} = ?")
                    )
                    return HttpResponse()

                # 檢查是否要結束練習
                elif user_message.lower() in ['結束', 'end', 'n', '否']:
                    if user_id in user_sessions:
                        del user_sessions[user_id]
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="謝謝參與，下次見！")
                    )
                    return HttpResponse()

                # 檢查答案
                elif user_id in user_sessions:
                    correct_answer = user_sessions[user_id]['answer']
                    response = check_answer(user_message, correct_answer)
                    
                    # 創建按鈕模板
                    template = ButtonsTemplate(
                        text=response,
                        actions=[
                            MessageAction(label='繼續練習', text='是'),
                            MessageAction(label='結束練習', text='否')
                        ]
                    )
                    
                    message = TemplateSendMessage(
                        alt_text='繼續練習？',
                        template=template
                    )
                    
                    line_bot_api.reply_message(event.reply_token, message)
                    
                    # 如果答對了，清除該用戶的session
                    if "正確" in response:
                        del user_sessions[user_id]
                    return HttpResponse()

                # 如果不是特殊指令，則使用原本的回覆邏輯
                else:
                    currentDateAndTime = datetime.now()
                    currentTime = currentDateAndTime.strftime("%H:%M:%S")
                    txtmsg = "您所傳的訊息是:\n"
                    txtmsg += currentTime + "\n"
                    txtmsg += event.message.text
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=txtmsg)
                    )

        return HttpResponse()
    else:
        return HttpResponseBadRequest()