import { useMutation } from '@tanstack/react-query';
import { profileApi, type UpdateProfilePayload } from '../profileApi';
import { useUserStore } from '../../../entities/user/model/userStore';

export function useUpdateProfile() {
  return useMutation({
    mutationFn: (payload: UpdateProfilePayload) =>
      profileApi.updateProfile(payload),
    onSuccess: async () => {
      const fresh = await profileApi.getProfile();
      useUserStore.getState().setUser(fresh);
    },
  });
}
