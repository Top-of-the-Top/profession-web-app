import { useCallback } from 'react';
import { sileo, type SileoPosition } from 'sileo';
import { Button } from '@shared/ui';
import { useSileoHost } from '@shared/lib/sileo/SileoHost';
import styles from './ToastPlaygroundPage.module.css';

const POSITIONS: SileoPosition[] = [
  'top-left',
  'top-center',
  'top-right',
  'bottom-left',
  'bottom-center',
  'bottom-right',
];

const SILEO_DOCS = 'https://sileo.aaryan.design/docs/api';

export default function ToastPlaygroundPage() {
  const { config, setConfig } = useSileoHost();

  const baseOpts = useCallback(
    () => ({
      position: config.position,
      duration: config.defaultToastOptions.duration ?? 5000,
      roundness: config.defaultToastOptions.roundness ?? 16,
    }),
    [config.defaultToastOptions.duration, config.defaultToastOptions.roundness, config.position],
  );

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Плейграунд тостов (Sileo)</h1>
      <p className={styles.lead}>
        Ниже — черновая схема, куда какие уведомления логично вешать, и кнопки, чтобы
        перебрать варианты. Один общий{' '}
        <code>Toaster</code> на всё приложение; настройки здесь меняют его же (см.{' '}
        <a className={styles.docLink} href={SILEO_DOCS} target="_blank" rel="noreferrer">
          документацию Sileo
        </a>
        ).
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Схема (черновик)</h2>
        <div className={styles.card}>
          <table className={styles.schemaTable}>
            <tbody>
              <tr>
                <th>Контекст</th>
                <td>
                  <strong>Магазин / корзина</strong> — короткий feedback после действия
                  (успех или отказ), не перекрывает форму целиком.
                </td>
              </tr>
              <tr>
                <th>Типы</th>
                <td>
                  <code>success</code> — «добавлено в корзину»; <code>error</code> — нет
                  доступа, дубликат, сеть; при необходимости <code>warning</code> для
                  мягких ограничений.
                </td>
              </tr>
              <tr>
                <th>Публичные формы</th>
                <td>
                  Сброс и восстановление пароля: <code>error</code> для валидации и ответов
                  API; <code>success</code> — только если не перекрываем уже готовый экран
                  успеха (можно оставить один канал: либо тост, либо карточка).
                </td>
              </tr>
              <tr>
                <th>Единый стиль</th>
                <td>
                  Одна позиция по умолчанию (часто <code>top-right</code> или{' '}
                  <code>top-center</code>); заголовок короткий, детали в description;
                  длительность 4–6 с; скругление и тема — от шапки /app (ниже можно
                  сымитировать отступ под topbar).
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Настройки Toaster (глобально)</h2>
        <div className={styles.card}>
          <div className={styles.controlsGrid}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="tg-position">
                Позиция viewport
              </label>
              <select
                id="tg-position"
                className={styles.select}
                value={config.position}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    position: e.target.value as SileoPosition,
                  }))
                }
              >
                {POSITIONS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="tg-theme">
                Тема
              </label>
              <select
                id="tg-theme"
                className={styles.select}
                value={config.theme}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    theme: e.target.value as typeof c.theme,
                  }))
                }
              >
                <option value="system">system</option>
                <option value="light">light</option>
                <option value="dark">dark</option>
              </select>
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="tg-duration">
                Длительность по умолчанию (мс)
              </label>
              <input
                id="tg-duration"
                type="number"
                min={1000}
                step={500}
                className={styles.numberInput}
                value={config.defaultToastOptions.duration ?? 5000}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    defaultToastOptions: {
                      ...c.defaultToastOptions,
                      duration: Number(e.target.value) || 5000,
                    },
                  }))
                }
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="tg-round">
                Скругление (roundness)
              </label>
              <input
                id="tg-round"
                type="number"
                min={0}
                max={32}
                className={styles.numberInput}
                value={config.defaultToastOptions.roundness ?? 16}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    defaultToastOptions: {
                      ...c.defaultToastOptions,
                      roundness: Number(e.target.value) || 0,
                    },
                  }))
                }
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="tg-inset">
                Отступ от края (px)
              </label>
              <input
                id="tg-inset"
                type="number"
                min={0}
                max={160}
                className={styles.numberInput}
                value={config.edgeInsetPx}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    edgeInsetPx: Number(e.target.value) || 0,
                  }))
                }
              />
              <p className={styles.hint}>
                Для макета /app попробуйте ~88 под высоту шапки (только для top/bottom
                позиций).
              </p>
            </div>
          </div>
          <p className={styles.note}>
            Отдельный тост может переопределить <code>position</code>, <code>duration</code>
            , <code>roundness</code>, <code>fill</code>, <code>styles</code>,{' '}
            <code>autopilot</code> — см. кнопки ниже.
          </p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Базовые варианты API</h2>
        <div className={styles.card}>
          <div className={styles.buttonRow}>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.success({
                  ...baseOpts(),
                  title: 'Успех',
                  description: 'Операция выполнена.',
                })
              }
            >
              success
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.error({
                  ...baseOpts(),
                  title: 'Ошибка',
                  description: 'Что-то пошло не так. Попробуйте ещё раз.',
                })
              }
            >
              error
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.warning({
                  ...baseOpts(),
                  title: 'Внимание',
                  description: 'Проверьте данные перед продолжением.',
                })
              }
            >
              warning
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.info({
                  ...baseOpts(),
                  title: 'Справка',
                  description: 'Подсказка или нейтральное сообщение.',
                })
              }
            >
              info
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.action({
                  ...baseOpts(),
                  title: 'Действие',
                  description: 'Нужен выбор пользователя.',
                  button: {
                    title: 'Открыть',
                    onClick: () => sileo.info({ ...baseOpts(), title: 'Нажато' }),
                  },
                })
              }
            >
              action
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.show({
                  ...baseOpts(),
                  type: 'info',
                  title: 'show()',
                  description: 'Универсальный вызов с type из опций.',
                })
              }
            >
              show (type: info)
            </Button>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Кастом за один клик</h2>
        <div className={styles.card}>
          <div className={styles.buttonRow}>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.success({
                  ...baseOpts(),
                  title: 'Другая позиция',
                  description: 'Этот тост ушёл в bottom-center.',
                  position: 'bottom-center',
                })
              }
            >
              bottom-center
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.success({
                  ...baseOpts(),
                  title: 'Дольше на экране',
                  description: 'duration: 9000',
                  duration: 9000,
                })
              }
            >
              long duration
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.info({
                  ...baseOpts(),
                  title: 'Без автозакрытия',
                  description: 'Смахните или кликните, чтобы закрыть.',
                  duration: null,
                })
              }
            >
              sticky (duration: null)
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.success({
                  ...baseOpts(),
                  title: 'Свой fill',
                  description: 'Цвет заливки SVG (акцент бренда).',
                  fill: '#4f46e5',
                })
              }
            >
              custom fill
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.success({
                  ...baseOpts(),
                  title: 'Плоские углы',
                  description: 'roundness: 4',
                  roundness: 4,
                })
              }
            >
              roundness 4
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.success({
                  ...baseOpts(),
                  title: 'Без autopilot',
                  description: 'Раскрытие только вручную (hover / tap).',
                  autopilot: false,
                })
              }
            >
              autopilot: false
            </Button>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>promise()</h2>
        <div className={styles.card}>
          <div className={styles.buttonRow}>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.promise(
                  () =>
                    new Promise((resolve) =>
                      setTimeout(() => resolve({ ok: true }), 1800),
                    ),
                  {
                    position: config.position,
                    loading: {
                      title: 'Сохраняем',
                      description: 'Ждём ответ сервера…',
                    },
                    success: {
                      title: 'Сохранено',
                      description: 'Изменения применены.',
                    },
                    error: {
                      title: 'Сбой',
                      description: 'Запрос не выполнен.',
                    },
                  },
                )
              }
            >
              promise → success
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.promise(
                  () =>
                    new Promise((_, reject) =>
                      setTimeout(() => reject(new Error('demo')), 1200),
                    ),
                  {
                    position: config.position,
                    loading: {
                      title: 'Отправка',
                      description: 'Почти…',
                    },
                    success: {
                      title: 'Ок',
                      description: 'Не должны увидеть',
                    },
                    error: {
                      title: 'Ошибка запроса',
                      description: 'Имитация отказа сети или сервера.',
                    },
                  },
                )
              }
            >
              promise → error
            </Button>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Пресеты под реальные тексты</h2>
        <div className={styles.card}>
          <div className={styles.presetGrid}>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.success({
                  ...baseOpts(),
                  title: 'В корзине',
                  description: 'Курс «Основы аналитики» добавлен в корзину.',
                })
              }
            >
              Магазин: успех
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.error({
                  ...baseOpts(),
                  title: 'Нужен вход',
                  description: 'Авторизуйтесь, чтобы добавить курс в корзину.',
                })
              }
            >
              Магазин: 401
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.error({
                  ...baseOpts(),
                  title: 'Уже в корзине',
                  description: 'Этот курс уже добавлен.',
                })
              }
            >
              Магазин: дубликат
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.error({
                  ...baseOpts(),
                  title: 'Не удалось добавить',
                  description: 'Попробуйте обновить страницу.',
                })
              }
            >
              Магазин: общая ошибка
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.error({
                  ...baseOpts(),
                  title: 'Проверьте ввод',
                  description: 'Введите корректный email или номер телефона.',
                })
              }
            >
              Сброс: валидация
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.success({
                  ...baseOpts(),
                  title: 'Ссылка отправлена',
                  description:
                    'Ссылка для сброса пароля отправлена на почту или телефон.',
                })
              }
            >
              Сброс: успех
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.error({
                  ...baseOpts(),
                  title: 'Пользователь не найден',
                  description: 'Проверьте email или телефон.',
                })
              }
            >
              Сброс: 404
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.error({
                  ...baseOpts(),
                  title: 'Ссылка недействительна',
                  description: 'Запросите новую ссылку для восстановления.',
                })
              }
            >
              Recover: нет токена
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.error({
                  ...baseOpts(),
                  title: 'Срок ссылки истёк',
                  description: 'Запросите новую ссылку для восстановления пароля.',
                })
              }
            >
              Recover: 403 / 410
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                sileo.error({
                  ...baseOpts(),
                  title: 'Слишком много попыток',
                  description: 'Подождите немного и попробуйте снова.',
                })
              }
            >
              Лимит (429)
            </Button>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Сервис</h2>
        <div className={styles.card}>
          <div className={styles.buttonRow}>
            <Button type="button" variant="secondary" onClick={() => sileo.clear()}>
              clear() — убрать все
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => sileo.clear(config.position)}
            >
              clear(текущая позиция)
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
