import { redirect } from 'next/navigation';

// Land on Brands — first item of the first section in SettingsLayout's
// NAV_SECTIONS (Каталог → Бренды). Previously redirected to referrals,
// which sat 4 sections deep and confused operators expecting the
// "Settings" landing page to mirror the sidebar order.
export default function SettingsPage() {
  redirect('/admin/settings/brands');
}
