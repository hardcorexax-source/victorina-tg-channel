import asyncio
import apis
import gemini
import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Poll



all_quest = []

try:
    with open("questions.json", "r", encoding="UTF-8") as file:
        all_quest = json.load(file)
except Exception as e:
    all_quest = []


all_quest_str = ""
ind = 1

for quest in all_quest:
    all_quest_str += f"{ind}. {quest}. "
    ind += 1

basic_prompt = (
    "Сгенерируй один новый вопрос по программированию для викторины. "
    f"Вопрос не должен быть таким же как эти: {all_quest_str}. "
    "Ответ должен быть в формате ЧИСТОГО JSON без комментариев, кавычек вне объекта, "
    "без Markdown, без ```json, без текста до или после. "
    "Формат строго такой: "
    "{"
    "\"question\": \"текст вопроса\", "
    "\"options\": [\"вариант1\", \"вариант2\", \"вариант3\"], "
    "\"correct_option_id\": 0, "
    "\"explanation\": \"подробное объяснение правильного ответа\""
    "}. "
    "correct_option_id - это индекс правильного ответа в массиве options (начиная с 0). "
    "Вариантов ответа должно быть 3–6. "
    "Пиши только JSON. Никаких объяснений. Ограничение в длину 2000 символов"
)

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = apis.tg
CHANNEL_ID = '@prog_vectorina'
MAX_QUESTIONS = 50  # Максимальное количество вопросов в истории

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я готов. Напиши /quiz, чтобы отправить викторину в канал.")

@dp.message(Command("quiz"))
async def cmd_send_quiz(message: types.Message):
    answ = gemini.get_answer(basic_prompt)

    # Очистка
    answ = answ.strip()
    answ = answ.replace("```json", "").replace("```", "").strip()

    # Парсинг JSON
    try:
        answ_obj = json.loads(answ)
    except Exception as e:
        await message.answer(f"Ошибка JSON: {e}\nОтвет модели:\n{answ}")
        return

    # Извлекаем данные из ответа модели
    question = answ_obj["question"]
    options = answ_obj["options"]
    correct_option_id = answ_obj.get("correct_option_id", 0)
    explanation = answ_obj.get("explanation", "")

    # Проверка корректности индекса
    if not (0 <= correct_option_id < len(options)):
        await message.answer(f"Ошибка: correct_option_id={correct_option_id} выходит за пределы options (длина {len(options)})")
        return

    try:
        await bot.send_poll(
            chat_id=CHANNEL_ID,
            question=question,
            options=options,
            type='quiz',
            correct_option_id=correct_option_id,
            explanation=explanation,
            is_anonymous=True
        )
        await message.answer(f"Викторина отправлена!\nПравильный ответ: {options[correct_option_id]}")
        
        # Сохраняем вопрос
        all_quest.append(question)
        
        # Если вопросов больше 50, удаляем самый старый
        if len(all_quest) > MAX_QUESTIONS:
            all_quest.pop(0)  # Удаляет первый (самый старый) элемент
            
        with open("questions.json", "w", encoding="UTF-8") as file:
            json.dump(all_quest, file, ensure_ascii=False, indent=2)
            
    except Exception as e:
        await message.answer(f"Ошибка при отправке: {e}")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())