import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { MoneyInput } from '../MoneyInput';

function renderInput(props) {
  const onChange = vi.fn();
  const utils = render(
    <MoneyInput label="Цена" value={null} onChange={onChange} {...props} />,
  );
  return { onChange, ...utils };
}

describe('<MoneyInput>', () => {
  it('renders the label and the default currency suffix when only one currency is allowed', () => {
    renderInput({ currencies: ['RUB'] });
    expect(screen.getByLabelText('Цена')).toBeInTheDocument();
    // Single-currency mode renders the code as a static suffix, not a select.
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    // Use a regex to ignore extra whitespace from the formatted suffix span.
    expect(screen.getByText(/RUB/)).toBeInTheDocument();
  });

  it('emits a normalized money object when the user types digits', () => {
    const { onChange } = renderInput({ currencies: ['RUB'] });
    fireEvent.change(screen.getByLabelText('Цена'), {
      target: { value: '9900' },
    });
    expect(onChange).toHaveBeenCalledWith({ amount: 9900, currency: 'RUB' });
  });

  it('emits null when the user clears the amount input', () => {
    const { onChange } = renderInput({
      value: { amount: 9900, currency: 'RUB' },
      currencies: ['RUB'],
    });
    fireEvent.change(screen.getByLabelText('Цена'), { target: { value: '' } });
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it('strips non-digit characters before emitting', () => {
    const { onChange } = renderInput({ currencies: ['RUB'] });
    fireEvent.change(screen.getByLabelText('Цена'), {
      target: { value: '12,500₽' },
    });
    expect(onChange).toHaveBeenCalledWith({ amount: 12500, currency: 'RUB' });
  });

  it('renders a currency dropdown when multiple currencies are allowed', () => {
    renderInput({ currencies: ['RUB', 'CNY'] });
    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
    const options = Array.from(select.querySelectorAll('option')).map(
      (o) => o.value,
    );
    expect(options).toEqual(['RUB', 'CNY']);
  });

  it('changing the currency on a populated value re-emits with the new currency', () => {
    const { onChange } = renderInput({
      value: { amount: 8000, currency: 'RUB' },
      currencies: ['RUB', 'CNY'],
    });
    fireEvent.change(screen.getByRole('combobox'), {
      target: { value: 'CNY' },
    });
    expect(onChange).toHaveBeenCalledWith({ amount: 8000, currency: 'CNY' });
  });

  it('changing the currency on an empty value does not emit (user has not entered an amount yet)', () => {
    const { onChange } = renderInput({ currencies: ['RUB', 'CNY'] });
    fireEvent.change(screen.getByRole('combobox'), {
      target: { value: 'CNY' },
    });
    expect(onChange).not.toHaveBeenCalled();
  });

  it('renders the helper text when provided and no error', () => {
    renderInput({
      currencies: ['RUB', 'CNY'],
      helperText: 'Запускает пересчёт цены продажи',
    });
    expect(
      screen.getByText('Запускает пересчёт цены продажи'),
    ).toBeInTheDocument();
  });

  it('shows error text instead of helper when hasError is true', () => {
    renderInput({
      currencies: ['RUB'],
      helperText: 'Запускает пересчёт',
      hasError: true,
      errorText: 'Сумма должна быть положительной',
    });
    expect(screen.queryByText('Запускает пересчёт')).not.toBeInTheDocument();
    const error = screen.getByRole('alert');
    expect(error).toHaveTextContent('Сумма должна быть положительной');
  });

  it('marks the input as invalid when hasError is true', () => {
    renderInput({ currencies: ['RUB'], hasError: true });
    expect(screen.getByLabelText('Цена')).toHaveAttribute(
      'aria-invalid',
      'true',
    );
  });

  it('disables both inputs when disabled', () => {
    renderInput({ currencies: ['RUB', 'CNY'], disabled: true });
    expect(screen.getByLabelText('Цена')).toBeDisabled();
    expect(screen.getByRole('combobox')).toBeDisabled();
  });

  it('marks the label with an asterisk when required', () => {
    renderInput({ currencies: ['RUB'], required: true });
    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('hydrates the local currency from a value emitted by the parent (edit mode)', () => {
    const { onChange, rerender } = renderInput({
      currencies: ['RUB', 'CNY'],
    });
    rerender(
      <MoneyInput
        label="Цена"
        value={{ amount: 8000, currency: 'CNY' }}
        onChange={onChange}
        currencies={['RUB', 'CNY']}
      />,
    );
    expect(screen.getByRole('combobox')).toHaveValue('CNY');
  });

  it('in locked-currency mode the badge and the emitted currency match the locked value even if the cached value disagrees', () => {
    const onChange = vi.fn();
    render(
      <MoneyInput
        label="Цена"
        // Stale legacy currency that doesn't match the new lock — the
        // input should still render and emit CNY, not RUB.
        value={{ amount: 1500, currency: 'RUB' }}
        onChange={onChange}
        currencies={['CNY']}
      />,
    );
    // The badge reflects the locked currency, not the stale one.
    expect(screen.getByText(/CNY/)).toBeInTheDocument();
    expect(screen.queryByText(/RUB/)).not.toBeInTheDocument();
    // Typing emits with the locked currency, ignoring the stale value.
    fireEvent.change(screen.getByLabelText('Цена'), {
      target: { value: '2000' },
    });
    expect(onChange).toHaveBeenLastCalledWith({
      amount: 2000,
      currency: 'CNY',
    });
  });
});
