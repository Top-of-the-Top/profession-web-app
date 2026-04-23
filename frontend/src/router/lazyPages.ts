import { lazy } from 'react';

const importMap = {
  landing: () => import('@pages/landing/ui/LandingPage'),
  login: () => import('@pages/login/ui/LoginPage'),
  register: () => import('@pages/register/ui/RegistrationPage'),
  recover: () => import('@pages/recover/ui/RecoverPage'),
  reset: () => import('@pages/reset/ui/ResetPage'),
  notFound: () => import('@pages/notfound/NotFoundPage'),
  notAuthorized: () => import('@pages/notAuthorized/NotAuthorizedPage'),

  appLayout: () => import('@widgets/AppLayout/ui/AppLayout'),
  appHome: () => import('@pages/home/ui/AppHomePage'),
  profile: () => import('@pages/profile/ui/ProfilePage'),
  courseStore: () => import('@pages/store/ui/CourseStorePage'),
  coursePreview: () => import('@pages/coursePreview/ui/CoursePreviewPage'),
  courseLessons: () => import('@pages/courseLessons/ui/CourseLessonsPage'),
  lessonView: () => import('@pages/lessonView/ui/LessonViewPage'),
  lessonEdit: () => import('@pages/lessonEdit/ui/LessonEditPage'),
  cart: () => import('@pages/cart/Cart'),
  lessonPreview: () => import('@pages/lessonPreview/ui/LessonPreviewPage'),
  webinar: () => import('@pages/webinar/ui/WebinarPage'),
  webinarRecord: () => import('@pages/webinarRecord/ui/WebinarRecordPage'),
};

export const LandingPage = lazy(importMap.landing);
export const LoginPage = lazy(importMap.login);
export const RegistrationPage = lazy(importMap.register);
export const RecoverPage = lazy(importMap.recover);
export const ResetPage = lazy(importMap.reset);
export const NotFoundPage = lazy(importMap.notFound);
export const NotAuthorizedPage = lazy(importMap.notAuthorized);

export const AppLayout = lazy(importMap.appLayout);
export const AppHomePage = lazy(importMap.appHome);
export const ProfilePage = lazy(importMap.profile);
export const CourseStorePage = lazy(importMap.courseStore);
export const CoursePreviewPage = lazy(importMap.coursePreview);
export const CourseLessonsPage = lazy(importMap.courseLessons);
export const LessonViewPage = lazy(importMap.lessonView);
export const LessonEditPage = lazy(importMap.lessonEdit);
export const CartPage = lazy(importMap.cart);
export const LessonPreviewPage = lazy(importMap.lessonPreview);
export const WebinarPage = lazy(importMap.webinar);
export const WebinarRecordPage = lazy(importMap.webinarRecord);

export function preloadAppCore() {
  void importMap.appLayout();
  void importMap.appHome();
  void importMap.courseStore();
  void importMap.profile();
  void importMap.cart();
}

export function preloadAuthFormBundles() {
  void importMap.login();
  void importMap.register();
  void import('@pages/login/ui/LoginForm');
  void import('@pages/register/ui/RegistrationForm');
}

export function preloadLoginRoute() {
  void importMap.login();
  void import('@pages/login/ui/LoginForm');
}

export function preloadRegisterRoute() {
  void importMap.register();
  void import('@pages/register/ui/RegistrationForm');
}

export function preloadResetRoute() {
  void importMap.reset();
  void import('@pages/reset/ui/ResetForm');
}
