# -------------------------------------------------------------------
# 7. ПРИЕМ ДАННЫХ С САЙТА (С ПОДДЕРЖКОЙ CORS)
# -------------------------------------------------------------------
async def handle_website_order(request):
    global order_counter
    
    # Обработка предварительного CORS-запроса (OPTIONS)
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
            "client_chat_id": None
        }

        msg_text = (
            f"🚀 **НОВЫЙ ЗАКАЗ №{order_id}!**\n\n"
            f"📌 **Проект/Услуга:** {service}\n"
            f"👤 **Контакты клиента:** {contact}\n"
            f"📝 **Детали запроса:**\n{details}"
        )

        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=msg_text,
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard(order_id)
        )
        print("✅ Сообщение успешно отправлено в Telegram админу!")

        headers = {"Access-Control-Allow-Origin": "*"}
        return web.json_response({"status": "success", "order_id": order_id}, headers=headers)

    except Exception as e:
        print(f"❌ ОШИБКА ПРИ ОТПРАВКЕ В TELEGRAM: {e}")
        headers = {"Access-Control-Allow-Origin": "*"}
        return web.json_response({"status": "error", "message": str(e)}, status=400, headers=headers)


# -------------------------------------------------------------------
# 8. ЗАПУСК БОТА И ВЕБ-СЕРВЕРА
# -------------------------------------------------------------------
async def main():
    app = web.Application()
    # Добавляем маршруты для POST и OPTIONS (для CORS)
    app.router.add_post("/api/order", handle_website_order)
    app.router.add_options("/api/order", handle_website_order)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()

    print("🟢 Бот и сервер успешно запущены!")
    await dp.start_polling(bot)

# -------------------------------------------------------------------
# 8. ЗАПУСК БОТА И ВЕБ-СЕРВЕРА
# -------------------------------------------------------------------
async def main():
    app = web.Application()
    app.router.add_post("/api/order", handle_website_order)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()

    print("🟢 Бот и сервер успешно запущены!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())