import { RequireRole } from '@/shared/ui/RequireRole';
import { RequestDetailPage } from '@/tasks/my-requests/ui/RequestDetailPage';

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <RequireRole role="household">
      <RequestDetailPage id={id} />
    </RequireRole>
  );
}
