import { useRef } from 'react';
import { afterEach, describe, it, expect, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import CheckoutFormField from '../CheckoutFormField';

afterEach(() => {
  cleanup();
});

describe('CheckoutFormField (CHK-022)', () => {
  it('renders label text', () => {
    render(<CheckoutFormField label="ФИО" value="" onChange={() => {}} />);
    expect(screen.getByText('ФИО')).toBeInTheDocument();
  });

  it('does not float label when empty & blurred', () => {
    const { container } = render(<CheckoutFormField label="ФИО" value="" onChange={() => {}} />);
    const label = container.querySelector('label');
    expect(label.className).not.toMatch(/labelFloating/);
  });

  it('floats label when value present', () => {
    const { container } = render(
      <CheckoutFormField label="ФИО" value="Ivan" onChange={() => {}} />
    );
    const label = container.querySelector('label');
    expect(label.className).toMatch(/labelFloating/);
  });

  it('floats label on focus even with empty value', () => {
    const { container } = render(<CheckoutFormField label="ФИО" value="" onChange={() => {}} />);
    const input = container.querySelector('input');
    fireEvent.focus(input);
    expect(container.querySelector('label').className).toMatch(/labelFloating/);
    fireEvent.blur(input);
    expect(container.querySelector('label').className).not.toMatch(/labelFloating/);
  });

  it('renders error message and applies error styling to input + label', () => {
    const { container } = render(
      <CheckoutFormField label="Email" value="bad@" onChange={() => {}} error="Неверный формат" />
    );
    expect(screen.getByText('Неверный формат')).toBeInTheDocument();
    expect(container.querySelector('input').className).toMatch(/inputError/);
    expect(container.querySelector('label').className).toMatch(/labelError/);
  });

  it('forwards inputRef to the underlying input', () => {
    function Wrapper() {
      const ref = useRef(null);
      return (
        <CheckoutFormField
          label="Test"
          value=""
          onChange={() => {}}
          inputRef={ref}
          data-testid="probe"
        />
      );
    }
    render(<Wrapper />);
    expect(screen.getByTestId('probe')).toBeInstanceOf(HTMLInputElement);
  });

  it('renders rightSlot content', () => {
    render(
      <CheckoutFormField
        label="Phone"
        value=""
        onChange={() => {}}
        rightSlot={<span data-testid="slot">🇷🇺</span>}
      />
    );
    expect(screen.getByTestId('slot')).toBeInTheDocument();
  });

  it('calls onChange when typing', () => {
    const onChange = vi.fn();
    render(<CheckoutFormField label="ФИО" value="" onChange={onChange} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Ivan' } });
    expect(onChange).toHaveBeenCalled();
  });

  it('respects maxLength, inputMode, spellCheck props', () => {
    render(
      <CheckoutFormField
        label="ИНН"
        value=""
        onChange={() => {}}
        inputMode="numeric"
        maxLength={12}
        spellCheck={false}
      />
    );
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('maxLength', '12');
    expect(input).toHaveAttribute('inputMode', 'numeric');
    expect(input).toHaveAttribute('spellCheck', 'false');
  });
});
