import { AppRouter } from '../router';
import { SileoHost } from '../shared/lib/sileo/SileoHost';
import './App.module.css';

export default function App() {
  return (
    <SileoHost>
      <AppRouter />
    </SileoHost>
  );
}

