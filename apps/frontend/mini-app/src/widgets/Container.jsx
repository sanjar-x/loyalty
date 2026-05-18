import { cn } from '@/shared/lib/ui-utils';
import styles from './Container.module.css';

export default function Container({ children, className = '' }) {
  return <div className={cn(styles.root, className)}>{children}</div>;
}
