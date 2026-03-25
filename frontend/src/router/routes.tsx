import {
  LandingPage,
  LoginPage,
  RegistrationPage,
  RecoverPage,
  ResetPage,
  ProfilePage,
  AppHomePage,
  CourseStorePage,
  CourseDetailPage,
  CourseLessonsPage,
  CartPage,
  CreateLesson,
  LessonPreviewPage,
  LessonViewPage,
  ToastPlaygroundPage,
} from '../pages';
import AppLayout from '../widgets/AppLayout/ui/AppLayout';

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
      { index: true, element: <ToastPlaygroundPage /> },
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
        element: <CourseDetailPage />,
      },
      {
        path: 'create',
        element: <CreateLesson />,
      },
      {
        path: 'lesson/preview',
        element: <LessonPreviewPage />,
      },
      {
        path: 'cart',
        element: <CartPage />,
      },
      // { path: 'modify', element: <ModifyPage /> },
      // { path: 'distribute', element: <DistributePage /> },
    ],
  },
  // {
  //   path: '/cart',
  //   element: <CartPage />,
  //   protected: true,
  // },
];
