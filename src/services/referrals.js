import { referralsSeed } from '@/data/referrals';

const referrals = [...referralsSeed];

export function getReferrals() {
  return [...referrals];
}
