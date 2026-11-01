import { RequireRole } from '@/shared/ui/RequireRole';
import { QuoteFormPage } from '@/tasks/quote-form/ui/QuoteFormPage';

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <RequireRole role="vendor">
      <QuoteFormPage id={id} />
    </RequireRole>
  );
}
