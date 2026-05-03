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
  getCart(): Promise<CartResponse> {
    return apiClient.request<CartResponse>('/api/carts/', { method: 'GET' });
  },

  addCourse(slug: string) {
    return apiClient.request('/api/carts/add/' + slug + '/', {
      method: 'POST',
    });
  },

  removeCourse(slug: string) {
    return apiClient.request('/api/carts/remove/' + slug + '/', {
      method: 'DELETE',
    });
  },

  payCart() {
    return apiClient.request('/api/carts/pay/', { method: 'POST' });
  },
};

