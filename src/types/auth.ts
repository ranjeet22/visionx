export interface User {
  id: number;
  user_id: string;
  email: string;
  is_verified: boolean;
  created_at?: string;
  last_login_at?: string;
}

export interface AuthApiResponse {
  success: boolean;
  message?: string;
  error?: string;
  user?: User;
  requires_verification?: boolean;
  masked_email?: string;
  cooldown_seconds?: number;
  email_delivery?: {
    success: boolean;
    info: string;
    dev_otp?: string | null;
    smtp_configured?: boolean;
  };
}

export interface RegisterFormData {
  user_id: string;
  email: string;
  password: string;
  confirm_password: string;
}

export interface LoginFormData {
  identifier: string;
  password: string;
}

export interface VerifyOtpFormData {
  identifier: string;
  otp: string;
}
