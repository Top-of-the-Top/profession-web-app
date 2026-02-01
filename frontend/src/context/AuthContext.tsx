// context/AuthContext.tsx
import { createContext, useState, useEffect, type ReactNode } from 'react';
import { jwtDecode } from 'jwt-decode';
import { authEvents } from '../shared/events/authEvents';

export interface User {
  id: number;
  email?: string | null;
  phone?: string | null;
  first_name?: string | null;
  last_name?: string | null;
}

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
  refreshAuth: () => Promise<boolean>;
  isAuthenticated: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);


	useEffect(() => {
  const handler = () => logout();
  authEvents.addEventListener('logout', handler);

  return () => {
    authEvents.removeEventListener('logout', handler);
  };
}, []);

  // Инициализация и проверка токена
  useEffect(() => {
    const initAuth = async () => {
      const accessToken = localStorage.getItem('access_token');
      const refreshToken = localStorage.getItem('refresh_token');

      if (!accessToken || !refreshToken) {
        setIsLoading(false);
        return;
      }

      try {
        // Проверяем валидность access токена
        const decoded: any = jwtDecode(accessToken);
        const isExpired = Date.now() >= new Date(decoded.exp * 1000).getTime();

        if (isExpired) {
          // Пробуем обновить
          const success = await refreshAuth();
          if (!success) {
            logout();
          }
        } else {
          setUserFromToken(accessToken);
        }
      } catch (error) {
        logout();
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const setUserFromToken = (token: string) => {
    try {
      const decoded: any = jwtDecode(token);
      setUser({
        id: decoded.user_id || decoded.id,
        email: decoded.email,
        phone: decoded.phone,
        first_name: decoded.first_name,
        last_name: decoded.last_name
      });
    } catch (error) {
      console.error('Invalid token:', error);
    }
  };

  const login = (tokens: Tokens) => {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    localStorage.setItem('access_expires_at', tokens.access_expires_at);
    localStorage.setItem('refresh_expires_at', tokens.refresh_expires_at);
    
    setUserFromToken(tokens.access_token);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('access_expires_at');
    localStorage.removeItem('refresh_expires_at');
    setUser(null);
  };

  const refreshAuth = async (): Promise<boolean> => {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) return false;

    try {
      const response = await fetch('/api/auth/token/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken })
      });

      if (!response.ok) return false;

      const tokens: Tokens = await response.json();
      login(tokens);
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return false;
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      isLoading,
      login,
      logout,
      refreshAuth,
      isAuthenticated: !!user
    }}>
      {children}
    </AuthContext.Provider>
  );
};