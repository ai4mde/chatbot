import { createCookieSessionStorage, redirect } from '@remix-run/node';
import type { CustomUser } from '../types/auth.types';

// Session configuration
const sessionSecret = process.env.SESSION_SECRET;
if (!sessionSecret) {
  throw new Error('SESSION_SECRET must be set');
}

export const sessionStorage = createCookieSessionStorage({
  cookie: {
    name: '__session',
    httpOnly: true,
    path: '/',
    sameSite: 'lax',
    secrets: [sessionSecret],
    secure: process.env.NODE_ENV === 'production',
  },
});

// Get the session from the request
export async function getSession(request: Request) {
  const cookie = request.headers.get('Cookie');
  return sessionStorage.getSession(cookie);
}

// Create a new session with user data
export async function createUserSession(user: CustomUser, redirectTo: string) {
  const session = await sessionStorage.getSession();
  session.set('user', user);
  return redirect(redirectTo, {
    headers: {
      'Set-Cookie': await sessionStorage.commitSession(session),
    },
  });
}

// Get user from session
export async function getUserFromSession(request: Request): Promise<CustomUser | null> {
  const session = await getSession(request);
  const user = session.get('user');
  return user || null;
}

// Destroy session (logout)
export async function destroySession(request: Request) {
  const session = await getSession(request);
  return redirect('/login', {
    headers: {
      'Set-Cookie': await sessionStorage.destroySession(session),
    },
  });
}

// Helper to require authentication
export async function requireUser(request: Request) {
  console.log('requireUser: Starting');
  const user = await getUserFromSession(request);
  console.log('requireUser: User:', user);
  
  if (!user) {
    throw new Error('Unauthorized');
  }
  
  return user;
}

export async function logout(request: Request) {
  const session = await getSession(request);
  return redirect('/', {
    headers: {
      'Set-Cookie': await sessionStorage.destroySession(session)
    }
  });
}
