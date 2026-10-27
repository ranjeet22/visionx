import React, { useState, useEffect } from 'react';
import { RouterContext } from './routerContext';

export const RouterProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const getPath = () => {
    if (typeof window === 'undefined') return '/';
    const path = window.location.pathname;
    const hash = window.location.hash;

    // Check pathname first
    const knownPaths = ['/scan', '/login', '/register', '/verify-otp'];
    for (const p of knownPaths) {
      if (path === p || path.startsWith(p + '/')) {
        return p;
      }
    }

    // Check hash for SPA fallback
    for (const p of knownPaths) {
      const cleanHash = hash.replace(/^#\/?/, '/');
      if (cleanHash === p || cleanHash.startsWith(p + '/')) {
        return p;
      }
    }

    return '/';
  };

  const [currentPath, setCurrentPath] = useState<string>(getPath);
  const [routeState, setRouteState] = useState<any>(null);

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(getPath());
      if (typeof window !== 'undefined' && window.history.state && window.history.state.routeState !== undefined) {
        setRouteState(window.history.state.routeState);
      }
    };

    window.addEventListener('popstate', handlePopState);
    window.addEventListener('hashchange', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('hashchange', handlePopState);
    };
  }, []);

  const navigate = (to: string, state?: any) => {
    if (typeof window !== 'undefined') {
      const cleanTo = to.split('?')[0];
      window.history.pushState({ routeState: state }, '', to);
      setCurrentPath(cleanTo);
      setRouteState(state || null);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  return (
    <RouterContext.Provider value={{ currentPath, routeState, navigate }}>
      {children}
    </RouterContext.Provider>
  );
};
