import { act, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writeSession } from '@/shared/api/session';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import { RequireRole } from './RequireRole';

const replace = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }));

function setup() {
  render(
    <I18nProvider>
      <RequireRole role="vendor">
        <p>secret</p>
      </RequireRole>
    </I18nProvider>,
  );
}

const session = (role: 'vendor' | 'household') => ({
  token: 't',
  user: { id: 'u', role, full_name: 'N', phone: '1', preferred_lang: 'en' as const },
});

describe('RequireRole', () => {
  beforeEach(() => {
    replace.mockClear();
    act(() => writeSession(null));
  });

  it('sends a signed-out visitor to login', () => {
    setup();
    expect(replace).toHaveBeenCalledWith('/login');
    expect(screen.queryByText('secret')).not.toBeInTheDocument();
  });

  it('sends the wrong role to its own home', () => {
    act(() => writeSession(session('household')));
    setup();
    expect(replace).toHaveBeenCalledWith('/household');
    expect(screen.queryByText('secret')).not.toBeInTheDocument();
  });

  it('shows the page to the right role', () => {
    act(() => writeSession(session('vendor')));
    setup();
    expect(screen.getByText('secret')).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });
});
