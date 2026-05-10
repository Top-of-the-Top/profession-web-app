import { Suspense } from 'react';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import { PublicRoute } from './PublicRoute';
import { RoleGuard } from '@shared/lib/rbac/RoleGuard';
import { routes } from './routes';
import { NotFoundPage } from './lazyPages';
import { RouterErrorFallback, Spinner } from '@shared/ui';
import type { AppRoute } from './types';
import type { RouteObject } from 'react-router-dom';

const mapRoutes = (appRoutes: AppRoute[]): RouteObject[] =>
  appRoutes.map(
    ({
      path,
      index: routeIndex,
      element,
      protected: isProtected,
      publicOnly,
      roles,
      children,
    }): RouteObject => {
      let wrappedElement = element as React.JSX.Element;

      if (isProtected) wrappedElement = <ProtectedRoute>{wrappedElement}</ProtectedRoute>;
      if (publicOnly) wrappedElement = <PublicRoute>{wrappedElement}</PublicRoute>;
      if (roles) wrappedElement = <RoleGuard allowed={roles}>{wrappedElement}</RoleGuard>;

      if (routeIndex) {
        return { index: true, element: wrappedElement };
      }

      return {
        path,
        element: wrappedElement,
        children: children ? mapRoutes(children) : undefined,
      };
    },
  );

const router = createBrowserRouter([
  {
    path: '/',
    errorElement: <RouterErrorFallback />,
    children: [
      ...mapRoutes(routes),
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

export const AppRouter = () => (
  <Suspense fallback={<Spinner full />}>
    <RouterProvider router={router} />
  </Suspense>
);
