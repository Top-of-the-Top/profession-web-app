import { useMutation, useQueryClient } from '@tanstack/react-query';
import { profileApi, type UpdateProfilePayload } from '../profileApi';
import { profileKeys } from '../queries/profile';

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: UpdateProfilePayload) =>
      profileApi.updateProfile(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: profileKeys.me(),
      });
    },
  });
}
