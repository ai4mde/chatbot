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
  handleAudioSubmit: (audioBlob: Blob) => Promise<void>;
  isLoading?: boolean;
  lastMessageId?: string;
  hasActiveSession: boolean;
}

// Function to find a supported mimeType
const getSupportedMimeType = (): string | null => {
  const types = [
    'audio/ogg; codecs=opus', // Preferred for Firefox/compatibility
    'audio/webm; codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/aac'
  ];
  for (const type of types) {
    if (MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }
  return null;
};

export function ChatInput({
  input,
  handleInputChange,
  handleSubmit,
  handleAudioSubmit,
  isLoading,
  lastMessageId,
  hasActiveSession
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Refs for MediaRecorder functionality
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // State for microphone functionality
  const [isRecording, setIsRecording] = useState(false);
  const [permissionStatus, setPermissionStatus] = useState<'idle' | 'pending' | 'granted' | 'denied' | 'prompt'>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(false);
  const [mimeType, setMimeType] = useState<string | null>(null);

  // Check for MediaRecorder support on mount
  useEffect(() => {
    if (typeof window !== 'undefined' && navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function' && typeof window.MediaRecorder === 'function') {
        const supportedType = getSupportedMimeType();
        if (supportedType) {
            setIsSupported(true);
            setMimeType(supportedType);
            // console.log("MediaRecorder supported with type:", supportedType);
            // Check initial permission status if possible (some browsers support this)
            navigator.permissions?.query({ name: 'microphone' as PermissionName }).then(permission => {
                setPermissionStatus(permission.state);
                permission.onchange = () => setPermissionStatus(permission.state);
            }).catch(() => {
                 console.warn("Permission query API not fully supported."); // Keep this general warning
                 // Keep status as 'idle' - will prompt on first click
            });
        } else {
            console.warn("No supported audio mimeType found for MediaRecorder.");
            setIsSupported(false);
            setErrorMessage("Your browser doesn't support required audio recording formats.");
        }
    } else {
      // console.warn("MediaRecorder API or getUserMedia not supported in this browser.");
      setIsSupported(false);
      setErrorMessage("Audio recording is not supported in your browser.");
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

  // Function to setup MediaRecorder instance
  const setupMediaRecorder = (stream: MediaStream) => {
      if (!mimeType) {
          console.error("Cannot setup MediaRecorder: mimeType is null");
          setErrorMessage("Audio format configuration error.");
          return;
      }
      console.log("Setting up MediaRecorder with stream and mimeType:", mimeType);
      try {
        mediaRecorderRef.current = new MediaRecorder(stream, { mimeType });
        audioChunksRef.current = []; // Reset chunks
        // console.log("MediaRecorder instance created successfully.");

        mediaRecorderRef.current.ondataavailable = (event: BlobEvent) => {
            // console.log("ondataavailable event fired");
            if (event.data.size > 0) {
                audioChunksRef.current.push(event.data);
                // console.log("Received audio chunk size:", event.data.size);
            } else {
                // console.log("ondataavailable fired with empty data.");
            }
        };

        mediaRecorderRef.current.onstop = async () => {
            // console.log("Recording stopped. Total chunks:", audioChunksRef.current.length);
            if (audioChunksRef.current.length > 0) {
                const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
                // console.log("Created audio blob size:", audioBlob.size, "type:", audioBlob.type);
                setIsRecording(false);
                // Send the blob using the new prop
                try {
                     setErrorMessage("Transcribing audio..."); // Indicate processing
                     await handleAudioSubmit(audioBlob);
                     setErrorMessage(null); // Clear message on success
                } catch (submitError) {
                     console.error("Error submitting audio:", submitError);
                     setErrorMessage("Failed to process audio. Please try again.");
                }

                // Clean up stream tracks after stopping and processing
                stream.getTracks().forEach(track => track.stop());
                mediaRecorderRef.current = null; // Clean up recorder instance
            } else {
                // console.warn("No audio data recorded.");
                 setIsRecording(false);
                 // Clean up stream tracks even if no data
                 stream.getTracks().forEach(track => track.stop());
                  mediaRecorderRef.current = null;
            }
            audioChunksRef.current = []; // Clear chunks
        };

         mediaRecorderRef.current.onerror = (event: Event) => {
             console.error("MediaRecorder error:", event);
             setErrorMessage("An error occurred during recording.");
             setIsRecording(false);
             // Clean up stream tracks on error
             stream.getTracks().forEach(track => track.stop());
             mediaRecorderRef.current = null;
             audioChunksRef.current = [];
         };
      } catch (error) {
          console.error("Failed to create MediaRecorder instance:", error);
          setErrorMessage("Failed to initialize audio recorder.");
          // Clean up stream tracks if setup fails
          stream.getTracks().forEach(track => track.stop());
          mediaRecorderRef.current = null;
          setIsRecording(false); // Ensure recording state is off
      }
  };

  // Function to start recording
  const startRecording = useCallback(async () => {
    if (!isSupported || !mimeType) {
      setErrorMessage("Audio recording not supported or no compatible format found.");
      return;
    }
    setErrorMessage(null); // Clear previous errors

    try {
      // Request microphone permission if not granted
      if (permissionStatus !== 'granted') {
          setPermissionStatus('pending');
          // Prompt user for permission
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          setPermissionStatus('granted'); // Permission granted
          setupMediaRecorder(stream); // Setup recorder with the granted stream
      } else {
          // If already granted, get the stream again (or reuse if stored)
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          setupMediaRecorder(stream);
      }
      // Start recording after setup
       if (mediaRecorderRef.current) {
          // console.log("Attempting to start recording...");
          mediaRecorderRef.current.start();
          // Check state immediately after calling start()
          // console.log("Called start(). Current recorder state:", mediaRecorderRef.current.state);
          if (mediaRecorderRef.current.state === "recording") {
              setIsRecording(true);
              // console.log("Recording successfully started.");
          } else {
              console.warn("MediaRecorder state is not 'recording' after start():", mediaRecorderRef.current.state);
              // Potentially set an error message here if state is unexpected
              setErrorMessage("Recorder failed to enter recording state.");
              setIsRecording(false);
          }
      } else {
          console.error("Cannot start recording: mediaRecorderRef is null after setup attempt.");
           setErrorMessage("Recorder setup failed.");
           setIsRecording(false);
      }

    } catch (err) {
      // console.error("Error accessing microphone or starting recording:", err);
      setPermissionStatus('denied'); // Assume denial if error occurs
      if (err instanceof Error && err.name === 'NotAllowedError') {
          setErrorMessage("Microphone permission denied. Please enable it in browser settings.");
      } else {
           setErrorMessage("Could not start microphone. Ensure it's connected and permissions are allowed.");
      }
       setIsRecording(false);
    }
  }, [isSupported, permissionStatus, mimeType, setupMediaRecorder]);

  // Function to stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      // console.log("Stopping recording manually...");
      mediaRecorderRef.current.stop(); // This triggers the 'onstop' handler
    }
  }, [isRecording]);

  // Handle Mic Button Click
  const handleMicClick = useCallback(() => {
    if (!isSupported) {
      setErrorMessage("Audio recording is not supported by your browser.");
      return;
    }
    if (isLoading) return; // Don't allow recording while AI is thinking

    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isSupported, isLoading, isRecording, stopRecording, startRecording]);


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
              isRecording ? 'Recording... Click mic to stop' :
              permissionStatus === 'pending' ? 'Requesting mic permission...' :
              permissionStatus === 'denied' ? 'Mic access denied. Check settings.' :
              errorMessage ? `Error: ${errorMessage}` :
              !isSupported ? 'Audio recording not supported.' :
              'Type your message or click the mic to record...'
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
            disabled={isLoading || isRecording || permissionStatus === 'pending'}
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
                    isRecording ? "text-red-500 hover:bg-red-100 animate-pulse" : "text-muted-foreground hover:bg-accent",
                    permissionStatus === 'denied' ? "text-destructive hover:bg-destructive/10 cursor-not-allowed" : "",
                    permissionStatus === 'pending' ? "text-orange-500 cursor-wait" : "",
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
              disabled={isLoading || !input.trim() || isRecording || permissionStatus === 'pending'}
              className={cn(
                'h-8 w-8',
                'bg-primary text-primary-foreground',
                'hover:bg-primary/90',
                'focus-visible:ring-1 focus-visible:ring-ring',
                'disabled:opacity-50'
              )}
            >
              <SendHorizontal className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
      {errorMessage && permissionStatus !== 'denied' && !isRecording && (
          <p className="text-xs text-destructive text-center px-8 pb-2">{errorMessage}</p>
      )}
    </form>
  );
} 