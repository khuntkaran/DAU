import { RequireRole } from '@/shared/ui/RequireRole';
import { VendorMapPage } from '@/tasks/vendor-map/ui/VendorMapPage';

export default function Page() {
  return (
    <RequireRole role="vendor">
      <VendorMapPage />
    </RequireRole>
  );
}
