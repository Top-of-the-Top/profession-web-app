import { lazy } from 'react';

const importMap = {
  landing: () => import('@pages/landing/ui/LandingPage'),
  login: () => import('@pages/login/ui/LoginPage'),
  register: () => import('@pages/register/ui/RegistrationPage'),
  recover: () => import('@pages/recover/ui/RecoverPage'),
  reset: () => import('@pages/reset/ui/ResetPage'),
  oauthVkCallback: () => import('@pages/oauth-vk-callback/ui/OAuthVkCallbackPage'),
  oauthYandexCallback: () => import('@pages/oauth-yandex-callback/ui/OAuthYandexCallbackPage'),
  notFound: () => import('@pages/notfound/NotFoundPage'),

  appLayout: () => import('@widgets/AppLayout/ui/AppLayout'),
  appHome: () => import('@pages/home/ui/AppHomePage'),
  profile: () => import('@pages/profile/ui/ProfilePage'),
  courseStore: () => import('@pages/store/ui/CourseStorePage'),
  coursePreview: () => import('@pages/coursePreview/ui/CoursePreviewPage'),
  courseLessons: () => import('@pages/courseLessons/ui/CourseLessonsPage'),
  lessonView: () => import('@pages/lessonView/ui/LessonViewPage'),
  homeworkSubmission: () =>
    import('@pages/homeworkSubmission/ui/HomeworkSubmissionPage'),
  homeworkReview: () => import('@pages/homeworkReview/ui/HomeworkReviewPage'),
  homeworkReviewAttempts: () =>
    import('@pages/homeworkReviewAttempts/ui/HomeworkReviewAttemptsPage'),
  lessonEdit: () => import('@pages/lessonEdit/ui/LessonEditPage'),
  cart: () => import('@pages/cart/Cart'),
  lessonPreview: () => import('@pages/lessonPreview/ui/LessonPreviewPage'),
  webinar: () => import('@pages/webinar/ui/WebinarPage'),
  webinarRecord: () => import('@pages/webinarRecord/ui/WebinarRecordPage'),
  myHomeworks: () => import('@pages/myHomeworks/ui/MyHomeworksPage'),
};

export const LandingPage = lazy(importMap.landing);
export const LoginPage = lazy(importMap.login);
export const RegistrationPage = lazy(importMap.register);
export const RecoverPage = lazy(importMap.recover);
export const ResetPage = lazy(importMap.reset);
export const OAuthVkCallbackPage = lazy(importMap.oauthVkCallback);
export const OAuthYandexCallbackPage = lazy(importMap.oauthYandexCallback);
export const NotFoundPage = lazy(importMap.notFound);

export const AppLayout = lazy(importMap.appLayout);
export const AppHomePage = lazy(importMap.appHome);
export const ProfilePage = lazy(importMap.profile);
export const CourseStorePage = lazy(importMap.courseStore);
export const CoursePreviewPage = lazy(importMap.coursePreview);
export const CourseLessonsPage = lazy(importMap.courseLessons);
export const LessonViewPage = lazy(importMap.lessonView);
export const HomeworkSubmissionPage = lazy(importMap.homeworkSubmission);
export const HomeworkReviewPage = lazy(importMap.homeworkReview);
export const HomeworkReviewAttemptsPage = lazy(importMap.homeworkReviewAttempts);
export const LessonEditPage = lazy(importMap.lessonEdit);
export const CartPage = lazy(importMap.cart);
export const LessonPreviewPage = lazy(importMap.lessonPreview);
export const WebinarPage = lazy(importMap.webinar);
export const WebinarRecordPage = lazy(importMap.webinarRecord);
export const MyHomeworksPage = lazy(importMap.myHomeworks);

export function runWhenIdle(fn: () => void, timeoutMs = 2500): void {
  if (typeof requestIdleCallback === 'function') {
    requestIdleCallback(() => {
      fn();
    }, { timeout: timeoutMs });
    return;
  }
  window.setTimeout(fn, 1);
}

export function preloadAppShell(): Promise<void> {
  return Promise.all([importMap.appLayout(), importMap.appHome()]).then(() => undefined);
}

export function preloadAppRest(): void {
  void importMap.courseStore();
  void importMap.profile();
  void importMap.cart();
}

export async function warmAppAfterAuth(): Promise<void> {
  await preloadAppShell();
  runWhenIdle(() => {
    preloadAppRest();
  });
}

export function preloadAppCore(): void {
  void preloadAppShell();
  preloadAppRest();
}

export function prefetchAppSidebarHref(href: string): void {
  if (href === '/app') {
    void importMap.appHome();
    return;
  }
  if (href === '/app/store') {
    void importMap.courseStore();
    return;
  }
}

export function preloadCourseDetailsRoutes(): void {
  void importMap.coursePreview();
  void importMap.courseLessons();
}

export function preloadWebinarRoute(): Promise<void> {
  return importMap.webinar().then(() => undefined);
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
