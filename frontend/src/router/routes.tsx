import {
  LandingPage,
  LoginPage,
  RegistrationPage,
  RecoverPage,
  ResetPage,
  ProfilePage,
  AppHomePage,
  CourseStorePage,
  CoursePreviewPage,
  CourseLessonsPage,
  CartPage,
  CreateLessonPage,
  LessonPreviewPage,
  LessonViewPage,
  NotAuthorizedPage,
  AppLayout,
} from './lazyPages';

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
    path: '/app',
    element: <AppLayout />,
    protected: true,
    children: [
      { index: true, element: <AppHomePage /> },
      { path: 'home', element: <AppHomePage /> },
      { path: 'profile', element: <ProfilePage /> },
      { path: 'store', element: <CourseStorePage /> },
      {
        path: 'courses/:slug/lessons',
        element: <CourseLessonsPage />,
      },
      {
        path: 'courses/:slug/lessons/:lessonSlug',
        element: <LessonViewPage />,
      },
      {
        path: 'courses/:slug',
        element: <CoursePreviewPage />,
      },
      {
        path: 'create',
        element: <CreateLessonPage />,
				roles: ['teacher', 'moderator']
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
