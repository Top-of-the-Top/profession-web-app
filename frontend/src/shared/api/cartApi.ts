import { apiClient } from './interceptor';
import type { CourseDTO } from './courseApi';

export interface CartResponse {
  cart_id: number;
  user: number;
  created_at: string;
  updated_at: string;
  courses: CourseDTO[];
}

export interface CartActionResponse {
  status?: string;
  detail?: string;
  [key: string]: unknown;
}

export const cartApi = {
  getCart(): Promise<CartResponse> {
    return apiClient.request<CartResponse>('/api/v1/carts/', { method: 'GET' });
  },

  addCourse(slug: string) {
    return apiClient.request<CartActionResponse>('/api/v1/carts/add/' + slug + '/', {
      method: 'POST',
    });
  },

  removeCourse(slug: string) {
    return apiClient.request<CartActionResponse>('/api/v1/carts/remove/' + slug + '/', {
      method: 'DELETE',
    });
  },

  payCart() {
    return apiClient.request<CartActionResponse>('/api/v1/carts/pay/', { method: 'POST' });
  },
};

