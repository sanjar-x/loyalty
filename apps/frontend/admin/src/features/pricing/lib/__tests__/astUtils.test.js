import { describe, expect, it } from 'vitest';

import { astToBindings, bindingsToAst, expressionToText } from '../astUtils';

describe('expressionToText', () => {
  it('renders a numeric constant as its string value', () => {
    expect(expressionToText({ const: '5' })).toBe('5');
  });

  it('renders a variable reference as its bare code', () => {
    expect(expressionToText({ var: 'purchase_price' })).toBe('purchase_price');
  });

  it('renders a binding reference as its bare name', () => {
    expect(expressionToText({ ref: 'subtotal' })).toBe('subtotal');
  });

  it('joins binary op args with the operator surrounded by spaces', () => {
    expect(
      expressionToText({ op: '+', args: [{ const: '1' }, { const: '2' }] }),
    ).toBe('1 + 2');
  });

  it('walks nested op trees recursively without parentheses', () => {
    const expr = {
      op: '*',
      args: [
        { op: '+', args: [{ const: '1' }, { const: '2' }] },
        { const: '3' },
      ],
    };
    expect(expressionToText(expr)).toBe('1 + 2 * 3');
  });

  it('renders a fn call with comma-separated args', () => {
    expect(
      expressionToText({
        fn: 'min',
        args: [{ const: '12' }, { const: '15' }],
      }),
    ).toBe('min(12, 15)');
  });

  it('returns empty string for null, undefined, and non-object input', () => {
    expect(expressionToText(null)).toBe('');
    expect(expressionToText(undefined)).toBe('');
    expect(expressionToText('not-an-object')).toBe('');
    expect(expressionToText(42)).toBe('');
  });

  it('falls through to JSON.stringify for unknown shapes', () => {
    const weird = { foo: 'bar' };
    expect(expressionToText(weird)).toBe(JSON.stringify(weird));
  });
});

describe('astToBindings', () => {
  it('returns an empty array for null and undefined input', () => {
    expect(astToBindings(null)).toEqual([]);
    expect(astToBindings(undefined)).toEqual([]);
  });

  it('returns an empty array when the AST has no bindings field', () => {
    expect(astToBindings({ version: 1 })).toEqual([]);
  });

  it('shallow-copies each binding (preserves shape, breaks aliasing)', () => {
    const original = { name: 'a', component_tag: 'cogs', expr: { const: '0' } };
    const ast = { bindings: [original] };
    const result = astToBindings(ast);
    expect(result[0]).toEqual(original);
    expect(result[0]).not.toBe(original);
  });
});

describe('bindingsToAst', () => {
  it('wraps bindings in {version: 1, bindings: [...]} envelope', () => {
    const result = bindingsToAst([
      { name: 'x', component_tag: 'cogs', expr: { const: '0' } },
    ]);
    expect(result).toEqual({
      version: 1,
      bindings: [{ name: 'x', component_tag: 'cogs', expr: { const: '0' } }],
    });
  });

  it('omits the label property when the source label is falsy', () => {
    const result = bindingsToAst([
      { name: 'x', component_tag: 'cogs', expr: { const: '0' }, label: '' },
    ]);
    expect(result.bindings[0]).not.toHaveProperty('label');
  });

  it('keeps the label property when the source label is truthy', () => {
    const result = bindingsToAst([
      {
        name: 'x',
        component_tag: 'cogs',
        expr: { const: '0' },
        label: 'Gross margin',
      },
    ]);
    expect(result.bindings[0].label).toBe('Gross margin');
  });
});
