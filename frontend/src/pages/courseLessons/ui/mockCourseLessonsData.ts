import type { AppCourseContentResponse } from '@shared/api/courseApi';

export const USE_MOCK = true;

export const MOCK_COURSE_PAGE_TITLE = 'Медицина';

export const MOCK_APP_COURSE: AppCourseContentResponse = {
  content: [
    {
      section_number: 1,
      section_id: 1,
      title: 'Название первого раздела',
      type: 'published',
      lessons: [
        {
          lesson_id: 101,
          lesson_number: '1.1',
          title: 'Название урока',
          slug: 'urok-1-1',
          type: 'published',
        },
      ],
    },
    {
      section_number: 2,
      section_id: 2,
      title: 'Название второго раздела',
      type: 'published',
      lessons: [
        {
          lesson_id: 201,
          lesson_number: '2.1',
          title: 'Название урока 1',
          slug: 'urok-2-1',
          type: 'published',
        },
        {
          lesson_id: 202,
          lesson_number: '2.2',
          title: 'Название урока 2',
          slug: 'urok-2-2',
          type: 'published',
        },
        {
          lesson_id: 203,
          lesson_number: '2.3',
          title: 'Название урока 3',
          slug: 'urok-2-3',
          type: 'draft',
        },
      ],
    },
    {
      section_number: 3,
      section_id: 3,
      title: 'Название третьего раздела',
      type: 'draft',
      lessons: [
        {
          lesson_id: 301,
          lesson_number: '3.1',
          title: 'Название урока 1',
          slug: 'urok-3-1',
          type: 'published',
        },
        {
          lesson_id: 302,
          lesson_number: '3.2',
          title: 'Название урока 2',
          slug: 'urok-3-2',
          type: 'draft',
        },
        {
          lesson_id: 303,
          lesson_number: '3.3',
          title: 'Название урока 3',
          slug: 'urok-3-3',
          type: 'published',
        },
      ],
    },
    {
      section_number: 4,
      section_id: 4,
      title: 'Название четвёртого раздела',
      type: 'published',
      lessons: [
        {
          lesson_id: 401,
          lesson_number: '4.1',
          title: 'Название урока 1',
          slug: 'urok-4-1',
          type: 'published',
        },
        {
          lesson_id: 402,
          lesson_number: '4.2',
          title: 'Название урока 2',
          slug: 'urok-4-2',
          type: 'published',
        },
      ],
    },
    ...[5, 6, 7].map((n) => ({
      section_number: n,
      section_id: n,
      title: `Название раздела ${n}`,
      type: 'draft' as const,
      lessons: [
        {
          lesson_id: n * 100 + 1,
          lesson_number: `${n}.1`,
          title: 'Название урока 1',
          slug: `urok-${n}-1`,
          type: 'draft' as const,
        },
      ],
    })),
  ],
  meta: {
    completed_sections_id: [1, 2, 4],
    completed_lessons_id: [
      101, 201, 202, 301, 303, 401, 402,
    ],
  },
};
