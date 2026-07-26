import { describe, expect, it } from 'vitest';
import en from './locales/en/translation.json';

const translationKeyPattern = /^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$/;

describe('i18n English translations', () => {
  it('should use namespaced non-empty translation keys', () => {
    const entries = Object.entries(en);

    expect(entries.length).toBeGreaterThan(0);
    expect(entries.every(([key, value]) => translationKeyPattern.test(key) && value.trim().length > 0)).toBe(true);
  });
});
