/**
 * Smoke test for staff list row rendering across the three "shape" cases
 * the backend can return after the data-anomaly surfacing change:
 *   - canonical (no badges)
 *   - profile missing (neutral badge + italic placeholder)
 *   - account-type mismatch (warning badge)
 *
 * SVG imports go through @svgr/webpack which only runs under webpack; mock
 * them for vitest so the renderer can resolve module specifiers.
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('@/assets/icons/alert-triangle.svg', () => ({
  default: (props) => <svg data-testid="alert-triangle-icon" {...props} />,
}));
vi.mock('@/assets/icons/info-circle.svg', () => ({
  default: (props) => <svg data-testid="info-circle-icon" {...props} />,
}));

import { StaffRow } from '../StaffRow';
import { hasStaffAnomaly } from '../StaffAnomalyBadges';

const BASE_MEMBER = {
  identityId: '019cdbf4-e987-7000-8080-000000000001',
  email: 'admin@example.com',
  firstName: 'Иван',
  lastName: 'Петров',
  position: 'Менеджер',
  department: 'Каталог',
  roles: ['admin'],
  isActive: true,
  createdAt: '2026-05-01T10:00:00Z',
  accountTypeMismatch: false,
  hasStaffMemberProfile: true,
};

const PROFILE_MISSING_MEMBER = {
  ...BASE_MEMBER,
  identityId: '019cdbf4-e987-7000-8080-000000000002',
  firstName: null,
  lastName: null,
  position: null,
  department: null,
  hasStaffMemberProfile: false,
};

const MISMATCH_MEMBER = {
  ...BASE_MEMBER,
  identityId: '019cdbf4-e987-7000-8080-000000000003',
  email: 'customer-with-role@example.com',
  accountTypeMismatch: true,
};

describe('hasStaffAnomaly', () => {
  it('returns false for the canonical row shape', () => {
    expect(hasStaffAnomaly(BASE_MEMBER)).toBe(false);
  });

  it('flags rows missing a staff_members profile', () => {
    expect(hasStaffAnomaly(PROFILE_MISSING_MEMBER)).toBe(true);
  });

  it('flags rows where the identity is CUSTOMER but has a staff role', () => {
    expect(hasStaffAnomaly(MISMATCH_MEMBER)).toBe(true);
  });

  it('handles a null/undefined member without throwing', () => {
    expect(hasStaffAnomaly(null)).toBe(false);
    expect(hasStaffAnomaly(undefined)).toBe(false);
  });
});

describe('<StaffRow>', () => {
  it('canonical row renders the full name without anomaly badges', () => {
    render(<StaffRow member={BASE_MEMBER} onOpen={() => {}} />);
    expect(screen.getByText('Иван Петров')).toBeInTheDocument();
    expect(screen.queryByTestId('alert-triangle-icon')).toBeNull();
    expect(screen.queryByTestId('info-circle-icon')).toBeNull();
    // Profile fields present
    expect(screen.getByText('Менеджер')).toBeInTheDocument();
  });

  it('profile-missing row shows neutral badge + italic placeholder', () => {
    render(<StaffRow member={PROFILE_MISSING_MEMBER} onOpen={() => {}} />);
    // Name placeholder spelled out so the operator knows it's not "blank
    // because nobody filled it in" but "no staff_members row exists".
    expect(screen.getByText('Профиль не заполнен')).toBeInTheDocument();
    expect(screen.getByText('Профиль не создан')).toBeInTheDocument();
    expect(screen.getByTestId('info-circle-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('alert-triangle-icon')).toBeNull();
  });

  it('mismatch row shows the warning badge alongside the name', () => {
    render(<StaffRow member={MISMATCH_MEMBER} onOpen={() => {}} />);
    expect(screen.getByText('Иван Петров')).toBeInTheDocument();
    expect(screen.getByText('Клиент с админ-ролью')).toBeInTheDocument();
    expect(screen.getByTestId('alert-triangle-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('info-circle-icon')).toBeNull();
  });
});
