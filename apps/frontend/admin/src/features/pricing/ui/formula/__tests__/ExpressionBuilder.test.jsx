/**
 * Regression tests for the formula expression builder (FA-401).
 *
 * Targets the display↔AST round-trip that has accumulated 6+ hot-fix commits
 * (d0e49e3 / ad73081a / 6376aa33 / 93eefe54 / bcb24ac9 / 1ccf2f98) — see PR
 * description for the full hotspot map.
 *
 * Consciously NOT covered here (document so future archaeologists know):
 *   - bcb24ac9 auto-expand textarea: jsdom reports scrollHeight = 0 so the
 *     height calculation cannot be exercised. e2e-only.
 *   - 1ccf2f98 ru→latin transliteration of variable codes: that logic lives
 *     in the binding/variable creation flow (separate slice). Tracked as
 *     FA-407.
 *   - Full a11y coverage (ARIA roles, aria-expanded, aria-activedescendant):
 *     the component has no ARIA today. Tests here only fixate existing
 *     keyboard behavior (Escape, Tab) so a future a11y pass (FA-406) has a
 *     known starting point.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ExpressionBuilder } from '../ExpressionBuilder';

const variables = [
  {
    code: 'purchase_price_cny',
    name: { ru: 'Закупочная цена (CNY)', en: 'Purchase price (CNY)' },
    unit: 'CNY',
    scope: 'product_input',
  },
  {
    code: 'rate_cny_rub',
    name: { ru: 'Курс CNY/RUB', en: 'CNY/RUB rate' },
    unit: 'RUB/CNY',
    scope: 'global',
  },
  {
    code: 'margin_pct',
    name: { en: 'Margin %' },
    unit: '%',
    scope: 'category',
  },
  {
    code: 'cost_only',
    name: {},
    unit: '$',
    scope: 'global',
  },
];

const bindings = [
  {
    name: 'gross_margin',
    label: 'Валовая маржа',
    component_tag: 'margin',
    expr: { const: '0' },
  },
  {
    name: 'subtotal',
    label: '',
    component_tag: 'intermediate',
    expr: { const: '0' },
  },
];

function renderBuilder({
  expr = null,
  vars = variables,
  binds = [],
  currentIndex = 0,
  readOnly = false,
} = {}) {
  const onChange = vi.fn();
  const utils = render(
    <ExpressionBuilder
      expr={expr}
      onChange={onChange}
      variables={vars}
      bindings={binds}
      currentIndex={currentIndex}
      readOnly={readOnly}
    />,
  );
  // FA-406: textarea has explicit role="combobox" per WAI-ARIA APG editable-
  // combobox pattern. Native textbox role is overridden — query reflects the
  // new ARIA contract. Behavior assertions throughout this file are unchanged.
  const textarea = utils.getByRole('combobox');
  return { ...utils, onChange, textarea };
}

function typeFast(textarea, value) {
  fireEvent.change(textarea, { target: { value } });
}

describe('initial render (AST → display)', () => {
  it('renders a single var as its ru display name', () => {
    const { textarea } = renderBuilder({ expr: { var: 'purchase_price_cny' } });
    expect(textarea.value).toBe('Закупочная цена (CNY)');
  });

  it('renders a binary op as "left OP right"', () => {
    const { textarea } = renderBuilder({
      expr: {
        op: '*',
        args: [{ var: 'purchase_price_cny' }, { var: 'rate_cny_rub' }],
      },
    });
    expect(textarea.value).toBe('Закупочная цена (CNY) * Курс CNY/RUB');
  });

  it('renders a constant as its raw string value', () => {
    const { textarea } = renderBuilder({ expr: { const: '100' } });
    expect(textarea.value).toBe('100');
  });

  it('renders empty for null expr', () => {
    const { textarea } = renderBuilder({ expr: null });
    expect(textarea.value).toBe('');
  });

  it('falls back to en when ru is missing', () => {
    const { textarea } = renderBuilder({ expr: { var: 'margin_pct' } });
    expect(textarea.value).toBe('Margin %');
  });

  it('falls back to bare code when both ru and en are missing', () => {
    const { textarea } = renderBuilder({ expr: { var: 'cost_only' } });
    expect(textarea.value).toBe('cost_only');
  });
});

describe('greedy display tokenizer (d0e49e3 hotspot)', () => {
  it('matches a multi-word display name with parentheses as a single var token', () => {
    const { textarea, onChange } = renderBuilder({ expr: null });
    typeFast(textarea, 'Закупочная цена (CNY)');
    expect(onChange).toHaveBeenLastCalledWith({ var: 'purchase_price_cny' });
  });

  it('does not invoke onChange while a name is half-typed (refuses partial parse)', () => {
    const { textarea, onChange } = renderBuilder({ expr: null });
    onChange.mockClear();
    typeFast(textarea, 'Закупочн');
    expect(onChange).not.toHaveBeenCalled();
  });

  it('does not leak a Cyrillic word fragment into the AST when input is unresolved', () => {
    const { textarea, onChange } = renderBuilder({ expr: null });
    onChange.mockClear();
    typeFast(textarea, 'Закупочная');
    for (const call of onChange.mock.calls) {
      const arg = call[0];
      expect(arg).not.toMatchObject({ var: 'Закупочная' });
    }
  });
});

describe('round-trip identity (display ↔ AST ↔ display)', () => {
  const goldenPairs = [
    {
      name: 'constant',
      display: '100',
      ast: { const: '100' },
    },
    {
      name: 'single var (code-only fallback display)',
      display: 'cost_only',
      ast: { var: 'cost_only' },
    },
    {
      name: 'var with parens in display name (d0e49e3 critical)',
      display: 'Закупочная цена (CNY)',
      ast: { var: 'purchase_price_cny' },
    },
    {
      name: 'multi-var arithmetic with precedence',
      display: 'Закупочная цена (CNY) + Курс CNY/RUB * 2',
      ast: {
        op: '+',
        args: [
          { var: 'purchase_price_cny' },
          {
            op: '*',
            args: [{ var: 'rate_cny_rub' }, { const: '2' }],
          },
        ],
      },
    },
    {
      name: 'reference to a prior binding (label as display)',
      display: 'Валовая маржа',
      ast: { ref: 'gross_margin' },
      binds: bindings,
      currentIndex: 2,
    },
    {
      name: 'function call with two constant args',
      display: 'min(12, 15)',
      ast: {
        fn: 'min',
        args: [{ const: '12' }, { const: '15' }],
      },
    },
    {
      name: 'reference + variable mix',
      display: 'Валовая маржа * Курс CNY/RUB',
      ast: {
        op: '*',
        args: [{ ref: 'gross_margin' }, { var: 'rate_cny_rub' }],
      },
      binds: bindings,
      currentIndex: 2,
    },
    {
      name: 'nested function with multi-word var inside',
      display: 'min(Закупочная цена (CNY), max(10, 20))',
      ast: {
        fn: 'min',
        args: [
          { var: 'purchase_price_cny' },
          { fn: 'max', args: [{ const: '10' }, { const: '20' }] },
        ],
      },
    },
  ];

  it.each(goldenPairs)(
    'forward: typing "$display" → expected AST ($name)',
    ({ display, ast, binds = [], currentIndex = 0 }) => {
      const { textarea, onChange } = renderBuilder({
        expr: null,
        binds,
        currentIndex,
      });
      typeFast(textarea, display);
      expect(onChange).toHaveBeenLastCalledWith(ast);
    },
  );

  it.each(goldenPairs)(
    'reverse: rendering with AST shows "$display" ($name)',
    ({ display, ast, binds = [], currentIndex = 0 }) => {
      const { textarea } = renderBuilder({
        expr: ast,
        binds,
        currentIndex,
      });
      expect(textarea.value).toBe(display);
    },
  );
});

describe('numeric and whitespace parsing', () => {
  it('returns {const: "0"} when the textarea is cleared', () => {
    const { textarea, onChange } = renderBuilder({
      expr: { var: 'purchase_price_cny' },
    });
    typeFast(textarea, '');
    expect(onChange).toHaveBeenLastCalledWith({ const: '0' });
  });

  it('normalizes whitespace-only input to {const: "0"}', () => {
    const { textarea, onChange } = renderBuilder({ expr: null });
    typeFast(textarea, '   ');
    expect(onChange).toHaveBeenLastCalledWith({ const: '0' });
  });

  it('respects operator precedence (* before +)', () => {
    const { textarea, onChange } = renderBuilder({ expr: null });
    typeFast(textarea, '12 + 3 * 4');
    expect(onChange).toHaveBeenLastCalledWith({
      op: '+',
      args: [
        { const: '12' },
        { op: '*', args: [{ const: '3' }, { const: '4' }] },
      ],
    });
  });

  it('parses decimal constants', () => {
    const { textarea, onChange } = renderBuilder({ expr: null });
    typeFast(textarea, '3.14');
    expect(onChange).toHaveBeenLastCalledWith({ const: '3.14' });
  });
});

describe('function calls', () => {
  it('parses a known function with two args', () => {
    const { textarea, onChange } = renderBuilder({ expr: null });
    typeFast(textarea, 'min(12, 15)');
    expect(onChange).toHaveBeenLastCalledWith({
      fn: 'min',
      args: [{ const: '12' }, { const: '15' }],
    });
  });

  it('refuses to parse an unknown identifier as a function call', () => {
    const { textarea, onChange } = renderBuilder({ expr: null });
    onChange.mockClear();
    typeFast(textarea, 'unknownFn(1, 2)');
    expect(onChange).not.toHaveBeenCalled();
  });
});

describe('references and currentIndex gating', () => {
  it('renders {ref: name} as the binding label when label is set', () => {
    const { textarea } = renderBuilder({
      expr: { ref: 'gross_margin' },
      binds: bindings,
      currentIndex: 2,
    });
    expect(textarea.value).toBe('Валовая маржа');
  });

  it('falls back to the binding name when label is empty', () => {
    const { textarea } = renderBuilder({
      expr: { ref: 'subtotal' },
      binds: bindings,
      currentIndex: 2,
    });
    expect(textarea.value).toBe('subtotal');
  });

  it('does not expose bindings at or beyond currentIndex (renders ref as raw code)', () => {
    const { textarea } = renderBuilder({
      expr: { ref: 'gross_margin' },
      binds: bindings,
      currentIndex: 0,
    });
    expect(textarea.value).toBe('gross_margin');
  });
});

describe('@-mention suggestions', () => {
  it('opens the suggestion popup when @ is typed at the caret', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@');
    expect(screen.getByText('Закупочная цена (CNY)')).toBeInTheDocument();
    expect(screen.getByText('Курс CNY/RUB')).toBeInTheDocument();
  });

  it('filters suggestions by a Russian display fragment', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@Закуп');
    expect(screen.getByText('Закупочная цена (CNY)')).toBeInTheDocument();
    expect(screen.queryByText('Курс CNY/RUB')).not.toBeInTheDocument();
  });

  it('hides suggestions on Escape', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@');
    expect(screen.getByText('Закупочная цена (CNY)')).toBeInTheDocument();
    await user.keyboard('{Escape}');
    expect(screen.queryByText('Закупочная цена (CNY)')).not.toBeInTheDocument();
  });
});

describe('caret position after suggestion insert (ad73081a hotspot)', () => {
  it('places the caret one character past the inserted display (after the trailing space)', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@Закуп');
    await user.keyboard('{Tab}');

    await waitFor(() => {
      const expected = 'Закупочная цена (CNY) ';
      expect(textarea.value).toBe(expected);
      expect(textarea.selectionStart).toBe(expected.length);
      expect(textarea.selectionEnd).toBe(expected.length);
    });
  });
});

describe('initial "0" focus selection (6376aa33 hotspot)', () => {
  it('selects the entire value on focus when initial text is "0"', () => {
    const { textarea } = renderBuilder({ expr: { const: '0' } });
    fireEvent.focus(textarea);
    expect(textarea.selectionStart).toBe(0);
    expect(textarea.selectionEnd).toBe(1);
  });

  it('does not auto-select on focus when initial text is non-zero', () => {
    const { textarea } = renderBuilder({ expr: { const: '42' } });
    fireEvent.focus(textarea);
    expect(textarea.selectionStart).toBe(textarea.selectionEnd);
  });
});

describe('read-only mode', () => {
  it('disables the textarea when readOnly is true', () => {
    const { textarea } = renderBuilder({
      expr: { const: '0' },
      readOnly: true,
    });
    expect(textarea).toBeDisabled();
  });
});

describe('recognized chip strip', () => {
  it('renders a chip with the variable code after a successful parse', () => {
    const { textarea } = renderBuilder({ expr: null });
    typeFast(textarea, 'Закупочная цена (CNY)');
    expect(screen.getByText('purchase_price_cny')).toBeInTheDocument();
  });
});

describe('ARIA combobox layer (FA-406)', () => {
  it('exposes the textarea as role="combobox" with haspopup/autocomplete/controls metadata', () => {
    const { textarea } = renderBuilder({ expr: null });
    expect(textarea).toHaveAttribute('role', 'combobox');
    expect(textarea).toHaveAttribute('aria-haspopup', 'listbox');
    expect(textarea).toHaveAttribute('aria-autocomplete', 'list');
    expect(textarea).toHaveAttribute('aria-controls');
  });

  it('toggles aria-expanded with the suggestion popup', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    expect(textarea).toHaveAttribute('aria-expanded', 'false');

    await user.click(textarea);
    await user.keyboard('@');
    expect(textarea).toHaveAttribute('aria-expanded', 'true');

    await user.keyboard('{Escape}');
    expect(textarea).toHaveAttribute('aria-expanded', 'false');
  });

  it('renders the suggestion popup as role="listbox" with the id referenced by aria-controls', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@');

    const listbox = screen.getByRole('listbox');
    expect(listbox).toBeInTheDocument();
    expect(listbox.id).toBe(textarea.getAttribute('aria-controls'));
  });

  it('exposes each suggestion as role="option"', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@');

    const options = screen.getAllByRole('option');
    expect(options.length).toBeGreaterThan(0);
    expect(options[0]).toHaveTextContent('Закупочная цена (CNY)');
  });
});

describe('ARIA active-descendant + arrow nav (FA-406d)', () => {
  // Per WAI-ARIA APG editable-combobox pattern:
  //   - No active option on popup open (typing @-mention).
  //   - Down/Up arrows activate; wrap at boundaries.
  //   - Enter accepts ONLY when an option is active; otherwise pass-through.
  //   - Tab inserts active option if any, otherwise first (preserves the
  //     FA-401 power-user shortcut).
  //   - Escape closes popup AND clears active state.
  //   - aria-activedescendant on combobox tracks the active option's id.

  it('has no aria-activedescendant on popup open until the user navigates', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@');

    expect(textarea).not.toHaveAttribute('aria-activedescendant');
    const options = screen.getAllByRole('option');
    options.forEach((opt) =>
      expect(opt).toHaveAttribute('aria-selected', 'false'),
    );
  });

  it('ArrowDown activates the first option (aria-activedescendant + aria-selected)', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@');
    await user.keyboard('{ArrowDown}');

    const options = screen.getAllByRole('option');
    expect(textarea.getAttribute('aria-activedescendant')).toBe(options[0].id);
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
    options
      .slice(1)
      .forEach((opt) => expect(opt).toHaveAttribute('aria-selected', 'false'));
  });

  it('ArrowDown twice advances to the second option', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@');
    await user.keyboard('{ArrowDown}{ArrowDown}');

    const options = screen.getAllByRole('option');
    expect(textarea.getAttribute('aria-activedescendant')).toBe(options[1].id);
    expect(options[1]).toHaveAttribute('aria-selected', 'true');
  });

  it('ArrowUp from no-active wraps to the last option', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@');
    await user.keyboard('{ArrowUp}');

    const options = screen.getAllByRole('option');
    const last = options[options.length - 1];
    expect(textarea.getAttribute('aria-activedescendant')).toBe(last.id);
    expect(last).toHaveAttribute('aria-selected', 'true');
  });

  it('wraps Down at last → first', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@');
    // Use ArrowUp from null to land directly on the last option (wraps per
    // APG), then a single ArrowDown to verify the last → first wrap.
    await user.keyboard('{ArrowUp}');
    await user.keyboard('{ArrowDown}');
    const options = screen.getAllByRole('option');
    expect(textarea.getAttribute('aria-activedescendant')).toBe(options[0].id);
  });

  it('wraps Up at first → last', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@');
    await user.keyboard('{ArrowDown}'); // index 0
    await user.keyboard('{ArrowUp}'); // wrap to last

    const options = screen.getAllByRole('option');
    const last = options[options.length - 1];
    expect(textarea.getAttribute('aria-activedescendant')).toBe(last.id);
  });

  it('Enter with an active option inserts that option and closes the popup', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ExpressionBuilder
        expr={null}
        onChange={onChange}
        variables={variables}
        bindings={[]}
        currentIndex={0}
      />,
    );
    const textarea = screen.getByRole('combobox');
    await user.click(textarea);
    await user.keyboard('@');
    await user.keyboard('{ArrowDown}{ArrowDown}'); // activate index 1 (rate_cny_rub)
    await user.keyboard('{Enter}');

    expect(onChange).toHaveBeenLastCalledWith({ var: 'rate_cny_rub' });
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('Enter with NO active option does not insert and does not close (default Enter pass-through)', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ExpressionBuilder
        expr={null}
        onChange={onChange}
        variables={variables}
        bindings={[]}
        currentIndex={0}
      />,
    );
    const textarea = screen.getByRole('combobox');
    await user.click(textarea);
    await user.keyboard('@');
    onChange.mockClear();
    await user.keyboard('{Enter}');

    // No structured insert — onChange not called with a {var}/{ref}/{const} for an item.
    for (const call of onChange.mock.calls) {
      const arg = call[0];
      expect(arg).not.toHaveProperty('var');
      expect(arg).not.toHaveProperty('ref');
    }
  });

  it('Tab without active option falls back to the first suggestion (FA-401 shortcut preserved)', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ExpressionBuilder
        expr={null}
        onChange={onChange}
        variables={variables}
        bindings={[]}
        currentIndex={0}
      />,
    );
    const textarea = screen.getByRole('combobox');
    await user.click(textarea);
    await user.keyboard('@Закуп');
    await user.keyboard('{Tab}');

    expect(onChange).toHaveBeenLastCalledWith({ var: 'purchase_price_cny' });
  });

  it('Tab with an active option inserts the ACTIVE option (not always-first)', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ExpressionBuilder
        expr={null}
        onChange={onChange}
        variables={variables}
        bindings={[]}
        currentIndex={0}
      />,
    );
    const textarea = screen.getByRole('combobox');
    await user.click(textarea);
    await user.keyboard('@');
    await user.keyboard('{ArrowDown}{ArrowDown}'); // activate second option
    await user.keyboard('{Tab}');

    expect(onChange).toHaveBeenLastCalledWith({ var: 'rate_cny_rub' });
  });

  it('Escape closes the popup AND clears aria-activedescendant', async () => {
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@');
    await user.keyboard('{ArrowDown}'); // activate first
    expect(textarea).toHaveAttribute('aria-activedescendant');

    await user.keyboard('{Escape}');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    expect(textarea).not.toHaveAttribute('aria-activedescendant');
  });

  it('clamps activeIndex when suggestions narrow past the prior position', async () => {
    // Implementation choice: clamp (preserves user navigation context)
    // over full reset. Documented in PR description.
    const user = userEvent.setup();
    const { textarea } = renderBuilder({ expr: null });
    await user.click(textarea);
    await user.keyboard('@');
    // Before narrowing: 4 options total (purchase_price_cny, rate_cny_rub,
    // margin_pct, cost_only). Activate the last (index 3).
    await user.keyboard('{ArrowUp}'); // ArrowUp from null → wraps to last (index 3)
    let options = screen.getAllByRole('option');
    expect(textarea.getAttribute('aria-activedescendant')).toBe(
      options[options.length - 1].id,
    );

    // Narrow filter to a subset → suggestions shrink. "Курс" matches only
    // rate_cny_rub (display "Курс CNY/RUB"), so suggestions.length === 1.
    await user.keyboard('Курс');
    options = screen.getAllByRole('option');
    expect(options.length).toBe(1);
    // Active index was 3 → clamped to 0 (the only remaining option).
    expect(textarea.getAttribute('aria-activedescendant')).toBe(options[0].id);
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
  });
});
