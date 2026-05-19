/**
 * Regression tests for binding label → name transliteration in <BindingRow>
 * (FA-407).
 *
 * Targets the module-private `labelToName(label)` helper at
 * src/features/pricing/ui/formula/BindingRow.jsx:213-229, exercised through
 * the row's label input. Integration via <BindingRow> matches the FA-401
 * anti-pattern-refusal of test-only exports.
 *
 * The hotspot commit `1ccf2f98` introduced this transliteration; tests fixate
 * the existing TRANSLIT mapping and the surrounding UI contract so a future
 * regression is caught at PR-CI.
 *
 * Consciously NOT covered here:
 *   - useProductForm.transliterate (different slice, kebab-case slug, distinct
 *     usage). Possible future ticket: extract both helpers to shared/lib.
 *   - The expression editor inside the row — covered by FA-401.
 *   - Move/remove buttons, component_tag select — out of FA-407 scope.
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { BindingRow } from '../BindingRow';

const COMPONENT_TAGS = [
  'cogs',
  'shipping',
  'commission',
  'tax',
  'margin',
  'final_price',
  'intermediate',
];

function makeBinding(overrides = {}) {
  return {
    name: '',
    label: '',
    component_tag: 'intermediate',
    expr: { const: '0' },
    ...overrides,
  };
}

function renderRow({
  binding = makeBinding(),
  index = 0,
  totalCount = 2,
  isLast = false,
  readOnly = false,
} = {}) {
  const onChange = vi.fn();
  const utils = render(
    <BindingRow
      index={index}
      binding={binding}
      bindings={[binding]}
      variables={[]}
      componentTags={COMPONENT_TAGS}
      isLast={isLast}
      totalCount={totalCount}
      onChange={onChange}
      onRemove={vi.fn()}
      onMoveUp={vi.fn()}
      onMoveDown={vi.fn()}
      readOnly={readOnly}
    />,
  );
  const labelInput = screen.getByPlaceholderText('Название строки');
  return { ...utils, onChange, labelInput };
}

function changeLabel(input, value) {
  fireEvent.change(input, { target: { value } });
}

describe('label → name transliteration (1ccf2f98 hotspot)', () => {
  const goldenPairs = [
    {
      name: 'simple Russian word',
      label: 'Маржа',
      expected: 'marzha',
    },
    {
      name: 'multi-word phrase joined by underscore',
      label: 'Маржа категории',
      expected: 'marzha_kategorii',
    },
    {
      name: 'leading capital ё mapped to "yo"',
      label: 'Ёжик',
      expected: 'yozhik',
    },
    {
      name: 'multi-char letters щ/ё/ч',
      label: 'Щёчки',
      expected: 'shchyochki',
    },
    {
      name: 'pure ASCII passes through unchanged',
      label: 'price_v2',
      expected: 'price_v2',
    },
    {
      name: 'mixed cyrillic and ascii',
      label: 'COGS себестоимость',
      expected: 'cogs_sebestoimost',
    },
    {
      name: 'soft and hard signs are dropped',
      label: 'объявление',
      expected: 'obyavlenie',
    },
    {
      name: 'special characters become _ then collapse',
      label: 'Цена!@# с пробелом',
      expected: 'tsena_s_probelom',
    },
  ];

  it.each(goldenPairs)(
    'transliterates "$label" → "$expected" ($name)',
    ({ label, expected }) => {
      const { labelInput, onChange } = renderRow();
      changeLabel(labelInput, label);
      expect(onChange).toHaveBeenLastCalledWith(
        expect.objectContaining({ label, name: expected }),
      );
    },
  );
});

describe('edge cases (length cap, fallback, empty)', () => {
  it('returns empty name when label is cleared (early-return branch)', () => {
    const { labelInput, onChange } = renderRow({
      binding: makeBinding({ label: 'Маржа', name: 'marzha' }),
    });
    changeLabel(labelInput, '');
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ label: '', name: '' }),
    );
  });

  it('falls back to "binding" when label has no usable characters', () => {
    const { labelInput, onChange } = renderRow();
    changeLabel(labelInput, '!@#');
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ name: 'binding' }),
    );
  });

  it('falls back to "binding" when label is whitespace-only', () => {
    const { labelInput, onChange } = renderRow();
    changeLabel(labelInput, '   ');
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ name: 'binding' }),
    );
  });

  it('caps name length at 64 characters', () => {
    // Each `я` transliterates to "ya" (2 chars); 35 я-letters → 70 chars
    // before the .slice(0, 64) cap.
    const longLabel = 'я'.repeat(35);
    const { labelInput, onChange } = renderRow();
    changeLabel(labelInput, longLabel);
    const callArg = onChange.mock.calls.at(-1)[0];
    expect(callArg.name).toBe('ya'.repeat(32));
    expect(callArg.name.length).toBe(64);
  });

  it('collapses consecutive underscores into one', () => {
    const { labelInput, onChange } = renderRow();
    changeLabel(labelInput, 'a !!! b');
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ name: 'a_b' }),
    );
  });

  it('trims leading and trailing underscores', () => {
    const { labelInput, onChange } = renderRow();
    changeLabel(labelInput, '!hello!');
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ name: 'hello' }),
    );
  });
});

describe('isFinalPrice locking', () => {
  it('disables the label input on the final_price terminator row', () => {
    const { labelInput } = renderRow({
      binding: makeBinding({ name: 'final_price', label: 'Итого' }),
      isLast: true,
      totalCount: 1,
    });
    expect(labelInput).toBeDisabled();
  });

  it('forces name to "final_price" regardless of label changes on the terminator row', () => {
    const { labelInput, onChange } = renderRow({
      binding: makeBinding({ name: 'final_price', label: 'Итого' }),
      isLast: true,
      totalCount: 1,
    });
    fireEvent.change(labelInput, { target: { value: 'Совсем другое' } });
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ name: 'final_price' }),
    );
  });

  it('treats name auto-derivation as normal when isLast is true but name is not final_price', () => {
    const { labelInput, onChange } = renderRow({
      binding: makeBinding({ name: 'subtotal', label: 'Промежуточно' }),
      isLast: true,
      totalCount: 1,
    });
    changeLabel(labelInput, 'Маржа');
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ name: 'marzha' }),
    );
  });
});

describe('UI reflection of derived name', () => {
  it('renders the technical name as a hint when name is set and row is not the terminator', () => {
    renderRow({
      binding: makeBinding({ label: 'Маржа', name: 'marzha' }),
    });
    expect(screen.getByText('marzha')).toBeInTheDocument();
    expect(screen.getByTitle('Техническое имя в формуле')).toBeInTheDocument();
  });

  it('does not render the tech name hint when name is empty', () => {
    renderRow({ binding: makeBinding({ label: '', name: '' }) });
    expect(
      screen.queryByTitle('Техническое имя в формуле'),
    ).not.toBeInTheDocument();
  });

  it('does not render the tech name hint on the final_price terminator row', () => {
    renderRow({
      binding: makeBinding({ name: 'final_price', label: 'Итого' }),
      isLast: true,
      totalCount: 1,
    });
    expect(
      screen.queryByTitle('Техническое имя в формуле'),
    ).not.toBeInTheDocument();
  });
});

describe('read-only mode', () => {
  it('disables the label input when readOnly is true', () => {
    const { labelInput } = renderRow({ readOnly: true });
    expect(labelInput).toBeDisabled();
  });
});

describe('ARIA accessibility (FA-406)', () => {
  it('exposes the label input via aria-label="Название строки"', () => {
    const { labelInput } = renderRow();
    expect(labelInput).toHaveAttribute('aria-label', 'Название строки');
  });

  it('label input is queryable by accessible name (getByRole + name)', () => {
    renderRow();
    expect(
      screen.getByRole('textbox', { name: 'Название строки' }),
    ).toBeInTheDocument();
  });
});
