/**
 * Zustand authentication store
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import {
  AuthState,
  User,
  AuthTokens,
  LoginRequest,
  RegisterRequest,
} from '../types/auth.types';
import { authService } from '../services/auth.service';

interface AuthActions {
  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  clearError: () => void;
  initializeAuth: () => void;

  // State setters
  setUser: (user: User | null) => void;
  setTokens: (tokens: AuthTokens | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      user: null,
      tokens: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      login: async (credentials: LoginRequest) => {
        try {
          set({ isLoading: true, error: null });

          // Login API call
          const tokens = await authService.login(credentials);

          // Store tokens
          authService.storeTokens(tokens);
          set({ tokens });

          // Get user profile
          const user = await authService.getCurrentUser();

          // Store user
          authService.storeUser(user);
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          });

        } catch (error: any) {
          const errorMessage = error.detail || 'Login failed';
          set({
            error: errorMessage,
            isLoading: false,
            isAuthenticated: false,
          });
          throw error;
        }
      },

      register: async (userData: RegisterRequest) => {
        try {
          set({ isLoading: true, error: null });

          // Register API call
          await authService.register(userData);

          set({ isLoading: false });

          // Note: After registration, user needs to login separately
          // This matches the backend behavior where register doesn't auto-login

        } catch (error: any) {
          const errorMessage = error.detail || 'Registration failed';
          set({
            error: errorMessage,
            isLoading: false,
          });
          throw error;
        }
      },

      logout: () => {
        authService.logout();
        set({
          user: null,
          tokens: null,
          isAuthenticated: false,
          error: null,
        });
      },

      refreshUser: async () => {
        try {
          set({ isLoading: true });

          const user = await authService.getCurrentUser();
          authService.storeUser(user);

          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          });

        } catch (error: any) {
          // If refresh fails, logout user
          get().logout();
          set({ isLoading: false });
        }
      },

      clearError: () => {
        set({ error: null });
      },

      initializeAuth: () => {
        const storedTokens = authService.getStoredTokens();
        const storedUser = authService.getStoredUser();

        if (storedTokens && storedUser && authService.isAuthenticated()) {
          set({
            user: storedUser,
            tokens: storedTokens,
            isAuthenticated: true,
          });
        } else {
          // Clear invalid stored data
          authService.logout();
        }
      },

      // State setters
      setUser: (user) => set({ user }),
      setTokens: (tokens) => set({ tokens }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
    }),
    {
      name: 'auth-store',
    }
  )
);