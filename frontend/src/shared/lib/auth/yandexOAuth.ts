const YANDEX_AUTHORIZE_URL = 'https://oauth.yandex.ru/authorize';

const YANDEX_CLIENT_ID = (import.meta.env.VITE_YANDEX_CLIENT_ID as string | undefined)?.trim();
const YANDEX_REDIRECT_URI = (import.meta.env.VITE_YANDEX_REDIRECT_URI as string | undefined)?.trim();
const YANDEX_RESPONSE_TYPE =
  (import.meta.env.VITE_YANDEX_RESPONSE_TYPE as string | undefined)?.trim() || 'code';

const OAUTH_STATE_STORAGE_KEY = 'yandex_oauth_state';

function buildYandexAuthorizeUrl() {
  if (!YANDEX_CLIENT_ID) {
    throw new Error('Yandex OAuth client_id не задан: VITE_YANDEX_CLIENT_ID');
  }

  if (!YANDEX_REDIRECT_URI) {
    throw new Error('Yandex OAuth redirect_uri не задан: VITE_YANDEX_REDIRECT_URI');
  }

  const state = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  localStorage.setItem(OAUTH_STATE_STORAGE_KEY, state);

  const query = new URLSearchParams({
    response_type: YANDEX_RESPONSE_TYPE,
    client_id: YANDEX_CLIENT_ID,
    redirect_uri: YANDEX_REDIRECT_URI,
    state,
  });

  return `${YANDEX_AUTHORIZE_URL}?${query.toString()}`;
}

export function startYandexOAuth() {
  const url = buildYandexAuthorizeUrl();
  window.location.assign(url);
}

export function consumeYandexOAuthState() {
  const state = localStorage.getItem(OAUTH_STATE_STORAGE_KEY);
  localStorage.removeItem(OAUTH_STATE_STORAGE_KEY);
  return state;
}
