import { authApi } from '../../../shared/api/authApi';

export const resetPassword = async (data: {
  password_hash: string;
  token: string;
}) => authApi.resetPassword(data);
