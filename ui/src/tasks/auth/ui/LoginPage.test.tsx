import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readSession, writeSession } from '@/shared/api/session';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import { clearPendingOtps } from '../mock';
import { LoginPage, toPhoneDigits } from './LoginPage';

const replace = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }));

function setup() {
  render(
    <I18nProvider>
      <LoginPage />
    </I18nProvider>,
  );
}

describe('LoginPage', () => {
  beforeEach(() => {
    replace.mockClear();
    clearPendingOtps();
    act(() => writeSession(null));
  });

  it('rejects a short phone number', async () => {
    setup();
    await userEvent.type(screen.getByLabelText('Phone number'), '123');
    await userEvent.click(screen.getByRole('button', { name: 'Send code' }));
    expect(screen.getByText('Enter a 10-digit phone number.')).toBeInTheDocument();
    expect(screen.queryByLabelText('6-digit code')).not.toBeInTheDocument();
  });

  it('stops at ten digits', async () => {
    setup();
    const field = screen.getByLabelText('Phone number');
    await userEvent.type(field, '98765432109999');
    expect(field).toHaveValue('9876543210');
  });

  it('ignores anything that is not a digit', async () => {
    setup();
    const field = screen.getByLabelText('Phone number');
    await userEvent.type(field, '98a7-6 5');
    expect(field).toHaveValue('98765');
  });

  it.each([
    ['+91 98765 43210', '9876543210'],
    ['+919876543210', '9876543210'],
    ['919876543210', '9876543210'],
    ['9198765432', '9198765432'],
    ['91987654321', '9198765432'],
  ])('reads %s as %s', (input, expected) => {
    expect(toPhoneDigits(input)).toBe(expected);
  });

  it('signs in with phone and code', async () => {
    setup();
    await userEvent.type(screen.getByLabelText('Phone number'), '9000000002');
    await userEvent.click(screen.getByRole('button', { name: 'Send code' }));
    await userEvent.type(await screen.findByLabelText('6-digit code'), '123456');
    await userEvent.click(screen.getByRole('button', { name: 'Verify and continue' }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/vendor'));
    expect(readSession()?.user.role).toBe('vendor');
  });

  it('shows an error for a wrong code', async () => {
    setup();
    await userEvent.type(screen.getByLabelText('Phone number'), '9000000002');
    await userEvent.click(screen.getByRole('button', { name: 'Send code' }));
    await userEvent.type(await screen.findByLabelText('6-digit code'), '000000');
    await userEvent.click(screen.getByRole('button', { name: 'Verify and continue' }));
    expect(await screen.findByText('That code is not correct.')).toBeInTheDocument();
    expect(readSession()).toBeNull();
  });

  it.each(['Household', 'Vendor', 'Admin'])('does not sign in from the %s demo button alone', async (role) => {
    setup();
    await userEvent.click(screen.getByRole('button', { name: role }));

    expect(await screen.findByLabelText('6-digit code')).toHaveValue('');
    expect(readSession()).toBeNull();
    expect(replace).not.toHaveBeenCalled();
  });

  it('needs the code after signing out and using another demo role', async () => {
    act(() => writeSession(null));
    setup();
    await userEvent.click(screen.getByRole('button', { name: 'Admin' }));
    await screen.findByLabelText('6-digit code');
    expect(screen.getByLabelText('Phone number')).toHaveValue('9000000003');
    await userEvent.click(screen.getByRole('button', { name: 'Verify and continue' }));
    expect(await screen.findByText('That code is not correct.')).toBeInTheDocument();
    expect(readSession()).toBeNull();
  });

  it('lets the user go back and use another number', async () => {
    setup();
    await userEvent.click(screen.getByRole('button', { name: 'Vendor' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Use a different number' }));
    expect(screen.queryByLabelText('6-digit code')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Phone number')).toBeEnabled();
  });

  it('sends a signed-in user to their own home', async () => {
    act(() =>
      writeSession({
        token: 't',
        user: { id: 'u', role: 'admin', full_name: 'A', phone: '1', preferred_lang: 'en' },
      }),
    );
    setup();
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/admin'));
  });
});
