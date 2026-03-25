export default function Loading() {
  return (
    <section className="animate-fadeIn">
      <div className="flex items-center gap-3.5 mb-7">
        <div className="h-[46px] w-[46px] rounded-full bg-app-card" />
        <div className="h-9 w-56 rounded-lg bg-app-card" />
      </div>
      <div className="space-y-4">
        <div className="h-5 w-80 rounded bg-app-card" />
        <div className="h-48 rounded-2xl bg-app-card" />
        <div className="h-48 rounded-2xl bg-app-card" />
      </div>
    </section>
  );
}
