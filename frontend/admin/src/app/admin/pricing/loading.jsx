import { LoadingSkeleton } from '@/components/admin/pricing/shared/LoadingSkeleton';

export default function PricingLoading() {
  return (
    <section className="animate-fadeIn">
      <h1 className="mb-5 text-[40px] font-bold leading-[44px] tracking-tight text-[#2d2d2d]">
        Формулы цен
      </h1>
      <div className="rounded-2xl border border-[#f0f0f0] bg-white p-5">
        <LoadingSkeleton rows={6} columns={4} />
      </div>
    </section>
  );
}
