import styles from './LandingPage.module.css';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '../../../shared/ui';
import { Plus, Minus } from 'lucide-react';

const learningProcess = [
  {
    id: '01',
    title: 'Выбор курса',
    description:
      'Изучите каталог профессий. Здесь каждый курс содержит подробное описание, программу и информацию о преподавателе. Ребёнок может выбрать направление, которое ему интересно',
    imagePlaceholder: 'Курсы',
  },
  {
    id: '02',
    title: 'Онлайн-занятия с преподавателем',
    description:
      'Живые интерактивные занятия с опытными преподавателями в формате видеоконференций. Дети могут задавать вопросы и участвовать в обсуждениях в реальном времени.',
    imagePlaceholder: 'Онлайн урок',
  },
  {
    id: '03',
    title: 'Интерактивная онлайн-доска',
    description:
      'Современная цифровая доска для совместной работы, где преподаватель и ученики могут рисовать, писать, решать задачи и визуализировать сложные концепции.',
    imagePlaceholder: 'Доска',
  },
  {
    id: '04',
    title: 'Практические задания',
    description:
      'Реальные проекты и задачи, которые помогают закрепить теорию на практике. Каждое задание приближает к получению профессионального навыка.',
    imagePlaceholder: 'Задания',
  },
  {
    id: '05',
    title: 'Поддержка ИИ-помощника',
    description:
      'Умный помощник доступен 24/7 для ответов на вопросы, проверки заданий и персональных рекомендаций по обучению.',
    imagePlaceholder: 'ИИ Помощник',
  },
  {
    id: '06',
    title: 'Прогресс, доступ к материалам',
    description:
      'Личный кабинет с трекером прогресса, записями всех занятий и библиотекой материалов для повторения в любое время.',
    imagePlaceholder: 'Прогресс',
  },
];

export default function CollapsibleSection() {
  return (
    <section className={styles.learningSection} id="ways">
      <div className={styles.sectionHeader}>
				<div className={styles.sectionTitleRow}>
        <h2 id="tracks" className={styles.sectionTitle}>
          Процесс обучения
        </h2>
      </div>
      <p className={styles.sectionDescription}>
        Учебный процесс - это гибрид живых занятий с преподавателем и
        практических домашних заданий, которые вместе переводят теорию в навык
      </p>
			</div>

      <div className={styles.collapsibleContainer}>
        {learningProcess.map((item) => (
          <Collapsible key={item.id} className={styles.collapsibleItem}>
            <CollapsibleTrigger className={styles.collapsibleTrigger}>
              <div className={styles.collapsibleTriggerContent}>
                <span className={styles.collapsibleNumber}>{item.id}</span>
                <div className={styles.collapsibleTitleWrapper}>
                  <span className={styles.collapsibleTitle}>{item.title}</span>
                </div>
                <div className={styles.plusMinusIconContainer}>
                  <div className={styles.plusMinusIcon}>
                    <div className={styles.plusMinusIconHorizontal}></div>
                    <div className={styles.plusMinusIconVertical}></div>
                  </div>
                </div>
              </div>
            </CollapsibleTrigger>

            <CollapsibleContent className={styles.collapsibleContent}>
              <div className={styles.collapsibleContentWrapper}>
                <div className={styles.collapsibleDescription}>
                  <p>{item.description}</p>
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>
        ))}
      </div>
    </section>
  );
}
