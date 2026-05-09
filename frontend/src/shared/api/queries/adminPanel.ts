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
  token: string;
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
    queryFn: async () => {
      const raw = await apiClient.request<unknown>('/api/v1/courses/');
      const list: unknown[] = Array.isArray(raw)
        ? raw
        : Array.isArray((raw as { data?: unknown })?.data)
          ? (raw as { data: unknown[] }).data
          : [];
      return list.map((item) => {
        const c = (item ?? {}) as Record<string, unknown>;
        const rawType = c.type ?? c.status ?? c.course_status;
        const typeStr =
          typeof rawType === 'string' ? rawType.trim().toLowerCase() : '';
        const type: AdminCourse['type'] =
          typeStr === 'published' ? 'published' : 'draft';
        return {
          course_id: String(c.course_id ?? c.id ?? ''),
          title: String(c.title ?? ''),
          sub_title: String(c.sub_title ?? ''),
          slug: String(c.slug ?? ''),
          price: Number(c.price ?? 0),
          type,
          authors: Array.isArray(c.authors) ? c.authors : [],
          image_url: c.image_url != null ? String(c.image_url) : null,
        } satisfies AdminCourse;
      });
    },
  });
}
