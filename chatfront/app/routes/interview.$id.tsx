import * as React from 'react';
import { json } from '@remix-run/node';
import type { LoaderFunctionArgs, MetaFunction } from '@remix-run/node';
import { Link, useLoaderData } from '@remix-run/react';
import { promises as fs } from 'fs';
import path from 'path';
import matter from 'gray-matter';
import Markdown from 'markdown-to-jsx';
import hljs from 'highlight.js';
import 'highlight.js/styles/atom-one-dark.css';
import MaxWidthWrapper from '../components/layout/max-width-wrapper';
import { requireUser } from '../services/session.server';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent } from '../components/ui/dialog';
import { ChevronLeft, ZoomIn } from 'lucide-react';
import { cn } from '../lib/utils';
import { redirect } from '@remix-run/node';

interface InterviewData {
  id: string;
  title: string;
  description: string;
  date?: string;
  filename: string;
}

interface Interview {
  content: string;
  data: InterviewData;
}

interface Message {
  speaker: string;
  timestamp: string;
  content: string;
  isAI: boolean;
}

export const meta: MetaFunction<typeof loader> = ({ data }) => {
  if (!data?.interview) {
    return [
      { title: 'Interview Not Found - AI4MDE' },
      { description: 'The requested interview log could not be found.' },
    ];
  }

  return [
    { title: `${data.interview.data.title} - AI4MDE` },
    { description: data.interview.data.description },
  ];
};

async function getInterview(groupName: string, id: string): Promise<Interview | null> {
  const interviewsDir = path.join(process.cwd(), 'data', groupName, 'interviews');
  
  try {
    const files = await fs.readdir(interviewsDir);
    const mdFiles = files.filter(file => file.endsWith('.md'));
    
    for (const file of mdFiles) {
      const content = await fs.readFile(path.join(interviewsDir, file), 'utf-8');
      const { data: frontMatter, content: interviewContent } = matter(content);
      
      const fileId = frontMatter.id || file.replace('.md', '');
      if (fileId === id) {
        return {
          content: interviewContent,
          data: {
            id: fileId,
            title: frontMatter.title || file.replace('.md', '').replace(/-/g, ' '),
            description: frontMatter.description || interviewContent.slice(0, 150) + '...',
            date: frontMatter.date || new Date().toISOString(),
            filename: file,
          },
        };
      }
    }
    
    return null;
  } catch (error) {
    console.error('Error reading interview:', error);
    return null;
  }
}

export async function loader({ request, params }: LoaderFunctionArgs) {
  try {
    const user = await requireUser(request);
    
    if (!user.group_name) {
      throw new Response('User group not found', { status: 403 });
    }

    const interview = await getInterview(user.group_name, params.id || '');
    
    if (!interview) {
      throw new Response('Interview not found', { status: 404 });
    }

    return json(
      { interview },
      {
        headers: {
          'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0',
        },
      }
    );
  } catch (error) {
    // Redirect to login if authentication fails
    if (error instanceof Response && error.status === 401) {
      return redirect(`/login?redirectTo=/interview/${params.id}`);
    }
    throw error;
  }
}

// Add components for enlargeable elements (DiagramImage, EnlargeableTable, EnlargeableCode)
// ... (same components as in srsdoc.$id.tsx) ...

function parseMessages(content: string): { metadata: string; messages: Message[] } {
  const messages: Message[] = [];
  const sections = content.split('## Messages');
  const metadata = sections[0] || '';
  
  // Skip the first two lines (title and date) and take the rest of the metadata
  const filteredMetadata = metadata
    .split('\n')
    .slice(2)
    .join('\n')
    .trim();
  
  if (!sections[1]) return { metadata: filteredMetadata, messages };

  const messageRegex = /### \*\*([^*]+)\*\* \(([^)]+)\)\n([\s\S]*?)(?=### \*\*|$)/g;
  let match;

  while ((match = messageRegex.exec(sections[1])) !== null) {
    const [_, speaker, timestamp, content] = match;
    const isAI = speaker.toLowerCase().includes('assistant') || speaker.toLowerCase().includes('agent');
    // Remove the "---" lines from the content
    const cleanContent = content
      .split('\n')
      .filter(line => !line.trim().startsWith('---'))
      .join('\n')
      .trim();
    messages.push({
      speaker,
      timestamp,
      content: cleanContent,
      isAI
    });
  }

  return { metadata: filteredMetadata, messages };
}

interface ChatBubbleProps {
  children: React.ReactNode;
  isAI?: boolean;
  speaker: string;
  timestamp: string;
}

function ChatBubble({ children, isAI, speaker, timestamp }: ChatBubbleProps) {
  return (
    <div className={cn(
      'flex w-full mb-4',
      isAI ? 'justify-start' : 'justify-end'
    )}>
      <div className={cn(
        'max-w-[95%] rounded-2xl px-4 py-2',
        isAI ? 'bg-muted' : 'bg-primary text-primary-foreground'
      )}>
        <div className="text-sm font-semibold mb-2">
          {speaker} {timestamp}
        </div>
        {children}
      </div>
    </div>
  );
}

function CodeBlock({ className = '', children }: { className?: string; children: string }) {
  const language = className.replace(/language-/, '');
  const html = React.useMemo(() => {
    if (language && hljs.getLanguage(language)) {
      try {
        return hljs.highlight(children, { language }).value;
      } catch (err) {
        console.error('Error highlighting code:', err);
      }
    }
    return hljs.highlightAuto(children).value;
  }, [children, language]);

  return (
    <pre className='!p-0 !m-0 !bg-transparent mb-10'>
      <code 
        className={`block p-4 rounded-lg bg-muted overflow-x-auto ${language ? `hljs language-${language}` : 'hljs'}`}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </pre>
  );
}

const metadataMarkdownOptions = {
  options: {
    forceBlock: true,
    forceWrapper: true,
    wrapper: 'div',
    disableParsingRawHTML: false,
    escapeHtml: false,
  },
  overrides: {
    h1: { props: { className: 'text-3xl font-bold mt-8 mb-4' } },
    h2: { props: { className: 'text-2xl font-semibold mt-6 mb-3' } },
    h3: { props: { className: 'text-xl font-semibold mt-4 mb-2' } },
    h4: { props: { className: 'text-lg font-semibold mt-4 mb-2' } },
    p: { props: { className: 'text-muted-foreground mb-4' } },
    ul: { props: { className: 'list-disc list-inside mb-4 ml-4' } },
    ol: { props: { className: 'list-decimal list-inside mb-4 ml-4' } },
    li: { props: { className: 'mb-1' } },
    a: { props: { className: 'text-primary hover:underline' } },
    blockquote: { props: { className: 'border-l-4 border-primary pl-4 italic my-4' } },
    code: {
      component: CodeBlock
    },
    pre: {
      component: ({ children }: { children: React.ReactNode }) => children
    },
    img: { 
      props: { 
        className: 'max-w-full h-auto my-4 mx-auto rounded-lg shadow-md',
        loading: 'lazy'
      } 
    },
  },
};

const markdownOptions = {
  options: {
    forceBlock: true,
    forceWrapper: true,
    wrapper: 'div',
    disableParsingRawHTML: false,
    escapeHtml: false,
  },
  overrides: {
    h1: { props: { className: 'text-3xl font-bold mt-8 mb-4' } },
    h2: { props: { className: 'text-2xl font-semibold mt-6 mb-3' } },
    h3: { props: { className: 'text-xl font-semibold mt-4 mb-2' } },
    h4: { props: { className: 'text-lg font-semibold mt-4 mb-2' } },
    p: { 
      component: ({ children }: { children: React.ReactNode }) => (
        <ChatBubble isAI={true} speaker="" timestamp="">
          <p className="text-muted-foreground">{children}</p>
        </ChatBubble>
      )
    },
    ul: { 
      component: ({ children }: { children: React.ReactNode }) => (
        <ChatBubble isAI={true} speaker="" timestamp="">
          <ul className="list-disc list-inside mb-4 ml-4">{children}</ul>
        </ChatBubble>
      )
    },
    ol: { 
      component: ({ children }: { children: React.ReactNode }) => (
        <ChatBubble isAI={true} speaker="" timestamp="">
          <ol className="list-decimal list-inside mb-4 ml-4">{children}</ol>
        </ChatBubble>
      )
    },
    li: { props: { className: 'mb-1' } },
    a: { props: { className: 'text-primary hover:underline' } },
    blockquote: { 
      component: ({ children }: { children: React.ReactNode }) => (
        <ChatBubble isAI={true} speaker="" timestamp="">
          <blockquote className="border-l-4 border-primary pl-4 italic my-4">{children}</blockquote>
        </ChatBubble>
      )
    },
    code: {
      component: CodeBlock
    },
    pre: {
      component: ({ children }: { children: React.ReactNode }) => (
        <ChatBubble isAI={true} speaker="" timestamp="">
          {children}
        </ChatBubble>
      )
    },
    img: { 
      component: ({ src, alt }: { src: string; alt?: string }) => (
        <ChatBubble isAI={true} speaker="" timestamp="">
          <img 
            src={src} 
            alt={alt} 
            className="max-w-full h-auto my-4 mx-auto rounded-lg shadow-md"
            loading="lazy"
          />
        </ChatBubble>
      )
    },
  },
};

export default function InterviewLog() {
  const { interview } = useLoaderData<typeof loader>();
  const { metadata, messages } = parseMessages(interview.content);

  return (
    <MaxWidthWrapper className='py-8'>
      <div className='mb-8'>
        <Button asChild variant='ghost' size='sm'>
          <Link to='/interviews' className='flex items-center gap-2'>
            <ChevronLeft className='h-4 w-4' />
            Back to Interviews
          </Link>
        </Button>
      </div>

      <article className={cn(
        'max-w-none',
        '[&>h1]:text-4xl [&>h1]:font-bold [&>h1]:mb-4',
        '[&>h2]:text-3xl [&>h2]:font-semibold [&>h2]:mb-3 [&>h2]:mt-8',
        '[&>h3]:text-2xl [&>h3]:font-semibold [&>h3]:mb-2 [&>h3]:mt-6',
        '[&>p]:text-muted-foreground [&>p]:mb-4',
        '[&>ul]:list-disc [&>ul]:ml-6 [&>ul]:mb-4',
        '[&>ol]:list-decimal [&>ol]:ml-6 [&>ol]:mb-4',
        '[&>li]:mb-1',
        '[&>blockquote]:border-l-4 [&>blockquote]:border-primary [&>blockquote]:pl-4 [&>blockquote]:italic [&>blockquote]:my-4',
        '[&>pre]:bg-muted [&>pre]:p-4 [&>pre]:rounded-lg [&>pre]:mb-4 [&>pre]:overflow-x-auto',
        '[&>code]:bg-muted [&>code]:px-1.5 [&>code]:py-0.5 [&>code]:rounded'
      )}>
        <h1 className='text-4xl font-bold mb-4'>{interview.data.title}</h1>
        {/* <p className='text-muted-foreground mb-4'>{interview.data.description}</p> */}
        
        {/* Metadata Section */}
        {metadata.trim() && (
          <div className="mb-8">
            <Markdown options={metadataMarkdownOptions}>{metadata}</Markdown>
          </div>
        )}

        {/* Messages Section */}
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold mb-6">Chat history</h2>
          {messages.map((message, index) => (
            <ChatBubble 
              key={index} 
              isAI={message.isAI}
              speaker={message.speaker}
              timestamp={message.timestamp}
            >
              {message.isAI ? (
                <Markdown options={markdownOptions}>{message.content}</Markdown>
              ) : (
                <div className="text-primary-foreground">
                  <Markdown options={{
                    ...markdownOptions,
                    overrides: {
                      ...markdownOptions.overrides,
                      p: { props: { className: 'mb-4' } },
                      ul: { props: { className: 'list-disc list-inside mb-4 ml-4' } },
                      ol: { props: { className: 'list-decimal list-inside mb-4 ml-4' } },
                      blockquote: { props: { className: 'border-l-4 border-primary-foreground pl-4 italic my-4' } },
                      code: { props: { className: 'bg-primary-foreground/20 px-1.5 py-0.5 rounded' } },
                      pre: { props: { className: 'bg-primary-foreground/20 p-4 rounded-lg mb-4 overflow-x-auto' } },
                    }
                  }}>{message.content}</Markdown>
                </div>
              )}
            </ChatBubble>
          ))}
        </div>
      </article>
    </MaxWidthWrapper>
  );
} 