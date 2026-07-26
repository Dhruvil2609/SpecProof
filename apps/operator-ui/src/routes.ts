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
    path: '/capture',
    labelKey: 'navigation.capture',
    titleKey: 'capture.title',
  },
];

export function resolveRoute(pathname: string): AppRoute {
  return routes.find((route) => route.path === pathname) ?? routes[0]!;
}
