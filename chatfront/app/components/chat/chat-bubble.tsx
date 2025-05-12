import React, { useState } from 'react';
import ChatWindow from './chat-window';

// Define props for ChatBubble
interface ChatBubbleProps {
  docId: string;
}

const ChatBubble: React.FC<ChatBubbleProps> = ({ docId }) => {
  const [isOpen, setIsOpen] = useState(false);

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className="fixed bottom-5 right-5 z-50">
      {/* Chat Window - Conditionally render based on isOpen state */} 
      {isOpen && <ChatWindow onClose={toggleChat} docId={docId} />}

      {/* Bubble Button */} 
      {!isOpen && (
        <button
          onClick={toggleChat}
          className="bg-primary hover:bg-primary/90 text-primary-foreground rounded-full p-3 shadow-lg focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          aria-label="Open chat"
        >
           {/* Placeholder Icon - Decrease size */}
           <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
             <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.76c0 1.6 1.123 2.994 2.707 3.227 1.068.157 2.148.279 3.238.364.466.037.893.281 1.153.671L12 21l2.652-3.978c.26-.39.687-.634 1.153-.67 1.09-.086 2.17-.208 3.238-.365 1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
           </svg>
        </button>
      )}
    </div>
  );
};

export default ChatBubble; 