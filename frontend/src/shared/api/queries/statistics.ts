import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../interceptor';

export const statsKeys = {
  webinars: (courseTitle?: string, from?: string, to?: string) =>
    ['statistics', 'webinars', courseTitle ?? '', from ?? '', to ?? ''] as const,
  students: (courseTitle?: string, q?: string) =>
    ['statistics', 'students', courseTitle ?? '', q ?? ''] as const,
  studentCard: (userId: number | string, courseId: string) =>
    ['statistics', 'students', String(userId), 'courses', courseId] as const,
  schoolCourses: () => ['statistics', 'school', 'courses'] as const,
  schoolTeachers: () => ['statistics', 'school', 'teachers'] as const,
};

export interface StatWebinar {
  webinar_id: string;
  course_title: string;
  course_slug: string;
  lesson_title: string;
  started_at: string | null;
  ended_at: string | null;
  attended_total: number;
  attended_any: number;
  attended_threshold: number;
  homework_submitted_count: number;
}

export interface StatStudentCourse {
  course_id: string;
  course_slug: string;
  title: string;
}

export interface StatStudent {
  user_id: number;
  full_name: string;
  email: string;
  phone: string;
  courses: StatStudentCourse[];
}

export interface StatStudentCardHomework {
  homework_id: string;
  title: string;
  status: 'not_started' | 'draft' | 'submitted' | 'reviewed';
  grade: number | null;
}

export interface StatStudentCardWebinar {
  kind: 'live' | 'recording' | 'none';
  watched_ratio: number;
}

export interface StatStudentCardLesson {
  lesson_id: string;
  lesson_title: string;
  webinar: StatStudentCardWebinar | null;
  homeworks: StatStudentCardHomework[];
  homeworks_submitted: number;
  homeworks_total: number;
  is_completed: boolean;
}

export interface StatStudentCard {
  student_id: number;
  course_id: string;
  lessons: StatStudentCardLesson[];
}

export interface StatSchoolCourse {
  course_id: string;
  title: string;
  students: number;
  avg_progress: number;
  avg_attendance: number;
  avg_homework: number;
}

export interface StatSchoolTeacher {
  user_id: number;
  full_name: string;
  reviewed_7d: number;
  reviewed_30d: number;
  last_login: string | null;
}

export function useStatWebinars(courseTitle?: string, from?: string, to?: string) {
  const params = new URLSearchParams();
  if (courseTitle) params.set('course_title', courseTitle);
  if (from) params.set('from', from);
  if (to) params.set('to', to);
  const qs = params.toString();
  return useQuery({
    queryKey: statsKeys.webinars(courseTitle, from, to),
    queryFn: () =>
      apiClient.request<StatWebinar[]>(`/api/statistics/webinars/${qs ? `?${qs}` : ''}`),
  });
}

export function useStatStudents(courseTitle?: string, q?: string) {
  const params = new URLSearchParams();
  if (courseTitle) params.set('course_title', courseTitle);
  if (q) params.set('q', q);
  const qs = params.toString();
  return useQuery({
    queryKey: statsKeys.students(courseTitle, q),
    queryFn: () =>
      apiClient.request<StatStudent[]>(`/api/statistics/students/${qs ? `?${qs}` : ''}`),
  });
}

export function useStatStudentCard(userId: number | string | undefined, courseId: string | undefined) {
  return useQuery({
    queryKey: statsKeys.studentCard(userId!, courseId!),
    queryFn: () =>
      apiClient.request<StatStudentCard>(
        `/api/statistics/students/${userId}/courses/${courseId}/`,
      ),
    enabled: !!userId && !!courseId,
  });
}

export function useStatSchoolCourses() {
  return useQuery({
    queryKey: statsKeys.schoolCourses(),
    queryFn: () => apiClient.request<StatSchoolCourse[]>('/api/statistics/school/courses/'),
  });
}

export function useStatSchoolTeachers() {
  return useQuery({
    queryKey: statsKeys.schoolTeachers(),
    queryFn: () => apiClient.request<StatSchoolTeacher[]>('/api/statistics/school/teachers/'),
  });
}
