import React, { useState, useEffect, useCallback } from 'react';
import type { User, RegisterFormData, LoginFormData, AuthApiResponse } from '../types/auth';
import { AuthService } from '../features/auth/auth.service';
import { AuthContext } from './authContextDef';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await AuthService.getMe();
      setUser(currentUser);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    AuthService.getMe()
      .then((u) => {
        if (isMounted) setUser(u);
      })
      .catch(() => {
        if (isMounted) setUser(null);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (data: LoginFormData): Promise<AuthApiResponse> => {
    const res = await AuthService.login(data);
    if (res.success && res.user) {
      setUser(res.user);
    }
    return res;
  };

  const register = async (data: RegisterFormData): Promise<AuthApiResponse> => {
    return await AuthService.register(data);
  };

  const verifyOtp = async (identifier: string, otp: string): Promise<AuthApiResponse> => {
    const res = await AuthService.verifyOtp(identifier, otp);
    if (res.success && res.user) {
      setUser(res.user);
    }
    return res;
  };

  const resendOtp = async (identifier: string): Promise<AuthApiResponse> => {
    return await AuthService.resendOtp(identifier);
  };

  const logout = async () => {
    try {
      await AuthService.logout();
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        verifyOtp,
        resendOtp,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
