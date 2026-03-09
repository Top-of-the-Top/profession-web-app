import {
  LandingPage,
  LoginPage,
  RegistrationPage,
  RecoverPage,
  ResetPage,
  ProfilePage,
  CourseStorePage,
  CourseDetailPage,
  CartPage,
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
      // { path: '', element: <Navigate to="" replace /> },
      { path: 'profile', element: <ProfilePage /> },
      { path: 'store', element: <CourseStorePage /> },
      {
        path: 'courses/:slug', // Динамический параметр :slug
        element: <CourseDetailPage />,
      },
      {
        path: '/cart',
        element: <CartPage />,
        protected: true,
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
