import styles from './LandingPage.module.css';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn } from '../../../shared/lib/utils';
import { Menu, X } from 'lucide-react';
import { Button, Card, CardTitle, Spinner } from '../../../shared/ui';
import { ArrowUpRight } from 'lucide-react';
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '../../../shared/ui/Pagination';
import CollapsibleSection from './CollapsibleSection';
import Footer from './Footer';
import { useLandingCourses } from '../../../shared/api/queries/landing';

export default function LandingPage() {
  const navigate = useNavigate();

  const { data: landingData, isLoading: loading } = useLandingCourses();
  const tracks = landingData?.data ?? [];

  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 6;

  const toggleMenu = () => setIsMenuOpen((prev) => !prev);

  const totalPages = Math.ceil(tracks.length / PAGE_SIZE);
  const pagedTracks = tracks.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE,
  );

  useEffect(() => {
    if (totalPages > 0 && currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const visiblePageNumbers = (() => {
    if (totalPages <= 1) return [];
    if (totalPages <= 5) return Array.from({ length: totalPages }, (_, i) => i + 1);

    const left = currentPage - 1;
    const right = currentPage + 1;

    const result: Array<number | 'ellipsis'> = [1];

    if (left > 2) result.push('ellipsis');

    for (let p = left; p <= right; p += 1) {
      if (p > 1 && p < totalPages) result.push(p);
    }

    if (right < totalPages - 1) result.push('ellipsis');

    result.push(totalPages);
    return result;
  })();

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // Скролл по якорям
  useEffect(() => {
    const links = document.querySelectorAll('a[href^="#"]');
    links.forEach((link) => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const id = (link as HTMLAnchorElement).getAttribute('href')?.slice(1);
        if (id) {
          const el = document.getElementById(id);
          if (el) {
            const offset = 100;
            const top =
              el.getBoundingClientRect().top + window.scrollY - offset;
            window.scrollTo({ top, behavior: 'smooth' });
          }
        }
      });
    });
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerWrapper}>
          <div>
            <div className={styles.logo}>
              <img src="profession-logo-blue.svg" alt="" />
            </div>
          </div>

          <nav className={styles.nav} aria-label="Основная навигация">
            <Button
              variant="ghost"
              size="lg"
              className={styles.navLink}
              asChild
            >
              <a href="#intro">О нас</a>
            </Button>
            <Button
              variant="ghost"
              size="lg"
              className={styles.navLink}
              asChild
            >
              <a href="#tracks">Направления</a>
            </Button>
            <Button
              variant="ghost"
              size="lg"
              className={styles.navLink}
              asChild
            >
              <a href="#ways">Процесс обучения</a>
            </Button>
          </nav>

          <div className={styles.desktopAuth}>
            <Button
              onClick={() => navigate('/login')}
              variant="outline"
              size="lg"
            >
              Войти
            </Button>
            <Button
              onClick={() => navigate('/register')}
              variant="primary"
              size="lg"
            >
              Регистрация
            </Button>
          </div>
        </div>

        <button
          className={styles.burgerButton}
          onClick={toggleMenu}
          data-open={isMenuOpen}
        >
          {isMenuOpen ? (
            <X width="35px" height="35px" />
          ) : (
            <Menu width="35px" height="35px" />
          )}
        </button>
      </header>
      <div
        className={cn(styles.menuBackground, isMenuOpen && styles.bgOpen)}
        onClick={toggleMenu}
      />
      <div className={`${styles.mobileMenu} ${isMenuOpen ? styles.open : ''}`}>
        <nav className={styles.mobileNav} aria-label="Мобильная навигация">
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
        <div className={styles.mobileAuth}>
          <Button
            onClick={() => navigate('/login')}
            variant="outline"
            size="lg"
          >
            Войти
          </Button>
          <Button
            onClick={() => navigate('/register')}
            variant="primary"
            size="lg"
          >
            Регистрация
          </Button>
        </div>
      </div>
      <div className={styles.container}>
        <main>
          <section className={styles.hero} id="intro">
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
                <Button
                  onClick={() => navigate('/register')}
                  asChild
                  size="lg"
                  className={styles.buttonInline}
                >
                  <p>Присоединиться</p>
                </Button>
              </div>
            </div>
            {/* <div className={styles.children}></div> */}
          </section>

          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionTitleRow}>
                <h2 id="tracks" className={styles.sectionTitle}>
                  Направления
                </h2>
              </div>
              <p className={styles.sectionDescription}>
                Не бойтесь пробовать себя в разных сферах. Мы собрали программы
                по популярным профессиям, чтобы подростки могли безопасно и
                интересно исследовать мир работы взрослых.
              </p>
            </div>

            <div className={styles.tracksGrid}>
              {loading ? (
                <Spinner />
              ) : (
                pagedTracks.map((track) => (
                  <Card
                    key={track.id}
                    className={styles.trackCard}
                    style={{ backgroundColor: track.bgColor }}
                    onClick={() => navigate('/register')}
                  >
                    <div className={styles.trackCardLayout}>
                      <div className={styles.trackCardLeft}>
                        <div className={styles.trackCardTop}>
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
                          <div
                            className={styles.trackPrice}
                            style={{ color: track.subtitleColor }}
                          >
                            от {track.price} ₽
                          </div>
                        </div>
                        <div className={styles.trackCardActions}>
                          <Button
                            style={{ backgroundColor: 'transparent' }}
                            className={styles.moreButton}
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate('/register');
                            }}
                          >
                            <div
                              className={styles.trackButton}
                              style={{
                                backgroundColor: track.arrowBgColor,
                                color: track.arrowColor,
                              }}
                            >
                              <ArrowUpRight size={30} />
                            </div>
                            <p style={{ color: track.moreColor }}>Подробнее</p>
                          </Button>
                        </div>
                      </div>
                      <div className={styles.trackImageCol}>
                        <img
                          src={track.image}
                          alt={track.title}
                          className={styles.trackImage}
                        />
                      </div>
                    </div>
                  </Card>
                ))
              )}
            </div>

            {!loading && totalPages > 1 && (
              <Pagination className={styles.tracksPagination}>
                <PaginationContent>
                  <PaginationPrevious
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      if (currentPage <= 1) return;
                      handlePageChange(currentPage - 1);
                    }}
                  />

                  {visiblePageNumbers.map((item, idx) => {
                    if (item === 'ellipsis') {
                      return (
                        <PaginationItem key={`ellipsis-${idx}`}>
                          <PaginationEllipsis />
                        </PaginationItem>
                      );
                    }

                    return (
                      <PaginationItem key={item}>
                        <PaginationLink
                          href="#"
                          isActive={item === currentPage}
                          onClick={(e) => {
                            e.preventDefault();
                            handlePageChange(item);
                          }}
                        >
                          {item}
                        </PaginationLink>
                      </PaginationItem>
                    );
                  })}

                  <PaginationNext
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      if (currentPage >= totalPages) return;
                      handlePageChange(currentPage + 1);
                    }}
                  />
                </PaginationContent>
              </Pagination>
            )}
          </section>

          <section className={styles.section} id="ways">
            <CollapsibleSection />
          </section>
        </main>
      </div>

      <Footer />
    </div>
  );
}
