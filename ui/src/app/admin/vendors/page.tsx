import { RequireRole } from '@/shared/ui/RequireRole';
import { AdminVendorsPage } from '@/tasks/admin/ui/AdminVendorsPage';

export default function Page() {
  return (
    <RequireRole role="admin">
      <AdminVendorsPage />
    </RequireRole>
  );
}
