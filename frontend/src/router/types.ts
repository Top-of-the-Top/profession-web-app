// router/types.ts
import { type ReactNode } from 'react';


export type AppRoute = {
  /** Для вложенного index-маршрута (например «/app» без хвоста) задайте index: true и не указывайте path */
  path?: string;
  index?: boolean;
  element: ReactNode;
  protected?: boolean;
  publicOnly?: boolean;
  children?: AppRoute[]; // вложенные маршруты
};
