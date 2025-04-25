import * as React from 'react';
import { useEffect, useState, useCallback } from 'react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';

interface SessionTimeoutWarningProps {
  timeoutMinutes: number;
  onTimeout: () => void;
}

// Create a singleton to track the timer across components
let globalTimer: NodeJS.Timeout | null = null;
let lastActivity: number;

// Function to update last activity timestamp
export function updateLastActivity() {
  lastActivity = Date.now();
}

export function SessionTimeoutWarning({ timeoutMinutes, onTimeout }: SessionTimeoutWarningProps) {
  const [remainingTime, setRemainingTime] = useState(timeoutMinutes * 60);
  const [showWarning, setShowWarning] = useState(false);

  const resetTimer = useCallback(() => {
    setRemainingTime(timeoutMinutes * 60);
    setShowWarning(false);
    updateLastActivity();
  }, [timeoutMinutes]);

  useEffect(() => {
    updateLastActivity();
    setRemainingTime(timeoutMinutes * 60);

    // Clear any existing timer
    if (globalTimer) {
      clearInterval(globalTimer);
    }

    const handleUserActivity = () => {
      updateLastActivity();
    };

    // Add event listeners for user activity
    window.addEventListener('mousemove', handleUserActivity);
    window.addEventListener('keydown', handleUserActivity);
    window.addEventListener('click', handleUserActivity);
    window.addEventListener('scroll', handleUserActivity);
    window.addEventListener('touchstart', handleUserActivity);

    const warningTime = 60; // 60 seconds warning
    
    globalTimer = setInterval(() => {
      const now = Date.now();
      const inactiveTime = Math.floor((now - lastActivity) / 1000);
      const timeLeft = (timeoutMinutes * 60) - inactiveTime;

      setRemainingTime(timeLeft);

      if (timeLeft <= 0) {
        onTimeout();
        if (globalTimer) {
          clearInterval(globalTimer);
          globalTimer = null;
        }
      } else if (timeLeft <= warningTime) {
        setShowWarning(true);
      } else {
        setShowWarning(false);
      }
    }, 1000);

    return () => {
      if (globalTimer) {
        clearInterval(globalTimer);
        globalTimer = null;
      }
      // Remove event listeners
      window.removeEventListener('mousemove', handleUserActivity);
      window.removeEventListener('keydown', handleUserActivity);
      window.removeEventListener('click', handleUserActivity);
      window.removeEventListener('scroll', handleUserActivity);
      window.removeEventListener('touchstart', handleUserActivity);
    };
  }, [timeoutMinutes, onTimeout]);

  if (!showWarning) return null;

  const seconds = remainingTime % 60;

  return (
    <Alert className='fixed bottom-4 right-4 max-w-md bg-yellow-50 border-yellow-200 dark:bg-yellow-900/10 dark:border-yellow-900/20'>
      <AlertDescription className='flex flex-col gap-3'>
        <p>Your session will expire in {seconds} seconds.</p>
        <div className='flex justify-end gap-2'>
          <Button variant='outline' onClick={resetTimer}>
            Continue Session
          </Button>
          <Button variant='destructive' onClick={onTimeout}>
            Log Off
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  );
} 