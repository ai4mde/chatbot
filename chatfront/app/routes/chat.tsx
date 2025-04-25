import * as React from 'react';
import { useState, useRef, useEffect } from 'react';
import { json, redirect } from '@remix-run/node';
import type { LoaderFunction, ActionFunction } from '@remix-run/node';
import { useChat } from '../hooks/use-chat';
import { ChatHeader } from '../components/chat/chat-header';
import { ChatInput } from '../components/chat/chat-input';
import { ChatMessage } from '../components/chat/chat-message';
import { NewChatDialog } from '../components/chat/new-chat-dialog';
import { Alert, AlertDescription } from '../components/ui/alert';
import { requireUser, logout } from '../services/session.server';
import { ScrollArea } from '../components/ui/scroll-area';
import { Card } from '../components/ui/card';
import { cn } from '../lib/utils';
import { SessionTimeoutWarning } from '../components/layout/session-timeout-warning';
import { useNavigate, useLoaderData, Form } from '@remix-run/react';

export const loader: LoaderFunction = async ({ request }) => {
  try {
    const user = await requireUser(request);
    return json({
      user,
      sessionTimeoutMinutes: Number(process.env.SESSION_TIMEOUT_MINUTES) || 30
    });
  } catch (error) {
    return redirect('/login?redirectTo=/chat');
  }
};

export const action: ActionFunction = async ({ request }) => {
  if (request.method === 'POST') {
    return logout(request);
  }
  return null;
};

export default function Chat() {
  const { user, sessionTimeoutMinutes } = useLoaderData<typeof loader>();
  // console.log('Chat component rendered with user:', user?.id);
  
  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    handleAudioSubmit,
    isLoading,
    error,
    startNewChat,
    sessions,
    currentSession,
    selectChat,
    deleteChat,
    progress,
  } = useChat(user);
  
  const [isNewChatOpen, setIsNewChatOpen] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const isAutoScrollEnabled = useRef(true);
  const lastMessageRef = useRef<HTMLDivElement>(null);

  // Add initialization effect
  useEffect(() => {
    // console.log('Initialization effect:', { isLoading, sessions, error });
    if (!isLoading) {
      setIsInitializing(false);
    }
  }, [isLoading, sessions, error]);

  // Auto scroll to bottom when messages change
  useEffect(() => {
    if (scrollAreaRef.current && isAutoScrollEnabled.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [messages, isLoading]);

  useEffect(() => {
    const scrollContainer = scrollAreaRef.current?.querySelector('[data-radix-scroll-area-viewport]');
    if (!scrollContainer) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
      const isNearBottom = scrollHeight - (scrollTop + clientHeight) < 100;
      isAutoScrollEnabled.current = isNearBottom;
    };

    scrollContainer.addEventListener('scroll', handleScroll);
    return () => scrollContainer.removeEventListener('scroll', handleScroll);
  }, []);

  const handleNewChat = async (title: string) => {
    await startNewChat(title);
    setIsNewChatOpen(false);
  };

  const handleTimeout = () => {
    const form = document.getElementById('logoutForm') as HTMLFormElement;
    if (form) {
      form.submit();
    }
  };

  if (isInitializing) {
    return (
      <div className='container py-8 mx-auto'>
        <Card className='h-[calc(100vh-16rem)] flex flex-col border-0 items-center justify-center'>
          <div className='animate-pulse space-y-4'>
            <div className='h-4 w-48 bg-muted rounded'></div>
            <div className='h-4 w-32 bg-muted rounded'></div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className='container py-8 mx-auto'>
      <Card className='h-[calc(100vh-16rem)] flex flex-col border-0'>
        <ChatHeader 
          isLoading={isLoading}
          onNewChat={() => setIsNewChatOpen(true)}
          onSelectChat={selectChat}
          onClearChat={deleteChat}
          sessions={sessions}
          currentSession={currentSession}
          progress={progress ?? 0}
        />
        <ScrollArea ref={scrollAreaRef} className='flex-1 p-4'>
          {messages.map((message, index) => (
            <div
              key={message.id}
              ref={index === messages.length - 1 ? lastMessageRef : null}
              className={cn(
                'mb-4',
                message.role === 'ASSISTANT' ? 'pl-2' : 'pr-2'
              )}
            >
              <ChatMessage
                message={message}
                isLoading={isLoading && index === messages.length - 1}
              />
            </div>
          ))}
          {error && (
            <Alert variant='destructive' className='mt-4'>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </ScrollArea>
        <div className='p-4 border-t'>
          <ChatInput
            input={input}
            handleInputChange={handleInputChange}
            handleSubmit={handleSubmit}
            handleAudioSubmit={handleAudioSubmit}
            isLoading={isLoading}
            hasActiveSession={Boolean(currentSession)}
          />
        </div>
      </Card>
      <NewChatDialog
        isOpen={isNewChatOpen}
        onClose={() => setIsNewChatOpen(false)}
        onCreateChat={handleNewChat}
      />
      <Form method='post' id='logoutForm' className='hidden' />
      <SessionTimeoutWarning 
        timeoutMinutes={sessionTimeoutMinutes}
        onTimeout={handleTimeout}
      />
    </div>
  );
} 