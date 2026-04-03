import { authApi } from '../../../shared/api/authApi';
import { buildResetPayload } from '../../../shared/utils/validation';
import { ResetSchema } from '../../../schemas/auth/reset.schema';

interface ResetParams {
  emailOrPhone: string;
}

export const resetUser = async ({ emailOrPhone }: ResetParams) => {
  const payload = buildResetPayload(emailOrPhone);
  const raw = await authApi.resetRequest(payload);
  return ResetSchema.parse(raw);
};
