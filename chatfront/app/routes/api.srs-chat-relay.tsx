import { json, type ActionFunctionArgs } from '@remix-run/node';
import { getUserFromSession } from '~/services/session.server'; // Assuming this gets user + token

// Define the expected request body structure (matching frontend payload)
interface RelayRequestBody {
    docId: string;
    message: string;
}

export async function action({ request }: ActionFunctionArgs) {
    if (request.method !== 'POST') {
        return json({ error: 'Method Not Allowed' }, { status: 405 });
    }

    // 1. Get User/Auth Token from session
    const user = await getUserFromSession(request);
    if (!user?.access_token) {
        return json({ error: 'Unauthorized' }, { status: 401 });
    }

    try {
        // 2. Parse incoming request body from frontend
        const { docId, message }: RelayRequestBody = await request.json();

        if (!docId || !message) {
             return json({ error: 'Missing required fields: docId and message' }, { status: 400 });
        }

        // 3. Prepare request for the actual backend
        const backendUrl = 'http://chatback:8000/api/v1/srs-chat'; 
        const backendPayload = {
            doc_id: docId,
            message: message,
        };

        // 4. Fetch from the actual backend service (server-to-server)
        const backendResponse = await fetch(backendUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${user.access_token}`
            },
            body: JSON.stringify(backendPayload)
        });

        // 5. Handle backend response
        if (!backendResponse.ok) {
            let errorDetail = `Backend Error: ${backendResponse.status} ${backendResponse.statusText}`;
            try {
                const errorJson = await backendResponse.json();
                errorDetail = errorJson.detail || errorDetail; // Use backend's detail if available
            } catch (e) { /* Ignore if response is not JSON */ }
            console.error("Backend API call failed:", errorDetail);
            // Return the backend's status and error message if possible
            return json({ error: errorDetail }, { status: backendResponse.status }); 
        }

        const backendData = await backendResponse.json();

        // 6. Return backend data to the frontend
        return json(backendData); // Contains { response: "agent message" }

    } catch (error) {
        console.error('Error in SRS chat relay:', error);
        const errorMessage = error instanceof Error ? error.message : 'Internal Server Error';
        // Handle JSON parsing errors or other unexpected issues
        if (error instanceof SyntaxError) {
             return json({ error: 'Invalid request format.' }, { status: 400 });
        }
        return json({ error: errorMessage }, { status: 500 });
    }
}

// Optional: Add a loader function if you ever need to GET this route, 
// otherwise it might return a 405 Method Not Allowed for GET requests.
// export async function loader() {
//   return json({ message: "Use POST to chat." }, { status: 405 });
// } 