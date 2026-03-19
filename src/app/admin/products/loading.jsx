export default function ProductsLoading() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="flex items-center justify-between">
        <div className="h-11 w-40 rounded-lg bg-[#efeff0]" />
        <div className="h-11 w-44 rounded-2xl bg-[#efeff0]" />
      </div>
      <div className="h-28 rounded-2xl bg-[#efeff0]" />
      <div className="h-12 rounded-xl bg-[#efeff0]" />
      <div className="space-y-3">
        <div className="h-20 rounded-2xl bg-[#efeff0]" />
        <div className="h-20 rounded-2xl bg-[#efeff0]" />
        <div className="h-20 rounded-2xl bg-[#efeff0]" />
      </div>
    </div>
  );
}
