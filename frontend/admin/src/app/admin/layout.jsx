'use client';

import { Sidebar } from '@/widgets/Sidebar';
import { AuthProvider } from '@/features/auth';
import { ToastProvider } from '@/shared/hooks/useToast';
import { QueryProvider } from '@/shared/query';
import styles from './layout.module.css';

export default function AdminLayout({ children }) {
  return (
    <QueryProvider>
      <AuthProvider>
        <ToastProvider>
          <div className="bg-app-panel min-h-screen w-full">
            <div className="flex min-h-screen w-full flex-col md:flex-row">
              <Sidebar />
              <main className="min-w-0 flex-1 p-5 md:px-9 md:py-7">
                <div className={styles.scaleOuter}>
                  <div className={styles.scaleInner}>{children}</div>
                </div>
              </main>
            </div>
          </div>
        </ToastProvider>
      </AuthProvider>
    </QueryProvider>
  );
}
