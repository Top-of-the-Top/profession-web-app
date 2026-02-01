import {
  LandingPage,
  LoginPage,
  RegistrationPage,
  RecoverPage,
  ResetPage,
} from '../pages';

// import MainApp from '../pages/MainApp';
// import Dashboard from '../pages/MainApp/Dashboard';

import type { AppRoute } from './types';

export const routes: AppRoute[] = [
  {
    path: '/',
    element: <LandingPage />,
    publicOnly: true,
  },
  {
    path: '/login',
    element: <LoginPage />,
    publicOnly: true,
  },
  {
    path: '/register',
    element: <RegistrationPage />,
    publicOnly: true,
  },
  {
    path: '/reset',
    element: <ResetPage />,
    publicOnly: true,
  },
  {
    path: '/recover',
    element: <RecoverPage />,
  },

  // Protected (пример)
  // {
  //   path: '/app',
  //   element: <MainApp />,
  //   protected: true,
  // },
];
