import { RequireRole } from '@/shared/ui/RequireRole';
import { AdminRequestsPage } from '@/tasks/admin/ui/AdminRequestsPage';

export default function Page() {
  return (
    <RequireRole role="admin">
      <AdminRequestsPage />
    </RequireRole>
  );
}
