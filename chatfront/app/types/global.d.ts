interface Window {
  ENV: {
    PUBLIC_CHATBACK_URL: string;
    SESSION_SECRET: string;
    SESSION_TIMEOUT_MINUTES: string;
    NODE_ENV: 'development' | 'production' | 'test';
    RUNTIME_ENV: string;
  }
}