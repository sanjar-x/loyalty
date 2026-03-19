'use client';

import { Sidebar } from '@/components/admin/Sidebar';
import { AuthProvider } from '@/hooks/useAuth';
import styles from './layout.module.css';

export default function AdminLayout({ children }) {
  return (
    <AuthProvider>
      <div className="min-h-screen w-full bg-[#ffffff]">
        <div className="flex min-h-screen w-full flex-col md:flex-row">
          <Sidebar />
          <main className="min-w-0 flex-1 p-5 md:px-9 md:py-7">
            <div className={styles.scaleOuter}>
              <div className={styles.scaleInner}>{children}</div>
            </div>
          </main>
        </div>
      </div>
    </AuthProvider>
  );
}
