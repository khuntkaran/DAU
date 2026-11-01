import { RequireRole } from '@/shared/ui/RequireRole';
import { AdminReviewPage } from '@/tasks/admin/ui/AdminReviewPage';

export default function Page() {
  return (
    <RequireRole role="admin">
      <AdminReviewPage />
    </RequireRole>
  );
}
