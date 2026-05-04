import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useUserStore } from '@entities/user/model/userStore';
import { consumeYandexOAuthState } from '@shared/lib/auth/yandexOAuth';
import { parseApiError } from '@shared/lib/api/parseApiError';
import { messageForApiFailure, notifyError } from '@shared/lib/sileo/notify';
import { exchangeYandexCode } from '../api';
import { warmAppAfterAuth } from '@router/lazyPages';
import styles from './OAuthYandexCallbackPage.module.css';

function readErrorDescription(rawError: string | null, rawDescription: string | null) {
  if (!rawError && !rawDescription) return 'Авторизация не завершена.';
  if (rawDescription) return rawDescription;
  return rawError ?? 'Ошибка OAuth.';
}

export default function OAuthYandexCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const login = useUserStore((s) => s.login);

  useEffect(() => {
    const run = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const providerError = searchParams.get('error');
      const providerErrorDescription = searchParams.get('error_description');

      if (providerError) {
        notifyError({
          title: 'вход через Яндекс отклонен',
          description: readErrorDescription(providerError, providerErrorDescription),
        });
        navigate('/login', { replace: true });
        return;
      }

      if (!code || !state) {
        notifyError({
          title: 'неполный ответ OAuth',
          description: 'В callback отсутствует code или state.',
        });
        navigate('/login', { replace: true });
        return;
      }

      const expectedState = consumeYandexOAuthState();
      if (!expectedState || expectedState !== state) {
        notifyError({
          title: 'неверный OAuth state',
          description: 'Повторите вход через Яндекс еще раз.',
        });
        navigate('/login', { replace: true });
        return;
      }

      try {
        const payload = await exchangeYandexCode({ code, state });
        await login(payload);
        await warmAppAfterAuth();
        navigate('/app', { replace: true });
      } catch (err) {
        const parsed = parseApiError(err);
        if (!parsed) {
          notifyError({
            title: 'не удалось завершить вход через Яндекс',
            description: err instanceof Error ? err.message : 'Попробуйте еще раз.',
          });
          navigate('/login', { replace: true });
          return;
        }

        const msg = messageForApiFailure('login', parsed.status, parsed.body);
        notifyError({ title: msg.title, description: msg.description });
        navigate('/login', { replace: true });
      }
    };

    void run();
  }, [searchParams, login, navigate]);

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>Завершаем вход через Яндекс</h1>
        <p className={styles.description}>Подождите, выполняется авторизация.</p>
      </div>
    </div>
  );
}
