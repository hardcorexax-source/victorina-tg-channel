import requests
import json
import apis

# --- ВСТАВЛЯТЬ КЛЮЧ СЮДА ---
API_KEY = apis.openrouter
# ---------------------------

# Основные настройки
URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
# Используем рабочую бесплатную модель
MODEL = "amazon/nova-2-lite-v1:free" 

def get_answer(user_quest:str):

  # --- Первый запрос ---
  response1 = requests.post(
    url=URL,
    headers=HEADERS,
    data=json.dumps({
      "model": MODEL,
      "messages": [
          {
            "role": "user",
            "content": f"в ответе должно быть меньше 1000 символов. : {user_quest}"
          }
        ],
      "reasoning": {"enabled": True}
    })
  )

  # Проверяем на ошибки
  if response1.status_code != 200:
      print("Ошибка API:", response1.text)
      return " "

  return response1.json()['choices'][0]['message']['content']