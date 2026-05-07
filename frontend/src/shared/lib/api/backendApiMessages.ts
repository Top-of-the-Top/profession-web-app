/**
 * Сообщения для тостов: только явные соответствия телам ответов из репозитория backend/
 * (users/api/views.py, users/api/serializers.py, carts/api/views.py, courses/api/views.py,
 * payments/api/views.py). Без эвристик и «похожих» строк: совпадение по структуре/точным строкам.
 *
 * Если ответ не входит в каталог (например, неожиданный 500), используется fallback сцены.
 */

export type UserFacingMessage = { title: string; description: string };

export type ApiFailureScene =
  | 'register'
  | 'registerVerify'
  | 'login'
  | 'resetRequest'
  | 'recoverPhone'
  | 'recoverEmail'
  | 'recoverSet'
  | 'profileUpdate'
  | 'profileVerifyEmail'
  | 'profileVerifyPhone'
  | 'cartLoad'
  | 'cartAdd'
  | 'cartRemove'
  | 'cartPay'
  | 'courseDetail'
  | 'webinarStart'
  | 'webinarJoin'
  | 'webinarRecording'
  | 'webinarRecordingStop'
  | 'recordingPdfUpload'
  | 'recordingPdfDelete'
  | 'recordingDelete'
  | 'webinarStop'
  | 'webinarRecorderJoin'
  | 'mediaUpload';

export const ASSET_ERROR_MESSAGES: Record<string, UserFacingMessage> = {
  ASSET_INTENT_NOT_ALLOWED: {
    title: 'неподходящий сценарий загрузки',
    description: 'Попробуйте другой раздел или тип файла.',
  },
  ASSET_POLICY_VIOLATION: {
    title: 'файл нарушает правила',
    description: 'Проверьте размер и тип файла.',
  },
  ASSET_COMMIT_MISMATCH: {
    title: 'файл не загружен',
    description: 'Повторите загрузку — данные в хранилище не совпали.',
  },
  ASSET_PERMISSION_DENIED: {
    title: 'нет доступа',
    description: 'Вы не можете загрузить или привязать этот файл.',
  },
  ASSET_NOT_FOUND: {
    title: 'файл не найден',
    description: 'Загрузите файл заново.',
  },
  ASSET_STATUS_INVALID: {
    title: 'статус файла не годится',
    description: 'Файл ещё не готов. Дождитесь окончания загрузки.',
  },
  ASSET_BIND_CONFLICT: {
    title: 'конфликт привязки',
    description: 'Один и тот же файл уже привязан или достигнут лимит.',
  },
  ASSET_ALREADY_COMMITTED: {
    title: 'файл уже принят',
    description: 'Файл уже подтверждён сервером.',
  },
  ASSET_STORAGE_UNAVAILABLE: {
    title: 'хранилище недоступно',
    description: 'Попробуйте загрузить файл позже.',
  },
};

export function messageForAssetCode(code: string): UserFacingMessage | null {
  return ASSET_ERROR_MESSAGES[code] ?? null;
}

export function messageFromAssetError(body: unknown): UserFacingMessage | null {
  if (!isRecord(body)) return null;
  if (body.status !== 'error') return null;
  const code = typeof body.code === 'string' ? body.code : null;
  if (!code) return null;
  const direct = messageForAssetCode(code);
  if (direct) return direct;
  const message = typeof body.message === 'string' ? body.message : null;
  if (message) {
    return { title: 'ошибка загрузки', description: message };
  }
  return null;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

/** Точное совпадение массива строк (как в JSON serializer.errors). */
function strArrayEq(a: unknown, expected: readonly string[]): boolean {
  return (
    Array.isArray(a) &&
    a.length === expected.length &&
    a.every((x, i) => typeof x === 'string' && x === expected[i])
  );
}

function detailString(body: unknown): string | null {
  if (!isRecord(body)) return null;
  const d = body.detail;
  return typeof d === 'string' ? d : null;
}

/**
 * Ответы аутентификации DRF / SimpleJWT (не из наших views, но реально приходят на 401).
 * Только поле detail; лишние ключи (code и т.д.) не мешают.
 */
const JWT_OR_DRF_AUTH_DETAIL: Record<string, UserFacingMessage> = {
  'Authentication credentials were not provided.': {
    title: 'нужна авторизация',
    description: 'Войдите в аккаунт.',
  },
  'Given token not valid for any token type': {
    title: 'сессия недействительна',
    description: 'Войдите снова или обновите страницу.',
  },
  'Token is invalid or expired': {
    title: 'сессия истекла',
    description: 'Войдите снова.',
  },
  'Token is blacklisted': {
    title: 'сессия недействительна',
    description: 'Войдите снова.',
  },
};

function messageFromAuthDetail(body: unknown): UserFacingMessage | null {
  const d = detailString(body);
  if (d == null) return null;
  return JWT_OR_DRF_AUTH_DETAIL[d] ?? null;
}

// --- Register: RegisterView 403 + RegisterSerializer + встроенные проверки DRF CharField (min_length=8) ---

const REGISTER_PASSWORD_MIN_LENGTH_DRF = [
  'Ensure this field has at least 8 characters.',
] as const;

const REGISTER_FIELD_REQUIRED = ['This field is required.'] as const;

function collectRegister403(body: unknown): UserFacingMessage | null {
  if (!isRecord(body)) return null;
  const parts: UserFacingMessage[] = [];

  const add = (ok: boolean, msg: UserFacingMessage) => {
    if (ok) parts.push(msg);
  };

  add(strArrayEq(body.non_field_errors, ['Необходимо указать email или phone_number']), {
    title: 'нет контакта',
    description: 'Укажите email или номер телефона.',
  });

  add(strArrayEq(body.email, ['Пользователь с таким email уже существует']), {
    title: 'email занят',
    description: 'Пользователь с таким email уже зарегистрирован.',
  });

  add(strArrayEq(body.phone_number, ['Пользователь с таким телефоном уже существует']), {
    title: 'телефон занят',
    description: 'Пользователь с таким номером уже зарегистрирован.',
  });

  add(strArrayEq(body.password, REGISTER_PASSWORD_MIN_LENGTH_DRF), {
    title: 'короткий пароль',
    description: 'Пароль должен быть не короче 8 символов.',
  });

  add(strArrayEq(body.password, REGISTER_FIELD_REQUIRED), {
    title: 'нет пароля',
    description: 'Введите пароль.',
  });

  if (parts.length === 0) return null;
  if (parts.length === 1) return parts[0];
  return {
    title: 'не удалось создать аккаунт',
    description: parts.map((p) => p.description).join('\n'),
  };
}

// --- Login: LoginView 400 + LoginSerializer ---

function collectLogin400(body: unknown): UserFacingMessage | null {
  if (!isRecord(body)) return null;
  const parts: UserFacingMessage[] = [];
  const add = (ok: boolean, msg: UserFacingMessage) => {
    if (ok) parts.push(msg);
  };

  add(strArrayEq(body.non_field_errors, ['Необходимо указать email или phone_number']), {
    title: 'нет контакта',
    description: 'Укажите email или номер телефона.',
  });
  add(strArrayEq(body.non_field_errors, ['Неверная почта']), {
    title: 'неверная почта',
    description: 'Пользователь с такой почтой не найден.',
  });
  add(strArrayEq(body.non_field_errors, ['Неверный номер телефона']), {
    title: 'неверный телефон',
    description: 'Пользователь с таким номером не найден.',
  });
  add(strArrayEq(body.non_field_errors, ['Неверный пароль']), {
    title: 'неверный пароль',
    description: 'Проверьте пароль и попробуйте снова.',
  });
  add(strArrayEq(body.password, REGISTER_FIELD_REQUIRED), {
    title: 'нет пароля',
    description: 'Введите пароль.',
  });

  if (parts.length === 0) return null;
  if (parts.length === 1) return parts[0];
  return {
    title: 'не вышло войти',
    description: parts.map((p) => p.description).join('\n'),
  };
}

// --- ResetPasswordView ---

const RESET_DETAIL_NO_CONTACT = 'Необходимо указать email или phone_number';
const RESET_DETAIL_USER_NOT_FOUND = 'Пользователь не найден';


const RECOVER_DETAIL_MISSING = 'token и password обязательны';
const RECOVER_DETAIL_BAD_TOKEN = 'Невалидный или истёкший токен';

// --- Profile PATCH: UpdateProfileSerializer 400 ---

function collectProfilePatch400(body: unknown): UserFacingMessage | null {
  if (!isRecord(body)) return null;
  const parts: UserFacingMessage[] = [];
  const add = (ok: boolean, msg: UserFacingMessage) => {
    if (ok) parts.push(msg);
  };

  add(strArrayEq(body.email, ['Пользователь с таким email уже существует']), {
    title: 'email занят',
    description: 'Этот email уже используется другим пользователем.',
  });
  add(strArrayEq(body.phone_number, ['Пользователь с таким телефоном уже существует']), {
    title: 'телефон занят',
    description: 'Этот номер уже используется другим пользователем.',
  });
  add(strArrayEq(body.gender, ['Допустимые значения: Мужской, Женский']), {
    title: 'неверный пол',
    description: 'Выберите «Мужской» или «Женский».',
  });
  add(strArrayEq(body.avatar, ['Размер файла не должен превышать 5 МБ']), {
    title: 'большой файл',
    description: 'Аватар не должен быть больше 5 МБ.',
  });

  if (parts.length === 0) return null;
  if (parts.length === 1) return parts[0];
  return {
    title: 'проверьте данные',
    description: parts.map((p) => p.description).join('\n'),
  };
}

// --- Carts (views.py) ---

const CART_DETAIL_COURSE_NOT_IN_CATALOG =
  'Курс с таким slug не найден в списке курсов.';
const CART_DETAIL_COURSE_NOT_IN_CART = 'Курс с таким slug не найден в корзине.';
const CART_ERROR_ALREADY_IN_CART = 'Курс уже в корзине';

// --- CourseDetail ---

const COURSE_DETAIL_NOT_FOUND = 'Курс не найден';

// --- Payments CartPayView ---

const PAY_ERROR_EMPTY_CART = 'Корзина пуста. Добавьте курсы перед оплатой.';
const PAY_ERROR_ALREADY_PURCHASED = 'Некоторые курсы уже куплены.';

// --- Fallback по сценам (если тело не распознано) ---

const SCENE_FALLBACK: Record<ApiFailureScene, UserFacingMessage> = {
  register: {
    title: 'ошибка регистрации',
    description: 'Повторите попытку.',
  },
  registerVerify: {
    title: 'не удалось подтвердить',
    description: 'Проверьте код или запросите новый.',
  },
  login: {
    title: 'ошибка входа',
    description: 'Повторите попытку или обновите страницу.',
  },
  resetRequest: {
    title: 'ошибка запроса',
    description: 'Не удалось отправить ссылку.',
  },
  recoverPhone: {
    title: 'ошибка проверки кода',
    description: 'Повторите попытку.',
  },
  recoverEmail: {
    title: 'не удалось сменить пароль',
    description: 'Повторите попытку.',
  },
  recoverSet: {
    title: 'не удалось сменить пароль',
    description: 'Повторите попытку.',
  },
  profileUpdate: {
    title: 'не сохранилось',
    description: 'Повторите попытку позже.',
  },
  profileVerifyEmail: {
    title: 'не удалось подтвердить почту',
    description: 'Проверьте код из письма.',
  },
  profileVerifyPhone: {
    title: 'не удалось подтвердить телефон',
    description: 'Проверьте код из SMS.',
  },
  cartLoad: {
    title: 'ошибка загрузки',
    description: 'Корзина временно недоступна.',
  },
  cartAdd: {
    title: 'не удалось добавить',
    description: 'Повторите попытку.',
  },
  cartRemove: {
    title: 'не удалось удалить',
    description: 'Повторите попытку.',
  },
  cartPay: {
    title: 'не удалось оплатить',
    description: 'Повторите попытку.',
  },
  courseDetail: {
    title: 'не удалось загрузить курс',
    description: 'Обновите страницу или откройте курс из каталога.',
  },
  webinarStart: {
    title: 'не удалось запустить вебинар',
    description: 'Повторите попытку.',
  },
  webinarJoin: {
    title: 'не удалось подключиться',
    description: 'Проверьте, что вебинар запущен.',
  },
  webinarRecording: {
    title: 'не удалось начать запись',
    description: 'Повторите попытку.',
  },
  webinarRecordingStop: {
    title: 'не удалось остановить запись',
    description: 'Повторите попытку.',
  },
  recordingPdfUpload: {
    title: 'не удалось сохранить доску',
    description: 'Повторите попытку.',
  },
  recordingPdfDelete: {
    title: 'не удалось удалить PDF',
    description: 'Повторите попытку.',
  },
  recordingDelete: {
    title: 'не удалось удалить запись',
    description: 'Повторите попытку.',
  },
  webinarStop: {
    title: 'не удалось завершить вебинар',
    description: 'Повторите попытку.',
  },
  webinarRecorderJoin: {
    title: 'нет доступа к записи',
    description: 'Проверьте ссылку записи.',
  },
  mediaUpload: {
    title: 'не удалось загрузить файл',
    description: 'Повторите попытку позже.',
  },
};

const SCENE_STATUS_FALLBACK: Partial<
  Record<ApiFailureScene, Partial<Record<number, UserFacingMessage>>>
> = {
  login: {
    400: {
      title: 'не вышло войти',
      description: 'Проверьте почту или телефон и пароль.',
    },
    500: {
      title: 'сервер не отвечает',
      description: 'Повторите попытку позже.',
    },
  },
  register: {
    403: {
      title: 'не удалось создать аккаунт',
      description: 'Проверьте почту, телефон и пароль.',
    },
    429: {
      title: 'слишком часто',
      description: 'Подождите немного и попробуйте снова.',
    },
    500: {
      title: 'сервер не отвечает',
      description: 'Повторите попытку позже.',
    },
  },
  registerVerify: {
    400: {
      title: 'неверный или просроченный код',
      description: 'Запросите код заново на предыдущем шаге.',
    },
    429: {
      title: 'слишком часто',
      description: 'Подождите немного и попробуйте снова.',
    },
  },
  resetRequest: {
    403: {
      title: 'запрос не выполнен',
      description: 'Пользователь не найден или не указаны контакты.',
    },
    429: {
      title: 'слишком часто',
      description: 'Подождите немного и попробуйте снова.',
    },
    500: {
      title: 'письмо не отправлено',
      description: 'Повторите попытку позже.',
    },
  },
  recoverPhone: {
    400: {
      title: 'неверный или просроченный код',
      description: 'Проверьте SMS и попробуйте снова.',
    },
    403: {
      title: 'пользователь не найден',
      description: 'Проверьте номер телефона.',
    },
    429: {
      title: 'слишком часто',
      description: 'Подождите немного и попробуйте снова.',
    },
  },
  recoverEmail: {
    403: {
      title: 'ссылка недействительна',
      description: 'Запросите новую ссылку для восстановления пароля.',
    },
  },
  recoverSet: {
    403: {
      title: 'ссылка недействительна',
      description: 'Запросите новую ссылку для восстановления пароля.',
    },
  },
  profileUpdate: {
    400: {
      title: 'проверьте данные',
      description: 'Исправьте поля по подсказке сервера.',
    },
    401: {
      title: 'сессия устарела',
      description: 'Войдите в аккаунт снова.',
    },
  },
  profileVerifyEmail: {
    400: {
      title: 'неверный или просроченный код',
      description: 'Проверьте письмо и попробуйте снова.',
    },
    401: {
      title: 'сессия устарела',
      description: 'Войдите в аккаунт снова.',
    },
  },
  profileVerifyPhone: {
    400: {
      title: 'неверный или просроченный код',
      description: 'Проверьте SMS и попробуйте снова.',
    },
    401: {
      title: 'сессия устарела',
      description: 'Войдите в аккаунт снова.',
    },
  },
  cartLoad: {
    401: {
      title: 'нужна авторизация',
      description: 'Войдите, чтобы открыть корзину.',
    },
    500: {
      title: 'не удалось загрузить корзину',
      description: 'Попробуйте обновить страницу.',
    },
  },
  cartAdd: {
    400: {
      title: 'корзина',
      description: 'Курс уже в корзине.',
    },
    404: {
      title: 'курс не найден',
      description: 'Такого курса нет в каталоге.',
    },
  },
  cartRemove: {
    401: {
      title: 'сессия устарела',
      description: 'Войдите снова и повторите действие.',
    },
    404: {
      title: 'не удалось удалить',
      description: 'Курс не найден в корзине или в каталоге.',
    },
  },
  cartPay: {
    401: {
      title: 'сессия устарела',
      description: 'Войдите снова и повторите действие.',
    },
  },
  courseDetail: {
    401: {
      title: 'нужен вход',
      description: 'Авторизуйтесь, чтобы открыть страницу курса.',
    },
    404: {
      title: 'курс не найден',
      description: 'Проверьте ссылку или вернитесь в каталог.',
    },
    500: {
      title: 'сервер не отвечает',
      description: 'Попробуйте позже.',
    },
  },
  webinarStart: {
    400: {
      title: 'вебинар уже запущен',
      description: 'Вебинар для этого урока уже идёт.',
    },
    403: {
      title: 'нет доступа',
      description: 'Вы не являетесь автором курса.',
    },
    404: {
      title: 'урок не найден',
      description: 'Проверьте ссылку.',
    },
    502: {
      title: 'ошибка создания доски',
      description: 'Не удалось создать доску. Попробуйте позже.',
    },
  },
  webinarJoin: {
    403: {
      title: 'нет доступа',
      description: 'У вас нет доступа к этому вебинару.',
    },
    404: {
      title: 'вебинар не запущен',
      description: 'Дождитесь, пока преподаватель запустит вебинар.',
    },
  },
  webinarRecording: {
    400: {
      title: 'запись уже идет',
      description: 'Сначала остановите текущую запись.',
    },
    403: {
      title: 'нет доступа',
      description: 'Только автор курса или модератор может управлять записью.',
    },
    404: {
      title: 'вебинар не запущен',
      description: 'Вебинар не найден или уже завершён.',
    },
  },
  webinarRecordingStop: {
    400: {
      title: 'запись не идет',
      description: 'Сейчас нет активной записи для остановки.',
    },
    403: {
      title: 'нет доступа',
      description: 'Только автор курса или модератор может управлять записью.',
    },
    404: {
      title: 'вебинар не запущен',
      description: 'Вебинар не найден или уже завершён.',
    },
  },
  recordingPdfUpload: {
    400: {
      title: 'нет скриншотов',
      description: 'Доска пуста или не удалось снять скриншоты.',
    },
    403: {
      title: 'нет доступа',
      description: 'Только автор курса или модератор может сохранить доску.',
    },
    404: {
      title: 'запись не найдена',
      description: 'Проверьте состояние записи и попробуйте снова.',
    },
  },
  recordingPdfDelete: {
    403: {
      title: 'нет доступа',
      description: 'Только автор курса или модератор может удалить PDF.',
    },
    404: {
      title: 'PDF не найден',
      description: 'PDF уже удален или не был привязан к записи.',
    },
  },
  recordingDelete: {
    403: {
      title: 'нет доступа',
      description: 'Только автор курса или модератор может удалить запись.',
    },
    404: {
      title: 'запись не найдена',
      description: 'Запись уже удалена или не существует.',
    },
  },
  webinarStop: {
    403: {
      title: 'нет доступа',
      description: 'Только автор курса может завершить вебинар.',
    },
    404: {
      title: 'вебинар не найден',
      description: 'Вебинар уже завершён или не был запущен.',
    },
  },
  webinarRecorderJoin: {
    400: {
      title: 'нет токена',
      description: 'Ссылка на запись некорректна.',
    },
    403: {
      title: 'ссылка недействительна',
      description: 'Токен записи невалидный или истёк.',
    },
    404: {
      title: 'вебинар не найден',
      description: 'Проверьте ссылку.',
    },
  },
  mediaUpload: {
    400: {
      title: 'не удалось загрузить файл',
      description: 'Проверьте размер и тип файла.',
    },
    403: {
      title: 'нет доступа',
      description: 'Загрузка для этого сценария запрещена.',
    },
    404: {
      title: 'файл не найден',
      description: 'Попробуйте загрузить файл ещё раз.',
    },
    409: {
      title: 'конфликт состояния',
      description: 'Файл уже принят или находится в неподходящем статусе.',
    },
    503: {
      title: 'хранилище недоступно',
      description: 'Попробуйте загрузить файл позже.',
    },
  },
};

function statusFallback(scene: ApiFailureScene, status: number): UserFacingMessage | null {
  return SCENE_STATUS_FALLBACK[scene]?.[status] ?? null;
}

/**
 * ResetPasswordView: единственный осмысленный 500 — сбой send_mail; текст detail динамический,
 * поэтому для resetRequest+500 показываем фиксированное сообщение без разбора тела.
 */
function isResetRequestMailFailure(status: number, scene: ApiFailureScene): boolean {
  return scene === 'resetRequest' && status === 500;
}

export function resolveApiFailureMessage(
  scene: ApiFailureScene,
  status: number,
  body: unknown,
): UserFacingMessage {
  let mapped: UserFacingMessage | null = null;

  switch (scene) {
    case 'register': {
      if (status === 403) mapped = collectRegister403(body);
      break;
    }
    case 'registerVerify': {
      if (status === 400) {
        mapped = {
          title: 'неверный или просроченный код',
          description: 'Проверьте код из письма или SMS.',
        };
      }
      break;
    }
    case 'login': {
      if (status === 400) mapped = collectLogin400(body);
      break;
    }
    case 'resetRequest': {
      if (status === 403) {
        const d = detailString(body);
        if (d === RESET_DETAIL_NO_CONTACT) {
          mapped = {
            title: 'нет контакта',
            description: 'Укажите email или номер телефона.',
          };
        } else if (d === RESET_DETAIL_USER_NOT_FOUND) {
          mapped = {
            title: 'пользователь не найден',
            description: 'Проверьте email или телефон.',
          };
        }
      }
      if (isResetRequestMailFailure(status, scene)) {
        mapped = {
          title: 'письмо не отправлено',
          description: 'Повторите попытку позже.',
        };
      }
      break;
    }
    case 'recoverPhone': {
      if (status === 400) {
        mapped = {
          title: 'неверный или просроченный код',
          description: 'Проверьте SMS и попробуйте снова.',
        };
      }
      break;
    }
    case 'recoverEmail':
    case 'recoverSet': {
      if (status === 403) {
        const d = detailString(body);
        if (d === RECOVER_DETAIL_MISSING) {
          mapped = {
            title: 'неполные данные',
            description: 'Нужны токен и новый пароль.',
          };
        } else if (d === RECOVER_DETAIL_BAD_TOKEN) {
          mapped = {
            title: 'ссылка недействительна',
            description: 'Запросите новую ссылку для восстановления пароля.',
          };
        }
      }
      break;
    }
    case 'profileVerifyEmail':
    case 'profileVerifyPhone': {
      if (status === 400) {
        mapped = {
          title: 'неверный или просроченный код',
          description:
            scene === 'profileVerifyEmail'
              ? 'Проверьте код из письма.'
              : 'Проверьте код из SMS.',
        };
      } else if (status === 401) {
        mapped = messageFromAuthDetail(body);
      }
      break;
    }
    case 'profileUpdate': {
      if (status === 400) {
        mapped = collectProfilePatch400(body) ?? messageFromAssetError(body);
      } else if (status === 401) {
        mapped = messageFromAuthDetail(body);
      } else if (status === 403 || status === 404 || status === 409 || status === 503) {
        mapped = messageFromAssetError(body);
      }
      break;
    }
    case 'mediaUpload': {
      if (status === 401) mapped = messageFromAuthDetail(body);
      else mapped = messageFromAssetError(body);
      break;
    }
    case 'cartLoad': {
      if (status === 401) mapped = messageFromAuthDetail(body);
      break;
    }
    case 'cartAdd': {
      if (status === 401) mapped = messageFromAuthDetail(body);
      else if (status === 400 && isRecord(body) && body.error === CART_ERROR_ALREADY_IN_CART) {
        mapped = {
          title: 'корзина',
          description: 'Курс уже в корзине.',
        };
      } else if (status === 404 && detailString(body) === CART_DETAIL_COURSE_NOT_IN_CATALOG) {
        mapped = {
          title: 'курс не найден',
          description: 'Такого курса нет в каталоге.',
        };
      }
      break;
    }
    case 'cartRemove': {
      if (status === 401) mapped = messageFromAuthDetail(body);
      else if (status === 404) {
        const d = detailString(body);
        if (d === CART_DETAIL_COURSE_NOT_IN_CATALOG) {
          mapped = {
            title: 'курс не в каталоге',
            description: 'Курс с таким адресом не найден.',
          };
        } else if (d === CART_DETAIL_COURSE_NOT_IN_CART) {
          mapped = {
            title: 'нет в корзине',
            description: 'Этого курса уже нет в корзине.',
          };
        }
      }
      break;
    }
    case 'cartPay': {
      if (status === 401) mapped = messageFromAuthDetail(body);
      break;
    }
    case 'courseDetail': {
      if (status === 401) mapped = messageFromAuthDetail(body);
      else if (status === 404 && detailString(body) === COURSE_DETAIL_NOT_FOUND) {
        mapped = {
          title: 'курс не найден',
          description: 'Проверьте ссылку или вернитесь в каталог.',
        };
      }
      break;
    }
    case 'webinarStart':
    case 'webinarJoin':
    case 'webinarRecording':
    case 'webinarRecordingStop':
    case 'recordingPdfUpload':
    case 'recordingPdfDelete':
    case 'recordingDelete':
    case 'webinarStop':
    case 'webinarRecorderJoin': {
      if (status === 401) mapped = messageFromAuthDetail(body);
      break;
    }
    default:
      break;
  }

  if (mapped) return mapped;

  const byStatus = statusFallback(scene, status);
  if (byStatus) return byStatus;

  return SCENE_FALLBACK[scene];
}

/** Оплата корзины (CartPayView) — на будущее; сейчас те же явные тела из views.py */
export function resolveCartPayMessage(
  status: number,
  body: unknown,
): UserFacingMessage {
  if (status === 400 && isRecord(body)) {
    if (body.error === PAY_ERROR_EMPTY_CART) {
      return {
        title: 'пустая корзина',
        description: 'Добавьте курсы перед оплатой.',
      };
    }
    if (
      body.error === PAY_ERROR_ALREADY_PURCHASED &&
      Array.isArray(body.course_ids)
    ) {
      return {
        title: 'уже куплено',
        description: 'Некоторые курсы из корзины у вас уже есть.',
      };
    }
  }
  if (status === 401) {
    const m = messageFromAuthDetail(body);
    if (m) return m;
  }
  return {
    title: 'оплата не прошла',
    description: 'Повторите попытку позже.',
  };
}
