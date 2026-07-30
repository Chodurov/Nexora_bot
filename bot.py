import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiohttp import web

# -------------------------------------------------------------------
# НАСТРОЙКИ
# -------------------------------------------------------------------
BOT_TOKEN = "8936565888:AAFkpOjvW49VJsNsEyU1oujfFL9YbU-CPsA"  # Твой токен
ADMIN_IDS = [8756814132, 8481526135]  # Твой ID и ID друга

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# База данных в памяти
orders_db = {}
order_counter = 0


# Вспомогательная функция очистки юзернейма
def clean_username(raw_contact: str) -> str:
    """Очищает контакт от @, ссылок и пробелов для точного сравнения."""
    if not raw_contact:
        return ""
    contact = raw_contact.strip().lower()
    contact = contact.replace("https://t.me/", "").replace("t.me/", "").replace("@", "")
    return contact


# -------------------------------------------------------------------
# 1. КОМАНДА /start
# -------------------------------------------------------------------
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = clean_username(message.from_user.username)

    # 1. Если /start нажал кто-то из Админов (Ты или Твой друг)
    if user_id in ADMIN_IDS:
        await message.answer(
            "👑 **Привет, Админ Nexora Studio!**\n\n"
            "Панель управления готова к работе.",
            parse_mode="Markdown"
        )
        return

    # 2. Если /start нажал Клиент по глубокой ссылке (например, /start order_1)
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("order_"):
        try:
            order_id = int(args[1].split("_")[1])
            if order_id in orders_db:
                orders_db[order_id]["client_chat_id"] = message.chat.id
                await message.answer(
                    f"Здравствуйте, {message.from_user.first_name}! 😊\n\n"
                    f"Вы успешно привязаны к **Заказу №{order_id}**!\n"
                    f"Сюда будут приходить все обновления по вашей заявке.",
                    parse_mode="Markdown"
                )
                return
        except ValueError:
            pass

    # 3. Если /start нажал Клиент без ссылки — ищем по юзернейму
    found_order_id = None
    if username:
        for order_id, order in orders_db.items():
            saved_contact = clean_username(order.get("contact", ""))
            if saved_contact and saved_contact == username:
                order["client_chat_id"] = message.chat.id
                found_order_id = order_id
                break

    if found_order_id:
        await message.answer(
            f"Здравствуйте, {message.from_user.first_name}! 😊\n\n"
            f"Мы нашли ваш **Заказ №{found_order_id}**! ✅\n"
            f"Ваш аккаунт успешно привязан. Теперь сюда будут приходить статусы по заказу!",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "Здравствуйте! 😊 Спасибо за обращение в **Nexora Studio**.\n\n"
            "Ваша заявка обрабатывается. Как только разработчик изменит статус заказа, вы получите уведомление здесь!"
        )


# -------------------------------------------------------------------
# 2. КНОПКИ УПРАВЛЕНИЯ ДЛЯ АДМИНА
# -------------------------------------------------------------------
def get_admin_keyboard(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Принять заказ", callback_data=f"accept_{order_id}"),
            InlineKeyboardButton(text="⏳ В очередь", callback_data=f"queue_{order_id}")
        ],
        [
            InlineKeyboardButton(text="🔴 Занят", callback_data=f"busy_{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить заказ", callback_data=f"reject_{order_id}")
        ]
    ])


async def notify_client(order_id: int, text: str) -> bool:
    """Отправляет сообщение клиенту, если его chat_id привязан."""
    order = orders_db.get(order_id)
    if order and order.get("client_chat_id"):
        try:
            await bot.send_message(chat_id=order["client_chat_id"], text=text)
            return True
        except Exception as e:
            print(f"Ошибка отправки клиенту: {e}")
    return False


# -------------------------------------------------------------------
# 3. ОБРАБОТЧИКИ КНОПОК АДМИНА
# -------------------------------------------------------------------
@dp.callback_query(F.data.startswith(("accept_", "queue_", "busy_", "reject_")))
async def handle_admin_action(callback: CallbackQuery):
    # Проверяем, что кнопку нажал именно Админ
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав для управления заказами!", show_alert=True)
        return

    action, order_id_str = callback.data.split("_")
    order_id = int(order_id_str)

    order = orders_db.get(order_id)
    if not order:
        await callback.answer("Заказ устарел или не найден!", show_alert=True)
        return

    messages = {
        "accept": "Ваш заказ принят✅ Ваша работа будет готова спустя некоторое время. Спасибо что выбрали нас😊.",
        "queue": f"Вы вошли в очередь✅ Вы на {order_id} месте. Ожидайте своей очереди. Спасибо что выбрали нас😊.",
        "busy": "Разработчик сейчас занят! Просим подождать. Когда разработчик будет свободен, он ответит вам!",
        "reject": "Извините! Ваш заказ не соответствует нашим работам. Ваш заказ отклонен❌."
    }

    status_labels = {
        "accept": "🟢 Принят в работу",
        "queue": f"⏳ В очереди ({order_id} место)",
        "busy": "🔴 Разработчик занят",
        "reject": "❌ Отклонен"
    }

    client_msg = messages[action]
    sent_successfully = await notify_client(order_id, client_msg)

    order["last_status_text"] = client_msg
    order["status_label"] = status_labels[action]

    if sent_successfully:
        note = "\n\n✅ **Уведомление доставлено клиенту в Telegram!**"
    else:
        note = (
            "\n\n⚠️ **Клиент еще не привязался к боту.**\n"
            f"Как только клиент с юзернеймом `{order['contact']}` напишет боту `/start`, ему придет статус."
        )

    await callback.answer("Статус обновлен!")
    
    # Очищаем старые статусы в сообщении, чтобы не было дублей
    clean_text = callback.message.text.split("\n\n**СТАТУС:**")[0]
    
    await callback.message.edit_text(
        f"{clean_text}\n\n**СТАТУС:** {status_labels[action]}{note}",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard(order_id) if action != "reject" else None
    )


# -------------------------------------------------------------------
# 4. ПРИЕМ ДАННЫХ С САЙТА (И СЕРВЕР CORS)
# -------------------------------------------------------------------
async def handle_website_order(request):
    global order_counter

    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return web.Response(status=200, headers=headers)

    try:
        data = await request.json()
        print(f"📥 ПОЛУЧЕН ЗАКАЗ С САЙТА: {data}")

        order_counter += 1
        order_id = order_counter

        service = data.get("service", "Заказ с сайта")
        contact = data.get("contact", "Не указан")
        details = data.get("details", "Без описания")

        orders_db[order_id] = {
            "service": service,
            "contact": contact,
            "details": details,
            "client_chat_id": None,
            "created_at": datetime.now(),
            "status_label": "Новый"
        }

        msg_text = (
            f"🚀 **НОВЫЙ ЗАКАЗ №{order_id}!**\n\n"
            f"📌 **Проект/Услуга:** {service}\n"
            f"👤 **Контакты клиента:** {contact}\n"
            f"📝 **Детали запроса:**\n{details}"
        )

        # Отправляем сообщение ВСЕМ админам из списка
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=msg_text,
                    parse_mode="Markdown",
                    reply_markup=get_admin_keyboard(order_id)
                )
            except Exception as e:
                print(f"Ошибка отправки админу {admin_id}: {e}")

        headers = {"Access-Control-Allow-Origin": "*"}
        return web.json_response({"status": "success", "order_id": order_id}, headers=headers)

    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        headers = {"Access-Control-Allow-Origin": "*"}
        return web.json_response({"status": "error", "message": str(e)}, status=400, headers=headers)


# -------------------------------------------------------------------
# 5. ФОНОВАЯ ОЧИСТКА СТАРЫХ ЗАКАЗОВ (РАЗ В 24 ЧАСА)
# -------------------------------------------------------------------
async def auto_clean_old_orders():
    while True:
        await asyncio.sleep(86400)
        now = datetime.now()
        expired_ids = []

        for order_id, order in orders_db.items():
            created_at = order.get("created_at")
            if created_at and (now - created_at) > timedelta(days=7):
                expired_ids.append(order_id)

        for order_id in expired_ids:
            del orders_db[order_id]
            print(f"🧹 Заказ №{order_id} автоматически удален из памяти (прошло 7 дней).")


# -------------------------------------------------------------------
# 6. ЗАПУСК БОТА И ВЕБ-СЕРВЕРА
# -------------------------------------------------------------------
import os

async def main():
    asyncio.create_task(auto_clean_old_orders())

    app = web.Application()
    app.router.add_post("/api/order", handle_website_order)
    app.router.add_options("/api/order", handle_website_order)

    runner = web.AppRunner(app)
    await runner.setup()
    
    # Берем порт из окружения Railway (или 8080 по умолчанию) и хост 0.0.0.0
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print("🟢 Бот и сервер успешно запущены!")
    await dp.start_polling(bot)

    if __name__ == "__main__":
        asyncio.run(main())