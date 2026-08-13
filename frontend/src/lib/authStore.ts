'use client';
import { create } from 'zustand';
import { User, UserRole } from '@/types';

interface AuthState {
  user: User | null;
  token: string | null;
  hydrated: boolean;
  setAuth: (user: User, token: string) => void;
  updateUser: (user: User) => void;
  loginAsRole: (role: UserRole) => void;
  clearAuth: () => void;
  logout: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  hydrated: false,

  setAuth: (user, token) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
    }
    set({ user, token, hydrated: true });
  },

  updateUser: (user) => {
    if (typeof window !== 'undefined') localStorage.setItem('user', JSON.stringify(user));
    set((state) => ({ user, token: state.token, hydrated: true }));
  },

  loginAsRole: (role) => {
    set((state) => {
      if (!state.user) return state;
      const user: User = {
        ...state.user,
        role,
        full_name: role === 'employee' ? 'Nguyễn Minh Anh' : role === 'technician' ? 'Lê Minh Công' : role === 'manager' ? 'Phạm Thị Dung' : 'Trần Gia Huy',
      };
      if (typeof window !== 'undefined') localStorage.setItem('user', JSON.stringify(user));
      return { user, token: state.token ?? `demo-${role}`, hydrated: true };
    });
  },

  clearAuth: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
    set({ user: null, token: null, hydrated: true });
  },

  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
    set({ user: null, token: null, hydrated: true });
    window.location.href = '/login';
  },

  hydrate: () => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token');
      const userStr = localStorage.getItem('user');
      if (token && userStr) {
        try {
          const user = JSON.parse(userStr) as User;
          set({ user, token, hydrated: true });
        } catch {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          set({ user: null, token: null, hydrated: true });
        }
      } else {
        set({ user: null, token: null, hydrated: true });
      }
    }
  },
}));
