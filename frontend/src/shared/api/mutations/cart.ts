import { useMutation, useQueryClient } from '@tanstack/react-query';
import { cartApi, type CartResponse } from '../cartApi';
import { cartKeys } from '../queries/cart';

export function useAddToCart() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (slug: string) => cartApi.addCourse(slug),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: cartKeys.all });
    },
  });
}

export function useRemoveFromCart() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (slug: string) => cartApi.removeCourse(slug),
    onMutate: async (slug) => {
      await qc.cancelQueries({ queryKey: cartKeys.all });
      const prev = qc.getQueryData<CartResponse>(cartKeys.all);

      qc.setQueryData<CartResponse>(cartKeys.all, (old) =>
        old
          ? { ...old, courses: old.courses.filter((c) => c.slug !== slug) }
          : old,
      );

      return { prev };
    },
    onError: (_err, _slug, context) => {
      if (context?.prev) {
        qc.setQueryData<CartResponse>(cartKeys.all, context.prev);
      }
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: cartKeys.all });
    },
  });
}
