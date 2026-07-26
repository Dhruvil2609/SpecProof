import { describe, expect, it } from 'vitest';
import { resolveRoute } from './routes';

describe('resolveRoute', () => {
  it('should return capture route for capture path', () => {
    const route = resolveRoute('/capture');

    expect(route.titleKey).toBe('capture.title');
  });

  it('should return dashboard route for unknown path', () => {
    const route = resolveRoute('/missing');

    expect(route.path).toBe('/');
  });
});
