import { Button } from './Button';
import { cn } from '@shared/lib/utils';
import { startYandexOAuth } from '@shared/lib/auth/yandexOAuth';
import { startVkOAuth } from '@shared/lib/auth/vkOAuth';
import { notifyError } from '@shared/lib/sileo/notify';

type OAuthButtonsProps = {
  containerClassName?: string;
  buttonClassName?: string;
  vkButtonClassName?: string;
  yandexButtonClassName?: string;
  iconClassName?: string;
};

export function OAuthButtons({
  containerClassName,
  buttonClassName,
  vkButtonClassName,
  yandexButtonClassName,
  iconClassName,
}: OAuthButtonsProps) {
  const handleYandexLogin = () => {
    try {
      startYandexOAuth();
    } catch (err) {
      notifyError({
        title: 'не удалось запустить вход через Яндекс',
        description: err instanceof Error ? err.message : 'Проверьте настройки OAuth.',
      });
    }
  };

  const handleVkLogin = () => {
    void startVkOAuth().catch((err) => {
      notifyError({
        title: 'не удалось запустить вход через VK',
        description: err instanceof Error ? err.message : 'Проверьте настройки OAuth.',
      });
    });
  };

  return (
    <div className={containerClassName}>
      <Button
        variant="outline"
        type="button"
        className={cn(buttonClassName, vkButtonClassName)}
        onClick={handleVkLogin}
      >
        <span className={iconClassName}>
          <img src="login/vk.svg" alt="" />
        </span>
        Войти с VK ID
      </Button>
      <Button
        variant="outline"
        type="button"
        className={cn(buttonClassName, yandexButtonClassName)}
        onClick={handleYandexLogin}
      >
        <span className={iconClassName}>
          <img src="login/ya.svg" alt="" />
        </span>
        Войти с Яндекс ID
      </Button>
    </div>
  );
}
