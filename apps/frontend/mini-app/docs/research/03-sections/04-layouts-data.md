# 7. Layout-паттерны для enterprise-дашбордов (расширение)

> Расширение секций 7-8 из `03-ui-design-system.md` | Апрель 2026

---

## 7.1. Полная архитектура dashboard-layout

### Принцип: CSS Grid для каркаса, Flexbox для содержимого

Enterprise-дашборд строится на трех уровнях:

1. **Shell** -- CSS Grid (header + sidebar + main)
2. **Page** -- Flexbox/Grid (breadcrumbs + toolbar + content area)
3. **Widgets** -- Grid (KPI-карточки, графики, таблицы)

### Реализация корневого layout

```tsx
// app/(dashboard)/layout.tsx
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/app-sidebar';
import { Separator } from '@/components/ui/separator';
import { DynamicBreadcrumbs } from '@/components/dynamic-breadcrumbs';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        {/* Header */}
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <DynamicBreadcrumbs />
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
```

### CSS Grid структура (детальная)

```css
/* Tailwind v4 -- определяется через утилиты, но для понимания: */
.dashboard-shell {
  display: grid;
  grid-template-areas:
    'sidebar header'
    'sidebar main';
  grid-template-columns: var(--sidebar-width, 256px) 1fr;
  grid-template-rows: 56px 1fr;
  min-height: 100dvh; /* dvh для мобильных браузеров */
}

/* Свернутый sidebar */
.dashboard-shell[data-collapsed='true'] {
  grid-template-columns: var(--sidebar-width-collapsed, 48px) 1fr;
}

/* Мобильная версия: sidebar как Sheet overlay */
@media (max-width: 768px) {
  .dashboard-shell {
    grid-template-areas: 'header' 'main';
    grid-template-columns: 1fr;
  }
}
```

---

## 7.2. Sidebar: shadcn/ui Sidebar компонент

### Ключевые возможности

| Возможность             | Реализация                                                                      |
| ----------------------- | ------------------------------------------------------------------------------- |
| **Сворачивание**        | `collapsible="icon"` -- иконки остаются, текст скрывается                       |
| **Клавиатура**          | `Cmd+B` (Mac) / `Ctrl+B` (Win), настраивается через `SIDEBAR_KEYBOARD_SHORTCUT` |
| **Мобильная версия**    | Автоматический переход на Sheet (drawer) на экранах < 768px                     |
| **Персистентность**     | Состояние (open/closed) сохраняется в cookies                                   |
| **Вложенная навигация** | Collapsible группы с `ChevronRight` индикаторами                                |

### Полная реализация sidebar с вложенной навигацией

```tsx
// components/app-sidebar.tsx
'use client';

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
  SidebarHeader,
  SidebarFooter,
  SidebarRail,
} from '@/components/ui/sidebar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import {
  LayoutDashboard,
  BarChart3,
  Users,
  Settings,
  ChevronRight,
  CreditCard,
  FileText,
  Bell,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navigation = [
  {
    title: 'Dashboard',
    icon: LayoutDashboard,
    href: '/dashboard',
  },
  {
    title: 'Analytics',
    icon: BarChart3,
    items: [
      { title: 'Overview', href: '/analytics' },
      { title: 'Reports', href: '/analytics/reports' },
      { title: 'Real-time', href: '/analytics/realtime' },
    ],
  },
  {
    title: 'Users',
    icon: Users,
    items: [
      { title: 'All Users', href: '/users' },
      { title: 'Roles', href: '/users/roles' },
    ],
  },
  {
    title: 'Billing',
    icon: CreditCard,
    items: [
      { title: 'Invoices', href: '/billing/invoices' },
      { title: 'Plans', href: '/billing/plans' },
    ],
  },
  {
    title: 'Settings',
    icon: Settings,
    href: '/settings',
  },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/dashboard">
                <div className="bg-primary text-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                  A
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">Acme Corp</span>
                  <span className="text-muted-foreground truncate text-xs">Enterprise</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Platform</SidebarGroupLabel>
          <SidebarMenu>
            {navigation.map((item) =>
              item.items ? (
                <Collapsible
                  key={item.title}
                  defaultOpen={item.items.some((sub) => pathname.startsWith(sub.href))}
                  className="group/collapsible"
                >
                  <SidebarMenuItem>
                    <CollapsibleTrigger asChild>
                      <SidebarMenuButton tooltip={item.title}>
                        <item.icon className="size-4" />
                        <span>{item.title}</span>
                        <ChevronRight className="ml-auto size-4 transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                      </SidebarMenuButton>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <SidebarMenuSub>
                        {item.items.map((sub) => (
                          <SidebarMenuSubItem key={sub.href}>
                            <SidebarMenuSubButton asChild isActive={pathname === sub.href}>
                              <Link href={sub.href}>{sub.title}</Link>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        ))}
                      </SidebarMenuSub>
                    </CollapsibleContent>
                  </SidebarMenuItem>
                </Collapsible>
              ) : (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={pathname === item.href} tooltip={item.title}>
                    <Link href={item.href!}>
                      <item.icon className="size-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ),
            )}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>{/* User menu, notifications, etc. */}</SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
```

### Кастомизация клавиатурного шортката

```tsx
// По умолчанию: Cmd+B / Ctrl+B
// Изменение:
import { SIDEBAR_KEYBOARD_SHORTCUT } from '@/components/ui/sidebar';

// В sidebar.tsx компоненте можно переопределить:
const SIDEBAR_KEYBOARD_SHORTCUT = 's'; // теперь Cmd+S / Ctrl+S
```

---

## 7.3. Breadcrumbs с динамическими сегментами

```tsx
// components/dynamic-breadcrumbs.tsx
'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { Fragment } from 'react';

// Маппинг slug -> человекочитаемое название
const segmentLabels: Record<string, string> = {
  dashboard: 'Dashboard',
  analytics: 'Analytics',
  reports: 'Reports',
  users: 'Users',
  settings: 'Settings',
  billing: 'Billing',
  invoices: 'Invoices',
};

function formatSegment(segment: string): string {
  return segmentLabels[segment] ?? segment.charAt(0).toUpperCase() + segment.slice(1);
}

export function DynamicBreadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split('/').filter(Boolean);

  if (segments.length === 0) return null;

  return (
    <Breadcrumb>
      <BreadcrumbList>
        {segments.map((segment, index) => {
          const href = '/' + segments.slice(0, index + 1).join('/');
          const isLast = index === segments.length - 1;

          return (
            <Fragment key={href}>
              {index > 0 && <BreadcrumbSeparator />}
              <BreadcrumbItem>
                {isLast ? (
                  <BreadcrumbPage>{formatSegment(segment)}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink asChild>
                    <Link href={href}>{formatSegment(segment)}</Link>
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>
            </Fragment>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
```

---

## 7.4. Стратегия responsive-брейкпоинтов

### Mobile-first подход Tailwind v4

Tailwind использует **mobile-first** систему: стили без префикса применяются ко всем экранам, префикс `md:` -- от 768px и выше. Это означает, что базовые стили пишутся для мобильных устройств.

### Стандартные брейкпоинты + кастомные

```css
/* globals.css */
@theme {
  /* Стандартные Tailwind v4 брейкпоинты: */
  /* sm: 640px, md: 768px, lg: 1024px, xl: 1280px, 2xl: 1536px */

  /* Кастомные для enterprise-дашбордов: */
  --breakpoint-3xl: 1920px; /* Full HD мониторы */
  --breakpoint-4xl: 2560px; /* 2K мониторы */
}
```

### Стратегия для dashboard-компонентов

| Брейкпоинт        | Ширина    | Layout | Sidebar             | Колонки KPI                |
| ----------------- | --------- | ------ | ------------------- | -------------------------- |
| **Base** (mobile) | < 640px   | Стек   | Sheet (overlay)     | 1 колонка                  |
| **sm**            | >= 640px  | Стек   | Sheet (overlay)     | 2 колонки                  |
| **md**            | >= 768px  | Grid   | Свернутый (icon)    | 2 колонки                  |
| **lg**            | >= 1024px | Grid   | Развернутый (256px) | 3 колонки                  |
| **xl**            | >= 1280px | Grid   | Развернутый         | 4 колонки                  |
| **2xl**           | >= 1536px | Grid   | Развернутый         | 4 колонки + боковая панель |

### Применение в компонентах

```tsx
// KPI-карточки: адаптивная сетка
<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
  <KPICard title="Revenue" value="$124,500" trend={+12.5} />
  <KPICard title="Users" value="12,340" trend={+5.2} />
  <KPICard title="Orders" value="1,234" trend={-2.1} />
  <KPICard title="Conversion" value="3.2%" trend={+0.8} />
</div>

// Графики: полная ширина на мобильном, 2 колонки на десктопе
<div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
  <AreaChartWidget />
  <BarChartWidget />
</div>

// Таблица: горизонтальный скролл на мобильном
<div className="overflow-x-auto">
  <DataTable columns={columns} data={data} />
</div>
```

### Container queries -- будущее responsive

```tsx
// Tailwind v4 поддерживает container queries нативно:
<div className="@container">
  <div className="grid grid-cols-1 @md:grid-cols-2 @lg:grid-cols-3">
    {/* Карточки адаптируются к размеру контейнера, а не viewport */}
  </div>
</div>
```

Container queries позволяют виджетам адаптироваться к размеру **родительского контейнера**, а не viewport. Это критично для дашбордов, где один и тот же виджет может быть размещен в разных зонах разного размера.

---

# 8. Отображение данных (расширение)

## 8.1. TanStack Table: серверная пагинация, сортировка, фильтрация

### Архитектура: разделение client/server

Ключевой принцип -- `manualPagination`, `manualSorting`, `manualFiltering`. Когда эти опции включены, TanStack Table **не обрабатывает данные сам**, а ожидает уже обработанные данные с сервера.

### Типы и интерфейсы

```ts
// types/table.ts
export interface PaginationState {
  pageIndex: number;
  pageSize: number;
}

export interface SortingState {
  id: string;
  desc: boolean;
}

export interface ColumnFilter {
  id: string;
  value: unknown;
}

export interface ServerTableResponse<T> {
  data: T[];
  pageCount: number;
  totalRows: number;
}

// URL search params формат для серверной обработки
export interface TableSearchParams {
  page?: string;
  per_page?: string;
  sort?: string; // "name.asc" или "name.desc"
  filters?: string; // JSON-строка фильтров
}
```

### Server Action для получения данных

```ts
// app/(dashboard)/users/actions.ts
'use server';

import { db } from '@/lib/db';
import { users } from '@/lib/db/schema';
import { asc, desc, like, eq, sql, and, type SQL } from 'drizzle-orm';
import type { TableSearchParams, ServerTableResponse } from '@/types/table';

export async function getUsers(params: TableSearchParams): Promise<ServerTableResponse<User>> {
  const page = Number(params.page) || 1;
  const perPage = Number(params.per_page) || 10;
  const offset = (page - 1) * perPage;

  // Сортировка
  const [sortField, sortOrder] = (params.sort ?? 'createdAt.desc').split('.');
  const orderBy =
    sortOrder === 'asc'
      ? asc(users[sortField as keyof typeof users])
      : desc(users[sortField as keyof typeof users]);

  // Фильтрация
  const conditions: SQL[] = [];
  if (params.filters) {
    const filters = JSON.parse(params.filters) as Array<{ id: string; value: string }>;
    for (const filter of filters) {
      if (filter.id === 'name') {
        conditions.push(like(users.name, `%${filter.value}%`));
      }
      if (filter.id === 'status') {
        conditions.push(eq(users.status, filter.value));
      }
    }
  }

  const where = conditions.length > 0 ? and(...conditions) : undefined;

  const [data, countResult] = await Promise.all([
    db.select().from(users).where(where).orderBy(orderBy).limit(perPage).offset(offset),
    db
      .select({ count: sql<number>`count(*)` })
      .from(users)
      .where(where),
  ]);

  const totalRows = countResult[0]?.count ?? 0;

  return {
    data,
    pageCount: Math.ceil(totalRows / perPage),
    totalRows,
  };
}
```

### Клиентский компонент таблицы с URL-синхронизацией

```tsx
// components/data-table/data-table.tsx
'use client';

import { useCallback, useMemo } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
  type PaginationState,
  type SortingState,
  type ColumnFiltersState,
} from '@tanstack/react-table';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { DataTablePagination } from './data-table-pagination';
import { DataTableToolbar } from './data-table-toolbar';

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  pageCount: number;
  totalRows: number;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  pageCount,
  totalRows,
}: DataTableProps<TData, TValue>) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Читаем состояние из URL
  const pagination: PaginationState = {
    pageIndex: Number(searchParams.get('page') ?? 1) - 1,
    pageSize: Number(searchParams.get('per_page') ?? 10),
  };

  const sorting: SortingState = useMemo(() => {
    const sort = searchParams.get('sort');
    if (!sort) return [];
    const [id, order] = sort.split('.');
    return [{ id, desc: order === 'desc' }];
  }, [searchParams]);

  // Обновляем URL при изменении состояния
  const updateSearchParams = useCallback(
    (updates: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value === null) params.delete(key);
        else params.set(key, value);
      }
      router.push(`${pathname}?${params.toString()}`);
    },
    [router, pathname, searchParams],
  );

  const table = useReactTable({
    data,
    columns,
    pageCount,
    state: { pagination, sorting },
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
    getCoreRowModel: getCoreRowModel(),
    onPaginationChange: (updater) => {
      const next = typeof updater === 'function' ? updater(pagination) : updater;
      updateSearchParams({
        page: String(next.pageIndex + 1),
        per_page: String(next.pageSize),
      });
    },
    onSortingChange: (updater) => {
      const next = typeof updater === 'function' ? updater(sorting) : updater;
      updateSearchParams({
        sort: next.length > 0 ? `${next[0].id}.${next[0].desc ? 'desc' : 'asc'}` : null,
        page: '1', // сброс на первую страницу при смене сортировки
      });
    },
  });

  return (
    <div className="space-y-4">
      <DataTableToolbar table={table} />
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <DataTablePagination table={table} totalRows={totalRows} />
    </div>
  );
}
```

### Column visibility (переключение колонок)

```tsx
// components/data-table/data-table-view-options.tsx
'use client';

import { type Table } from '@tanstack/react-table';
import { Settings2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface DataTableViewOptionsProps<TData> {
  table: Table<TData>;
}

export function DataTableViewOptions<TData>({ table }: DataTableViewOptionsProps<TData>) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="ml-auto hidden h-8 lg:flex">
          <Settings2 className="mr-2 size-4" />
          Columns
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-37.5">
        <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {table
          .getAllColumns()
          .filter((col) => col.getCanHide())
          .map((col) => (
            <DropdownMenuCheckboxItem
              key={col.id}
              className="capitalize"
              checked={col.getIsVisible()}
              onCheckedChange={(value) => col.toggleVisibility(!!value)}
            >
              {col.id}
            </DropdownMenuCheckboxItem>
          ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

---

## 8.2. TanStack Table: виртуальный скроллинг для больших датасетов

Когда датасет содержит тысячи строк и серверная пагинация нежелательна (например, оффлайн-режим), используется `@tanstack/react-virtual`.

```bash
pnpm add @tanstack/react-virtual
```

```tsx
// components/data-table/virtualized-table.tsx
'use client';

import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useReactTable, getCoreRowModel, flexRender, type ColumnDef } from '@tanstack/react-table';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

const ROW_HEIGHT = 48;

interface VirtualizedTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
}

export function VirtualizedTable<TData, TValue>({
  columns,
  data,
}: VirtualizedTableProps<TData, TValue>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const { rows } = table.getRowModel();

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 20, // рендерим 20 строк за пределами viewport для плавного скролла
  });

  return (
    <div ref={parentRef} className="h-150 overflow-auto rounded-md border">
      <Table>
        <TableHeader className="bg-background sticky top-0 z-10">
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {/* Верхний спейсер */}
          {virtualizer.getVirtualItems()[0]?.start > 0 && (
            <tr>
              <td style={{ height: virtualizer.getVirtualItems()[0].start }} />
            </tr>
          )}

          {virtualizer.getVirtualItems().map((virtualRow) => {
            const row = rows[virtualRow.index];
            return (
              <TableRow key={row.id} style={{ height: ROW_HEIGHT }}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            );
          })}

          {/* Нижний спейсер */}
          <tr>
            <td
              style={{
                height:
                  virtualizer.getTotalSize() - (virtualizer.getVirtualItems().at(-1)?.end ?? 0),
              }}
            />
          </tr>
        </TableBody>
      </Table>
    </div>
  );
}
```

**Производительность:** виртуальный скроллинг рендерит только видимые строки + `overscan`. 10,000 строк ведут себя как 50 -- DOM содержит только ~50-70 элементов.

---

## 8.3. Графики: Recharts -- настройка и типовые графики

### Установка и настройка

```bash
pnpm add recharts
```

### Обертка для responsive-графиков

```tsx
// components/charts/chart-container.tsx
'use client';

import { ResponsiveContainer } from 'recharts';

interface ChartContainerProps {
  children: React.ReactElement;
  height?: number;
}

export function ChartContainer({ children, height = 350 }: ChartContainerProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      {children}
    </ResponsiveContainer>
  );
}
```

### Area Chart (основной для revenue/traffic)

```tsx
// components/charts/area-chart-widget.tsx
'use client';

import { Area, AreaChart, CartesianGrid, XAxis, YAxis, Tooltip } from 'recharts';
import { ChartContainer } from './chart-container';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const data = [
  { month: 'Jan', revenue: 4000, expenses: 2400 },
  { month: 'Feb', revenue: 3000, expenses: 1398 },
  { month: 'Mar', revenue: 9800, expenses: 2000 },
  { month: 'Apr', revenue: 3908, expenses: 2780 },
  { month: 'May', revenue: 4800, expenses: 1890 },
  { month: 'Jun', revenue: 3800, expenses: 2390 },
];

export function AreaChartWidget() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Revenue vs Expenses</CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer>
          <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--chart-1))" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(var(--chart-1))" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="month" className="fill-muted-foreground text-xs" />
            <YAxis className="fill-muted-foreground text-xs" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--popover))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
              }}
            />
            <Area
              type="monotone"
              dataKey="revenue"
              stroke="hsl(var(--chart-1))"
              fill="url(#colorRevenue)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="expenses"
              stroke="hsl(var(--chart-2))"
              fill="none"
              strokeWidth={2}
              strokeDasharray="5 5"
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
```

### Bar Chart, Pie Chart, Line Chart -- краткие примеры

```tsx
// Bar Chart
import { Bar, BarChart, XAxis, YAxis, Tooltip } from 'recharts';

<BarChart data={data}>
  <XAxis dataKey="name" />
  <YAxis />
  <Tooltip />
  <Bar dataKey="value" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
</BarChart>;

// Pie Chart
import { Pie, PieChart, Cell, Tooltip } from 'recharts';

const COLORS = ['hsl(var(--chart-1))', 'hsl(var(--chart-2))', 'hsl(var(--chart-3))'];

<PieChart>
  <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
    {data.map((_, index) => (
      <Cell key={index} fill={COLORS[index % COLORS.length]} />
    ))}
  </Pie>
  <Tooltip />
</PieChart>;

// Line Chart
import { Line, LineChart, XAxis, YAxis, Tooltip, Legend } from 'recharts';

<LineChart data={data}>
  <XAxis dataKey="date" />
  <YAxis />
  <Tooltip />
  <Legend />
  <Line type="monotone" dataKey="users" stroke="hsl(var(--chart-1))" strokeWidth={2} dot={false} />
  <Line
    type="monotone"
    dataKey="sessions"
    stroke="hsl(var(--chart-2))"
    strokeWidth={2}
    dot={false}
  />
</LineChart>;
```

---

## 8.4. Tremor vs Recharts: руководство по выбору

### Архитектурное отличие

Tremor -- это **высокоуровневая обертка над Recharts** с нативной интеграцией Tailwind CSS. Tremor генерирует Recharts-компоненты внутри, но предоставляет упрощенный декларативный API.

### Когда что использовать

| Критерий                     | Recharts               | Tremor                           |
| ---------------------------- | ---------------------- | -------------------------------- |
| **Уровень контроля**         | Полный (SVG-примитивы) | Ограничен API                    |
| **Кастомные tooltip/legend** | Полная свобода         | Через props                      |
| **Скорость разработки**      | Средняя (больше кода)  | Высокая (1 компонент = 1 график) |
| **Bundle size**              | ~180 KB                | ~240 KB (Recharts + обертка)     |
| **Tailwind интеграция**      | Ручная (CSS vars)      | Нативная                         |
| **Кол-во типов графиков**    | 10+                    | 6 основных                       |
| **KPI-карточки**             | Нет (делать самим)     | Есть из коробки                  |
| **Темная тема**              | Ручная настройка       | Автоматическая                   |

### Рекомендация

- **Recharts**: когда нужны кастомные визуализации, нестандартные tooltip, анимации, комбинированные графики, интерактивные элементы (brush, zoom)
- **Tremor**: когда нужен быстрый MVP дашборда с KPI-карточками и стандартными графиками
- **Nivo**: избегать для enterprise -- плохая документация, сложная кастомизация

### Гибридный подход (рекомендуемый)

Начать с Tremor для быстрого прототипирования. Заменять отдельные графики на Recharts по мере роста требований к кастомизации. Поскольку Tremor использует Recharts внутри, миграция безболезненна.

---

## 8.5. KPI Card -- паттерн компонента

```tsx
// components/kpi-card.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowUpRight, ArrowDownRight, Minus, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface KPICardProps {
  title: string;
  value: string;
  trend?: number; // процент изменения, например +12.5 или -3.2
  trendLabel?: string; // "vs last month"
  icon?: LucideIcon;
  description?: string;
}

export function KPICard({
  title,
  value,
  trend,
  trendLabel,
  icon: Icon,
  description,
}: KPICardProps) {
  const TrendIcon =
    trend === undefined || trend === 0 ? Minus : trend > 0 ? ArrowUpRight : ArrowDownRight;

  const trendColor =
    trend === undefined || trend === 0
      ? 'text-muted-foreground'
      : trend > 0
        ? 'text-emerald-600 dark:text-emerald-400'
        : 'text-red-600 dark:text-red-400';

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-muted-foreground text-sm font-medium">{title}</CardTitle>
        {Icon && <Icon className="text-muted-foreground size-4" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {trend !== undefined && (
          <div className="mt-1 flex items-center gap-1">
            <TrendIcon className={cn('size-4', trendColor)} />
            <span className={cn('text-xs font-medium', trendColor)}>
              {trend > 0 ? '+' : ''}
              {trend}%
            </span>
            {trendLabel && <span className="text-muted-foreground text-xs">{trendLabel}</span>}
          </div>
        )}
        {description && <p className="text-muted-foreground mt-1 text-xs">{description}</p>}
      </CardContent>
    </Card>
  );
}
```

### Использование

```tsx
<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
  <KPICard
    title="Total Revenue"
    value="$45,231.89"
    trend={20.1}
    trendLabel="vs last month"
    icon={DollarSign}
  />
  <KPICard
    title="Subscriptions"
    value="+2,350"
    trend={180.1}
    trendLabel="vs last month"
    icon={Users}
  />
  <KPICard title="Sales" value="+12,234" trend={19} trendLabel="vs last month" icon={CreditCard} />
  <KPICard title="Active Now" value="573" trend={-2.5} trendLabel="vs last hour" icon={Activity} />
</div>
```

---

## 8.6. Empty State паттерны

Empty state -- критически важный UX-элемент. Три типа:

### Универсальный компонент

```tsx
// components/empty-state.tsx
import { type LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex min-h-100 flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
      <div className="bg-muted flex size-12 items-center justify-center rounded-full">
        <Icon className="text-muted-foreground size-6" />
      </div>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      <p className="text-muted-foreground mt-2 max-w-sm text-sm">{description}</p>
      {action && (
        <Button onClick={action.onClick} className="mt-6">
          {action.label}
        </Button>
      )}
    </div>
  );
}
```

### Три типа empty state

```tsx
// 1. Первый запуск (onboarding)
<EmptyState
  icon={Inbox}
  title="No projects yet"
  description="Get started by creating your first project. It only takes a minute."
  action={{ label: "Create Project", onClick: () => setOpen(true) }}
/>

// 2. Пустой результат поиска/фильтрации
<EmptyState
  icon={SearchX}
  title="No results found"
  description="Try adjusting your search or filter criteria to find what you're looking for."
  action={{ label: "Clear Filters", onClick: clearFilters }}
/>

// 3. Ошибка загрузки
<EmptyState
  icon={AlertCircle}
  title="Something went wrong"
  description="We couldn't load the data. Please try again or contact support if the issue persists."
  action={{ label: "Try Again", onClick: refetch }}
/>
```

---

## Итоговая карта компонентов

```
Dashboard Layout
+-- SidebarProvider
|   +-- AppSidebar (collapsible, nested nav, mobile sheet, Cmd+B)
|   +-- SidebarInset
|       +-- Header (SidebarTrigger + Breadcrumbs + Actions)
|       +-- Main Content
|           +-- KPI Cards (grid, responsive cols)
|           +-- Charts (Recharts/Tremor, ResponsiveContainer)
|           +-- DataTable (TanStack Table, server-side ops)
|           +-- EmptyState (onboarding / no results / error)

Данные:
  Server Action -> URL search params -> DataTable (manual pagination/sorting)
  Large datasets -> VirtualizedTable (@tanstack/react-virtual)

Графики:
  Стандартные -> Tremor (быстро, Tailwind-нативно)
  Кастомные -> Recharts (полный контроль)
  Не рекомендуется -> Nivo (плохая документация)
```

---

_Источники:_

- _[shadcn/ui Sidebar](https://ui.shadcn.com/docs/components/radix/sidebar)_
- _[TanStack Table Pagination Guide](https://tanstack.com/table/v8/docs/guide/pagination)_
- _[TanStack Table Sorting Guide](https://tanstack.com/table/v8/docs/guide/sorting)_
- _[Tailwind CSS Responsive Design](https://tailwindcss.com/docs/responsive-design)_
- _[Tremor](https://www.tremor.so/)_
- _[Recharts](https://recharts.org/)_
- _[Advanced Shadcn Table](https://next.jqueryscript.net/shadcn-ui/advanced-shadcn-table/)_
- _[AdminLTE: Build Admin Dashboard with shadcn/ui](https://adminlte.io/blog/build-admin-dashboard-shadcn-nextjs/)_
- _[Responsive Design Breakpoints 2025](https://dev.to/gerryleonugroho/responsive-design-breakpoints-2025-playbook-53ih)_
- _[Nivo vs Recharts](https://www.speakeasy.com/blog/nivo-vs-recharts)_
