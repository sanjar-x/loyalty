export default function ProductsLoading() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="flex items-center justify-between">
        <div className="bg-app-bg h-11 w-40 rounded-lg" />
        <div className="bg-app-bg h-11 w-44 rounded-2xl" />
      </div>
      <div className="bg-app-bg h-28 rounded-2xl" />
      <div className="bg-app-bg h-12 rounded-xl" />
      <div className="space-y-3">
        <div className="bg-app-bg h-20 rounded-2xl" />
        <div className="bg-app-bg h-20 rounded-2xl" />
        <div className="bg-app-bg h-20 rounded-2xl" />
      </div>
    </div>
  );
}
