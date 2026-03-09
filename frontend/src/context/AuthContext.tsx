// context/AuthContext.tsx
import { createContext, type ReactNode } from 'react';
import { useUserStore, type User } from '../entities/user/model/userStore';

export interface Tokens {
  access_token: string;
  access_expires_at: string;
  refresh_token: string;
  refresh_expires_at: string;
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (tokens: Tokens) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const { user, isLoading, isAuthChecked, fetchUser, logout } = useUserStore();

  const login = (tokens: Tokens) => {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    localStorage.setItem('access_expires_at', tokens.access_expires_at);
    localStorage.setItem('refresh_expires_at', tokens.refresh_expires_at);

    // После успешного логина запрашиваем профиль пользователя
    void fetchUser();
  };

  const value: AuthContextType = {
    user,
    isLoading: isLoading || !isAuthChecked,
    login,
    logout,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
