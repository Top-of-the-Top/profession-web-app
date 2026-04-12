import { ErrorBoundary } from 'react-error-boundary';
import { AppRouter } from '@router/index.tsx';
import { SileoHost } from '@shared/lib/sileo/SileoHost';
import { RootErrorFallback } from '@shared/ui';
import './App.module.css';

export default function App() {
  return (
    <ErrorBoundary FallbackComponent={RootErrorFallback}>
      <SileoHost>
        <AppRouter />
      </SileoHost>
    </ErrorBoundary>
  );
}

