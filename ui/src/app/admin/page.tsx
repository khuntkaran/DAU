import { RequireRole } from '@/shared/ui/RequireRole';
import { AdminPage } from '@/tasks/admin/ui/AdminPage';

export default function Page() {
  return (
    <RequireRole role="admin">
      <AdminPage />
    </RequireRole>
  );
}
