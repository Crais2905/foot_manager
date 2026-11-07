# Football Management System

Навчальне ядро футбольного менеджера: спринти 2–4.
Python 3.12+, SQLAlchemy 2.x, asyncpg, PostgreSQL, Alembic, pytest.

## Запуск і перевірки

Команди виконуються з кореня проєкту в PowerShell:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[test]"
# Для нового середовища: скопіюйте .env.example у .env і задайте свої параметри.
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic current
.venv\Scripts\python.exe -m alembic check
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m mypy app
```

Лише доменні тести, без БД:

```powershell
.venv\Scripts\python.exe -m pytest -q -m "not integration"
```

Лише інтеграційні тести:

```powershell
.venv\Scripts\python.exe -m pytest -q -m integration
```

Інтеграційні тести використовують `TEST_DATABASE_URL`, а за його відсутності —
налаштування основного підключення. Кожен тест створює власну схему `fm_test_<uuid>`,
виконує в ній справжні міграції та видаляє тільки цю схему після завершення.
Користувач PostgreSQL повинен мати право створення схем у вибраній БД.
Якщо підключення не налаштоване, інтеграційні тести пропускаються; якщо воно
налаштоване, але недоступне, тести завершуються помилкою.

Пріоритет конфігурації: `DATABASE_URL`, сумісний зі старим проєктом
`DATABASE_ALEMBIC_URL`, потім `DB_HOST/PORT/NAME/USER/PASSWORD`.
Для кожного ключа змінна середовища має пріоритет перед `.env`.
Пароль з особливими символами безпечніше передавати через `DB_PASSWORD`:
`URL.create()` правильно його екранує. Не публікуйте `.env`.

## Архітектура

- `app/domain/`: звичайні Python-класи, валідація та зв'язки предметної області.
- `app/application/national_team_builder.py`: вибір гравців і створення збірної.
- `app/common/shell_sorter.py`: незалежний Shell Sort з ключем.
- `app/db/base.py`: `DeclarativeBase` і правила іменування обмежень.
- `app/db/enums.py`: повторне використання доменного enum без залежності Domain від ORM.
- `app/db/models.py`: ORM-моделі та асоціативна сутність складу.
- `app/db/session.py`: конфігурація, async engine, фабрика й контекст сесії.
- `alembic/versions/`: історія схеми БД.
- `tests/`: доменні, сценарні та PostgreSQL інтеграційні тести.

Repository, Service, Unit of Work, GUI та повний Domain↔ORM Mapper до спринтів 2–4
не входять і тут не реалізовані.




