// router/index.tsx
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { ProtectedRoute } from './ProtectedRoute';
import { PublicRoute } from './PublicRoute';
import { routes } from './routes';
import type { AppRoute } from './types';
import React from 'react';
import { NotFoundPage } from '../pages';

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
  <AuthProvider>
    <Routes>
      {renderRoutes(routes)}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  </AuthProvider>
);
