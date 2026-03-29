import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = "8383011601:AAHN71NavpUYgureHQ0j5JxQAVA-TjDquj0"
CHAT_ID = -1002977350246

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EKATERINBURG_TZ = timezone(timedelta(hours=5))
RUSSIAN_WEEKDAYS = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
POLL_OPTIONS = ["6-7","7-9","9-11","11-13","13-15","15-17","17-19","19-21","21-23"," -"]
PASSWORD = "Билли"

bot_enabled = True
user_states = {}


def get_tomorrow_ekb() -> str:
    now_ekb = datetime.now(EKATERINBURG_TZ)
    tomorrow = now_ekb + timedelta(days=1)
    return f"{RUSSIAN_WEEKDAYS[tomorrow.weekday()]} {tomorrow.strftime('%d.%m.%Y')}"


def seconds_until_time(hour: int, minute: int = 0) -> float:
    now_ekb = datetime.now(EKATERINBURG_TZ)
    target = now_ekb.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now_ekb >= target:
        target += timedelta(days=1)
    return (target - now_ekb).total_seconds()


async def send_daily_poll(application: Application) -> None:
    global bot_enabled
    if not bot_enabled:
        logger.info("Бот выключен — опрос не отправляется.")
        return
    tomorrow_str = get_tomorrow_ekb()
    logger.info(f"Отправка опроса на дату: {tomorrow_str}")
    try:
        await application.bot.send_message(chat_id=CHAT_ID, text=tomorrow_str)
        await application.bot.send_poll(
            chat_id=CHAT_ID,
            question="Опрос 🐵🔵",
            options=POLL_OPTIONS,
            is_anonymous=False,
            type="regular",
        )
        logger.info("Опрос успешно отправлен.")
    except Exception as e:
        logger.error(f"Ошибка при отправке опроса: {e}")


async def window_controller(application: Application) -> None:
    now_ekb = datetime.now(EKATERINBURG_TZ)
    hour = now_ekb.hour

    if hour >= 20:
        logger.info("Запуск после 20:00 — бот завершает работу.")
        os._exit(0)

    if hour >= 19:
        logger.info("Запуск между 19:00 и 20:00 — отправляем опрос сразу.")
        await send_daily_poll(application)
    else:
        wait_poll = seconds_until_time(19, 0)
        logger.info(f"Ждём до 19:00. Осталось {int(wait_poll/60)} минут.")
        await asyncio.sleep(wait_poll)
        await send_daily_poll(application)

    wait_stop = seconds_until_time(20, 0)
    logger.info(f"Бот завершит работу через {int(wait_stop/60)} минут.")
    await asyncio.sleep(wait_stop)

    logger.info("20:00 — бот завершает работу.")
    os._exit(0)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    user_states[user_id] = "waiting_password"
    await update.message.reply_text("Введите пароль")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state = user_states.get(user_id)
    if state == "waiting_password":
        if text == PASSWORD:
            user_states[user_id] = "authenticated"
            await show_menu(update)
        else:
            user_states.pop(user_id, None)
            await update.message.reply_text("Неверный пароль")
    else:
        user_states[user_id] = "waiting_password"
        await update.message.reply_text("Введите пароль")


async def show_menu(update: Update) -> None:
    keyboard = [[
        InlineKeyboardButton("Включить бота", callback_data="enable"),
        InlineKeyboardButton("Выключить бота", callback_data="disable"),
    ]]
    await update.message.reply_text("Панель управления:", reply_markup=InlineKeyboardMarkup(keyboard))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global bot_enabled
    query = update.callback_query
    user_id = query.from_user.id
    if user_states.get(user_id) != "authenticated":
        await query.answer("Сначала введите пароль.", show_alert=True)
        return
    await query.answer()
    if query.data == "enable":
        if bot_enabled:
            await query.message.reply_text("Бот уже включен")
        else:
            bot_enabled = True
            await query.message.reply_text("Бот включён ✅")
    elif query.data == "disable":
        if not bot_enabled:
            await query.message.reply_text("Бот уже выключен")
        else:
            bot_enabled = False
            await query.message.reply_text("Бот выключен ❌")


async def post_init(application: Application) -> None:
    asyncio.create_task(window_controller(application))


def main() -> None:
    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(CallbackQueryHandler(button_handler))
    logger.info("Бот запущен. Ожидание окна 19:00–20:00 (Екатеринбург).")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
