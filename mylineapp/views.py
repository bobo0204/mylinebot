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
                
                # 檢查是否是算術練習相關的指令
                if user_message.lower() in ['開始', '練習', 'start', 'y', '是']:
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
                if user_message.lower() in ['結束', 'end', 'n', '否']:
                    if user_id in user_sessions:
                        del user_sessions[user_id]
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="謝謝參與，下次見！")
                    )
                    return HttpResponse()

                # 檢查答案
                if user_id in user_sessions:
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

                # 如果不是算術練習相關的訊息，則使用原本的回覆邏輯
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
    