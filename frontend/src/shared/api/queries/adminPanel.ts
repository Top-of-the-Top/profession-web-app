import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../interceptor';

export const adminKeys = {
  teachers: () => ['admin', 'teachers'] as const,
  invites: () => ['admin', 'invites'] as const,
  courses: () => ['admin', 'courses'] as const,
};

export interface AdminTeacher {
  id: number;
  first_name: string;
  last_name: string;
  email: string | null;
}

export interface AdminTeacherInvite {
  id: string;
  email: string;
  created_by: AdminTeacher | null;
  created_at: string;
  expires_at: string;
  status: 'pending' | 'used' | 'expired';
}

export interface AdminCourse {
  course_id: string;
  title: string;
  sub_title: string;
  slug: string;
  price: number;
  type: 'draft' | 'published';
  authors: number[];
  image_url: string | null;
}

export function useAdminTeachers() {
  return useQuery({
    queryKey: adminKeys.teachers(),
    queryFn: () => apiClient.request<AdminTeacher[]>('/api/v1/admin-panel/teachers/'),
  });
}

export function useAdminInvites() {
  return useQuery({
    queryKey: adminKeys.invites(),
    queryFn: () => apiClient.request<AdminTeacherInvite[]>('/api/v1/admin-panel/invites/'),
  });
}

export function useAdminCourses() {
  return useQuery({
    queryKey: adminKeys.courses(),
    queryFn: () => apiClient.request<AdminCourse[]>('/api/v1/courses/'),
  });
}
