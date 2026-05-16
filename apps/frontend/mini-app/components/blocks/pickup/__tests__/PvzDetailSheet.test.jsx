import { afterEach, describe, it, expect, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import PvzDetailSheet from '../PvzDetailSheet';

afterEach(() => {
  cleanup();
});

const POINT = {
  externalId: 'pvz-1',
  providerCode: 'cdek',
  providerLabel: 'CDEK',
  pickupPointTypeLabel: 'ПВЗ',
  addressLine: 'Москва, ул. Тверская 1',
  workSchedule: 'Пн-Пт 9:00-21:00; Сб 10:00-18:00',
  phone: '+7 999 111-22-33',
  isCashAllowed: true,
  isCardAllowed: false,
  lat: 55.75,
  lon: 37.62,
};

describe('PvzDetailSheet (CHK-019)', () => {
  it('returns null when not open', () => {
    const { container } = render(
      <PvzDetailSheet open={false} point={POINT} onClose={() => {}} onConfirm={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('returns null when point is null even if open', () => {
    const { container } = render(
      <PvzDetailSheet open point={null} onClose={() => {}} onConfirm={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders address, schedule, phone, payment', () => {
    render(<PvzDetailSheet open point={POINT} onClose={() => {}} onConfirm={() => {}} />);
    expect(screen.getByText(POINT.addressLine)).toBeInTheDocument();
    expect(screen.getByText(/Пн-Пт 9:00-21:00/)).toBeInTheDocument();
    expect(screen.getByText(/Сб 10:00-18:00/)).toBeInTheDocument();
    expect(screen.getByText(POINT.phone)).toBeInTheDocument();
    expect(screen.getByText(/наличные/)).toBeInTheDocument();
  });

  it('renders providerLabel + pickupPointTypeLabel as title', () => {
    render(<PvzDetailSheet open point={POINT} onClose={() => {}} onConfirm={() => {}} />);
    expect(screen.getByText('CDEK · ПВЗ')).toBeInTheDocument();
  });

  it('omits schedule row when workSchedule absent', () => {
    render(
      <PvzDetailSheet
        open
        point={{ ...POINT, workSchedule: '' }}
        onClose={() => {}}
        onConfirm={() => {}}
      />
    );
    // No '9:00' fragment anywhere
    expect(screen.queryByText(/9:00/)).toBeNull();
  });

  it('calls onClose when × clicked', () => {
    const onClose = vi.fn();
    render(<PvzDetailSheet open point={POINT} onClose={onClose} onConfirm={() => {}} />);
    fireEvent.click(screen.getByLabelText('Закрыть'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onConfirm with full point when 'Доставить сюда' clicked", () => {
    const onConfirm = vi.fn();
    render(<PvzDetailSheet open point={POINT} onClose={() => {}} onConfirm={onConfirm} />);
    fireEvent.click(screen.getByText('Доставить сюда'));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith(POINT);
  });

  it('shows both cash and card when isCardAllowed=true', () => {
    render(
      <PvzDetailSheet
        open
        point={{ ...POINT, isCardAllowed: true }}
        onClose={() => {}}
        onConfirm={() => {}}
      />
    );
    expect(screen.getByText(/наличные, карта/)).toBeInTheDocument();
  });

  it('omits payment row when both flags false', () => {
    render(
      <PvzDetailSheet
        open
        point={{ ...POINT, isCashAllowed: false, isCardAllowed: false }}
        onClose={() => {}}
        onConfirm={() => {}}
      />
    );
    expect(screen.queryByText(/наличные|карта/)).toBeNull();
  });

  it('phone link uses tel: scheme', () => {
    render(<PvzDetailSheet open point={POINT} onClose={() => {}} onConfirm={() => {}} />);
    const link = screen.getByText(POINT.phone);
    expect(link.tagName).toBe('A');
    expect(link.getAttribute('href')).toBe(`tel:${POINT.phone}`);
  });
});
