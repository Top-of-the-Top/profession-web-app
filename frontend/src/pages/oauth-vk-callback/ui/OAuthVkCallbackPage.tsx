import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useUserStore } from '@entities/user/model/userStore';
import { consumeVkOAuthSession } from '@shared/lib/auth/vkOAuth';
import { parseApiError } from '@shared/lib/api/parseApiError';
import { messageForApiFailure, notifyError } from '@shared/lib/sileo/notify';
import { exchangeVkCode } from '../api';
import { warmAppAfterAuth } from '@router/lazyPages';
import styles from './OAuthVkCallbackPage.module.css';

function readErrorDescription(rawError: string | null, rawDescription: string | null) {
  if (!rawError && !rawDescription) return 'Авторизация не завершена.';
  if (rawDescription) return rawDescription;
  return rawError ?? 'Ошибка OAuth.';
}

export default function OAuthVkCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const login = useUserStore((s) => s.login);

  useEffect(() => {
    const run = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const deviceId = searchParams.get('device_id');
      const providerError = searchParams.get('error');
      const providerErrorDescription = searchParams.get('error_description');

      if (providerError) {
        notifyError({
          title: 'вход через VK отклонен',
          description: readErrorDescription(providerError, providerErrorDescription),
        });
        navigate('/login', { replace: true });
        return;
      }

      if (!code || !state || !deviceId) {
        notifyError({
          title: 'неполный ответ OAuth',
          description: 'В callback отсутствует code, state или device_id.',
        });
        navigate('/login', { replace: true });
        return;
      }

      const session = consumeVkOAuthSession();
      if (!session || session.state !== state) {
        notifyError({
          title: 'неверный OAuth state',
          description: 'Повторите вход через VK еще раз.',
        });
        navigate('/login', { replace: true });
        return;
      }

      try {
        const payload = await exchangeVkCode({
          code,
          state,
          codeVerifier: session.codeVerifier,
          deviceId,
        });
        await login(payload);
        await warmAppAfterAuth();
        navigate('/app', { replace: true });
      } catch (err) {
        const parsed = parseApiError(err);
        if (!parsed) {
          notifyError({
            title: 'не удалось завершить вход через VK',
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
        <h1 className={styles.title}>Завершаем вход через VK</h1>
        <p className={styles.description}>Подождите, выполняется авторизация.</p>
      </div>
    </div>
  );
}
