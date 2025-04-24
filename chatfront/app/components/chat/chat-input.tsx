import * as React from 'react';
import { useRef, useEffect, useState, useCallback } from 'react';
import { Button } from '../ui/button';
import { SendHorizontal, MessageCircleOff, Mic, MicOff } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Textarea } from '../ui/textarea';

interface ChatInputProps {
  input: string;
  handleInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  handleSubmit: (e: React.FormEvent) => void;
  isLoading?: boolean;
  lastMessageId?: string;
  hasActiveSession: boolean;
}

// Type definition for SpeechRecognition (adjust if needed for different browsers)
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export function ChatInput({
  input,
  handleInputChange,
  handleSubmit,
  isLoading,
  lastMessageId,
  hasActiveSession
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null); // Ref to store SpeechRecognition instance

  // State for microphone functionality
  const [isRecording, setIsRecording] = useState(false);
  const [permissionStatus, setPermissionStatus] = useState<'idle' | 'pending' | 'granted' | 'denied'>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(false);

  useEffect(() => {
    // Feature detection
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setIsSupported(true);
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true; // Get interim results for live feedback
      recognition.lang = 'en-US'; // Default language, can be made configurable

      recognition.onstart = () => {
        console.log('Speech recognition started');
        setIsRecording(true);
        setErrorMessage(null);
        setPermissionStatus('granted'); // Assume granted if onstart fires
      };

      recognition.onend = () => {
        console.log('Speech recognition ended');
        setIsRecording(false);
      };

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        let errorMsg = 'An unknown error occurred.';
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          errorMsg = 'Microphone permission denied. Please enable it in browser settings.';
          setPermissionStatus('denied');
        } else if (event.error === 'no-speech') {
          errorMsg = 'No speech detected. Please try again.';
        } else if (event.error === 'audio-capture') {
          errorMsg = 'Microphone not found or not working.';
        } else if (event.error === 'network') {
          errorMsg = 'Network error during speech recognition.';
        }
        setErrorMessage(errorMsg);
        setIsRecording(false);
      };

      // Add onresult handler to process transcripts
      recognition.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript + ' ';
          } else {
            interimTranscript += transcript;
          }
        }

        console.log('Interim:', interimTranscript);
        console.log('Final:', finalTranscript);

        // Update the input field with the final transcript
        if (finalTranscript.trim()) {
          // Use the handleInputChange prop to update the parent state
          // We simulate a change event for compatibility with useChat hook
          const syntheticEvent = {
            target: { value: input + finalTranscript.trim() }, // Append to existing input
          } as React.ChangeEvent<HTMLTextAreaElement>; 
          handleInputChange(syntheticEvent);

          // Optional: Focus the textarea after transcription
          textareaRef.current?.focus();
        }
        
        // Optional: Update placeholder or state with interim results for live feedback
        // You could set another state variable here if you want to display interim results elsewhere
      };

      recognitionRef.current = recognition;
    } else {
      console.warn('SpeechRecognition API not supported in this browser.');
      setIsSupported(false);
    }
  }, []);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  useEffect(() => {
    if (!isLoading && textareaRef.current && hasActiveSession) {
      textareaRef.current.focus();
    }
  }, [isLoading, hasActiveSession]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSubmit(e);
  };

  const handleMicClick = useCallback(() => {
    if (!isSupported || !recognitionRef.current) {
      setErrorMessage('Speech recognition is not supported in your browser.');
      return;
    }

    if (permissionStatus === 'denied') {
        setErrorMessage('Microphone permission denied. Please enable it in browser settings.');
        return;
    }

    if (isRecording) {
      console.log('Stopping recording manually');
      recognitionRef.current.stop();
    } else {
      setPermissionStatus('pending'); // Indicate permission might be requested
      setErrorMessage(null); // Clear previous errors
      try {
        recognitionRef.current.start();
      } catch (error) {
        console.error("Error starting recognition:", error);
        setErrorMessage('Could not start microphone.');
        setPermissionStatus('idle'); // Reset status if start fails immediately
      }
    }
  }, [isSupported, isRecording, permissionStatus]);

  if (!hasActiveSession) {
    return (
      <div className='flex flex-col items-center justify-center p-8 text-center'>
        <MessageCircleOff className='h-8 w-8 mb-4 text-muted-foreground' />
        <p className='text-lg font-semibold'>
          No Active Chat
        </p>
        <p className='text-sm text-muted-foreground mt-1'>
          Please start a new chat or select an existing one to continue.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleFormSubmit}>
      <div className={cn(
        'relative flex items-center',
        'px-8 py-4',
        'max-w-7xl mx-auto w-full',
        'bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60'
      )}>
        <div className='relative w-full flex items-end space-x-2'>
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={
              isRecording ? 'Listening...' :
              permissionStatus === 'denied' ? 'Mic access denied' :
              errorMessage ? `Error: ${errorMessage}` :
              'Type your message or click the mic...'
            }
            className={cn(
              'min-h-[80px] w-full resize-none pr-12',
              'bg-background',
              'rounded-md border border-input',
              'focus-visible:outline-none focus-visible:ring-1',
              'focus-visible:ring-ring',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'text-foreground placeholder:text-muted-foreground',
              'scrollbar-custom'
            )}
            disabled={isLoading || isRecording}
          />
          <div className="flex items-center absolute right-2 bottom-2 space-x-1">
            {isSupported && (
              <Button
                type="button"
                size="icon"
                variant="ghost"
                onClick={handleMicClick}
                disabled={isLoading || !hasActiveSession || permissionStatus === 'pending'}
                className={cn(
                    "h-8 w-8",
                    isRecording ? "text-red-500 hover:bg-red-100" : "text-muted-foreground hover:bg-accent",
                    permissionStatus === 'denied' ? "text-destructive hover:bg-destructive/10 cursor-not-allowed" : "",
                )}
                aria-label={isRecording ? "Stop recording" : "Start recording"}
              >
                {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                {permissionStatus === 'pending' && <span className="sr-only">Requesting permission...</span>}
              </Button>
            )}
            <Button
              type='submit'
              size='icon'
              disabled={isLoading || !input.trim() || isRecording}
              className={cn(
                'h-8 w-8',
                'bg-primary text-primary-foreground',
                'hover:bg-primary/90',
                'focus-visible:ring-1 focus-visible:ring-ring',
                'disabled:opacity-50'
              )}
            >
              <SendHorizontal className='h-4 w-4' />
              <span className='sr-only'>Send message</span>
            </Button>
          </div>
        </div>
        {errorMessage && permissionStatus !== 'denied' && (
            <p className="text-xs text-destructive mt-1 ml-1">{errorMessage}</p>
        )}
        {!isSupported && hasActiveSession && (
             <p className="text-xs text-muted-foreground mt-1 ml-1">Voice input not supported by your browser.</p>
        )}
      </div>
    </form>
  );
} 