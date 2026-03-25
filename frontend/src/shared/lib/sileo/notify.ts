import { sileo } from 'sileo';
import { capitalizeFirst } from '../api/parseApiError';
import {
  resolveApiFailureMessage,
  type ApiFailureScene,
} from '../api/backendApiMessages';

const DURATION_OK = 5000;
const DURATION_ERR = 6500;
const DURATION_WARN = 5500;

type NotifyBase = {
  title: string;
  description?: string;
  duration?: number | null;
};

function titleOk(t: string) {
  return capitalizeFirst(t);
}

export function notifySuccess({ title, description, duration = DURATION_OK }: NotifyBase) {
  sileo.success({
    title: titleOk(title),
    description,
    duration,
  });
}

const CART_TOAST_BUTTON_SHIFT_CLASS = 'sileo-cart-toast-button-shift';

/** Успех добавления в корзину: кнопка перехода; сдвиг кнопки — только у этого тоста (класс в sileo-tokens.css). */
export function notifyCartCourseAdded({
  title,
  description,
  duration = DURATION_OK
}: NotifyBase) {
  sileo.success({
    title: titleOk(title),
    description,
    duration,
    
    styles: {
      button: CART_TOAST_BUTTON_SHIFT_CLASS,
    },
  });
}

export function notifyError({ title, description, duration = DURATION_ERR }: NotifyBase) {
  sileo.error({
    title: titleOk(title),
    description,
    duration,
  });
}

export function notifyWarning({ title, description, duration = DURATION_WARN }: NotifyBase) {
  sileo.warning({
    title: titleOk(title),
    description,
    duration,
  });
}

export function notifyInfo({ title, description, duration = DURATION_OK }: NotifyBase) {
  sileo.info({
    title: titleOk(title),
    description,
    duration,
  });
}

/** Сообщение для тоста по сцене и ответу API (каталог backendApiMessages). */
export function messageForApiFailure(
  scene: ApiFailureScene,
  status: number,
  body: unknown,
): { title: string; description: string } {
  return resolveApiFailureMessage(scene, status, body);
}
