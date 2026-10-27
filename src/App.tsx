import React from 'react';
import { RouterProvider } from './lib/router';
import { useRouter } from './lib/useRouter';
import { AuthProvider } from './context/AuthContext';
import { LandingPage } from './pages/LandingPage';
import { ScanPage } from './pages/ScanPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { VerifyOtpPage } from './pages/VerifyOtpPage';

const AppContent: React.FC = () => {
  const { currentPath } = useRouter();

  if (currentPath === '/scan') {
    return <ScanPage />;
  }

  if (currentPath === '/login') {
    return <LoginPage />;
  }

  if (currentPath === '/register') {
    return <RegisterPage />;
  }

  if (currentPath === '/verify-otp') {
    return <VerifyOtpPage />;
  }

  return <LandingPage />;
};

export const App: React.FC = () => {
  return (
    <RouterProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </RouterProvider>
  );
};

export default App;
