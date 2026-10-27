import type { User, AuthApiResponse, RegisterFormData, LoginFormData } from '../../types/auth';
import { getApiUrl } from '../../lib/apiConfig';

export class AuthService {
  /**
   * Helper to perform fetch requests with cookies and structured error extraction.
   */
  private static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = getApiUrl(endpoint);
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    };

    const config: RequestInit = {
      ...options,
      headers,
      credentials: 'include', // Strictly required for HttpOnly cookie persistence
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const errorMsg = data?.detail || data?.error || `HTTP ${response.status}: ${response.statusText}`;
        throw new Error(errorMsg);
      }

      return data as T;
    } catch (err: any) {
      // In development, if relative proxy failed, try explicit 127.0.0.1:8000
      if (err.message && (err.message.includes('Failed to fetch') || err.message.includes('NetworkError'))) {
        try {
          const directUrl = `http://127.0.0.1:8000${endpoint}`;
          const fallbackRes = await fetch(directUrl, config);
          const fallbackData = await fallbackRes.json().catch(() => null);
          if (fallbackRes.ok) {
            return fallbackData as T;
          }
          throw new Error(fallbackData?.detail || fallbackData?.error || 'Authentication server unreachable.');
        } catch {
          // fall through to throw original error
        }
      }
      throw err;
    }
  }

  /**
   * Registers a new user and triggers email OTP delivery.
   */
  public static async register(payload: RegisterFormData): Promise<AuthApiResponse> {
    return this.request<AuthApiResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Verifies the 6-digit OTP code and establishes an authenticated session.
   */
  public static async verifyOtp(identifier: string, otp: string): Promise<AuthApiResponse> {
    return this.request<AuthApiResponse>('/api/auth/verify-otp', {
      method: 'POST',
      body: JSON.stringify({ identifier, otp }),
    });
  }

  /**
   * Resends a fresh 6-digit OTP code to the registered email.
   */
  public static async resendOtp(identifier: string): Promise<AuthApiResponse> {
    return this.request<AuthApiResponse>('/api/auth/resend-otp', {
      method: 'POST',
      body: JSON.stringify({ identifier }),
    });
  }

  /**
   * Authenticates user via User ID or Email and password.
   */
  public static async login(payload: LoginFormData): Promise<AuthApiResponse> {
    return this.request<AuthApiResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Invalidates active session and removes HttpOnly session cookie.
   */
  public static async logout(): Promise<AuthApiResponse> {
    try {
      return await this.request<AuthApiResponse>('/api/auth/logout', {
        method: 'POST',
      });
    } catch {
      return { success: true, message: 'Logged out.' };
    }
  }

  /**
   * Retrieves authenticated profile using the HttpOnly session cookie.
   * Returns null if unauthenticated.
   */
  public static async getMe(): Promise<User | null> {
    try {
      return await this.request<User>('/api/auth/me', {
        method: 'GET',
      });
    } catch {
      return null;
    }
  }
}
