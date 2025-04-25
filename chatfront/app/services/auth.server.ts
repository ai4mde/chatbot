import { Authenticator } from 'remix-auth';
import { FormStrategy } from 'remix-auth-form';
import { sessionStorage } from './session.server';
import type { CustomUser } from '../types/auth.types';
import { jwtVerify } from 'jose';
import { TextEncoder } from 'util';

const CHATBACK_URL = process.env.CHATBACK_URL || 'http://localhost:8000';
const JWT_SECRET = process.env.JWT_SECRET_KEY || 'your-super-secret-key-here';

// Create an instance of the authenticator
export const authenticator = new Authenticator<CustomUser>(sessionStorage, {
  sessionKey: 'user', // key for storing the user in the session
  sessionErrorKey: 'error', // key for storing error messages
});

// Configure the form strategy
authenticator.use(
  new FormStrategy(async ({ form }) => {
    const username = form.get('username') as string;
    const password = form.get('password') as string;

    if (!username || !password) {
      throw new Error('Username and password are required');
    }

    try {
      console.log('Attempting login for user:', username);
      
      // Create form data for OAuth2 password flow
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const response = await fetch(`${CHATBACK_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json'
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        console.error('Login failed:', {
          status: response.status,
          statusText: response.statusText,
          error: errorData
        });
        
        if (errorData?.detail) {
          throw new Error(errorData.detail);
        }
        throw new Error(`Login failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Login response:', data);
      
      if (!data.access_token) {
        console.error('Invalid response data:', data);
        throw new Error('Invalid response from server');
      }

      // Decode the token to check the is_admin claim
      let isAdmin = false; // Default to false
      try {
        const secret = new TextEncoder().encode(JWT_SECRET);
        const { payload } = await jwtVerify(data.access_token, secret);
        console.log('Decoded token payload:', payload);
        // Check if is_admin exists and is true (boolean check)
        if (payload && typeof payload.is_admin === 'boolean') {
          isAdmin = payload.is_admin;
        } else {
             console.warn('is_admin claim missing or not a boolean in token for user:', username);
        }
      } catch (jwtError) {
        // Log error but don't necessarily fail login, just treat as non-admin
        console.error('Token verification/decoding failed during standard login:', jwtError);
        // Optionally, you could throw an error here if a valid token is strictly required
        // throw new Error('Invalid authentication token.'); 
      }

      // Create the user object from the response data, including is_admin
      const user: CustomUser = {
        id: data.id || username,
        username: data.username || username,
        group_name: data.group_name,
        access_token: data.access_token,
        token_type: (data.token_type || 'bearer').charAt(0).toUpperCase() + (data.token_type || 'bearer').slice(1),
        is_admin: isAdmin
      };

      console.log('Created user object:', user);
      return user;
    } catch (error) {
      console.error('Authentication error:', {
        error,
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined
      });
      throw error;
    }
  }),
  'form'
);

// Define the admin strategy
authenticator.use(
  new FormStrategy(async ({ form }) => {
    const username = form.get('username') as string;
    const password = form.get('password') as string;

    if (!username || !password) {
      throw new Error('Username and password are required');
    }

    try {
      console.log('[Admin] Attempting login for user:', username);
      
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const response = await fetch(`${CHATBACK_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json'
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        console.error('[Admin] Login failed:', { status: response.status, error: errorData });
        if (errorData?.detail) throw new Error(errorData.detail);
        throw new Error(`[Admin] Login failed: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('[Admin] Login response:', data);
      
      if (!data.access_token) {
        throw new Error('[Admin] Invalid response from server');
      }

      // Decode the token to check the is_admin claim
      try {
        const secret = new TextEncoder().encode(JWT_SECRET);
        const { payload } = await jwtVerify(data.access_token, secret, {
          // Add expected algorithms if needed, e.g., algorithms: ['HS256']
        });
        console.log('[Admin] Decoded token payload:', payload);
        
        if (!payload.is_admin) { // Check the is_admin flag from the token
          console.warn('[Admin] User is not an admin:', username);
          throw new Error('User does not have admin privileges.');
        }

        // Construct the user object for the session
        const user: CustomUser = {
          id: data.id || username,
          username: data.username || username,
          group_name: data.group_name,
          access_token: data.access_token,
          token_type: (data.token_type || 'bearer').charAt(0).toUpperCase() + (data.token_type || 'bearer').slice(1),
          is_admin: true // We confirmed this from the token
        };
        console.log('[Admin] Admin user authenticated:', user.username);
        return user;

      } catch (jwtError) {
        console.error('[Admin] Token verification/decoding failed:', jwtError);
        if (jwtError instanceof Error && jwtError.message === 'User does not have admin privileges.') {
             throw jwtError; // Re-throw the specific admin error
        }
        throw new Error('Invalid authentication token or structure.');
      }

    } catch (error) {
      console.error('[Admin] Authentication error:', error);
      throw error; // Re-throw the error to be handled by remix-auth
    }
  }),
  // Name the strategy 'admin-form'
  'admin-form' 
);

// Helper function to check if user is authenticated
export async function isAuthenticated(request: Request): Promise<boolean> {
  try {
    const user = await authenticator.authenticate('form', request, {
      failureRedirect: undefined,
    });
    return !!user;
  } catch {
    return false;
  }
}

// Helper function to get authenticated user
export async function getAuthenticatedUser(request: Request): Promise<CustomUser | null> {
  try {
    const clonedRequest = request.clone();
    return await authenticator.authenticate('form', clonedRequest, {
      failureRedirect: undefined,
    });
  } catch {
    return null;
  }
}
