import { describe, it, expect } from 'vitest';
import { vesselTypeInfo } from '../../app/static/js/utils.js';

describe('vesselTypeInfo', () => {
  it('identifies cargo ships correctly', () => {
    const info = vesselTypeInfo(71);
    expect(info.label).toBe('Cargo');
    expect(info.color).toBe('#4a9eff');
  });

  it('handles unknown or empty types', () => {
    const info = vesselTypeInfo(null);
    expect(info.label).toBe('Unknown');
  });

  it('handles passenger ships correctly', () => {
    const info = vesselTypeInfo(65);
    expect(info.label).toBe('Passenger');
    expect(info.color).toBe('#2ed573');
  });
});
