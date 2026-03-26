import { lazy } from 'react';

const importMap = {
  landing: () => import('../pages/landing/ui/LandingPage'),
  login: () => import('../pages/login/ui/LoginPage'),
  register: () => import('../pages/register/ui/RegistrationPage'),
  recover: () => import('../pages/recover/ui/RecoverPage'),
  reset: () => import('../pages/reset/ui/ResetPage'),
  notFound: () => import('../pages/notfound/NotFoundPage'),

  appLayout: () => import('../widgets/AppLayout/ui/AppLayout'),
  appHome: () => import('../pages/home/ui/AppHomePage'),
  profile: () => import('../pages/profile/ui/ProfilePage'),
  courseStore: () => import('../pages/store/ui/CourseStorePage'),
  coursePreview: () => import('../pages/coursePreview/ui/CoursePreviewPage'),
  courseLessons: () => import('../pages/courseLessons/ui/CourseLessonsPage'),
  lessonView: () => import('../pages/lessonView/ui/LessonViewPage'),
  cart: () => import('../pages/cart/Cart'),
  createLesson: () => import('../pages/lessonCreate/ui/CreateLessonPage'),
  lessonPreview: () => import('../pages/lessonPreview/ui/LessonPreviewPage'),
  toastPlayground: () => import('../pages/toast-playground/ui/ToastPlaygroundPage'),
};

export const LandingPage = lazy(importMap.landing);
export const LoginPage = lazy(importMap.login);
export const RegistrationPage = lazy(importMap.register);
export const RecoverPage = lazy(importMap.recover);
export const ResetPage = lazy(importMap.reset);
export const NotFoundPage = lazy(importMap.notFound);

export const AppLayout = lazy(importMap.appLayout);
export const AppHomePage = lazy(importMap.appHome);
export const ProfilePage = lazy(importMap.profile);
export const CourseStorePage = lazy(importMap.courseStore);
export const CoursePreviewPage = lazy(importMap.coursePreview);
export const CourseLessonsPage = lazy(importMap.courseLessons);
export const LessonViewPage = lazy(importMap.lessonView);
export const CartPage = lazy(importMap.cart);
export const CreateLessonPage = lazy(importMap.createLesson);
export const LessonPreviewPage = lazy(importMap.lessonPreview);
export const ToastPlaygroundPage = lazy(importMap.toastPlayground);

/**
 * Preload the app shell and most common post-login pages.
 * Called from auth pages via requestIdleCallback so bundles are
 * cached by the time the user finishes entering credentials.
 */
export function preloadAppCore() {
  importMap.appLayout();
  importMap.appHome();
  importMap.courseStore();
  importMap.profile();
}
