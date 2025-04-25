import type { ChatSession, Message, MessageResponse } from '../types/chat.types';
import type { CustomUser } from '../types/auth.types';

let CHATBACK_URL: string;

// Initialize the URL based on the environment
if (typeof window !== 'undefined') {
  // Client-side
  CHATBACK_URL = (window as any).ENV.PUBLIC_CHATBACK_URL || 'http://localhost:8000';
} else {
  // Server-side
  CHATBACK_URL = process.env.CHATBACK_URL || 'http://localhost:8000';
}

// Only log in client environment
if (typeof window !== 'undefined') {
  // console.log('Configured CHATBACK_URL (Client):', CHATBACK_URL);
}

interface ApiResponse<T> {
  data?: T;
  error?: string;
}

// Added type for transcription response data
interface TranscriptionResponse {
  transcription: string;
}

function getAuthHeader(user: CustomUser): string {
  const tokenType = user.token_type.charAt(0).toUpperCase() + user.token_type.slice(1).toLowerCase();
  return `${tokenType} ${user.access_token}`;
}

async function handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    
    // Handle authentication errors
    if (response.status === 401 || error?.detail === 'Could not validate credentials') {
      window.location.href = `/login?redirectTo=${window.location.pathname}`;
      return { error: 'Session expired. Please log in again.' };
    }
    
    return {
      error: error?.detail || `API error: ${response.status} ${response.statusText}`
    };
  }

  try {
    const data = await response.json();
    return { data };
  } catch (error) {
    return {
      error: 'Failed to parse response'
    };
  }
}

const defaultHeaders = (user: CustomUser, omitContentType: boolean = false) => {
  const headers: Record<string, string> = {
    'Authorization': getAuthHeader(user),
    'Accept': 'application/json',
  };
  // Content-Type is handled by FormData when sending files
  if (!omitContentType) {
      headers['Content-Type'] = 'application/json';
  }
  return headers;
};

export const chatApi = {
  async getSessions(user: CustomUser): Promise<ApiResponse<ChatSession[]>> {
    try {
      // console.log('Fetching sessions...');
      // console.log('Using CHATBACK_URL:', CHATBACK_URL);
      // console.log('Auth header:', getAuthHeader(user));
      
      const response = await fetch(`${CHATBACK_URL}/api/v1/chat/sessions`, {
        headers: defaultHeaders(user),
        mode: 'cors'
      });
      
      // console.log('Sessions response status:', response.status);
      const result = await handleResponse<ChatSession[]>(response);
      // console.log('Sessions response:', result);
      return result;
    } catch (error) {
      console.error('Error fetching sessions:', error);
      return {
        error: error instanceof Error ? error.message : 'Failed to fetch sessions'
      };
    }
  },

  async getSession(user: CustomUser, sessionId: number): Promise<ApiResponse<ChatSession>> {
    try {
      const response = await fetch(`${CHATBACK_URL}/api/v1/chat/sessions/${sessionId}`, {
        headers: defaultHeaders(user),
        mode: 'cors'
      });
      return handleResponse<ChatSession>(response);
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Failed to fetch session'
      };
    }
  },

  async createChatSession(title: string, user: CustomUser): Promise<ApiResponse<ChatSession>> {
    try {
      // console.log('Creating chat session with title:', title);
      // console.log('Auth header:', getAuthHeader(user));
      
      const response = await fetch(`${CHATBACK_URL}/api/v1/chat/sessions`, {
        method: 'POST',
        headers: defaultHeaders(user),
        mode: 'cors',
        body: JSON.stringify({ title })
      });

      // console.log('Response status:', response.status);
      const responseText = await response.text();
      // console.log('Response text:', responseText);

      if (!response.ok) {
        return {
          error: `Failed to create chat session: ${response.status} ${response.statusText}\n${responseText}`
        };
      }

      try {
        const data = JSON.parse(responseText);
        return { data };
      } catch (error) {
        console.error('Failed to parse response:', error);
        return {
          error: 'Failed to parse server response'
        };
      }
    } catch (error) {
      console.error('Failed to create chat session:', error);
      return {
        error: error instanceof Error ? error.message : 'Failed to create session'
      };
    }
  },

  async deleteSession(user: CustomUser, sessionId: number): Promise<ApiResponse<void>> {
    try {
      const response = await fetch(`${CHATBACK_URL}/api/v1/chat/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: defaultHeaders(user),
        mode: 'cors'
      });
      return handleResponse<void>(response);
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Failed to delete session'
      };
    }
  },

  async sendMessage(
    user: CustomUser,
    sessionId: number,
    content: string
  ): Promise<ApiResponse<Message>> {
    try {
      const message_uuid = crypto.randomUUID();
      const response = await fetch(`${CHATBACK_URL}/api/v1/chat/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: defaultHeaders(user),
        mode: 'cors',
        body: JSON.stringify({ content, message_uuid })
      });

      const apiResponse = await handleResponse<MessageResponse>(response);
      
      if (apiResponse.error) {
        return { error: apiResponse.error };
      }
      if (!apiResponse.data) {
        return { error: 'No data received from server' };
      }

      // Convert MessageResponse to Message
      const message: Message = {
        id: apiResponse.data.message_uuid,
        role: 'ASSISTANT',
        content: apiResponse.data.message,
        created_at: new Date().toISOString(),
        message_uuid: apiResponse.data.message_uuid,
        progress: apiResponse.data.progress
      };

      return { data: message };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Failed to send message'
      };
    }
  },

  async getMessages(user: CustomUser, sessionId: number): Promise<ApiResponse<Message[]>> {
    try {
      const response = await fetch(`${CHATBACK_URL}/api/v1/chat/sessions/${sessionId}/messages`, {
        headers: defaultHeaders(user),
        mode: 'cors'
      });

      const apiResponse = await handleResponse<Message[]>(response);
      if (apiResponse.error) {
        return { error: apiResponse.error };
      }
      if (!apiResponse.data) {
        return { error: 'No messages received from server' };
      }

      return { data: apiResponse.data };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Failed to fetch messages'
      };
    }
  },

  // New method for audio transcription
  async transcribeAudio(
      user: CustomUser,
      sessionId: number, // Include session ID for context if needed by backend
      audioBlob: Blob
  ): Promise<ApiResponse<TranscriptionResponse>> {
    try {
      const formData = new FormData();
      // Use a filename that includes the session ID, could be useful on backend
      const filename = `session_${sessionId}_recording.${audioBlob.type.split('/')[1]?.split(';')[0] || 'audio'}`;
      formData.append('file', audioBlob, filename);
      // Optional: send session ID as separate field if backend needs it
      // formData.append('session_id', sessionId.toString());

      // console.log(`Sending audio to ${CHATBACK_URL}/api/v1/stt/transcribe, filename: ${filename}`);

      const response = await fetch(`${CHATBACK_URL}/api/v1/stt/transcribe`, {
        method: 'POST',
        // Omit Content-Type header, let browser set it for FormData
        headers: defaultHeaders(user, true),
        mode: 'cors',
        body: formData,
      });

      return handleResponse<TranscriptionResponse>(response);
    } catch (error) {
      console.error('Error sending audio for transcription:', error);
      return {
        error: error instanceof Error ? error.message : 'Failed to send audio'
      };
    }
  }
}; 