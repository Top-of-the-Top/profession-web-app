import {
  LandingPage,
  LoginPage,
  RegistrationPage,
  RecoverPage,
  ResetPage,
  AppHomePage,
  CourseStorePage,
  CoursePreviewPage,
  CourseLessonsPage,
  CartPage,
  LessonEditPage,
  LessonPreviewPage,
  LessonViewPage,
  HomeworkSubmissionPage,
  NotAuthorizedPage,
  WebinarPage,
  WebinarRecordPage,
  AppLayout,
} from './lazyPages';
import ProfileRoutePage from '@pages/profile/ui/ProfileRoutePage';

import type { AppRoute } from './types';

export const routes: AppRoute[] = [
  {
    path: '/',
    element: <LandingPage />,
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegistrationPage />,
  },
  {
    path: '/reset',
    element: <ResetPage />,
  },
  {
    path: '/recover',
    element: <RecoverPage />,
  },
  {
    path: '/webinar-record/:slug/:lessonSlug',
    element: <WebinarRecordPage />,
  },
  {
    path: '/app/courses/:slug/:lessonSlug/webinar',
    element: <WebinarPage />,
		protected: true
  },
  {
    path: '/app',
    element: <AppLayout />,
    protected: true,
    children: [
      { index: true, element: <AppHomePage /> },
      { path: 'profile', element: <ProfileRoutePage /> },
      { path: 'store', element: <CourseStorePage /> },
      {
        path: 'store/:slug',
        element: <CoursePreviewPage />,
      },

      {
        path: 'courses/:slug/:lessonSlug/edit',
        element: <LessonEditPage />,
        roles: ['teacher', 'moderator'],
      },
      {
        path: 'courses/:slug/:lessonSlug/homework/:homeworkSlug',
        element: <HomeworkSubmissionPage />,
      },
      {
        path: 'courses/:slug/:lessonSlug',
        element: <LessonViewPage />,
      },
      {
        path: 'courses/:slug',
        element: <CourseLessonsPage />,
      },
      {
        path: 'lesson/preview',
        element: <LessonPreviewPage />,
      },
      {
        path: 'cart',
        element: <CartPage />,
      },
      {
        path: 'not-authorized',
        element: <NotAuthorizedPage />,
      },
    ],
  },
];
