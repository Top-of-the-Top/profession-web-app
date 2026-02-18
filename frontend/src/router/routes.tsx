import {
  LandingPage,
  LoginPage,
  RegistrationPage,
  RecoverPage,
  ResetPage,
} from '../pages';
import { Navigate } from 'react-router-dom';
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
		// TODO: ПОМЕНЯТЬ НА TRUE
    // protected: ,
    children: [
			{ path: '', element: <Navigate to="" replace /> },
      // { path: 'home', element: <Home /> },
      // { path: 'upload', element: <UploadPage /> },
      // { path: 'modify', element: <ModifyPage /> },
			// { path: 'distribute', element: <DistributePage /> },
    ],
  },
];
