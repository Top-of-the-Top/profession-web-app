import styles from './Footer.module.css';

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.content}>
        <div className={styles.header}>
					<img src="profession-logo-white.svg" alt="" />
					<div></div> 
					{/* Для грида */}
					<div className={styles.linkContainer}>
						<a href="#intro">О нас</a>
						<a href="#tracks">Направления</a>
						<a href="#ways">Процесс обучения</a>
					</div>
				</div>
				<div className={styles.contactInfo}>
					<h5>Свяжитесь с нами:</h5>
					 <a href="mailto:abrakadabra@yandex.ru">Почта: profession.ru@yandex.ru</a>
					 <a href="tel:+79999999999">Телефон: +7 (964) 623-90-72</a>
				</div>
      </div>

      <div className={styles.copyright}>
        &copy; 2026 ПРОФЕССИЯ
      </div>
    </footer>
  );
}
