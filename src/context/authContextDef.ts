import { createContext } from 'react';
import type { User, RegisterFormData, LoginFormData, AuthApiResponse } from '../types/auth';

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (data: LoginFormData) => Promise<AuthApiResponse>;
  register: (data: RegisterFormData) => Promise<AuthApiResponse>;
  verifyOtp: (identifier: string, otp: string) => Promise<AuthApiResponse>;
  resendOtp: (identifier: string) => Promise<AuthApiResponse>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);
