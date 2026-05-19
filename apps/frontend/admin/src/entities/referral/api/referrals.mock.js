import { referralsSeed } from '@/shared/mocks/referrals';

const referrals = [...referralsSeed];

export function getReferrals() {
  return [...referrals];
}
