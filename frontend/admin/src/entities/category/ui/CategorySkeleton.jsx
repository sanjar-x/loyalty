export function CategorySkeleton() {
  const rows = [
    { width: 'w-48', indent: 0 },
    { width: 'w-36', indent: 1 },
    { width: 'w-28', indent: 2 },
    { width: 'w-32', indent: 2 },
    { width: 'w-36', indent: 1 },
    { width: 'w-40', indent: 0 },
  ];

  return (
    <div className="flex flex-col gap-2">
      {rows.map((row, i) => (
        <div
          key={i}
          className="flex items-center gap-2"
          style={{ paddingLeft: row.indent * 24 }}
        >
          <div className="h-4 w-4 animate-pulse rounded bg-[#e0dedb]" />
          <div
            className={`h-4 ${row.width} animate-pulse rounded bg-[#e0dedb]`}
          />
        </div>
      ))}
    </div>
  );
}
