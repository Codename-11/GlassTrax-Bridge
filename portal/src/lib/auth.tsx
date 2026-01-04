import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { api } from './api';

interface User {
  username: string;
  role: 'admin';
}

interface LoginResponse {
  success: boolean;
  data: {
    token: string;
    token_type: string;
    expires_in: number;
    is_default_password: boolean;
  };
  message?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isDefaultPassword: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDefaultPassword, setIsDefaultPassword] = useState(false);

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('auth_token');
      const apiKey = localStorage.getItem('admin_api_key');

      if (token || apiKey) {
        // Set up API headers
        if (apiKey) {
          api.defaults.headers.common['X-API-Key'] = apiKey;
        }
        if (token) {
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        }

        // Restore user session
        const savedUser = localStorage.getItem('auth_user');
        if (savedUser) {
          setUser(JSON.parse(savedUser));
          setIsDefaultPassword(localStorage.getItem('is_default_password') === 'true');
        }
      }
      setIsLoading(false);
    };
    checkAuth();
  }, []);

  const login = async (username: string, password: string) => {
    // Try the new login endpoint
    try {
      const response = await api.post<LoginResponse>('/api/v1/admin/login', {
        username,
        password,
      });

      if (response.data.success) {
        const { token, is_default_password } = response.data.data;

        // Store token
        localStorage.setItem('auth_token', token);
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;

        // If they logged in with an API key, store it for data endpoints
        // JWT Bearer token is sufficient for admin endpoints
        if (password.startsWith('gtb_') || password.includes('-key-')) {
          localStorage.setItem('admin_api_key', password);
          api.defaults.headers.common['X-API-Key'] = password;
        }

        // Set user
        const userData: User = { username, role: 'admin' };
        setUser(userData);
        localStorage.setItem('auth_user', JSON.stringify(userData));

        // Track default password
        setIsDefaultPassword(is_default_password);
        localStorage.setItem('is_default_password', is_default_password.toString());

        return;
      }
    } catch (error: any) {
      // If login endpoint fails, check if password looks like an API key
      // and try using it directly (fallback for API key auth)
      if (password.startsWith('gtb_') || password.includes('-key-')) {
        // Verify the API key works by trying to hit an admin endpoint
        api.defaults.headers.common['X-API-Key'] = password;
        try {
          await api.get('/api/v1/admin/tenants?page_size=1');
          // API key works - set up session
          localStorage.setItem('admin_api_key', password);
          const userData: User = { username: 'admin', role: 'admin' };
          setUser(userData);
          localStorage.setItem('auth_user', JSON.stringify(userData));
          setIsDefaultPassword(false);
          return;
        } catch {
          delete api.defaults.headers.common['X-API-Key'];
        }
      }
      throw new Error(error.response?.data?.detail || 'Invalid credentials');
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('admin_api_key');
    localStorage.removeItem('auth_user');
    localStorage.removeItem('is_default_password');
    delete api.defaults.headers.common['X-API-Key'];
    delete api.defaults.headers.common['Authorization'];
    setUser(null);
    setIsDefaultPassword(false);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        isDefaultPassword,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
