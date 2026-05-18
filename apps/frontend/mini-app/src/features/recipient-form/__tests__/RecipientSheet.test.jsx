import { afterEach, describe, it, expect, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import RecipientSheet from '../ui/RecipientSheet';

afterEach(() => {
  cleanup();
});

const VALID = {
  fullName: 'Иван Петров',
  phoneDigits: '9990001122',
  email: 'ivan@example.ru',
  country: 'RU',
};

function findInputByLabel(text) {
  const labels = Array.from(document.querySelectorAll('label'));
  const label = labels.find((l) => l.textContent === text);
  if (!label) return null;
  // CheckoutFormField: input is the next sibling of label in fieldShell.
  return label.parentElement?.querySelector('input');
}

describe('RecipientSheet (CHK-020/021/022)', () => {
  it('returns null when not open', () => {
    const { container } = render(
      <RecipientSheet open={false} onClose={() => {}} onSave={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders title and form when open', () => {
    render(<RecipientSheet open onClose={() => {}} onSave={() => {}} />);
    expect(screen.getByText('Получатель')).toBeInTheDocument();
    expect(findInputByLabel('ФИО')).not.toBeNull();
  });

  it('hydrates form from initialValue', () => {
    render(<RecipientSheet open onClose={() => {}} onSave={() => {}} initialValue={VALID} />);
    expect(findInputByLabel('ФИО')).toHaveValue(VALID.fullName);
  });

  it('calls onSave with normalized payload when valid', () => {
    const onSave = vi.fn();
    render(<RecipientSheet open onClose={() => {}} onSave={onSave} initialValue={VALID} />);
    fireEvent.click(screen.getByText('Сохранить'));
    expect(onSave).toHaveBeenCalledWith(VALID);
  });

  it('blocks save and surfaces error on invalid', () => {
    const onSave = vi.fn();
    render(<RecipientSheet open onClose={() => {}} onSave={onSave} />);
    fireEvent.click(screen.getByText('Сохранить'));
    expect(onSave).not.toHaveBeenCalled();
  });
});
