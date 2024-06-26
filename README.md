# LifeSync Telegram Bot

## Обзор

LifeSync — это многофункциональный Telegram-бот, предназначенный для упрощения управления задачами и повышения продуктивности. Бот предлагает ряд функций, включая управление задачами, интервальное повторение слов, конвертер валют и менеджер тренировок.

### Функции

- **Управление списком задач**: Эффективное отслеживание ваших задач.
- **Интервальное повторение слов**: Улучшение словарного запаса с помощью интервального повторения.
- **Конвертер валют**: Получение актуальных курсов обмена валют.
- **Менеджер тренировок**:
  - Отслеживание параметров тела для мониторинга прогресса.
  - Ведение подробного дневника тренировок.
  - Генерация PDF-отчетов по тренировкам, отфильтрованных по различным критериям.

### Технологический стек

- **Backend**: FastAPI
- **Telegram Клиент**: aiogram
- **База данных**: SQLAlchemy с миграциями через Alembic
- **Генерация PDF**: Интегрированная генерация PDF и шаблонизация
- **Контейнеризация**: Docker

## Настройка проекта

### Клонирование репозитория

Для начала клонируйте репозиторий с GitHub:

```bash
git clone https://github.com/iStas56/LifeSync.git
cd LifeSync
```

## Настройка окружения

1. Создание файла .env: Скопируйте предоставленный .env.example в .env и настройте переменные окружения.

```
cp .env.example .env
```

2. Конфигурация переменных окружения: Обновите файл .env с вашими значениями, такими как учетные данные базы данных, токен Telegram-бота и т.д.


## Настройка Docker

1. Сборка Docker-контейнеров: Используйте Docker Compose для сборки необходимых контейнеров.

```
docker-compose build
```

2. Запуск Docker-контейнеров: Запустите контейнеры с помощью Docker Compose.
```
docker-compose up -d
```

## Миграция базы данных

Примените миграции базы данных для настройки схемы:
```
docker-compose exec backend alembic upgrade head
```

## Доступ к боту

После запуска контейнеров:

- Telegram-бот: Взаимодействуйте с ботом в Telegram, используя токен, настроенный в файле .env.
- Документация FastAPI: Доступна по адресу http://localhost:8000/docs для интерактивного исследования API.

