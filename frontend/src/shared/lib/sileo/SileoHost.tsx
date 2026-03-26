import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { Toaster, type SileoOptions, type SileoPosition } from 'sileo';

export type SileoHostTheme = 'light' | 'dark' | 'system';

export type SileoHostConfig = {
  position: SileoPosition;
  theme: SileoHostTheme;
  edgeInsetPx: number;
  defaultToastOptions: Partial<SileoOptions>;
};


const toasterBaseOptions: Partial<SileoOptions> = {
  fill: '#f1f1f1',
  roundness: 16,
};

const defaultConfig: SileoHostConfig = {
  position: 'bottom-right',
  theme: 'system',
  edgeInsetPx: 12,
  defaultToastOptions: {
    duration: 5000,
    roundness: 16,
  },
};

type SileoHostContextValue = {
  config: SileoHostConfig;
  setConfig: React.Dispatch<React.SetStateAction<SileoHostConfig>>;
};

const SileoHostContext = createContext<SileoHostContextValue | null>(null);

export function useSileoHost() {
  const ctx = useContext(SileoHostContext);
  if (!ctx) {
    throw new Error('useSileoHost must be used within SileoHost');
  }
  return ctx;
}

function offsetForPosition(
  position: SileoPosition,
  px: number,
): { top?: number; bottom?: number } | undefined {
  if (position.startsWith('top')) return { top: px };
  if (position.startsWith('bottom')) return { bottom: px };
  return undefined;
}

export function SileoHost({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<SileoHostConfig>(() => ({
    ...defaultConfig,
    defaultToastOptions: { ...defaultConfig.defaultToastOptions },
  }));

  const offset = useMemo(
    () => offsetForPosition(config.position, config.edgeInsetPx),
    [config.position, config.edgeInsetPx],
  );

  const value = useMemo(() => ({ config, setConfig }), [config]);

  const toasterOptions = useMemo(
    () => ({
      ...toasterBaseOptions,
      ...config.defaultToastOptions,
      styles: {
        ...toasterBaseOptions.styles,
        ...config.defaultToastOptions.styles,
      },
    }),
    [config.defaultToastOptions],
  );

  return (
    <SileoHostContext.Provider value={value}>
      {children}
      <Toaster
        position={config.position}
        theme={config.theme}
        offset={offset}
        options={toasterOptions}
      />
    </SileoHostContext.Provider>
  );
}
