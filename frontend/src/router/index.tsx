// src/router/index.tsx - ИСПРАВЛЕННЫЙ ВАРИАНТ
import { Routes, Route, Navigate } from 'react-router-dom'; // Убрали BrowserRouter!
import { AuthProvider } from '../context/AuthContext';
import { ProtectedRoute } from './ProtectedRoute';
import { PublicRoute } from './PublicRoute';

// Страницы
import { 
  LandingPage, 
  LoginPage, 
  RegistrationPage, 
  RecoverPage, 
  ResetPage 
} from '../pages';

// // Основное приложение
// import MainApp from '../pages/MainApp';
// import Dashboard from '../pages/MainApp/Dashboard';
// import Courses from '../pages/MainApp/Courses';
// import Profile from '../pages/MainApp/Profile';

export const AppRouter = () => {
  return (
    // НЕТ BrowserRouter здесь!
    <AuthProvider>
      <Routes>
        {/* Public маршруты */}
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
        
        <Route path="/reset-password/" element={
          <PublicRoute>
            <ResetPage />
          </PublicRoute>
        } />

        {/* Protected маршруты */}
        {/* <Route path="/app" element={
          <ProtectedRoute>
            <MainApp />
          </ProtectedRoute>
        }>
          <Route index element={<Dashboard />} />
          <Route path="courses" element={<Courses />} />
          <Route path="profile" element={<Profile />} />
        </Route> */}

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
};