import { Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import { PublicRoute } from './PublicRoute';
import { routes } from './routes';
import { NotFoundPage } from './lazyPages';
import { Spinner } from '../shared/ui';
import type { AppRoute } from './types';

const renderRoutes = (routes: AppRoute[], basePath = '') =>
  routes.map(
    ({
      path,
      index: routeIndex,
      element,
      protected: isProtected,
      publicOnly,
      children,
    }) => {
      let wrappedElement = element as React.JSX.Element;

      if (isProtected) wrappedElement = <ProtectedRoute>{wrappedElement}</ProtectedRoute>;
      if (publicOnly) wrappedElement = <PublicRoute>{wrappedElement}</PublicRoute>;

      if (routeIndex) {
        return (
          <Route key={`${basePath || 'root'}::index`} index element={wrappedElement}>
            {children && renderRoutes(children, basePath)}
          </Route>
        );
      }

      const segment = path ?? '';
      const fullPath = basePath + (segment.startsWith('/') ? segment : '/' + segment);

      return (
        <Route key={fullPath} path={fullPath} element={wrappedElement}>
          {children && renderRoutes(children, fullPath)}
        </Route>
      );
    },
  );

export const AppRouter = () => (
  <Suspense fallback={<Spinner full />}>
    <Routes>
      {renderRoutes(routes)}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  </Suspense>
);
