import { create } from 'zustand';

interface AuthState {
  // Simplified auth for MVP/Admin
  userRole: 'admin' | 'student' | null;
  studentId: string | null;
  setRole: (role: 'admin' | 'student' | null) => void;
  setStudentId: (id: string | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  userRole: 'admin', // Default to admin for the dashboard
  studentId: null,
  setRole: (role) => set({ userRole: role }),
  setStudentId: (id) => set({ studentId: id }),
  logout: () => set({ userRole: null, studentId: null }),
}));
