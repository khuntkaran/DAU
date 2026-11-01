import { RequireRole } from '@/shared/ui/RequireRole';
import { NewRequestPage } from '@/tasks/new-request/ui/NewRequestPage';

export default function Page() {
  return (
    <RequireRole role="household">
      <NewRequestPage />
    </RequireRole>
  );
}
