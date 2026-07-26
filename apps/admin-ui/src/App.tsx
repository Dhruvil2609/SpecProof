import { useTranslation } from 'react-i18next';
import { resolveRoute, routes } from './routes';
import './tokens.css';

export function App() {
  const { t } = useTranslation();
  const currentRoute = resolveRoute(window.location.pathname);

  return (
    <main className="app-shell">
      <h1>{t('app.title')}</h1>
      <nav aria-label={t('navigation.dashboard')}>
        {routes.map((route) => (
          <a key={route.path} href={route.path}>
            {t(route.labelKey)}
          </a>
        ))}
      </nav>
      <section aria-labelledby="route-title">
        <h2 id="route-title">{t(currentRoute.titleKey)}</h2>
      </section>
      <p>{t('admin.ready')}</p>
    </main>
  );
}
