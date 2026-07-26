import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { App } from './App';
import './i18n';

describe('App', () => {
  it('should render translated operator title', () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: 'SpecProof Operator' })).toBeDefined();
    expect(screen.getByRole('heading', { name: 'Operator Dashboard' })).toBeDefined();
  });
});
