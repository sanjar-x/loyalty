import { afterEach, describe, it, expect, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import CustomsSheet from '../CustomsSheet';

afterEach(() => {
  cleanup();
});

const VALID = {
  passportSeries: '1234',
  passportNumber: '567890',
  issueDate: '01.06.2015',
  birthDate: '15.01.1990',
  inn: '123456789012',
};

function findInputByLabel(text) {
  const labels = Array.from(document.querySelectorAll('label'));
  const label = labels.find((l) => l.textContent === text);
  if (!label) return null;
  return label.parentElement?.querySelector('input');
}

describe('CustomsSheet (CHK-020/021/022)', () => {
  it('returns null when not open', () => {
    const { container } = render(
      <CustomsSheet open={false} onClose={() => {}} onSave={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders title and form fields when open', () => {
    render(<CustomsSheet open onClose={() => {}} onSave={() => {}} />);
    expect(screen.getByText('Данные для таможни')).toBeInTheDocument();
    expect(findInputByLabel('Серия')).not.toBeNull();
    expect(findInputByLabel('Номер')).not.toBeNull();
    expect(findInputByLabel('ИНН')).not.toBeNull();
  });

  it('hydrates from initialValue', () => {
    render(<CustomsSheet open onClose={() => {}} onSave={() => {}} initialValue={VALID} />);
    expect(findInputByLabel('Серия')).toHaveValue(VALID.passportSeries);
    expect(findInputByLabel('ИНН')).toHaveValue(VALID.inn);
  });

  it('calls onSave with trimmed payload when valid', () => {
    const onSave = vi.fn();
    render(<CustomsSheet open onClose={() => {}} onSave={onSave} initialValue={VALID} />);
    fireEvent.click(screen.getByText('Сохранить'));
    expect(onSave).toHaveBeenCalledWith(VALID);
  });

  it('blocks save on invalid (empty draft)', () => {
    const onSave = vi.fn();
    render(<CustomsSheet open onClose={() => {}} onSave={onSave} />);
    fireEvent.click(screen.getByText('Сохранить'));
    expect(onSave).not.toHaveBeenCalled();
  });
});
