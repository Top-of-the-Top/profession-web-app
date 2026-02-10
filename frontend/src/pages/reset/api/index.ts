// src/features/register/api/index.ts
import { apiClient } from '../../../shared/api/interceptor';
import { prepareAuthData } from '../../../shared/utils/validation';
import { ResetSchema } from '../../../schemas/auth/reset.schema';

interface ResetParams {
  emailOrPhone: string;
}

/**
 * Выполняет ресет через API и возвращает статус.
 * @throws Error с текстом ошибки, если неудачно
 */
export const resetUser = async ({
  emailOrPhone,
}: ResetParams) => {
  try {
		
    const payload = prepareAuthData(emailOrPhone);
    const tokensRaw = await apiClient.resetRequest(payload);
    // Проверка через Zod
    const status = ResetSchema.parse(tokensRaw);
    return status;
  } catch (err: any) {
		console.log(err)
    if (err.message.includes('403')) {
      throw new Error('Неверная почта/телефон');
    }
    if (err.message.includes('500')) {
      throw new Error('Сервер временно недоступен. Попробуйте позже.');
    }
    throw err;
  }
};
