import { redirect } from 'next/navigation';

export default function SearchPage({ searchParams }) {
  const params = new URLSearchParams();

  const query = searchParams?.query;
  if (query) params.set('query', query);

  const categoryId = searchParams?.category_id;
  if (categoryId) params.set('category_id', categoryId);

  const typeId = searchParams?.type_id;
  if (typeId) params.set('type_id', typeId);

  const qs = params.toString();
  redirect(qs ? `/?${qs}` : '/');
}
