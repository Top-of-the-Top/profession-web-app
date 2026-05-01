# Загрузка файлов и изображений — план для фронтенда

## Обзор архитектуры

Загрузка файлов происходит **в три шага**. Django не принимает бинарные данные напрямую — файл уходит прямо в Yandex Object Storage (S3) через presigned URL. Django только управляет метаинформацией.

```
Фронт  →  Django API  →  Фронт  →  S3 напрямую  →  Фронт  →  Django API
  1. initiate              2. upload                    3. commit
```

---

## Шаг 1 — Инициировать загрузку

**Endpoint:** `POST /api/uploads/initiate`  
**Auth:** Bearer token обязателен

### Тело запроса

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `intent` | string | ✅ | Тип загрузки (см. таблицу ниже) |
| `filename` | string | ✅ | Оригинальное имя файла |
| `mime_type` | string | ✅ | MIME-тип файла |
| `size` | integer | ✅ | Размер в байтах |
| `sha256` | string | ❌ | HEX-хэш файла (64 символа). Если передан и файл уже есть — сервер вернёт `dedup: true` |

### Допустимые значения `intent`

| intent | Назначение | Макс. размер | Допустимые MIME |
|--------|-----------|-------------|-----------------|
| `homework_attachment` | Прикрепление к ответу на задание | 10 MB | pdf, zip, png, jpeg, txt |
| `homework_material` | Материал к домашке от автора | 10 MB | pdf, zip, png, jpeg, txt, docx, xlsx, pptx, mp3, mp4 |
| `lesson_image` | Изображение внутри урока | 10 MB | png, jpeg, webp, gif, svg |
| `lesson_file` | Файл внутри урока | 100 MB | pdf, zip, docx, xlsx, pptx, txt |
| `course_cover` | Обложка курса | 10 MB | png, jpeg, webp |
| `user_avatar` | Аватар пользователя | 10 MB | png, jpeg |
| `webinar_whiteboard` | PDF-доска вебинара | 50 MB | pdf |

### Ответ — новый файл (201 Created)

```json
{
  "asset_id": "550e8400-e29b-41d4-a716-446655440000",
  "dedup": false,
  "storage_backend": "s3",
  "upload": {
    "method": "POST",
    "url": "https://storage.yandexcloud.net/bucket-name",
    "fields": {
      "key": "assets/u/42/202501/abc123def456",
      "Content-Type": "image/jpeg",
      "policy": "eyJleHBpcmF0aW9uIjoiMjAyNS0...",
      "x-amz-algorithm": "AWS4-HMAC-SHA256",
      "x-amz-credential": "...",
      "x-amz-date": "...",
      "x-amz-signature": "..."
    },
    "expires_at": "2026-05-01T12:05:00Z"
  }
}
```

### Ответ — файл уже существует (200 OK, дедупликация)

```json
{
  "asset_id": "уже-существующий-uuid",
  "dedup": true,
  "storage_backend": "s3",
  "upload": null
}
```

> Если `dedup: true` — файл уже загружен ранее. Переходи сразу к шагу 3 (commit) или используй `asset_id` напрямую, если файл уже `ready`.

---

## Шаг 2 — Загрузить файл в S3

**Запрос уходит напрямую в S3, НЕ на наш сервер.**

```javascript
const { upload, asset_id } = response; // из шага 1

if (!upload) {
  // dedup=true, файл уже готов — пропускаем загрузку
  return asset_id;
}

const formData = new FormData();

// Все поля из upload.fields добавляем ПЕРВЫМИ
for (const [key, value] of Object.entries(upload.fields)) {
  formData.append(key, value);
}

// Файл добавляем ПОСЛЕДНИМ — требование S3
formData.append('file', fileBlob);

await fetch(upload.url, {
  method: 'POST',   // всегда POST для presigned POST
  body: formData,
  // НЕ устанавливать Content-Type вручную — браузер сам ставит boundary
});

// S3 вернёт 204 No Content при успехе
```

> ⚠️ Файл в `FormData` должен идти **последним** полем — это требование AWS S3 Presigned POST.

---

## Шаг 3 — Подтвердить загрузку (commit)

**Endpoint:** `POST /api/uploads/{asset_id}/commit`  
**Auth:** Bearer token обязателен  
**Body:** пустое

Сервер проверяет что файл реально появился в S3, считает SHA-256, обновляет статус на `ready`.

### Ответ (200 OK)

```json
{
  "asset_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready",
  "storage_backend": "s3",
  "visibility": "public",
  "mime_type": "image/jpeg",
  "size_bytes": 204800,
  "original_filename": "cover.jpg",
  "checksum_sha256": "a1b2c3d4...",
  "created_at": "2026-05-01T12:00:00Z",
  "committed_at": "2026-05-01T12:00:05Z"
}
```

После получения `status: "ready"` — `asset_id` можно передавать в domain-специфичные endpoint'ы.

---

## Шаг 4 — Привязать ассет к объекту

После commit `asset_id` нужно отправить в соответствующий endpoint чтобы привязать файл к сущности.

### Обложка курса

```http
PUT /api/courses/{slug}/cover/
Content-Type: application/json

{ "asset_id": "550e8400-..." }
```

### Аватар пользователя

```http
PUT /api/users/profile/avatar/
Content-Type: application/json

{ "asset_id": "550e8400-..." }
```

### Файлы при сабмите домашки

`asset_id` передаётся внутри items при submit-е попытки:

```http
POST /api/homeworks/{homework_slug}/attempt/submit
Content-Type: application/json

{
  "homework_id": "...",
  "attempt_id": "...",
  "send_at": "2026-05-01T12:00:00Z",
  "items": [
    {
      "type": "task",
      "id": "task-uuid",
      "number": 1,
      "user_answer": "Мой ответ",
      "asset_ids": ["550e8400-...", "другой-uuid"]
    }
  ]
}
```

---

## Проверка статуса (опционально)

Если нужно опросить статус ассета без commit:

```http
GET /api/uploads/{asset_id}/status
```

Возвращает тот же формат что и commit. Полезно при polling если commit делается асинхронно.

---

## Полный пример — загрузка обложки курса

```javascript
async function uploadCourseCover(courseSlug, file) {
  // 1. Инициировать
  const initRes = await fetch('/api/uploads/initiate', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      intent: 'course_cover',
      filename: file.name,
      mime_type: file.type,
      size: file.size,
    }),
  });
  const { asset_id, dedup, upload } = await initRes.json();

  // 2. Загрузить в S3 (пропускаем если дедупликация)
  if (!dedup) {
    const formData = new FormData();
    for (const [key, value] of Object.entries(upload.fields)) {
      formData.append(key, value);
    }
    formData.append('file', file);

    const s3Res = await fetch(upload.url, { method: 'POST', body: formData });
    if (!s3Res.ok) throw new Error('S3 upload failed');
  }

  // 3. Подтвердить
  await fetch(`/api/uploads/${asset_id}/commit`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
  });

  // 4. Привязать к курсу
  await fetch(`/api/courses/${courseSlug}/cover/`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ asset_id }),
  });
}
```

---

## Ошибки

Все ошибки возвращаются в формате:

```json
{
  "status": "error",
  "code": "ASSET_POLICY_VIOLATION",
  "message": "Файл не соответствует политике загрузки.",
  "details": { "size": 15000000, "max_size": 10485760 }
}
```

| HTTP | Код | Причина |
|------|-----|---------|
| 400 | `ASSET_INTENT_NOT_ALLOWED` | Неверный `intent` |
| 400 | `ASSET_POLICY_VIOLATION` | Превышен размер или недопустимый MIME |
| 400 | `ASSET_COMMIT_MISMATCH` | Файл в S3 не совпадает с заявленным |
| 401 | — | Не авторизован |
| 403 | `ASSET_PERMISSION_DENIED` | Не владелец ассета |
| 404 | `ASSET_NOT_FOUND` | Ассет не найден |
| 409 | `ASSET_STATUS_INVALID` | Попытка commit уже удалённого ассета |
| 503 | `ASSET_STORAGE_UNAVAILABLE` | S3 недоступен |
