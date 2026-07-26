export interface AppRoute {
  readonly path: string;
  readonly labelKey: string;
  readonly titleKey: string;
}

export const routes: readonly AppRoute[] = [
  {
    path: '/',
    labelKey: 'navigation.dashboard',
    titleKey: 'dashboard.title',
  },
  {
    path: '/settings',
    labelKey: 'navigation.settings',
    titleKey: 'settings.title',
  },
];

export function resolveRoute(pathname: string): AppRoute {
  return routes.find((route) => route.path === pathname) ?? routes[0]!;
}
