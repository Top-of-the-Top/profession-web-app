import {
  LandingPage,
  LoginPage,
  RegistrationPage,
  RecoverPage,
  ResetPage,
  OAuthVkCallbackPage,
  OAuthYandexCallbackPage,
  AppHomePage,
  CourseStorePage,
  CoursePreviewPage,
  CourseLessonsPage,
  CartPage,
  LessonEditPage,
  LessonPreviewPage,
  LessonViewPage,
  HomeworkSubmissionPage,
  HomeworkReviewPage,
  HomeworkReviewAttemptsPage,
  WebinarPage,
  WebinarRecordPage,
  MyHomeworksPage,
  SchedulePage,
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
    path: '/oauth/vk/callback',
    element: <OAuthVkCallbackPage />,
  },
  {
    path: '/oauth/yandex/callback',
    element: <OAuthYandexCallbackPage />,
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
      { path: 'homeworks', element: <MyHomeworksPage /> },
      { path: 'schedule', element: <SchedulePage /> },
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
        path: 'courses/:slug/:lessonSlug/homework/:homeworkSlug/review',
        element: <HomeworkReviewAttemptsPage />,
        roles: ['teacher', 'moderator'],
      },
      {
        path: 'courses/:slug/:lessonSlug/homework/:homeworkSlug/review/:attemptId',
        element: <HomeworkReviewPage />,
        roles: ['teacher', 'moderator'],
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
    ],
  },
];
