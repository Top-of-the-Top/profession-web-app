// router/types.ts
import { type ReactNode } from 'react';


export type AppRoute = {
  path: string;
  element: ReactNode;
  protected?: boolean;
  publicOnly?: boolean;
  children?: AppRoute[]; // вложенные маршруты
};
