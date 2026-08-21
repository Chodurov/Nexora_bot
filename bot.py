import os
import json
import logging
import asyncio
import re
import uvicorn
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# -------------------------------------------------------------------
# НАСТРОЙКА ЛОГИРОВАНИЯ
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# КОНФИГУРАЦИЯ (ТОКЕН И АДМИНЫ)
# -------------------------------------------------------------------
BOT_TOKEN = "8936565888:AAH-dX1vxyGFx7bSgNQiNElBLVtqKkx2ACg"  # Укажи здесь свой полный токен бота, если он отличается
ADMIN_IDS = [8756814132]  # Твой Telegram ID и ID твоих соразработчиков

# Файл базы данных
ORDERS_FILE = "orders_db.json"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# FastAPI сервер
app = FastAPI()

# -------------------------------------------------------------------
# РАБОТА С ФАЙЛОМ БАЗЫ ДАННЫХ (PERSISTENT STORAGE)
# -------------------------------------------------------------------
def load_orders() -> dict:
    """Загружает заказы из файла JSON при запуске"""
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ключи в JSON всегда строки, преобразуем обратно в int (ID заказа)
                return {int(k): v for k, v in data.items()}
        except Exception as e:
            logger.error(f"Ошибка чтения {ORDERS_FILE}: {e}")
    return {}

def save_orders():
    """Сохраняет текущее состояние заказов в файл JSON"""
    try:
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(orders_db, f, ensure_ascii=False, indent=2)
    except Exception as e:
            logger.error(f"Ошибка сохранения {ORDERS_FILE}: {e}")

# Загружаем сохраненные заказы из файла
orders_db = load_orders()

def clean_username(raw: str) -> str:
    """Очищает юзернейм от @ и символов пробела"""
    if not raw:
        return ""
    cleaned = raw.strip()
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]
    return cleaned.lower()

# -------------------------------------------------------------------
# 1. КОМАНДА /start
# -------------------------------------------------------------------
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    raw_username = message.from_user.username or ""
    username = clean_username(raw_username)

    # 1. Если /start нажал Админ
    if user_id in ADMIN_IDS:
        await message.answer(
            "👑 **Привет, Админ Nexora Studio!**\n\n"
            "Панель управления готова к работе.",
            parse_mode="Markdown"
        )
        return

    # Вспомогательная функция отправки статуса
    async def send_order_status(order_id: int, order: dict):
        order["client_chat_id"] = message.chat.id
        save_orders()  # Сохраняем привязанный chat_id
        
        status_label = order.get("status_label", "Обрабатывается")
        
        if "last_status_text" in order:
            await message.answer(
                f"Здравствуйте, {message.from_user.first_name}! 😊\n\n"
                f"📌 **Статус Заказа №{order_id}:** {status_label}\n\n"
                f"💬 **Ответ от разработчика:**\n{order['last_status_text']}",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"Здравствуйте, {message.from_user.first_name}! 😊\n\n"
                f"Вы успешно привязаны к **Заказу №{order_id}**! ✅\n"
                f"Ваша заявка обрабатывается. Как только разработчик изменит статус заказа, вы получите уведомление здесь!",
                parse_mode="Markdown"
            )

    # 2. Если /start по глубокой ссылке (/start order_1)
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("order_"):
        try:
            order_id = int(args[1].split("_")[1])
            if order_id in orders_db:
                await send_order_status(order_id, orders_db[order_id])
                return
        except ValueError:
            pass

    # 3. Поиск заказа по юзернейму
    if username:
        for order_id in sorted(orders_db.keys(), reverse=True):
            order = orders_db[order_id]
            saved_contact = clean_username(order.get("contact", ""))
            
            if saved_contact and (saved_contact == username or username in saved_contact or saved_contact in username):
                await send_order_status(order_id, order)
                return

    # 4. Если заказов не найдено
    await message.answer(
        "Здравствуйте! 😊 Спасибо за обращение в **Nexora Studio**.\n\n"
        "У вас пока нет активных заказов. Вы можете оформить заявку на нашем сайте!"
    )

# -------------------------------------------------------------------
# 2. ВСПОМОГАТЕЛЬНЫЕ КНОПКИ УПРАВЛЕНИЯ ЗАКАЗОМ
# -------------------------------------------------------------------
def get_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять заказ", callback_data=f"accept_{order_id}"),
                InlineKeyboardButton(text="⏳ В очередь", callback_data=f"queue_{order_id}")
            ],
            [
                InlineKeyboardButton(text="🔴 Занят", callback_data=f"busy_{order_id}"),
                InlineKeyboardButton(text="❌ Отклонить заказ", callback_data=f"decline_{order_id}")
            ]
        ]
    )

# -------------------------------------------------------------------
# 3. ОБРАБОТКА НАЖАТИЯ КНОПОК АДМИНОМ
# -------------------------------------------------------------------
@dp.callback_query()
async def process_callback(callback: CallbackQuery):
    data = callback.data
    
    if "_" not in data:
        await callback.answer()
        return

    action, order_id_str = data.split("_", 1)
    try:
        order_id = int(order_id_str)
    except ValueError:
        await callback.answer("Ошибка в формате заказа.")
        return

    # Проверяем наличие заказа в базе данных
    if order_id not in orders_db:
        await callback.answer("Заказ устарел или не найден!", show_alert=True)
        return

    order = orders_db[order_id]
    client_chat_id = order.get("client_chat_id")
    client_username = order.get("contact", "клиент")

    # Формируем ответы и статусы
    if action == "accept":
        status_label = "✅ Принят"
        client_text = f"Ваш **Заказ №{order_id}** успешно принят в работу! 🚀 Разработчик уже занимается вашей задачей."
        admin_note = "✅ **Вы ПРИНЯЛИ заказ.** Клиент уведомлен!"
    elif action == "queue":
        status_label = "⏳ В очереди"
        client_text = f"Здравствуйте! Вы вошли в очередь по **Заказу №{order_id}** ✅ Как только подойдет ваш черед, мы начнем разработку!"
        admin_note = "⏳ **Заказ помещен В ОЧЕРЕДЬ.** Клиент уведомлен!"
    elif action == "busy":
        status_label = "🔴 Разработчик занят"
        client_text = f"Здравствуйте! Разработчик сейчас занят работой по текущим проектам. Ваш **Заказ №{order_id}** принят на рассмотрение, мы ответим при первой возможности!"
        admin_note = "🔴 **Вы установили статус 'ЗАНЯТ'.**"
    elif action == "decline":
        status_label = "❌ Отклонен"
        client_text = f"К сожалению, ваш **Заказ №{order_id}** отклонен. Свяжитесь с нами, если у вас возникли вопросы."
        admin_note = "❌ **Заказ ОТКЛОНЕН.**"
    else:
        await callback.answer()
        return

    # Сохраняем обновленный статус
    order["status_label"] = status_label
    order["last_status_text"] = client_text
    save_orders()  # Сохраняем в файл!

    # Отправка сообщения клиенту, если он привязан
    if client_chat_id:
        try:
            await bot.send_message(client_chat_id, client_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить статус клиенту {client_chat_id}: {e}")

    # Обновляем сообщение у Админа
    client_info = f"@{client_username}" if not client_username.startswith("http") else client_username
    
    warning_text = ""
    if not client_chat_id:
        warning_text = (
            f"\n\n⚠️ *Клиент еще не написали боту /start.*\n"
            f"Как только пользователь @{clean_username(client_username)} напишет `/start`, ему сразу придет этот статус."
        )

    updated_message = (
        f"🚀 **ЗАКАЗ №{order_id}**\n\n"
        f"📌 **Проект/Услуга:** {order.get('service', 'Н/Д')}\n"
        f"👤 **Контакты клиента:** {client_info}\n"
        f"📝 **Детали:** {order.get('details', 'Без описания')}\n\n"
        f"СТАТУС: **{status_label}**\n"
        f"_{admin_note}_{warning_text}"
    )

    try:
        await callback.message.edit_text(
            updated_message,
            reply_markup=get_order_keyboard(order_id),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка редактирования сообщения админа: {e}")

    await callback.answer("Статус заказа обновлен!")

# -------------------------------------------------------------------
# 4. API ЭНДПОИНТ ДЛЯ ПРИЕМА ЗАКАЗОВ С САЙТА
# -------------------------------------------------------------------
@app.post("/api/order")
async def create_order(request: Request):
    try:
        data = await request.json()
        
        # Определяем следующий ID заказа
        next_id = max(orders_db.keys(), default=0) + 1
        
        # Записываем заказ
        new_order = {
            "service": data.get("service", "Дизайн / Разработка"),
            "contact": data.get("contact", "Не указан"),
            "details": data.get("details", "Без описания"),
            "client_chat_id": None
        }
        
        orders_db[next_id] = new_order
        save_orders()  # Мгновенно сохраняем в файл JSON!

        # Рассылаем уведомление ВСЕМ Админам
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚀 **НОВЫЙ ЗАКАЗ №{next_id}!**\n\n"
                    f"📌 **Проект/Услуга:** {new_order['service']}\n"
                    f"👤 **Контакты клиента:** {new_order['contact']}\n"
                    f"📝 **Детали запроса:** {new_order['details']}",
                    reply_markup=get_order_keyboard(next_id),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки админу {admin_id}: {e}")

        return {"status": "success", "order_id": next_id}
    except Exception as e:
        logger.error(f"Ошибка обработки заказа с сайта: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"status": "running", "orders_count": len(orders_db)}

# -------------------------------------------------------------------
# 5. ЗАПУСК БОТА И ВЕБ-СЕРВЕРА С ЗАЩИТОЙ ОТ КОНФЛИКТОВ
# -------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    # Удаляем вебхук при старте, чтобы исключить конфликты
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем polling в фоновой задаче
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)