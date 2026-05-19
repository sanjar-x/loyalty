import { reviewsSeed } from '@/shared/mocks/reviews';

let reviews = [...reviewsSeed];

export function getReviews() {
  return [...reviews];
}

export async function deleteReview(id) {
  reviews = reviews.filter((r) => r.id !== id);
}
