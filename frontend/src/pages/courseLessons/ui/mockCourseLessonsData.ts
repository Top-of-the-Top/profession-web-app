import type { Course, Lesson } from '../../../shared/api/courseApi';

/**
 * Включить мок-режим: true — не ходим в API за списком уроков.
 * Иначе используем backend эндпоинты.
 */
export const USE_MOCK = true;

export const MOCK_COURSE: Course = {
  course_id: 1,
  title: 'Тестовый курс',
  sub_title: 'Моковый список уроков',
  image_url: '',
  price: 0,
  slug: 'mock-course',
  created_at: new Date().toISOString(),
  description: 'Данные для отладки',
};

export const MOCK_LESSONS: Lesson[] = [
  {
    lesson_id: 1,
    course_id: 1,
    title: 'Урок 1',
    slug: 'mock-lesson-1',
    // date используется для форматирования в UI
    date: new Date(Date.now() + 1000 * 60 * 60 * 24).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    last_modified_by: null,
  },
];

