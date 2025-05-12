import React from 'react';
import { Trash2 } from 'lucide-react'; // Ensure this import is correct and present

// Define the Message type matching the backend schema
interface Message {
  sender: 'user' | 'agent';
  text: string;
}

interface ChatWindowProps {
  onClose: () => void;
  docId: string;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ onClose, docId }) => {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [inputValue, setInputValue] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);
  const [isHistoryLoading, setIsHistoryLoading] = React.useState(true);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  // Function to scroll to the bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Effect to load history on mount
  React.useEffect(() => {
    const fetchHistory = async () => {
        setIsHistoryLoading(true);
        let historyLoadedSuccessfully = false;
        let loadedMessages: Message[] = [];

        try {
            if (!docId) {
                console.warn("docId is not available, skipping history fetch.");
                loadedMessages = [{ sender: 'agent', text: 'Cannot load chat: Document ID is missing.' }];
                setIsHistoryLoading(false);
                setMessages(loadedMessages);
                return;
            }
            const response = await fetch(`/api/srs-history-relay/${docId}`);
            if (!response.ok) {
                let errorMsg = `History Error: ${response.status} ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.error || errorMsg;
                } catch (e) { /* Ignore */ }
                throw new Error(errorMsg);
            }
            const data = await response.json();
            if (data.full_history && Array.isArray(data.full_history)) {
                loadedMessages = data.full_history;
                historyLoadedSuccessfully = true;
            } else {
                 console.warn("Received history response without valid full_history array.");
                 // Will fall through to the initial message logic if history is empty
            }
        } catch (error) {
            console.error("Failed to fetch chat history:", error);
            loadedMessages = [{ sender: 'agent', text: `Error loading history: ${error instanceof Error ? error.message : 'Unknown error'}` }];
        } finally {
            setIsHistoryLoading(false);
            const introductoryMessage: Message = {
                sender: 'agent',
                text: "Hello, I'm Agent Brown! I'm here to help you with UML diagrams in this document. You can ask me to create new class diagrams, or add, remove, or modify elements like classes, attributes, and methods in existing diagrams. For general text edits, please use the main editor."
            };

            if (loadedMessages.length === 0 && docId) { // If no history (or error message wasn't set to prevent this)
                setMessages([introductoryMessage]);
            } else if (historyLoadedSuccessfully && loadedMessages.length > 0) {
                // If history was loaded and it's not empty, prepend the intro if it's not already there (heuristic)
                // This is a bit tricky, as we don't want to add it every time. 
                // A better approach might be to only add it if the first message isn't it and the history isn't too long,
                // or have a separate flag. For now, let's only add if history is empty.
                setMessages(loadedMessages); 
            } else { // Handles cases where loadedMessages has an error message
                 setMessages(loadedMessages);
            }

            requestAnimationFrame(scrollToBottom);
        }
    };

    if (docId) { // Only run if docId is present
        fetchHistory();
    } else {
        // If no docId on initial mount, show a placeholder or the intro message directly
        setIsHistoryLoading(false);
        setMessages([
            {
                sender: 'agent',
                text: "Hello! I'm here to help you with UML diagrams in this document. You can ask me to create new class diagrams, or add, remove, or modify elements like classes, attributes, and methods in existing diagrams. For general text edits, please use the main editor."
            },
            { sender: 'agent', text: 'Document ID is missing. Chat functionality may be limited.' }
        ]);
    }
  }, [docId]);

  // Scroll to bottom whenever messages change
  React.useEffect(() => {
    // Only scroll if not currently loading initial history to avoid jumping
    // and if there's a docId (meaning chat is active)
    if (!isHistoryLoading && docId) {
        scrollToBottom();
    }
  }, [messages, isHistoryLoading, docId]);

  // Updated handleSend function to call backend API
  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = { sender: 'user', text: inputValue };
    const currentHistory = [...messages, userMessage];

    setMessages(currentHistory);
    setInputValue('');
    setIsLoading(true);
    scrollToBottom();

    try {
      // --- Call the Remix Relay Route --- 
      const response = await fetch('/api/srs-chat-relay', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          docId: docId,
          message: userMessage.text,
        })
      });

      // Check if the relay itself returned an error (e.g., 401, 404, 500)
      if (!response.ok) {
        let errorMsg = `Relay Error: ${response.status} ${response.statusText}`;
        try {
          const errorData = await response.json();
          // Use the error message provided by the relay action
          errorMsg = errorData.error || errorMsg; 
        } catch (e) { /* Ignore if response body isn't JSON */ }
        throw new Error(errorMsg);
      }

      // The successful response body is the data directly from the backend
      const data = await response.json();
      
      // Always update the messages state with the full history from the backend
      if (data.full_history && Array.isArray(data.full_history)) {
          setMessages(data.full_history);
      } else {
          // Fallback if history isn't returned, just show the latest response
          // (Might happen if Redis saving/loading failed)
          const agentResponse: Message = { sender: 'agent', text: data.response };
          // Append to existing messages instead of replacing
          setMessages(prev => [...prev, agentResponse]); 
      }
      
    } catch (error) {
      console.error("Failed to send message:", error);
      const errorText = error instanceof Error ? error.message : 'Sorry, I encountered an error. Please try again.';
      const errorResponse: Message = { sender: 'agent', text: errorText };
      // Append error message
      setMessages(prev => [...prev, errorResponse]);
    } finally {
      setIsLoading(false);
      // Ensure scroll happens after potential height change
      requestAnimationFrame(scrollToBottom); 
    }
  };

  const handleDeleteHistory = async () => {
    if (!docId) {
      console.error("Cannot delete history: Document ID is missing.");
      // Optionally, show an error to the user
      setMessages(prev => [...prev, { sender: 'agent', text: 'Error: Document ID is missing, cannot delete history.'}]);
      return;
    }

    // Confirmation dialog
    if (!window.confirm("Are you sure you want to delete the chat history for this document? This action cannot be undone.")) {
      return;
    }

    console.log(`Requesting to delete history for docId: ${docId}`);
    setIsLoading(true); // Use general loading state or a new one for deletion

    try {
      const response = await fetch(`/api/srs-history-relay/${docId}`, {
        method: 'DELETE',
        headers: {
          // No Content-Type needed for DELETE with no body, but Authorization might be if not handled by session
          // 'Authorization': `Bearer ${token}`, // If your relay needs it explicitly
        }
      });

      if (!response.ok) {
        let errorMsg = `Delete Error: ${response.status} ${response.statusText}`;
        if (response.status !== 204) { // 204 No Content might not have a JSON body
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) { /* Ignore if response body isn't JSON or if it's a 204*/ }
        }
        throw new Error(errorMsg);
      }

      setMessages([]); // Clear messages locally on successful deletion
      console.log(`History for docId: ${docId} deleted successfully.`);
      // Optionally, show a success message that auto-dismisses or provide a subtle feedback
      // For example, briefly change the icon or show a small toast.

    } catch (error) {
      console.error("Failed to delete chat history:", error);
      const errorText = error instanceof Error ? error.message : 'Could not delete history.';
      setMessages(prev => [...prev, { sender: 'agent', text: `Error deleting history: ${errorText}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed bottom-[calc(3.5rem+1.25rem)] right-5 mb-2 flex flex-col w-[35%] h-[50%] bg-card border border-border rounded-lg shadow-xl overflow-hidden z-40 text-card-foreground">
      {/* Header */}
      <div className="flex justify-between items-center p-2 bg-muted border-b border-border">
        <h3 className="text-sm font-semibold text-muted-foreground">Chat with Document</h3>
        <div className="flex items-center space-x-1">
          {/* Conditionally render the delete button */}
          {!isHistoryLoading && messages.length > 0 && (
            <button 
              onClick={handleDeleteHistory} 
              className="text-muted-foreground hover:text-destructive p-1 rounded-full hover:bg-destructive/10"
              title="Delete chat history"
              disabled={isLoading} // Only disable if an action (send/delete) is in progress
            >
              <Trash2 size={16} />
            </button>
          )}
          {/* Use theme colors for close button */}
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground p-1 rounded-full hover:bg-accent">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
          </button>
        </div>
      </div>

      {/* Message Area - Use background color */}
      <div className="flex-1 p-2 overflow-y-auto space-y-2 bg-background">
        {/* Show loading indicator for initial history load */}
        {isHistoryLoading && (
             <div className="flex justify-center items-center h-full">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
             </div>
        )}
        {!isHistoryLoading && messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            {/* Apply theme colors to messages */}
            <div className={`p-2 rounded-lg text-sm ${msg.sender === 'user' ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'}`} style={{maxWidth: '80%'}}>
               {msg.text}
            </div>
          </div>
        ))}
        {!isHistoryLoading && isLoading && (
            <div className="flex justify-center">
                {/* Use muted foreground for loading text */}
                <p className="text-xs text-muted-foreground italic">Agent is thinking...</p>
            </div>
        )}
        {/* Div to mark the end of messages for scrolling */}
        <div ref={messagesEndRef} /> 
      </div>

      {/* Input Area - Use theme colors */}
      <div className="p-2 border-t border-border bg-background flex items-center">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSend()}
          placeholder="Ask something..."
          className="flex-1 bg-input border border-input text-foreground rounded-l-md px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring mr-[-1px]"
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          className="bg-primary hover:bg-primary/90 text-primary-foreground rounded-r-md px-3 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50 flex items-center justify-center h-[30px] w-[50px]"
          disabled={isLoading || !inputValue.trim()}
        >
          {isLoading ?
             <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-foreground"></div>
            :
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          }
        </button>
      </div>
    </div>
  );
};

export default ChatWindow; 