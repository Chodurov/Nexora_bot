document.getElementById('quizForm').addEventListener('submit', async function(e) {
  e.preventDefault();

  // Собираем данные (замени id элементов на свои из html)
  const orderData = {
    service: "2D игра на Python",  // или значение из опроса
    contact: document.getElementById('contact').value, // Контакт клиента
    details: document.getElementById('details').value, // Описание
    answers: {
      "Платформа": "ПК и Смартфон",
      "Жанр": "Платформер",
      "Сроки": "До 1 недели"
    }
  };

  try {
    const response = await fetch('http://localhost:8080/api/order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(orderData)
    });

    const result = await response.json();

    if (result.status === 'success') {
      // Показываем клиенту благодарность и кнопку перехода в бота
      document.getElementById('formContainer').innerHTML = `
        <div style="text-align: center; padding: 20px;">
          <h3>✅ Заявка №${result.order_id} успешно отправлена!</h3>
          <p>Перейдите в нашего бота, чтобы подтвердить заказ и отслеживать статус:</p>
          <a href="https://t.me/твой_юзернейм_бота" target="_blank" 
             style="display: inline-block; padding: 12px 24px; background: #0088cc; color: white; border-radius: 8px; text-decoration: none; font-weight: bold;">
            💬 Перейти в Telegram-бота
          </a>
        </div>
      `;
    }
  } catch (err) {
    alert("Ошибка соединения с сервером бота.");
  }
});