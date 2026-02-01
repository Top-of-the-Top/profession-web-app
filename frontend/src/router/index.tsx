import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { ProtectedRoute } from './ProtectedRoute';
import { PublicRoute } from './PublicRoute';
import { routes } from './routes';
import React from 'react';

export const AppRouter = () => {
  return (
    <AuthProvider>
      <Routes>
        {routes.map(({ path, element, protected: isProtected, publicOnly }) => {
          let wrappedElement = element;

          if (isProtected) {
            wrappedElement = (
              <ProtectedRoute>{element as React.JSX.Element}</ProtectedRoute>
            );
          }

          if (publicOnly) {
            wrappedElement = (
              <PublicRoute>{element as React.JSX.Element}</PublicRoute>
            );
          }

          return <Route key={path} path={path} element={wrappedElement} />;
        })}

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
};
