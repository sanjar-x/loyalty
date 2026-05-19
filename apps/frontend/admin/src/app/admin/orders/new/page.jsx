import { WalkInOrderForm } from '@/features/walk-in-order-form';

// Walk-in order creation page. Thin shell — every section, validation,
// idempotency lifecycle, and submit plumbing lives inside the feature.
export default function NewOrderPage() {
  return (
    <section className="animate-fadeIn max-w-5xl">
      <WalkInOrderForm />
    </section>
  );
}
