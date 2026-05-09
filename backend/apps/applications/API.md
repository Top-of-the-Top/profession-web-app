# Applications API

## Общее

- **Base URL:** `/api/v1/`
- **Аутентификация:** Bearer JWT во всех запросах
- **Формат ошибок:**
  ```json
  { "detail": "Описание ошибки" }
  ```

---

## Сводная таблица

| Метод | URL | Права | Описание |
|---|---|---|---|
| `POST` | `/api/v1/courses/{slug}/applications/apply/` | Студент | Подать заявку |
| `DELETE` | `/api/v1/courses/{slug}/applications/my/` | Студент | Отозвать свою заявку |
| `GET` | `/api/v1/courses/{slug}/applications/` | Автор / модератор | Список заявок |
| `POST` | `/api/v1/courses/{slug}/applications/{id}/approve/` | Автор / модератор | Одобрить |
| `POST` | `/api/v1/courses/{slug}/applications/{id}/reject/` | Автор / модератор | Отклонить |

---

## 1. Подать заявку

### `POST /api/v1/courses/{course_slug}/applications/apply/`

Студент подаёт заявку на специальный курс.

**Права:** `IsAuthenticated`

**Path params:**

| Параметр | Тип | Описание |
|---|---|---|
| `course_slug` | `string` | Slug курса |

**Request body:** не требуется

**Response `201 Created`:** пустое тело

**Ошибки:**

| Код | `detail` | Условие |
|---|---|---|
| `401` | `"Требуется авторизация"` | Не передан или невалидный JWT |
| `404` | `"Курс не найден"` | Курс с таким slug не существует или удалён |
| `400` | `"На этот курс нельзя подать заявку"` | Курс не является специальным (`is_special=False`) |
| `400` | `"Вы уже записаны на этот курс"` | У студента уже есть активный `CourseEnrollment` |
| `409` | `"Заявка уже подана"` | `CourseApplication` от этого студента уже существует |

---

## 2. Отозвать заявку

### `DELETE /api/v1/courses/{course_slug}/applications/my/`

Студент отзывает свою заявку, пока она в статусе `pending`. Запись удаляется из БД — студент может подать заявку повторно.

**Права:** `IsAuthenticated`

**Path params:**

| Параметр | Тип | Описание |
|---|---|---|
| `course_slug` | `string` | Slug курса |

**Request body:** не требуется

**Response `204 No Content`:** пустое тело

> Фронт не получает `application_id` при подаче — отзыв привязан к текущему пользователю и курсу, id не нужен.

**Ошибки:**

| Код | `detail` | Условие |
|---|---|---|
| `401` | `"Требуется авторизация"` | Не передан или невалидный JWT |
| `404` | `"Заявка не найдена"` | Заявка от этого студента на этот курс не существует |
| `409` | `"Нельзя отозвать рассмотренную заявку"` | Статус заявки `approved` или `rejected` |

---

## 3. Список заявок

### `GET /api/v1/courses/{course_slug}/applications/?status=pending`

Возвращает все заявки на курс. Опциональная фильтрация по статусу.

**Права:** автор курса или модератор

**Path params:**

| Параметр | Тип | Описание |
|---|---|---|
| `course_slug` | `string` | Slug курса |

**Query params:**

| Параметр | Тип | Обязательный | Описание |
|---|---|---|---|
| `status` | `pending \| approved \| rejected` | Нет | Фильтр по статусу. По умолчанию — все |

**Response `200 OK`:**

```json
[
  {
    "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "pending",
    "created_at": "2026-05-10T12:00:00Z",
    "updated_at": "2026-05-10T12:00:00Z",
    "reviewed_at": null,
    "reviewed_by": null,
    "user": {
      "id": 1,
      "first_name": "Иван",
      "last_name": "Иванов",
      "email": "ivan@example.com"
    }
  },
  {
    "application_id": "7cb12a31-1234-4abc-b3fc-9d8e2f11bc42",
    "status": "approved",
    "created_at": "2026-05-09T10:30:00Z",
    "updated_at": "2026-05-09T11:00:00Z",
    "reviewed_at": "2026-05-09T11:00:00Z",
    "reviewed_by": 42,
    "user": {
      "id": 2,
      "first_name": "Мария",
      "last_name": "Петрова",
      "email": "maria@example.com"
    }
  }
]
```

**Поля объекта заявки:**

| Поле | Тип | Описание |
|---|---|---|
| `application_id` | `uuid` | Уникальный идентификатор заявки |
| `status` | `pending \| approved \| rejected` | Текущий статус |
| `created_at` | `datetime (ISO 8601)` | Дата подачи заявки |
| `updated_at` | `datetime (ISO 8601)` | Дата последнего изменения |
| `reviewed_at` | `datetime (ISO 8601) \| null` | Дата рассмотрения |
| `reviewed_by` | `integer \| null` | ID пользователя, который рассмотрел заявку |
| `user.id` | `integer` | ID студента |
| `user.first_name` | `string` | Имя студента |
| `user.last_name` | `string` | Фамилия студента |
| `user.email` | `string` | Email студента |

**Ошибки:**

| Код | `detail` | Условие |
|---|---|---|
| `401` | `"Требуется авторизация"` | Не передан или невалидный JWT |
| `403` | `"Доступ запрещён"` | Пользователь не автор курса и не модератор |
| `404` | `"Курс не найден"` | Курс с таким slug не существует |

---

## 4. Одобрить заявку

### `POST /api/v1/courses/{course_slug}/applications/{application_id}/approve/`

> `application_id` берётся из списка заявок (эндпоинт 3).

Одобряет заявку студента. Автоматически создаёт `CourseEnrollment` с `source=application` и `access_expires_at = now + 1 год`.

**Права:** автор курса или модератор

**Path params:**

| Параметр | Тип | Описание |
|---|---|---|
| `course_slug` | `string` | Slug курса |
| `application_id` | `uuid` | ID заявки |

**Request body:** не требуется

**Response `200 OK`:**

```json
{
  "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "approved",
  "reviewed_at": "2026-05-10T12:05:00Z",
  "reviewed_by": 42
}
```

**Поля ответа:**

| Поле | Тип | Описание |
|---|---|---|
| `application_id` | `uuid` | ID заявки |
| `status` | `"approved"` | Новый статус |
| `reviewed_at` | `datetime (ISO 8601)` | Момент одобрения |
| `reviewed_by` | `integer` | ID пользователя, одобрившего заявку |

**Ошибки:**

| Код | `detail` | Условие |
|---|---|---|
| `401` | `"Требуется авторизация"` | Не передан или невалидный JWT |
| `403` | `"Доступ запрещён"` | Пользователь не автор курса и не модератор |
| `404` | `"Курс не найден"` | Курс с таким slug не существует |
| `404` | `"Заявка не найдена"` | Заявка с таким ID не найдена на этом курсе |
| `409` | `"Заявка уже рассмотрена"` | Статус заявки уже `approved` или `rejected` |

---

## 5. Отклонить заявку

### `POST /api/v1/courses/{course_slug}/applications/{application_id}/reject/`

> `application_id` берётся из списка заявок (эндпоинт 3).

Отклоняет заявку студента. `CourseEnrollment` не создаётся. Студент получает in-app уведомление.

**Права:** автор курса или модератор

**Path params:**

| Параметр | Тип | Описание |
|---|---|---|
| `course_slug` | `string` | Slug курса |
| `application_id` | `uuid` | ID заявки |

**Request body:** не требуется

**Response `200 OK`:**

```json
{
  "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "rejected",
  "reviewed_at": "2026-05-10T12:05:00Z",
  "reviewed_by": 42
}
```

**Поля ответа:**

| Поле | Тип | Описание |
|---|---|---|
| `application_id` | `uuid` | ID заявки |
| `status` | `"rejected"` | Новый статус |
| `reviewed_at` | `datetime (ISO 8601)` | Момент отклонения |
| `reviewed_by` | `integer` | ID пользователя, отклонившего заявку |

**Ошибки:**

| Код | `detail` | Условие |
|---|---|---|
| `401` | `"Требуется авторизация"` | Не передан или невалидный JWT |
| `403` | `"Доступ запрещён"` | Пользователь не автор курса и не модератор |
| `404` | `"Курс не найден"` | Курс с таким slug не существует |
| `404` | `"Заявка не найдена"` | Заявка с таким ID не найдена на этом курсе |
| `409` | `"Заявка уже рассмотрена"` | Статус заявки уже `approved` или `rejected` |

---

## Изменения в существующих эндпоинтах

### `GET /api/v1/courses/{slug}/`

Добавляется поле `is_special` в ответ:

```json
{
  "course_id": "uuid",
  "title": "Название курса",
  "is_special": true,
  ...
}
```

Если `is_special=True` и пользователь не авторизован — возвращается `404`.

### `GET /api/v1/courses/` и `GET /api/v1/landing/courses/`

Специальные курсы (`is_special=True`) **не включаются** в ответ для студентов и анонимных пользователей. Модератор и автор курса видят все курсы.
