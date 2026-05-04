import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import "../globals.css"
import "../sileo-tokens.css"
import './index.css'
import App from './app/App.tsx'
import { queryClient } from '@shared/api/queryClient';
import { applySiteFavicon } from '@shared/lib/siteFavicon';

applySiteFavicon();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
      {/* <ReactQueryDevtools position='left' initialIsOpen={false} /> */}
    </QueryClientProvider>
  </StrictMode>
);
