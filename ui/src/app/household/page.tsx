import { RequireRole } from '@/shared/ui/RequireRole';
import { MyRequestsPage } from '@/tasks/my-requests/ui/MyRequestsPage';

export default function Page() {
  return (
    <RequireRole role="household">
      <MyRequestsPage />
    </RequireRole>
  );
}
