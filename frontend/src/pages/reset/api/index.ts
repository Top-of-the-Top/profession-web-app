import { authApi } from '../../../shared/api/authApi';
import { prepareAuthData } from '../../../shared/utils/validation';
import { ResetSchema } from '../../../schemas/auth/reset.schema';

interface ResetParams {
  emailOrPhone: string;
}

export const resetUser = async ({ emailOrPhone }: ResetParams) => {
  const payload = prepareAuthData(emailOrPhone);
  const raw = await authApi.resetRequest(payload);
  return ResetSchema.parse(raw);
};
