import random

def generate_question():
    while True:
        # 隨機生成三個個位數的數字
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        num3 = random.randint(1, 9)
        
        # 隨機選擇兩個運算符
        operators = ['+', '-', '*', '/']
        operator1 = random.choice(operators)
        operator2 = random.choice(operators)

        # 構建運算表達式
        expression = f"{num1} {operator1} {num2} {operator2} {num3}"
        
        # 計算正確答案
        try:
            correct_answer = eval(expression)
            # 確認答案為整數且無餘數
            if correct_answer == int(correct_answer):
                return expression, int(correct_answer)
        except ZeroDivisionError:
            continue
        except SyntaxError:
            continue

def ask_question():
    # 生成一個隨機題目
    expression, correct_answer = generate_question()
    
    # 提示用戶輸入答案
    prompt = f"請計算：{expression}"
    
    return prompt, correct_answer

def check_answer(user_answer, correct_answer):
    try:
        user_answer = int(user_answer)
    except ValueError:
        return "請輸入有效的整數答案。"
    
    if user_answer == correct_answer:
        return "很棒，正確 ~"
    else:
        return f"錯誤，加油，再想想 ~"

# Example usage in a chatbot (such as LINE bot):
def main():
    prompt, correct_answer = ask_question()
    print(prompt)  # For testing purposes, replace with sending prompt to user
    
    while True:
        user_input = input("你的答案是：")  # For testing purposes, replace with receiving user input
        response = check_answer(user_input, correct_answer)
        print(response)  # For testing purposes, replace with sending response to user
        
        if response == "很棒，正確 ~":
            break

if __name__ == "__main__":
    main()
