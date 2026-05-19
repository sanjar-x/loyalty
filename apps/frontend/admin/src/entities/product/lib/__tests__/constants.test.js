import { describe, expect, it } from 'vitest';
import {
  PRODUCT_STATUS_LABELS,
  PRODUCT_STATUS_TRANSITIONS,
} from '../constants';

describe('PRODUCT_STATUS_LABELS', () => {
  it('has Russian label for every backend status', () => {
    const expected = [
      'draft',
      'enriching',
      'ready_for_review',
      'published',
      'archived',
    ];
    expected.forEach((s) => {
      expect(PRODUCT_STATUS_LABELS[s]).toBeTruthy();
    });
  });
});

describe('PRODUCT_STATUS_TRANSITIONS', () => {
  it('matches the FSM defined in product-creation-flow.md', () => {
    expect(PRODUCT_STATUS_TRANSITIONS.draft.map((t) => t.target)).toEqual([
      'enriching',
    ]);
    expect(PRODUCT_STATUS_TRANSITIONS.enriching.map((t) => t.target)).toEqual([
      'draft',
      'ready_for_review',
    ]);
    expect(
      PRODUCT_STATUS_TRANSITIONS.ready_for_review.map((t) => t.target),
    ).toEqual(['enriching', 'published']);
    expect(PRODUCT_STATUS_TRANSITIONS.published.map((t) => t.target)).toEqual([
      'archived',
    ]);
    expect(PRODUCT_STATUS_TRANSITIONS.archived.map((t) => t.target)).toEqual([
      'draft',
    ]);
  });

  it('every transition has a Russian label', () => {
    Object.values(PRODUCT_STATUS_TRANSITIONS).forEach((transitions) => {
      transitions.forEach((t) => {
        expect(t.label).toBeTruthy();
        expect(typeof t.label).toBe('string');
      });
    });
  });
});
