import { LoadingSkeleton } from '@/features/pricing';

export default function PricingLoading() {
  return (
    <section className="animate-fadeIn">
      <h1 className="text-app-text-dark mb-5 text-[40px] leading-11 font-bold tracking-tight">
        Формулы цен
      </h1>
      <div className="border-app-border-soft rounded-2xl border bg-white p-5">
        <LoadingSkeleton rows={6} columns={4} />
      </div>
    </section>
  );
}
