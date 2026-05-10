import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../interceptor';

export const adminKeys = {
  teachers: () => ['admin', 'teachers'] as const,
  invites: () => ['admin', 'invites'] as const,
  courses: () => ['admin', 'courses'] as const,
  course: (slug: string) => ['admin', 'courses', slug] as const,
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
  description: string;
  slug: string;
  price: number;
  type: 'draft' | 'published';
  is_special: boolean;
  starts_at: string | null;
  duration_weeks: number | null;
  min_age: number | null;
  authors: (number | AdminTeacher)[];
  image_url: string | null;
  created_at: string | null;
  updated_at: string | null;
  last_modified_by: number | null;
}

function normalizeAdminCourseAuthor(entry: unknown): number | AdminTeacher {
  if (typeof entry === 'number' && !Number.isNaN(entry)) return entry;
  if (entry !== null && typeof entry === 'object') {
    const o = entry as Record<string, unknown>;
    return {
      id: Number(o.id ?? 0),
      first_name: String(o.first_name ?? ''),
      last_name: String(o.last_name ?? ''),
      email: o.email == null ? null : String(o.email),
    };
  }
  const n = Number(entry);
  return Number.isNaN(n) ? 0 : n;
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

export function useAdminCourseBySlug(slug: string) {
  return useQuery({
    queryKey: adminKeys.course(slug),
    queryFn: async () => {
      const raw = await apiClient.request<unknown>(`/api/v1/courses/${slug}/`);
      const c = ((raw as { course?: unknown })?.course ?? raw ?? {}) as Record<string, unknown>;
      const rawType = c.type ?? c.status ?? c.course_status;
      const typeStr = typeof rawType === 'string' ? rawType.trim().toLowerCase() : '';
      const type: AdminCourse['type'] = typeStr === 'published' ? 'published' : 'draft';
      const imageRaw = c.image_url;
      const imageUrl = imageRaw != null && String(imageRaw).trim() !== '' ? String(imageRaw) : null;
      return {
        course_id: String(c.course_id ?? c.id ?? ''),
        title: String(c.title ?? ''),
        sub_title: String(c.sub_title ?? ''),
        description: String(c.description ?? ''),
        slug: String(c.slug ?? ''),
        price: Number(c.price ?? 0),
        type,
        is_special: Boolean(c.is_special),
        starts_at: c.starts_at == null || c.starts_at === '' ? null : String(c.starts_at),
        duration_weeks: c.duration_weeks == null || c.duration_weeks === '' ? null : Number(c.duration_weeks),
        min_age: c.min_age == null || c.min_age === '' ? null : Number(c.min_age),
        authors: Array.isArray(c.authors) ? c.authors.map(normalizeAdminCourseAuthor) : [],
        image_url: imageUrl,
        created_at: typeof c.created_at === 'string' ? c.created_at : null,
        updated_at: typeof c.updated_at === 'string' ? c.updated_at : null,
        last_modified_by: c.last_modified_by == null ? null : Number(c.last_modified_by),
      } satisfies AdminCourse;
    },
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
        const imageRaw = c.image_url;
        const imageUrl =
          imageRaw != null && String(imageRaw).trim() !== ''
            ? String(imageRaw)
            : null;
        return {
          course_id: String(c.course_id ?? c.id ?? ''),
          title: String(c.title ?? ''),
          sub_title: String(c.sub_title ?? ''),
          description: String(c.description ?? ''),
          slug: String(c.slug ?? ''),
          price: Number(c.price ?? 0),
          type,
          is_special: Boolean(c.is_special),
          starts_at:
            c.starts_at == null || c.starts_at === ''
              ? null
              : String(c.starts_at),
          duration_weeks:
            c.duration_weeks == null || c.duration_weeks === ''
              ? null
              : Number(c.duration_weeks),
          min_age:
            c.min_age == null || c.min_age === '' ? null : Number(c.min_age),
          authors: Array.isArray(c.authors)
            ? c.authors.map(normalizeAdminCourseAuthor)
            : [],
          image_url: imageUrl,
          created_at:
            typeof c.created_at === 'string' ? c.created_at : null,
          updated_at:
            typeof c.updated_at === 'string' ? c.updated_at : null,
          last_modified_by:
            c.last_modified_by == null ? null : Number(c.last_modified_by),
        } satisfies AdminCourse;
      });
    },
  });
}
