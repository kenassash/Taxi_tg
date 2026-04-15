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

    Создайте файл `.env` в корне проекта и укажите id администраторов:

    ```bash
    CHAT_ID_ADMIN=<id_админа_или_несколько_id_через_запятую>
    ```

4. **Настройте `settings.yaml`:**

    В файле `settings.yaml` заполните:
    - `bot.token` — токен бота.
    - `db.dsn` — строку подключения к PostgreSQL (например, `postgresql+asyncpg://user:password@localhost/dbname`).

5. **Запустите бота:**

    ```bash
    python run.py
    ```

## Запуск на Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m alembic upgrade head
python run.py
```

## Автозапуск через systemd (Ubuntu)

1. Скопируйте сервис-файл и обновите systemd:

```bash
sudo cp deploy/taxi-bot.service /etc/systemd/system/taxi-bot.service
sudo systemctl daemon-reload
```

2. Запустите сервис и включите автозапуск:

```bash
sudo systemctl enable --now taxi-bot.service
```

3. Проверка статуса и логов:

```bash
sudo systemctl status taxi-bot.service
sudo journalctl -u taxi-bot.service -f
```

4. Если путь/пользователь у вас другой, отредактируйте значения в `deploy/taxi-bot.service`:
   - `User`
   - `WorkingDirectory`
   - `EnvironmentFile`
   - `ExecStart`

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

![Скриншот Такси бот](https://github.com/kenassash/Taxi_tg/blob/master/img/1.png)
![Скриншот Панель](https://github.com/kenassash/Taxi_tg/blob/master/img/2.png)
![Скриншот Заказ](https://github.com/kenassash/Taxi_tg/blob/master/img/3.png)
![Скриншот Сделать заказ](https://github.com/kenassash/Taxi_tg/blob/master/img/4.png)
![Скриншот Админ панель](https://github.com/kenassash/Taxi_tg/blob/master/img/5.png)
![Скриншот Информация о заказе](https://github.com/kenassash/Taxi_tg/blob/master/img/6.png)

Уникальность таблицы сделать секвенцию:
Найди имя последовательности:

sql
Копировать
Редактировать
SELECT pg_get_serial_sequence('city_routes', 'id');
Пример ответа: 'city_routes_id_seq'

Сбрось значение последовательности на максимум текущих id:

sql
Копировать
Редактировать
SELECT setval('city_routes_id_seq', (SELECT MAX(id) FROM city_routes));


Работа с alembic

alembic revision --autogenerate -m "add price to settings"
alembic upgrade head