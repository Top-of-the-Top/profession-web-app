import { useEffect } from 'react';
import { AppRouter } from '../router';
import './App.module.css';
import { useUserStore } from '../entities/user/model/userStore';

export default function App() {
  const fetchUser = useUserStore((state) => state.fetchUser);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  return <AppRouter />;
}

