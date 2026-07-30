<?php
// 1. Вставьте данные вашего бота
$botToken = "8936565888:AAG_SvTLOvA4DY9bHvXk4y0OQ-G0DpImV0U";
$chatId = "8756814132";

// Проверяем, что форма была отправлена методом POST
if ($_SERVER['REQUEST_METHOD'] === 'POST') {

    // 2. Получаем и очищаем данные из формы
    $service = htmlspecialchars($_POST['service'] ?? 'Не указано');
    $contact = htmlspecialchars($_POST['contact'] ?? 'Не указан');
    $details = htmlspecialchars($_POST['details'] ?? 'Без описания');

    // 3. Формируем текст сообщения
    if ($service === 'Личный разговор') {
        $message  = "📞 *КЛИЕНТ ХОЧЕТ ПОГОВОРИТЬ С ВАМИ ЛИЧНО*\n\n";
        $message .= "👤 *Контакты:* " . $contact . "\n";
        $message .= "💬 *Тема:* " . $details;
    } else {
        $message  = "🚀 *ВАМ ПРИШЁЛ НОВЫЙ ЗАКАЗ!*\n\n";
        $message .= "📌 *Услуга:* " . $service . "\n";
        $message .= "👤 *Контакты:* " . $contact . "\n\n";
        $message .= "📝 *Детали заказа:*\n" . $details;
    }

    // 4. Формируем URL для отправки в Telegram API
    $url = "https://api.telegram.org/bot{$botToken}/sendMessage";
    
    $postData = [
        'chat_id' => $chatId,
        'text' => $message,
        'parse_mode' => 'Markdown' // Включает жирный шрифт и красивое оформление
    ];

    // 5. Отправляем запрос через cURL (безопасный способ)
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    curl_close($ch);

    // 6. Ответ пользователю после отправки формы
    echo "<h1>Спасибо! Ваша заявка отправлена.</h1>";
    echo "<p><a href='index.html'>Вернуться на сайт</a></p>";
} else {
    echo "Ошибка отправки формы.";
}
?>