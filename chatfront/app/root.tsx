import * as React from 'react';
import { cssBundleHref } from '@remix-run/css-bundle';
import type { 
  LinksFunction, 
  LoaderFunctionArgs, 
  MetaFunction, 
  ActionFunctionArgs,
  SerializeFrom 
} from '@remix-run/node';
import {
  Links,
  LiveReload,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
  json,
  isRouteErrorResponse,
  useRouteError,
  Link,
  useNavigate,
  useLoaderData,
  Form,
} from '@remix-run/react';
import { Button } from './components/ui/button';
import { Header } from './components/layout/header';
import { Footer } from './components/layout/footer';
import { ThemeProvider } from './components/layout/theme-provider';
import stylesheet from './tailwind.css';
import { sessionStorage, getSession } from './services/session.server';
import NotFound from './routes/_error-404';
import { Toaster } from './components/ui/toaster';
import { SessionTimeoutWarning } from './components/layout/session-timeout-warning';
import type { CustomUser } from './types/auth.types';

// Types
interface Environment {
  PUBLIC_CHATBACK_URL: string;
  SESSION_SECRET: string;
  SESSION_TIMEOUT_MINUTES: string;
  NODE_ENV: "development" | "production" | "test";
}

interface LoaderData {
  user: CustomUser | null;
  ENV: Environment;
}

declare global {
  interface Window {
    ENV: {
      PUBLIC_CHATBACK_URL: string;
      SESSION_SECRET: string;
      SESSION_TIMEOUT_MINUTES: string;
      NODE_ENV: "development" | "production" | "test";
      RUNTIME_ENV: string;
    };
  }
}

export const meta: MetaFunction = () => {
  return [
    { title: 'AI4MDE' },
    { name: 'description', content: 'AI-powered Model-Driven Engineering' },
    { name: 'viewport', content: 'width=device-width,initial-scale=1' },
  ];
};

export const links: LinksFunction = () => [
  { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
  { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossOrigin: 'anonymous' },
  { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Oxanium:wght@200;300;400;500;600;700;800&display=swap' },
  { rel: 'stylesheet', href: stylesheet },
  ...(cssBundleHref ? [{ rel: 'stylesheet', href: cssBundleHref }] : []),
];

export const headers = () => {
  const isDev = process.env.NODE_ENV === 'development';
  const chatbackUrl = process.env.PUBLIC_CHATBACK_URL || 'http://localhost:8000';
  
  return {
    'Content-Security-Policy': `
      default-src 'self' ${isDev ? 'ws: wss:' : ''};
      script-src 'self' 'unsafe-inline' 'unsafe-eval';
      style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
      font-src 'self' https://fonts.gstatic.com;
      img-src 'self' data: blob: https://www.plantuml.com https://plantuml.com;
      connect-src 'self' ${chatbackUrl} ${isDev ? 'ws://localhost:* wss://localhost:*' : ''};
      frame-src 'self';
      media-src 'self';
    `.replace(/\s+/g, ' ').trim(),
    'X-Frame-Options': 'DENY',
  };
};

export async function loader({ request }: LoaderFunctionArgs): Promise<Response> {
  const session = await getSession(request);
  const user = session.get('user') as CustomUser | null;

  const env: Environment = {
    PUBLIC_CHATBACK_URL: process.env.PUBLIC_CHATBACK_URL ?? 'http://localhost:8000',
    SESSION_SECRET: process.env.SESSION_SECRET ?? '',
    SESSION_TIMEOUT_MINUTES: process.env.SESSION_TIMEOUT_MINUTES ?? '30',
    NODE_ENV: (process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test') 
                ? process.env.NODE_ENV 
                : 'production',
  };

  return json<LoaderData>(
    {
      user,
      ENV: env
    },
    {
      headers: {
        'Cache-Control': 'private, must-revalidate, max-age=0, s-maxage=0',
        'Vary': 'Cookie, Authorization',
        'X-Remix-Revalidate': '1'
      }
    }
  );
}

export async function action({ request }: ActionFunctionArgs): Promise<Response> {
  const session = await getSession(request);
  return json(
    { success: true },
    {
      headers: {
        'Set-Cookie': await sessionStorage.destroySession(session),
      },
    }
  );
}

export function ErrorBoundary(): JSX.Element {
  const error = useRouteError();

  if (isRouteErrorResponse(error) && error.status === 404) {
    return <NotFound />;
  }

  return (
    <div className='min-h-screen flex items-center justify-center'>
      <div className='text-center space-y-4'>
        <h1 className='text-4xl font-bold'>Oops!</h1>
        <p className='text-xl text-muted-foreground'>Something went wrong.</p>
        <Button asChild>
          <Link to='/'>Back to Home</Link>
        </Button>
      </div>
    </div>
  );
}

export default function App(): JSX.Element {
  const { user, ENV } = useLoaderData<typeof loader>();
  // Restore hooks and handlers
  const navigate = useNavigate();
  const formRef = React.useRef<HTMLFormElement>(null);
  const memoizedUser = React.useMemo(() => user, [user?.id]);
  const handleTimeout = React.useCallback((): void => {
    if (formRef.current) {
      formRef.current.submit();
    }
    navigate('/login');
  }, [navigate]);

  return (
    <html lang='en' suppressHydrationWarning>
      <head>
        <meta charSet='utf-8' />
        <meta name='viewport' content='width=device-width, initial-scale=1' />
        {/* Restore meta tags if they were removed */}
        <meta name='color-scheme' content='light dark' /> 
        <link rel='icon' type='image/svg+xml' href='/images/logos/logo.svg' /> 
        <Meta />
        <Links />
      </head>
      {/* Restore body class */}
      <body className='min-h-screen bg-background font-sans antialiased'>
        {/* Restore commented out components */}
        <ThemeProvider>
          <div className='relative flex min-h-screen flex-col'>
            <Header user={memoizedUser} />
            <main className='flex-1'>
              <Outlet context={{ user: memoizedUser }} /> {/* Restore context user */}
            </main>
            <Footer />
            {memoizedUser && (
              <>
                <Form ref={formRef} method='post' />
                <SessionTimeoutWarning
                  timeoutMinutes={Number(ENV.SESSION_TIMEOUT_MINUTES)}
                  onTimeout={handleTimeout}
                />
              </>
            )}
          </div>
        </ThemeProvider>
        <Toaster />
        {/* --- End Restoration --- */}

        {/* Keep ENV script and Remix scripts */}
        <script
          dangerouslySetInnerHTML={{
            __html: `window.ENV = ${JSON.stringify({ ...ENV, RUNTIME_ENV: 'container' })}`
          }}
        />
        <ScrollRestoration />
        <Scripts />
        {ENV.NODE_ENV === 'development' && <LiveReload />}
      </body>
    </html>
  );
} 