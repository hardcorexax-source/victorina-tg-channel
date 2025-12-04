import asyncio
import apis
import gemini
import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = apis.tg
CHANNEL_ID = '@prog_vectorina'
MAX_QUESTIONS = 50  # Максимальное количество вопросов в истории
QUIZ_INTERVAL = 60  # Интервал отправки викторин в секундах (3600 = 1 час)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Загрузка вопросов
all_quest = []
try:
    with open("questions.json", "r", encoding="UTF-8") as file:
        all_quest = json.load(file)
except Exception as e:
    all_quest = []

basic_prompt = (
    "Сгенерируй один новый вопрос по программированию для викторины. "
    "Вопрос не должен повторяться с предыдущими. "
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
    "Пиши только JSON. Никаких объяснений. Ограничение в длину 1000 символов"
)


async def send_quiz():
    """Функция для отправки викторины в канал"""
    # Формируем промпт с историей вопросов
    all_quest_str = ""
    ind = 1
    for quest in all_quest:
        all_quest_str += f"{ind}. {quest}. "
        ind += 1
    
    prompt = basic_prompt
    if all_quest_str:
        prompt = prompt.replace(
            "Вопрос не должен повторяться с предыдущими.",
            f"Вопрос не должен быть таким же как эти: {all_quest_str}."
        )
    
    # Получаем ответ от модели
    answ = gemini.get_answer(prompt)
    
    # Очистка
    answ = answ.strip()
    answ = answ.replace("```json", "").replace("```", "").strip()
    
    # Парсинг JSON
    try:
        answ_obj = json.loads(answ)
    except Exception as e:
        logging.error(f"Ошибка JSON: {e}\nОтвет модели:\n{answ}")
        return False
    
    # Извлекаем данные из ответа модели
    question = answ_obj["question"]
    options = answ_obj["options"]
    correct_option_id = answ_obj.get("correct_option_id", 0)
    explanation = answ_obj.get("explanation", "")
    
    # Проверка корректности индекса
    if not (0 <= correct_option_id < len(options)):
        logging.error(f"Ошибка: correct_option_id={correct_option_id} выходит за пределы options (длина {len(options)})")
        return False
    
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
        
        logging.info(f"Викторина отправлена! Правильный ответ: {options[correct_option_id]}")
        
        # Сохраняем вопрос
        all_quest.append(question)
        
        # Если вопросов больше MAX_QUESTIONS, удаляем самый старый
        if len(all_quest) > MAX_QUESTIONS:
            all_quest.pop(0)
        
        # Сохраняем в файл
        with open("questions.json", "w", encoding="UTF-8") as file:
            json.dump(all_quest, file, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        logging.error(f"Ошибка при отправке: {e}")
        return False


async def quiz_scheduler():
    """Фоновая задача для периодической отправки викторин"""
    await asyncio.sleep(5)  # Небольшая задержка после запуска бота
    
    while True:
        try:
            logging.info("Отправка викторины...")
            await send_quiz()
        except Exception as e:
            logging.error(f"Ошибка в планировщике: {e}")
        
        # Ждем указанный интервал
        logging.info(f"Следующая викторина через {QUIZ_INTERVAL} секунд")
        await asyncio.sleep(QUIZ_INTERVAL)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет! Бот запущен и автоматически отправляет викторины каждые {QUIZ_INTERVAL} секунд.\n"
        "Используй /quiz для ручной отправки викторины.\n"
        "Используй /status для проверки статуса."
    )


@dp.message(Command("quiz"))
async def cmd_send_quiz(message: types.Message):
    """Команда для ручной отправки викторины"""
    await message.answer("Отправляю викторину...")
    success = await send_quiz()
    if success:
        await message.answer("✅ Викторина успешно отправлена!")
    else:
        await message.answer("❌ Ошибка при отправке викторины")


@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    """Команда для проверки статуса"""
    await message.answer(
        f"📊 Статус бота:\n"
        f"Интервал отправки: {QUIZ_INTERVAL} сек ({QUIZ_INTERVAL//60} мин)\n"
        f"Вопросов в истории: {len(all_quest)}/{MAX_QUESTIONS}\n"
        f"Канал: {CHANNEL_ID}"
    )


async def main():
    # Запускаем планировщик викторин в фоне
    asyncio.create_task(quiz_scheduler())
    
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())