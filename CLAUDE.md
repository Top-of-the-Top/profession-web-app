# profession-web-app

Образовательная платформа — покупка курсов, просмотр уроков, сдача домашних заданий, вебинары.

## Стек

- **Frontend:** React 19 + TypeScript (strict) + Vite 7 + Zustand 5 + CSS Modules + TanStack Query 5
- **Backend:** Django + DRF + SimpleJWT, API под `/api/`
- **UI-примитивы:** Radix UI (shadcn-подобные), lucide-react, sileo-тосты
- **Валидация:** Zod 4
- **Deploy:** Docker Compose (frontend, backend, redis, rabbitmq, celery, flower)

## Структура frontend (`frontend/src/`)

```
app/          → App.tsx, точка входа
router/       → routes.tsx, ProtectedRoute, PublicRoute, RoleGuard
pages/        → страницы по FSD (pageName/ui/*.tsx + *.module.css)
widgets/      → AppLayout (shell + sidebar + Outlet)
features/     → course-builder, notification, ai-chat
entities/     → user/model/userStore, cart/model/cartSummaryStore
components/   → переиспользуемые UI-виджеты (OtpInput и др.)
shared/
  api/        → interceptor.ts (ApiClient), queries/, mutations/, *Api.ts
  ui/         → Button, Card, Dialog, Spinner, PageFrame, Skeleton, Modal…
  lib/        → cn(), parseApiError, backendApiMessages, notify, rbac/
  events/     → authEvents (EventTarget)
  utils/      → encryption (мёртвый код), validation
schemas/      → Zod-схемы для auth
```

## Алиасы

`@app/*`, `@components/*`, `@entities/*`, `@pages/*`, `@router/*`, `@schemas/*`, `@shared/*`, `@widgets/*`, `@assets/*`

**`@features` не настроен** — фичи через относительные пути.

## Ключевые паттерны

### Загрузка данных

Только через TanStack Query хуки. Никаких `useEffect + useState` для server state.

```tsx
const { data, isLoading, error } = useCourseBySlug(slug);
```

### Мутации

```tsx
const addToCart = useAddToCart();
addToCart.mutate(slug, { onSuccess: () => notify..., onError: (err) => { parseApiError... } });
// addToCart.isPending — для disabled-состояния кнопки
```

### API-клиент

Singleton `apiClient` — единственная точка HTTP-запросов. Транспорт: нативный `fetch`. Автоматический Bearer из localStorage. 401 → refresh → retry → logout.

Ошибки выбрасываются как `new Error('API_ERROR_{status}: {body}')` или `'AUTH_EXPIRED'`.

### Обработка ошибок (стандартный паттерн)

```tsx
const parsed = parseApiError(err);
if (parsed) {
  const m = messageForApiFailure('sceneName', parsed.status, parsed.body);
  notifyError({ title: m.title, description: m.description });
  return;
}
notifyError({ title: 'Ошибка', description: 'Повторите попытку.' });
```

Для auth-ошибок сначала проверить: `msg === 'AUTH_EXPIRED' || msg.includes('API_ERROR_401')`.

### Тосты

```ts
import { notifySuccess, notifyError, notifyWarning, notifyInfo } from '@shared/lib/sileo/notify';
```

### Стилизация

CSS Modules + дизайн-токены из `globals.css`. `cn()` для объединения классов. Tailwind **не используется**. Шрифт: **Golos Text**.

### RBAC

Роли: `student`, `teacher`, `moderator` (из JWT).

```tsx
const { role, is, hasAny } = useRole();
<Can role="teacher">...</Can>
<Can role={['teacher', 'moderator']}>...</Can>
```

`<RoleGuard allowed={['moderator']}>` оборачивает маршруты автоматически через `routes.tsx`.

### Zustand-сторы

| Стор | Назначение |
|------|------------|
| `useUserStore` | Профиль, auth-состояние, role, userId |
| `useCartSummaryStore` | Флаг наличия товаров (не использовать — использовать `useCart()`) |
| `useCourseBuilderStore` | UI-состояние билдера |
| `useHomeworkStore` | Домашние задания |
| `useNotificationStore` | Уведомления |

### Auth-поток

1. Login → `useUserStore.login({ tokens, role })` → `fetchUser()` → role/userId из JWT
2. Проверка: `ProtectedRoute` → `fetchUser()` при наличии токена
3. Refresh: автоматически в `ApiClient` при 401
4. Logout: `interceptor.logout()` → `authEvents('logout')` → очистка сторов + QueryClient

Токены хранятся в `localStorage`: `access_token`, `refresh_token`, `*_expires_at`.

## Создание новой страницы

1. `pages/{name}/ui/{Name}Page.tsx` + `{Name}Page.module.css`
2. Экспорт из `pages/index.ts`
3. Маршрут в `router/routes.tsx`
4. Query-хуки из `shared/api/queries/` (или создать новый)

## Бэкенд-эндпоинты

- `/api/auth/register/`, `/api/auth/login/`, `/api/auth/token/refresh/`
- `/api/app/profile/` (GET, PATCH)
- `/api/app/store/`, `/api/app/courses/{slug}/`, `/api/app/my-courses/`
- `/api/landing/courses/`
- `/api/carts/`, `/api/carts/add/{slug}/`, `/api/carts/remove/{slug}/`
- `/api/courses/{slug}/lessons/`, `.../lessons/{slug}/`

## Запреты

- Не использовать `useEffect` для загрузки данных — только `useQuery`
- Не создавать `useState` для loading/error/data — это даёт `useQuery`
- Не использовать `axios` — только `apiClient`
- Не использовать `cartSummaryStore` — корзина через `useCart()`
- Не хардкодить API URL — через `apiClient`
- Не импортировать из внутренностей `shared/ui/Button/Button.tsx` — только через barrel
- Не запускать `npm run build` без явного запроса
- Не редактировать `backend/**` без явного запроса
- Не добавлять комментарии в код без явного запроса
- Tailwind **не настроен** — не использовать

## Известные проблемы (из аудита)

**CRITICAL:**
- `dangerouslySetInnerHTML` без DOMPurify в 3 местах (XSS)
- Race condition в refresh-токене при параллельных 401
- `RoleGuard` пускает при `role === null` (показывает контент до загрузки роли)
- Токены в localStorage (уязвимо при XSS)
- `frontend/.env` не в `.gitignore`

**HIGH:**
- `react-hooks/exhaustive-deps` выключен в ESLint
- `React.StrictMode` отсутствует
- Тестов нет (0 файлов)
- Нет security-заголовков в Nginx (CSP, X-Frame-Options и др.)
- `encryption.ts` — мёртвый код, не импортируется нигде
- `shared` импортирует из `pages` (нарушение FSD)
- Нет `manualChunks` в Vite (тяжёлые зависимости в одном чанке)

**MEDIUM:**
- Дубль источника данных корзины: `useCart` + `cartSummaryStore`
- `tokens.css` (~21 KB) не подключён нигде — мёртвый файл
- `Button` без `type="button"` по умолчанию
- `Spinner` без `role="status"`
