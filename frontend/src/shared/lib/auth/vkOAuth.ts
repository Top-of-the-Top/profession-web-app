const VK_AUTHORIZE_URL = 'https://id.vk.ru/authorize';

const VK_CLIENT_ID = (import.meta.env.VITE_VK_CLIENT_ID as string | undefined)?.trim();
const VK_REDIRECT_URI = (import.meta.env.VITE_VK_REDIRECT_URI as string | undefined)?.trim();
const VK_SCOPE = (import.meta.env.VITE_VK_SCOPE as string | undefined);

const VK_OAUTH_SESSION_STORAGE_KEY = 'vk_oauth_session';

type VkOAuthSession = {
  state: string;
  codeVerifier: string;
};

function base64UrlEncode(bytes: Uint8Array) {
  let binary = '';
  bytes.forEach((b) => {
    binary += String.fromCharCode(b);
  });
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function generateRandomString(length: number) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
  const random = new Uint8Array(length);
  globalThis.crypto.getRandomValues(random);
  let result = '';
  for (let i = 0; i < length; i += 1) {
    result += alphabet[random[i] % alphabet.length];
  }
  return result;
}

async function createCodeChallenge(codeVerifier: string) {
  const data = new TextEncoder().encode(codeVerifier);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', data);
  return base64UrlEncode(new Uint8Array(digest));
}

function saveSession(session: VkOAuthSession) {
  localStorage.setItem(VK_OAUTH_SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function consumeVkOAuthSession() {
  const raw = localStorage.getItem(VK_OAUTH_SESSION_STORAGE_KEY);
  localStorage.removeItem(VK_OAUTH_SESSION_STORAGE_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<VkOAuthSession>;
    if (!parsed.state || !parsed.codeVerifier) return null;
    return { state: parsed.state, codeVerifier: parsed.codeVerifier };
  } catch {
    return null;
  }
}

export async function startVkOAuth() {
  if (!VK_CLIENT_ID) {
    throw new Error('VK OAuth client_id не задан: VITE_VK_CLIENT_ID');
  }
  if (!VK_REDIRECT_URI) {
    throw new Error('VK OAuth redirect_uri не задан: VITE_VK_REDIRECT_URI');
  }
  if (!globalThis.crypto?.subtle) {
    throw new Error('WebCrypto недоступен в этом браузере.');
  }

  const state = globalThis.crypto.randomUUID();
  const codeVerifier = generateRandomString(64);
  const codeChallenge = await createCodeChallenge(codeVerifier);
  saveSession({ state, codeVerifier });

  const query = new URLSearchParams({
    response_type: 'code',
    client_id: VK_CLIENT_ID,
    redirect_uri: VK_REDIRECT_URI,
    state,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
  });

  if (VK_SCOPE) {
    query.set('scope', VK_SCOPE);
  }

  window.location.assign(`${VK_AUTHORIZE_URL}?${query.toString()}`);
}
