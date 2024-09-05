# Taxi Bot

## Описание

Этот бот создан для службы такси поселка, обеспечивая удобное взаимодействие с пользователями для заказа и управления поездками. Бот позволяет пользователям просматривать маршруты, заказывать такси и управлять ценами на поездки.

Также реализована панель администратора для управления данными о машинах и водителях.

## Установка и настройка

1. **Клонируйте репозиторий:**

    ```bash
    git clone <url-репозитория>
    cd <название-папки>
    ```

2. **Установите зависимости:**

    Убедитесь, что у вас установлен Python версии 3.7 или выше. Установите все зависимости:

    ```bash
    pip install -r requirements.txt
    ```

3. **Создайте файл `.env`:**

    Создайте файл `.env` в корне проекта и добавьте в него ваш токен Telegram API:

    ```bash
    BOT_TOKEN=<ваш_токен_бота>
    ```

4. **Запустите бота:**

    ```bash
    python bot.py
    ```

## Стек технологий

- **Aiogram 3.4.1** — библиотека для создания Telegram ботов.
- **Aiogram-Dialog 2.1.0** — библиотека для управления диалогами.
- **SQLite** — для хранения данных.
- **Asyncio** — для обработки асинхронных операций.

## Основные команды
- **/start** — Запуск бота и приветствие.
- **/meneger** — Менеджер для пользователей (доступ к функциям, связанным с управлением поездками и маршрутами).
- **/add_car** — Команда для добавления новой машины (добавить могут только администраторы).

## Админ-панель

Панель администратора предоставляет расширенные возможности для управления системой такси. Админ-панель доступна только пользователям с правами администратора.

## Скриншоты

![Скриншот Такси бот](https://github.com/kenassash/Taxi_tg/tree/master/img1.png)
![Скриншот Панель](https://github.com/kenassash/Taxi_tg/tree/master/img2.png)
![Скриншот Заказ](https://github.com/kenassash/Taxi_tg/tree/master/img3.png)
![Скриншот Сделать заказ](https://github.com/kenassash/Taxi_tg/tree/master/img4.png)
![Скриншот Админ панель](https://github.com/kenassash/Taxi_tg/tree/master/img5.png)
![Скриншот Информация о заказе](https://github.com/kenassash/Taxi_tg/tree/master/img6.png)