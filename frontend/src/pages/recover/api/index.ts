import { authApi } from '../../../shared/api/authApi';

export interface ResetPasswordParams {
  password: string;
  token: string;
}

/**
 * Устанавливает новый пароль через API
 * @throws Error с текстом ошибки, если неудачно
 */
export const resetPassword = async (data: ResetPasswordParams) => {
  try {
    // Добавляем timestamp, если нужно
    const payload = {
      ...data,
      date_time: new Date().toISOString()
    };
    
    const response = await authApi.resetPassword(payload);
    return response;
  } catch (err: any) {
    if (err.message.includes('403')) {
      throw new Error('Неверный или просроченный токен');
    }
    if (err.message.includes('400')) {
      throw new Error('Некорректные данные');
    }
    if (err.message.includes('500')) {
      throw new Error('Сервер временно недоступен. Попробуйте позже.');
    }
    throw err;
  }
};