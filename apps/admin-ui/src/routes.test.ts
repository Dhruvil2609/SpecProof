import { describe, expect, it } from 'vitest';
import { resolveRoute } from './routes';

describe('resolveRoute', () => {
  it('should return settings route for settings path', () => {
    const route = resolveRoute('/settings');

    expect(route.titleKey).toBe('settings.title');
  });

  it('should return dashboard route for unknown path', () => {
    const route = resolveRoute('/missing');

    expect(route.path).toBe('/');
  });
});
