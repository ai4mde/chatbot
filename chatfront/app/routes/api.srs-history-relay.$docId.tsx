import { json, type LoaderFunctionArgs, type ActionFunctionArgs } from '@remix-run/node';
import { getUserFromSession } from '~/services/session.server';

export async function loader({ request, params }: LoaderFunctionArgs) {
    // Ensure it's a GET request (loaders only handle GET)
    if (request.method !== 'GET') {
        return json({ error: 'Method Not Allowed' }, { status: 405 });
    }

    const docId = params.docId;
    if (!docId) {
        return json({ error: 'Missing document ID' }, { status: 400 });
    }

    // 1. Get User/Auth Token from session
    const user = await getUserFromSession(request);
    if (!user?.access_token) {
        return json({ error: 'Unauthorized' }, { status: 401 });
    }

    try {
        // 2. Prepare request for the actual backend history endpoint
        const backendUrl = `http://chatback:8000/api/v1/srs-chat/history/${docId}`;

        // 3. Fetch history from the actual backend service (server-to-server)
        const backendResponse = await fetch(backendUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${user.access_token}` // Pass token
            }
        });

        // 4. Handle backend response
        if (!backendResponse.ok) {
            let errorDetail = `Backend History Error: ${backendResponse.status} ${backendResponse.statusText}`;
            try {
                const errorJson = await backendResponse.json();
                errorDetail = errorJson.detail || errorDetail; 
            } catch (e) { /* Ignore */ }
            console.error("Backend API history call failed:", errorDetail);
            return json({ error: errorDetail }, { status: backendResponse.status }); 
        }

        const backendData = await backendResponse.json(); // Should contain { full_history: [...] }

        // 5. Return backend history data to the frontend
        return json(backendData);

    } catch (error) {
        console.error('Error in SRS history relay:', error);
        const errorMessage = error instanceof Error ? error.message : 'Internal Server Error';
        return json({ error: errorMessage }, { status: 500 });
    }
}

export async function action({ request, params }: ActionFunctionArgs) {
    const docId = params.docId;
    if (!docId) {
        return json({ error: 'Missing document ID' }, { status: 400 });
    }

    if (request.method !== 'DELETE') {
        return json({ error: 'Method Not Allowed' }, { status: 405 });
    }

    // 1. Get User/Auth Token from session
    const user = await getUserFromSession(request);
    if (!user?.access_token) {
        return json({ error: 'Unauthorized' }, { status: 401 });
    }

    try {
        // 2. Prepare request for the actual backend delete history endpoint
        const backendUrl = `http://chatback:8000/api/v1/srs-chat/history/${docId}`;

        // 3. Call the backend service to delete history
        const backendResponse = await fetch(backendUrl, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${user.access_token}`,
            },
        });

        // 4. Handle backend response
        if (!backendResponse.ok) {
            let errorDetail = `Backend Delete Error: ${backendResponse.status} ${backendResponse.statusText}`;
            try {
                const errorJson = await backendResponse.json();
                errorDetail = errorJson.detail || errorDetail; 
            } catch (e) { /* Ignore if response is not JSON */ }
            console.error("Backend API delete history call failed:", errorDetail);
            return json({ error: errorDetail }, { status: backendResponse.status }); 
        }

        // If backend returns no content (204) or some success message (200/202)
        if (backendResponse.status === 204) {
            return new Response(null, { status: 204 }); // Relay No Content
        }        
        // Try to parse JSON if not 204, in case backend sends a success message body
        const backendData = await backendResponse.json(); 
        return json(backendData, { status: backendResponse.status });

    } catch (error) {
        console.error('Error in SRS history delete relay:', error);
        const errorMessage = error instanceof Error ? error.message : 'Internal Server Error during delete';
        return json({ error: errorMessage }, { status: 500 });
    }
} 