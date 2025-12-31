import requests
import sys

BOT_TOKEN = "8235545385:AAEu0TEUlqJnL6FHHj6q9CDnyCn2fg6TPNw"

# Get bot info
bot_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe").json()
print("=== 봇 정보 ===")
print(f"이름: {bot_info['result']['first_name']}")
print(f"Username: @{bot_info['result']['username']}")
print()

# Get updates with offset
updates = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-100").json()
print("=== 받은 메시지 ===")
if updates['result']:
    for update in updates['result']:
        if 'message' in update:
            chat_id = update['message']['chat']['id']
            text = update['message'].get('text', '(no text)')
            username = update['message']['chat'].get('username', 'N/A')
            print(f"Chat ID: {chat_id}")
            print(f"Username: @{username}")
            print(f"Message: {text}")
            print()
else:
    print("메시지 없음")
