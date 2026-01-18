import { Link } from 'react-router-dom';
import { isAuthenticated } from '../../../shared/auth/isAuthenticated';
import React from 'react';
import styles from './Header.module.css';
import { Button } from '../../../components/ui';

import { useState } from 'react';
import { Infinity } from 'lucide-react';

export default function Header(): React.JSX.Element {
  const loggedIn: boolean = isAuthenticated(); // TODO: вернуть нормальную проверку
  const [logged, setLogged] = useState(false);

  return (
    <header className={styles.header}>
      <div className={styles.title}>
        <img className={styles.logo} src="vite.svg" alt="" />
        <h1 className={styles.titleText}>
					Про
          <Infinity className={styles.inlineIcon} />
          ессия
        </h1>
      </div>
      <button onClick={() => setLogged(!logged)}>Сменить уровень</button>
      {logged ? (
        <div className={`${styles.logged} ${styles.panel}`}>
          <Link to={'/app'}>
            <Button variant="outline">Личный кабинет</Button>
          </Link>
        </div>
      ) : (
        <div className={`${styles.notlogged} ${styles.panel}`}>
          <Link to={'/login'}>
            <Button variant="outline">Войти</Button>
          </Link>
          <Link to={'/registration'}>
            <Button variant="primary">Регистрация</Button>
          </Link>
        </div>
      )}
    </header>
  );
}
