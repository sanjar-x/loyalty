export default function OrdersLoading() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="bg-app-bg h-11 w-40 rounded-lg" />
      <div className="bg-app-bg h-32 rounded-2xl" />
      <div className="bg-app-bg h-12 rounded-xl" />
      <div className="space-y-3">
        <div className="bg-app-bg h-24 rounded-2xl" />
        <div className="bg-app-bg h-24 rounded-2xl" />
        <div className="bg-app-bg h-24 rounded-2xl" />
      </div>
    </div>
  );
}
