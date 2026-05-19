/**
 * Audit 7.1 (P0) regression — `CategoryNode` action buttons must stay
 * focusable AND announce themselves via `aria-label`. The pre-fix code
 * scoped visibility to `group-hover` only, leaving the buttons in the
 * tab order but visually invisible — that's what the test pins now.
 *
 * Audit 7.2 / 7.3 — expand button gets `aria-expanded` + `aria-label`,
 * action glyphs are wrapped in `aria-hidden` spans.
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { CategoryNode } from '../CategoryNode';

const SAMPLE_NODE = {
  id: 'cat-shoes',
  slug: 'shoes',
  nameI18N: { ru: 'Обувь', en: 'Shoes' },
  children: [
    {
      id: 'cat-sneakers',
      slug: 'sneakers',
      nameI18N: { ru: 'Кроссовки', en: 'Sneakers' },
      children: [],
    },
  ],
};

describe('<CategoryNode>', () => {
  it('exposes accessible names for action buttons (audit 7.1 / 7.3)', () => {
    render(
      <CategoryNode node={SAMPLE_NODE} onAddChild={vi.fn()} onEdit={vi.fn()} />,
    );

    expect(
      screen.getByRole('button', { name: 'Добавить подкатегорию в Обувь' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Редактировать категорию Обувь' }),
    ).toBeInTheDocument();
  });

  it('expand button announces aria-expanded + aria-label (audit 7.2)', () => {
    render(
      <CategoryNode node={SAMPLE_NODE} onAddChild={vi.fn()} onEdit={vi.fn()} />,
    );

    const expand = screen.getByRole('button', { name: /^Свернуть категорию/ });
    expect(expand).toHaveAttribute('aria-expanded', 'true');

    fireEvent.click(expand);
    const collapsed = screen.getByRole('button', {
      name: /^Развернуть категорию/,
    });
    expect(collapsed).toHaveAttribute('aria-expanded', 'false');
    expect(collapsed).toHaveAccessibleName('Развернуть категорию Обувь');
  });

  it('action buttons stay keyboard-focusable (focus reveals them)', () => {
    render(
      <CategoryNode node={SAMPLE_NODE} onAddChild={vi.fn()} onEdit={vi.fn()} />,
    );

    const addButton = screen.getByRole('button', {
      name: 'Добавить подкатегорию в Обувь',
    });
    addButton.focus();
    expect(addButton).toHaveFocus();
  });

  it('calls handlers when actions clicked', () => {
    const onAddChild = vi.fn();
    const onEdit = vi.fn();
    render(
      <CategoryNode
        node={SAMPLE_NODE}
        onAddChild={onAddChild}
        onEdit={onEdit}
      />,
    );

    fireEvent.click(
      screen.getByRole('button', { name: 'Добавить подкатегорию в Обувь' }),
    );
    expect(onAddChild).toHaveBeenCalledWith('cat-shoes');

    fireEvent.click(
      screen.getByRole('button', { name: 'Редактировать категорию Обувь' }),
    );
    expect(onEdit).toHaveBeenCalledWith(SAMPLE_NODE);
  });
});
