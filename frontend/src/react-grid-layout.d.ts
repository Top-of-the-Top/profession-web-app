declare module 'react-grid-layout' {
  import type { FC, ReactNode } from 'react';

  export interface LayoutItem {
    i: string;
    x: number;
    y: number;
    w: number;
    h: number;
    minW?: number;
    minH?: number;
    maxW?: number;
    maxH?: number;
    static?: boolean;
  }

  export type Layout = LayoutItem[];

  export interface ResponsiveLayout {
    lg?: LayoutItem[];
    md?: LayoutItem[];
    sm?: LayoutItem[];
    xs?: LayoutItem[];
    xxs?: LayoutItem[];
  }

  export interface GridLayoutProps {
    className?: string;
    style?: React.CSSProperties;
    width?: number;
    layouts?: ResponsiveLayout;
    layout?: LayoutItem[];
    breakpoints?: Record<string, number>;
    cols?: Record<string, number> | number;
    rowHeight?: number;
    measureBeforeMount?: boolean;
    useCSSTransforms?: boolean;
    compactType?: 'vertical' | 'horizontal' | null;
    preventCollision?: boolean;
    onLayoutChange?: (layout: Layout, layouts: ResponsiveLayout) => void;
    onBreakpointChange?: (breakpoint: string) => void;
    onDrop?: (layout: Layout, layoutItem: LayoutItem, event: DragEvent) => void;
    isDroppable?: boolean;
    droppingItem?: LayoutItem;
    containerPadding?: [number, number] | number[];
    margin?: [number, number];
    children?: ReactNode;
  }

  /** Non-responsive grid: single layout, fixed cols. Use for consistent export. */
  export interface FixedGridLayoutProps {
    className?: string;
    style?: React.CSSProperties;
    width?: number;
    layout?: LayoutItem[];
    cols?: number;
    rowHeight?: number;
    measureBeforeMount?: boolean;
    useCSSTransforms?: boolean;
    compactType?: 'vertical' | 'horizontal' | null;
    preventCollision?: boolean;
    onLayoutChange?: (layout: Layout) => void;
    onDrop?: (layout: Layout, layoutItem: LayoutItem, event: DragEvent) => void;
    isDroppable?: boolean;
    droppingItem?: LayoutItem;
    containerPadding?: [number, number] | number[];
    margin?: [number, number];
    children?: ReactNode;
  }

  export const Responsive: FC<GridLayoutProps>;
  export const WidthProvider: <P extends object>(
    component: React.ComponentType<P & { width?: number }>
  ) => FC<P>;

  const GridLayoutComponent: FC<FixedGridLayoutProps>;
  export default GridLayoutComponent;
}
