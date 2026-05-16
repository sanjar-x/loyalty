import { afterEach, describe, it, expect, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import CardSheet from '../CardSheet';

afterEach(() => {
  cleanup();
});

function findInputByLabel(text) {
  const labels = Array.from(document.querySelectorAll('label'));
  const label = labels.find((l) => l.textContent === text);
  if (!label) return null;
  return label.parentElement?.querySelector('input');
}

describe('CardSheet (CHK-020/022 — orphan)', () => {
  it('returns null when not open', () => {
    const { container } = render(<CardSheet open={false} onClose={() => {}} onSave={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders title and form fields when open', () => {
    render(<CardSheet open onClose={() => {}} onSave={() => {}} />);
    expect(screen.getByText('Добавить карту')).toBeInTheDocument();
    expect(findInputByLabel('Номер карты')).not.toBeNull();
    expect(findInputByLabel('MM/YY')).not.toBeNull();
    expect(findInputByLabel('CVV')).not.toBeNull();
    expect(findInputByLabel('Имя владельца')).not.toBeNull();
  });

  it('formats card number on typing', () => {
    render(<CardSheet open onClose={() => {}} onSave={() => {}} />);
    const numberInput = findInputByLabel('Номер карты');
    fireEvent.change(numberInput, { target: { value: '4242424242424242' } });
    expect(numberInput).toHaveValue('4242 4242 4242 4242');
  });

  it('blocks save and shows error on invalid Luhn', () => {
    const onSave = vi.fn();
    render(<CardSheet open onClose={() => {}} onSave={onSave} />);
    fireEvent.change(findInputByLabel('Номер карты'), {
      target: { value: '4242 4242 4242 4241' },
    });
    fireEvent.change(findInputByLabel('MM/YY'), {
      target: { value: '12/30' },
    });
    fireEvent.change(findInputByLabel('CVV'), {
      target: { value: '123' },
    });
    fireEvent.change(findInputByLabel('Имя владельца'), {
      target: { value: 'IVAN' },
    });
    fireEvent.click(screen.getByText('Сохранить'));
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByText(/Проверьте номер карты/)).toBeInTheDocument();
  });

  it('calls onSave with full draft when valid (4242 Luhn-valid)', () => {
    const onSave = vi.fn();
    render(<CardSheet open onClose={() => {}} onSave={onSave} />);
    fireEvent.change(findInputByLabel('Номер карты'), {
      target: { value: '4242 4242 4242 4242' },
    });
    fireEvent.change(findInputByLabel('MM/YY'), {
      target: { value: '1230' },
    });
    fireEvent.change(findInputByLabel('CVV'), {
      target: { value: '123' },
    });
    fireEvent.change(findInputByLabel('Имя владельца'), {
      target: { value: 'IVAN PETROV' },
    });
    fireEvent.click(screen.getByText('Сохранить'));
    expect(onSave).toHaveBeenCalledTimes(1);
    const payload = onSave.mock.calls[0][0];
    expect(payload.numberDigits).toBe('4242424242424242');
    expect(payload.exp).toBe('12/30');
    expect(payload.cvc).toBe('123');
    expect(payload.holder).toBe('IVAN PETROV');
  });
});
