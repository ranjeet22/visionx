import { createContext } from 'react';

export interface RouterContextType {
  currentPath: string;
  routeState?: any;
  navigate: (to: string, state?: any) => void;
}

export const RouterContext = createContext<RouterContextType>({
  currentPath: '/',
  routeState: null,
  navigate: () => {},
});
