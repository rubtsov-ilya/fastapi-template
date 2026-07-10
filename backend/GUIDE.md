# Руководство по работе с бэкенд-темплейтом FastAPI + SQLModel

В данном руководстве подробно описана архитектура бэкенда, его настройки, инициализация и приведен пошаговый пример создания новой функциональности (модели, схемы, репозитория, сервиса и эндпоинта).

---

## 1. Архитектура бэкенда

Проект построен на современном и производительном стеке Python:
* **FastAPI** — веб-фреймворк для создания API.
* **SQLModel** — обертка над **SQLAlchemy** и **Pydantic** от автора FastAPI, позволяющая описывать модели таблиц и Pydantic-схемы в едином стиле.
* **Alembic** — инструмент для управления миграциями базы данных.
* **Pydantic v2** — валидация данных и сериализация.
* **Pydantic Settings** — управление конфигурацией через переменные окружения и `.env`.
* **uv** — сверхбыстрый пакетный менеджер и инструмент для управления виртуальным окружением Python.

### Слои приложения (`backend/app/`)

Архитектура следует классическому разделению обязанностей (Separation of Concerns):

1. **`models/` (Слой данных / БД)**
   * Содержит декларативные классы таблиц базы данных (наследники `SQLModel` с флагом `table=True`).
   * Определяет структуру таблиц, типы данных колонок, индексы и связи (`Relationship`).

2. **`schemas/` (Слой валидации / DTO)**
   * Содержит Pydantic-модели (наследники `BaseModel`), используемые для валидации входных данных (payload запросов) и сериализации выходных данных (response body).
   * Изолирует базу данных от внешнего мира.

3. **`repositories/` (Слой работы с БД / DAO)**
   * Содержит низкоуровневые функции для взаимодействия с базой данных (выборки, фильтрация, создание, обновление записей).
   * Не содержит сложной бизнес-логики. Все функции принимают объект сессии `Session` от SQLModel.

4. **`services/` (Слой бизнес-логики)**
   * Содержит функции для реализации бизнес-логики приложения.
   * Координирует работу репозиториев, проверяет права доступа пользователей (например, является ли пользователь владельцем ресурса или суперпользователем), вызывает исключения `HTTPException` при нарушении логики.

5. **`api/` (Слой представления / Эндпоинты)**
   * Содержит маршруты API (`APIRouter`).
   * Внедряет зависимости (`Depends`), такие как сессия БД (`SessionDep`) и текущий пользователь (`CurrentUser`), вызывает функции из слоя сервисов (или напрямую из репозиториев для простых операций чтения/подсчета) и возвращает нужные Pydantic-схемы.

---

## 2. Настройки и конфигурация

Конфигурация приложения находится в файле [config.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/core/config.py).

* Класс `Settings` наследуется от `BaseSettings` (из `pydantic-settings`).
* Настройки считываются из файла `.env`, который должен находиться на один уровень выше директории `backend/` (в корне проекта), в соответствии с конфигурацией:
  ```python
  model_config = SettingsConfigDict(
      env_file="../.env",
      env_ignore_empty=True,
      extra="ignore",
  )
  ```
* **Основные параметры конфигурации:**
  * `API_V1_STR` — префикс для API (по умолчанию `/api/v1`).
  * `SECRET_KEY` — ключ для шифрования/генерации JWT токенов.
  * `ACCESS_TOKEN_EXPIRE_MINUTES` — время жизни токена авторизации.
  * `POSTGRES_SERVER`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` — реквизиты подключения к PostgreSQL.
  * `SQLALCHEMY_DATABASE_URI` — автоматически собираемый URI подключения к БД (использует драйвер `postgresql+psycopg`).
  * `FIRST_SUPERUSER` и `FIRST_SUPERUSER_PASSWORD` — логин/пароль администратора, которые создаются автоматически при инициализации базы.
  * `SENTRY_DSN` — DSN для логирования ошибок в Sentry.
  * Настройки SMTP серверов для отправки писем (`SMTP_HOST`, `SMTP_PORT` и т.д.).

---

## 3. Инициализация приложения (`main.py`)

Запуск и конфигурация FastAPI-приложения происходят в файле [main.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/main.py):

1. **Инициализация Sentry SDK**:
   ```python
   if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
       sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)
   ```
2. **Создание экземпляра FastAPI**:
   ```python
   app = FastAPI(
       title=settings.PROJECT_NAME,
       openapi_url=f"{settings.API_V1_STR}/openapi.json",
       generate_unique_id_function=custom_generate_unique_id,
   )
   ```
   *Параметр `generate_unique_id_function` генерирует уникальные идентификаторы эндпоинтов (например, `items-read_items`). Это критически важно для корректной автогенерации TypeScript-клиентов на фронтенде.*
3. **CORS Middleware**:
   Если в настройках заданы разрешенные источники (`all_cors_origins`), подключается `CORSMiddleware` для разрешения запросов со сторонних доменов (в частности, с фронтенда `http://localhost:5173`).
4. **Подключение роутеров**:
   ```python
   app.include_router(api_router, prefix=settings.API_V1_STR)
   ```
   Основной роутер импортируется из `app.api.main` и собирает в себе маршруты для авторизации, работы с пользователями, системных утилит и сущностей (например, items).

### Предстартовые скрипты и инициализация БД
Перед запуском веб-сервера запускаются вспомогательные скрипты (см. [prestart.sh](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/scripts/prestart.sh)):
1. **`backend_pre_start.py`** — проверяет соединение с базой данных (использует библиотеку `tenacity` для повторных попыток подключения, пока БД не станет доступна).
2. **`alembic upgrade head`** — применяет все миграции БД.
3. **`initial_data.py`** — инициализирует базу данных (создает первого суперпользователя на основе переменных окружения, если его еще нет).

---

## 4. Пример создания новой фичи: «Статьи» (Articles)

Рассмотрим пошаговое добавление новой фичи: сущность **Article (Статья)**, связанная с пользователем. У каждой статьи будет `title`, `content` и `owner_id`.

### Шаг 1. Создание модели базы данных
Создайте файл [backend/app/models/article.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/models/article.py):

```python
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User

def get_datetime_utc() -> datetime:
    return datetime.now(UTC)

class Article(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(min_length=1, max_length=255, index=True)
    content: str = Field(min_length=1)
    created_at: Optional[datetime] = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: Optional["User"] = Relationship(back_populates="articles")
```

Зарегистрируйте модель в [backend/app/models/\_\_init\_\_.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/models/__init__.py):

```python
from sqlmodel import SQLModel
from .user import User
from .item import Item
from .article import Article  # Добавлено

__all__ = [
    "SQLModel",
    "User",
    "Item",
    "Article",  # Добавлено
]
```

*Также не забудьте добавить отношение `articles` в модель пользователя `User` в [backend/app/models/user.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/models/user.py) (опционально, но рекомендуется для двунаправленной связи):*
```python
articles: list["Article"] = Relationship(back_populates="owner", cascade_delete=True)
```

---

### Шаг 2. Создание миграции Alembic
Так как проект использует автогенерацию миграций на основе импортированных SQLModel моделей, запустите команду генерации миграции (убедитесь, что БД запущена):

```bash
docker compose exec backend alembic revision --autogenerate -m "Add Article model"
```
Или, если вы запускаете локально без Docker:
```bash
alembic revision --autogenerate -m "Add Article model"
```
Затем примените миграцию к базе данных:
```bash
docker compose exec backend alembic upgrade head
```

---

### Шаг 3. Создание Pydantic схем (DTO)
Создайте файл [backend/app/schemas/article.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/schemas/article.py):

```python
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

# Общие поля для чтения/записи
class ArticleBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)

# Схема для создания статьи
class ArticleCreate(ArticleBase):
    pass

# Схема для обновления статьи
class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)

# Схема для возврата одной статьи через API
class ArticlePublic(ArticleBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Схема для возврата списка статей (пагинация)
class ArticlesPublic(BaseModel):
    data: list[ArticlePublic]
    count: int
```

Зарегистрируйте новые схемы в [backend/app/schemas/\_\_init\_\_.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/schemas/__init__.py):

```python
from .article import (
    ArticleBase,
    ArticleCreate,
    ArticleUpdate,
    ArticlePublic,
    ArticlesPublic,
)

__all__ = [
    # ... существующие схемы ...
    "ArticleBase",
    "ArticleCreate",
    "ArticleUpdate",
    "ArticlePublic",
    "ArticlesPublic",
]
```

---

### Шаг 4. Создание репозитория (Repository)
Создайте файл [backend/app/repositories/article.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/repositories/article.py):

```python
import uuid
from sqlmodel import Session, select, col, func
from app.models.article import Article
from app.schemas.article import ArticleCreate, ArticleUpdate

def get_article_by_id(*, session: Session, article_id: uuid.UUID) -> Article | None:
    return session.get(Article, article_id)

def get_articles_paginated(*, session: Session, skip: int = 0, limit: int = 100) -> list[Article]:
    statement = (
        select(Article).order_by(col(Article.created_at).desc()).offset(skip).limit(limit)
    )
    return list(session.exec(statement).all())

def count_articles(*, session: Session) -> int:
    count_statement = select(func.count()).select_from(Article)
    return session.exec(count_statement).one()

def get_articles_by_owner_paginated(
    *, session: Session, owner_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[Article]:
    statement = (
        select(Article)
        .where(Article.owner_id == owner_id)
        .order_by(col(Article.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    return list(session.exec(statement).all())

def count_articles_by_owner(*, session: Session, owner_id: uuid.UUID) -> int:
    count_statement = (
        select(func.count())
        .select_from(Article)
        .where(Article.owner_id == owner_id)
    )
    return session.exec(count_statement).one()

def create_article(*, session: Session, article_in: ArticleCreate, owner_id: uuid.UUID) -> Article:
    db_article = Article.model_validate(article_in, update={"owner_id": owner_id})
    session.add(db_article)
    session.commit()
    session.refresh(db_article)
    return db_article

def update_article(*, session: Session, db_article: Article, article_in: ArticleUpdate) -> Article:
    update_dict = article_in.model_dump(exclude_unset=True)
    db_article.sqlmodel_update(update_dict)
    session.add(db_article)
    session.commit()
    session.refresh(db_article)
    return db_article

def delete_article(*, session: Session, db_article: Article) -> None:
    session.delete(db_article)
    session.commit()
```

Зарегистрируйте репозиторий в [backend/app/repositories/\_\_init\_\_.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/repositories/__init__.py):

```python
from . import user as user_repo
from . import item as item_repo
from . import article as article_repo  # Добавлено

__all__ = ["user_repo", "item_repo", "article_repo"]
```

---

### Шаг 5. Создание сервиса (Service)
Создайте файл [backend/app/services/article.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/services/article.py):

```python
import uuid
from fastapi import HTTPException
from sqlmodel import Session
from app.models import Article, User
from app.schemas import ArticleCreate, ArticleUpdate
from app.repositories import article_repo

def get_article_service(*, session: Session, current_user: User, article_id: uuid.UUID) -> Article:
    article = article_repo.get_article_by_id(session=session, article_id=article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    # Ограничиваем доступ: только автор статьи или суперпользователь
    if not current_user.is_superuser and (article.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return article

def create_article_service(*, session: Session, article_in: ArticleCreate, owner_id: uuid.UUID) -> Article:
    return article_repo.create_article(session=session, article_in=article_in, owner_id=owner_id)

def update_article_service(
    *, session: Session, current_user: User, article_id: uuid.UUID, article_in: ArticleUpdate
) -> Article:
    article = get_article_service(session=session, current_user=current_user, article_id=article_id)
    return article_repo.update_article(session=session, db_article=article, article_in=article_in)

def delete_article_service(*, session: Session, current_user: User, article_id: uuid.UUID) -> None:
    article = get_article_service(session=session, current_user=current_user, article_id=article_id)
    article_repo.delete_article(session=session, db_article=article)
```

Зарегистрируйте сервисы в [backend/app/services/\_\_init\_\_.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/services/__init__.py):

```python
# ... существующие импорты ...
from .article import (
    get_article_service,
    create_article_service,
    update_article_service,
    delete_article_service,
)

__all__ = [
    # ... существующие экспорты ...
    "get_article_service",
    "create_article_service",
    "update_article_service",
    "delete_article_service",
]
```

---

### Шаг 6. Создание эндпоинтов (Routes)
Создайте файл [backend/app/api/routes/articles.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/api/routes/articles.py):

```python
import uuid
from typing import Any
from fastapi import APIRouter
from app.api.deps import CurrentUser, SessionDep
from app.schemas import ArticleCreate, ArticlePublic, ArticlesPublic, ArticleUpdate, Message
from app.repositories import article_repo
from app.services import (
    get_article_service,
    create_article_service,
    update_article_service,
    delete_article_service,
)

router = APIRouter(prefix="/articles", tags=["articles"])

@router.get("/", response_model=ArticlesPublic)
def read_articles(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Получить список статей.
    """
    if current_user.is_superuser:
        count = article_repo.count_articles(session=session)
        articles = article_repo.get_articles_paginated(session=session, skip=skip, limit=limit)
    else:
        count = article_repo.count_articles_by_owner(session=session, owner_id=current_user.id)
        articles = article_repo.get_articles_by_owner_paginated(
            session=session, owner_id=current_user.id, skip=skip, limit=limit
        )

    articles_public = [ArticlePublic.model_validate(art) for art in articles]
    return ArticlesPublic(data=articles_public, count=count)

@router.get("/{id}", response_model=ArticlePublic)
def read_article(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Получить статью по ID.
    """
    return get_article_service(session=session, current_user=current_user, article_id=id)

@router.post("/", response_model=ArticlePublic)
def create_article(
    *, session: SessionDep, current_user: CurrentUser, article_in: ArticleCreate
) -> Any:
    """
    Создать новую статью.
    """
    return create_article_service(session=session, article_in=article_in, owner_id=current_user.id)

@router.put("/{id}", response_model=ArticlePublic)
def update_article(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    article_in: ArticleUpdate,
) -> Any:
    """
    Обновить статью по ID.
    """
    return update_article_service(
        session=session, current_user=current_user, article_id=id, article_in=article_in
    )

@router.delete("/{id}")
def delete_article(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Удалить статью по ID.
    """
    delete_article_service(session=session, current_user=current_user, article_id=id)
    return Message(message="Article deleted successfully")
```

---

### Шаг 7. Регистрация роутера в основном API
Откройте файл [backend/app/api/main.py](file:///c:/Users/rubts/PycharmProjects/fastapi-template/backend/app/api/main.py) и добавьте новый роутер:

```python
from fastapi import APIRouter
from app.api.routes import items, login, private, users, utils, articles  # Добавлен articles
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(articles.router)  # Добавлено

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
```

Теперь ваши эндпоинты будут доступны по путям `/api/v1/articles/` и будут видны в документации Swagger по адресу `http://localhost:8000/docs` (или `http://localhost/docs` при проксировании через Traefik).
