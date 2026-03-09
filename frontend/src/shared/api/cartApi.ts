// shared/api/cartApi.ts
import { apiClient } from './interceptor';
import type { CourseDTO } from './courseApi';

export interface CartResponse {
  cart_id: number;
  user: number;
  created_at: string;
  updated_at: string;
  courses: CourseDTO[];
}

export const cartApi = {
  /**
   * Получить текущую корзину пользователя
   */
  getCart(): Promise<CartResponse> {
    return apiClient.request<CartResponse>('/api/carts/', { method: 'GET' });
  },

  /**
   * Добавить курс в корзину по slug
   */
  addCourse(slug: string) {
    return apiClient.request('/api/carts/add/' + slug + '/', {
      method: 'POST',
    });
  },

  /**
   * Удалить курс из корзины по slug
   */
  removeCourse(slug: string) {
    return apiClient.request('/api/carts/remove/' + slug + '/', {
      method: 'DELETE',
    });
  },
};

