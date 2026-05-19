/**
 * Integration tests for <RecipientSnapshotPanel> — covers the masking
 * policy (passport / phone / email partials, INN unmasked) and the
 * "Показать полностью" toggle. The pure helpers themselves are unit-
 * tested in `../lib/__tests__/mask.test.js`; this file pins the wiring
 * between the snapshot prop and the rendered DOM.
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RecipientSnapshotPanel } from '../RecipientSnapshotPanel';

const SNAPSHOT = {
  recipientId: 'rec-1',
  fullNameRu: 'Иванов Иван Иванович',
  fullNameLat: 'Ivanov Ivan Ivanovich',
  phone: '+79161234567',
  email: 'john.doe@example.com',
  passportSerial: '4520',
  passportNumber: '123456',
  passportIssueDate: '2018-04-15',
  birthDate: '1990-01-15',
  inn: '123456789012',
};

describe('<RecipientSnapshotPanel>', () => {
  it('falls back to the empty placeholder when snapshot is null', () => {
    render(<RecipientSnapshotPanel snapshot={null} />);
    expect(screen.getByTestId('recipient-snapshot-empty')).toBeInTheDocument();
  });

  it('renders masked passport / phone / email by default', () => {
    render(<RecipientSnapshotPanel snapshot={SNAPSHOT} />);

    expect(screen.getByText('**20 **3456')).toBeInTheDocument();
    expect(screen.getByText('+7 (***) ***-45-67')).toBeInTheDocument();
    expect(screen.getByText('j***e@example.com')).toBeInTheDocument();
  });

  it('always shows INN unmasked — required for customs declaration', () => {
    render(<RecipientSnapshotPanel snapshot={SNAPSHOT} />);
    expect(screen.getByText('123456789012')).toBeInTheDocument();
  });

  it('renders ФИО (RU + Lat) plain — not subject to masking', () => {
    render(<RecipientSnapshotPanel snapshot={SNAPSHOT} />);
    expect(screen.getByText('Иванов Иван Иванович')).toBeInTheDocument();
    expect(screen.getByText('Ivanov Ivan Ivanovich')).toBeInTheDocument();
  });

  it('toggles the masked fields when "Показать полностью" is pressed', () => {
    render(<RecipientSnapshotPanel snapshot={SNAPSHOT} />);

    const toggle = screen.getByRole('button', { name: /Показать полностью/ });
    expect(toggle).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(toggle);

    expect(
      screen.getByRole('button', { name: /Скрыть полностью/ }),
    ).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('4520 123456')).toBeInTheDocument();
    expect(screen.getByText('+79161234567')).toBeInTheDocument();
    expect(screen.getByText('john.doe@example.com')).toBeInTheDocument();

    // Re-clicking restores the masks — important for a screen-recording
    // scenario where the operator wants to revert before sharing.
    fireEvent.click(screen.getByRole('button', { name: /Скрыть полностью/ }));
    expect(screen.getByText('**20 **3456')).toBeInTheDocument();
  });

  it('exposes ARIA labels for each masked value', () => {
    render(<RecipientSnapshotPanel snapshot={SNAPSHOT} />);

    expect(
      screen.getByLabelText(
        'Паспорт получателя, замаскирован для безопасности',
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(
        'Телефон получателя, замаскирован для безопасности',
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('Email получателя, замаскирован для безопасности'),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(
        'ИНН получателя, не маскируется — нужен для таможенной декларации',
      ),
    ).toBeInTheDocument();
  });

  it('updates ARIA labels to non-masked variants when revealed', () => {
    render(<RecipientSnapshotPanel snapshot={SNAPSHOT} />);
    fireEvent.click(screen.getByRole('button', { name: /Показать полностью/ }));

    expect(screen.getByLabelText('Паспорт получателя')).toBeInTheDocument();
    expect(screen.getByLabelText('Телефон получателя')).toBeInTheDocument();
    expect(screen.getByLabelText('Email получателя')).toBeInTheDocument();
  });
});
