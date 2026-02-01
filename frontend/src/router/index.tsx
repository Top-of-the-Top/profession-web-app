// router/index.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { ProtectedRoute } from './ProtectedRoute';
import { PublicRoute } from './PublicRoute';

// Страницы
import {LandingPage, LoginPage, RegistrationPage, RecoverPage, ResetPage} from '../pages';


// Вложенные маршруты
import Dashboard from '../pages/MainApp/Dashboard';
import Courses from '../pages/MainApp/Courses';
import Profile from '../pages/MainApp/Profile';
import CourseDetail from '../pages/MainApp/CourseDetail';

export const AppRouter = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={
            <PublicRoute>
              <LandingPage />
            </PublicRoute>
          } />
          
          <Route path="/login" element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          } />
          
          <Route path="/register" element={
            <PublicRoute>
              <RegistrationPage />
            </PublicRoute>
          } />
          
          <Route path="/recover" element={
            <PublicRoute>
              <RecoverPage />
            </PublicRoute>
          } />
          
          <Route path="/reset-password/:token" element={
            <PublicRoute>
              <ResetPage />
            </PublicRoute>
          } />

          {/* Protected app routes */}
          <Route path="/app" element={
            <ProtectedRoute>
              <MainApp />
            </ProtectedRoute>
          }>
            <Route index element={<Dashboard />} />
            <Route path="courses" element={<Courses />} />
            <Route path="courses/:id" element={<CourseDetail />} />
            <Route path="profile" element={<Profile />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};