/**
 * Utility function to make authenticated fetch requests to the backend.
 * Automatically adds the Authorization header with the Bearer token.
 */
export async function fetchWithAuth(
  url: string,
  accessToken: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${accessToken}`);
  
  // Ensure Accept header is set, default to application/json if not provided
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }
  
  // If body is an object, stringify it and set Content-Type if not already set
  let body = options.body;
  if (body && typeof body === 'object' && !(body instanceof FormData) && !(body instanceof URLSearchParams) && !(body instanceof Blob) && !(body instanceof ArrayBuffer)) {
    try {
      body = JSON.stringify(body);
      if (!headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
      }
    } catch (e) {
      console.error("Failed to stringify body:", e);
      // Decide how to handle stringify error, maybe throw?
    }
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      body, // Use the potentially stringified body
    });
    return response;
  } catch (error) {
    console.error(`fetchWithAuth Error: Failed to fetch ${url}`, error);
    // Re-throw or handle as needed - perhaps return a generic error response?
    // For now, re-throwing to let the caller handle it.
    throw error;
  }
} 