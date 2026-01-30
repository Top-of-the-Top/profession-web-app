import styles from './LandingPage.module.css';
import { useEffect } from 'react';
import {
  Button,
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '../../../shared/ui';
import { ArrowUpRight } from 'lucide-react';
import CollapsibleSection from './CollapsibleSection';
import Footer from './Footer';


const tracks = [
  {
    id: 'medicine',
    title: 'Медицина',
    price: 3900,
    image: 'landing/il0.png',
    bgColor: '#E5E7EB', // цвет фона карточки
    accentColor: '#191970', // цвет акцента (рамки, кнопок)
    titleColor: '#E5E7EB', // цвет заголовка
    subtitleColor: '#000000',
    arrowColor: '#E5E7EB', // цвет стрелки
    arrowBgColor: '#191A23', // цвет фона стрелки/кружка
		moreColor: '#000000',
  },
  {
    id: 'chemistry',
    title: 'Химия',
    price: 3900,
    image: 'landing/il1.png',
    bgColor: '#191970', // темный фон
    accentColor: '#FFFFFF', // зеленый акцент
    titleColor: '#000000', // белый заголовок
    subtitleColor: '#E5E7EB',
    arrowColor: '#E5E7EB', // темная стрелка
    arrowBgColor: '#191A23', // зеленый фон стрелки
		moreColor: '#E5E7EB',
  },
  {
    id: 'programming',
    title: 'Программирование',
    image: 'landing/il2.png',
    price: 3900,
    bgColor: '#191A23', // светлый желтый фон
    accentColor: '#FFFFFF', // фиолетовый акцент
    titleColor: '#000000', // темный заголовок
    subtitleColor: '#E5E7EB',
    arrowColor: '#000000', // белая стрелка
    arrowBgColor: '#FFFFFF', // фиолетовый фон стрелки
		moreColor: '#ffffff',
  },
  {
    id: 'biology',
    title: 'Биология',
    image: 'landing/il3.png',
    bgColor: '#E5E7EB', // светлый зеленый фон
    price: 3900,
    accentColor: '#191970', // темно-зеленый акцент
    titleColor: '#E5E7EB', // темный заголовок
    subtitleColor: '#000000',
    arrowColor: '#E5E7EB', // белая стрелка
    arrowBgColor: '#191A23', // темно-зеленый фон стрелки
		moreColor: '#000000',
  },
  {
    id: 'creativity',
    title: 'Творчество',
    image: 'landing/il4.png',
    price: 3900,
    bgColor: '#191970', // светлый розовый фон
    accentColor: '#FFFFFF', // розовый акцент
    titleColor: '#000000', // темный заголовок
    subtitleColor: '#E5E7EB',
    arrowColor: '#E5E7EB', // белая стрелка
    arrowBgColor: '#191A23', // розовый фон стрелки
		moreColor: '#E5E7EB',
  },
  {
    id: 'designer',
    title: 'Дизайнер',
    image: 'landing/il5.png',
    price: 3900,
    bgColor: '#191A23', // светлый фиолетовый фон
    accentColor: '#E5E7EB', // фиолетовый акцент
    titleColor: '#000000', // темный заголовок
    subtitleColor: '#E5E7EB',
    arrowColor: '#000000', // белая стрелка
    arrowBgColor: '#ffffff', // фиолетовый фон стрелки
		moreColor: '#ffffff',
  },
];




export default function LandingPage() {

useEffect(() => {
  const links = document.querySelectorAll('nav a[href^="#"]');
  links.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const id = (link as HTMLAnchorElement).getAttribute('href')?.slice(1);
      if (id) {
        const el = document.getElementById(id);
        if (el) {
          const offset = 100;
          const top = el.getBoundingClientRect().top + window.scrollY - offset;
          window.scrollTo({ top, behavior: 'smooth' });
        }
      }
    });
  });
}, []);

  return (
    <div className={styles.page}>
      <header  className={styles.header}>
        <div>
          <div className={styles.logo}>
            <img src="landing/profession-logo.svg" alt="" />
          </div>
        </div>

        <nav className={styles.nav} aria-label="Основная навигация">
          <Button variant="ghost" size="lg" className={styles.navLink} asChild>
            <a href="#intro">О нас</a>
          </Button>
          <Button variant="ghost" size="lg" className={styles.navLink} asChild>
            <a href="#tracks">Направления</a>
          </Button>
          <Button variant="ghost" size="lg" className={styles.navLink} asChild>
            <a href="#ways">Процесс обучения</a>
          </Button>
        </nav>

        <div className={styles.authActions}>
          <Button variant="outline" size="lg">
            Войти
          </Button>
          <Button variant="primary" size="lg">
            Зарегистрироваться
          </Button>
        </div>
      </header>
      <div id='intro' className={styles.container}>
        <main>
          <section className={styles.hero}>
            <div className={styles.heroDescription}>
              <h1 className={styles.heroTitle}>
                Онлайн школа <br />
                <span className={styles.heroHighlight}>Профессия</span>
              </h1>

              <p className={styles.heroText}>
                Погружаем детей и подростков в увлекательный мир профессий.
                Дайте ребёнку шанс найти своё призвание и примерить на себя роль
                врача, биолога, химика или программиста.
              </p>

              <div className={styles.heroCta}>
                <Button size="lg">Присоединиться</Button>
              </div>
            </div>
						<div className={styles.children}>
							
						</div>
          </section>

          <section  className={styles.section} >
            <div className={styles.sectionHeader}>
              <div className={styles.sectionTitleRow}>
                <h2 id="tracks" className={styles.sectionTitle}>Направления</h2>
              </div>
              <p className={styles.sectionDescription}>
                Не бойтесь пробовать себя в разных сферах. Мы собрали программы
                по популярным профессиям, чтобы подростки могли безопасно и
                интересно исследовать мир работы взрослых.
              </p>
            </div>

            <div className={styles.tracksGrid}>
              {tracks.map((track) => (
                <Card
                  key={track.id}
                  className={styles.trackCard}
                  style={{
                    backgroundColor: track.bgColor,
                  }}
                >
                  <CardHeader>
                    <div className={styles.trackHeader}>
                      <CardTitle
                        className={styles.trackTitle}
                        style={{
                          color: track.titleColor,
                          backgroundColor: track.accentColor,
                        }}
                      >
                        {track.title}
                      </CardTitle>
                    </div>
                  </CardHeader>

                  <CardContent>
                    <div
                      className={styles.trackPrice}
                      style={{ color: track.subtitleColor }}
                    >
                      от {track.price} ₽
                    </div>
                  </CardContent>

                  <CardFooter className={styles.trackFooter}>
                    <Button variant='ghost'>
                      <div
                        className={styles.trackButton}
                        style={{
                          backgroundColor: track.arrowBgColor,
                          color: track.arrowColor,
                        }}
                      >
                        <ArrowUpRight size={30} />
                      </div>
											<p style={{color: track.moreColor}}>Подробнее</p>	
                    </Button>
                    <img
                      src={track.image}
                      alt={track.title}
                      className={styles.trackImage}
                    />
                  </CardFooter>
                </Card>
              ))}
            </div>
          </section>
					<section style={{width: '100%', height: '100vh'}} id='ways'><CollapsibleSection /></section>	
					<section><Footer /></section>
        </main>
      </div>
    </div>
  );
}
