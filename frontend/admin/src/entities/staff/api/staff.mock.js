import { staffSeed } from '@/shared/mocks/staff';

const staff = [...staffSeed];

export function getStaff() {
  return [...staff];
}
