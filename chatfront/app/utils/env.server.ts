/// <reference types='node' />

export function getEnvVar(key: string, defaultValue?: string): string {
  const value = process.env[key]
  if (!value && defaultValue === undefined) {
    throw new Error(`Environment variable ${key} is not set`)
  }
  return value || defaultValue || ''
}

// Export commonly used env vars
export const ENV = {
  NODE_ENV: getEnvVar('NODE_ENV', 'development'),
  CHATBACK_URL: getEnvVar('CHATBACK_URL', 'http://localhost:8000'),
  API_URL: `${getEnvVar('CHATBACK_URL')}/api/v1`,
  SESSION_SECRET: getEnvVar('SESSION_SECRET'),
  // Add other env vars as needed
} 