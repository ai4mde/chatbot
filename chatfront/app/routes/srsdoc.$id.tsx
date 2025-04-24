import { json, redirect } from '@remix-run/node';
import type { LoaderFunctionArgs, MetaFunction } from '@remix-run/node';
import { Link, useLoaderData } from '@remix-run/react';
import * as React from 'react';
import { promises as fs } from 'fs';
import path from 'path';
import matter from 'gray-matter';
import Markdown from 'markdown-to-jsx';
import hljs from 'highlight.js';
import 'highlight.js/styles/atom-one-dark.css';
import MaxWidthWrapper from '../components/layout/max-width-wrapper';
import { requireUser } from '../services/session.server';
import { Button } from '../components/ui/button';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader,
  DialogTitle, 
  DialogDescription 
} from '../components/ui/dialog';
import { ChevronLeft, ZoomIn } from 'lucide-react';
import { cn } from '../lib/utils';
import { convertPlantUmlToSvg } from '../utils/plantuml.server';
import { Suspense } from 'react';

// Types and interfaces
interface DocData {
  id: string;
  title: string;
  description: string;
  date?: string;
  filename: string;
}

interface Doc {
  content: string;
  data: DocData;
}

interface InteractiveWrapperProps {
  children: React.ReactNode;
  onOpen: () => void;
}

interface DiagramImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src: string;
  alt: string;
  className?: string;
}

interface EnlargeableTableProps {
  children: React.ReactNode;
}

interface EnlargeableCodeProps {
  language: string;
  children: string;
  html: string;
}

interface CodeBlockProps {
  className?: string;
  children: string;
}

export const meta: MetaFunction<typeof loader> = ({ data }) => {
  if (!data?.doc) {
    return [
      { title: 'Document Not Found - AI4MDE' },
      { description: 'The requested SRS document could not be found.' },
    ];
  }

  return [
    { title: `${data.doc.data.title} - AI4MDE` },
    { description: data.doc.data.description },
  ];
};

async function getDocument(id: string): Promise<Doc | null> {
  const docsDir = path.join(process.cwd(), 'data', 'liacs', 'srsdocs');
  
  try {
    const files = await fs.readdir(docsDir);
    const mdFiles = files.filter(file => file.endsWith('.md'));
    
    for (const file of mdFiles) {
      const content = await fs.readFile(path.join(docsDir, file), 'utf-8');
      const { data: frontMatter, content: docContent } = matter(content);
      
      const fileId = frontMatter.id || file.replace('.md', '');
      if (fileId === id) {
        return {
          content: docContent,
          data: {
            id: fileId,
            title: frontMatter.title || file.replace('.md', '').replace(/-/g, ' '),
            description: frontMatter.description || docContent.slice(0, 150) + '...',
            date: frontMatter.date || new Date().toISOString(),
            filename: file,
          },
        };
      }
    }
    
    return null;
  } catch (error) {
    console.error('Error reading document:', error);
    return null;
  }
}

export async function loader({ request, params }: LoaderFunctionArgs) {
  try {
    const user = await requireUser(request);
    
    if (!user.group_name) {
      throw new Response('User group not found', { status: 403 });
    }

    const doc = await getDocument(params.id || '');
    
    if (!doc) {
      throw new Response('Document not found', { status: 404 });
    }

    // Process the content to find and convert PlantUML diagrams
    const content = await processPlantUml(doc.content);

    return json(
      { doc: { ...doc, content } },
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
      return redirect(`/login?redirectTo=/srsdoc/${params.id}`);
    }
    throw error;
  }
}

// Simplified markdown options with consistent rendering
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
      component: ({ children, ...props }) => {
        // Convert children to array for easier handling
        const childArray = React.Children.toArray(children);
        
        // Check if this paragraph contains only a code block
        const hasOnlyCode = childArray.length === 1 && React.isValidElement(childArray[0]) && (
          childArray[0].type === CodeBlock ||
          childArray[0].type === 'pre' ||
          (childArray[0].type === 'code' && !childArray[0].props.inline)
        );

        // If it's just a code block, return it directly without a paragraph wrapper
        if (hasOnlyCode) {
          return childArray[0];
        }

        // Check for other special components
        const hasSpecialComponent = childArray.some(child => 
          React.isValidElement(child) && (
            child.type === DiagramImage ||
            child.type === EnlargeableTable ||
            child.type === EnlargeableCode ||
            child.type === 'pre' ||
            child.type === CodeBlock ||
            (typeof child.type === 'string' && child.type.startsWith('h'))
          )
        );

        // If it contains special components, render them in sequence
        if (hasSpecialComponent) {
          return (
            <>
              {childArray.map((child, index) => {
                if (React.isValidElement(child) && (
                  child.type === DiagramImage ||
                  child.type === EnlargeableTable ||
                  child.type === EnlargeableCode ||
                  child.type === 'pre' ||
                  child.type === CodeBlock ||
                  (typeof child.type === 'string' && child.type.startsWith('h'))
                )) {
                  // Render special components directly
                  return <React.Fragment key={index}>{child}</React.Fragment>;
                }
                // Wrap text content in spans to maintain inline formatting
                return <span key={index} className="text-muted-foreground">{child}</span>;
              })}
            </>
          );
        }

        // Regular paragraph content
        return <p className="text-muted-foreground mb-4" {...props}>{children}</p>;
      }
    },
    ul: { props: { className: 'list-disc list-inside mb-4 ml-4' } },
    ol: { props: { className: 'list-decimal list-inside mb-4 ml-4' } },
    li: { props: { className: 'mb-1' } },
    a: { props: { className: 'text-primary hover:underline' } },
    blockquote: { props: { className: 'border-l-4 border-primary pl-4 italic my-4' } },
    pre: {
      component: ({ children }) => children
    },
    img: { component: DiagramImage },
    table: {
      component: ({ children }) => (
        <EnlargeableTable>
          {children}
        </EnlargeableTable>
      )
    },
    thead: { component: ({ children }) => <thead>{children}</thead> },
    tbody: { component: ({ children }) => <tbody>{children}</tbody> },
    th: { props: { className: 'px-4 py-2 text-left text-sm font-medium text-foreground bg-muted' } },
    td: { props: { className: 'px-4 py-2 text-sm text-muted-foreground' } },
    code: {
      component: CodeBlock
    },
  },
};

// Interactive wrapper for enlargeable content
function InteractiveWrapper({ children, onOpen }: InteractiveWrapperProps) {
  const [isClient, setIsClient] = React.useState(false);

  React.useEffect(() => {
    setIsClient(true);
  }, []);

  const baseContent = (
    <div className='relative group'>
      {children}
    </div>
  );

  if (!isClient) {
    return baseContent;
  }

  return (
    <div 
      onClick={onOpen}
      className='relative group cursor-zoom-in'
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          onOpen();
        }
      }}
    >
      {children}
      <div className='absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity'>
        <div className='bg-background/80 p-2 rounded-full'>
          <ZoomIn className='w-6 h-6 text-foreground' />
        </div>
      </div>
    </div>
  );
}

// DiagramImage component
function DiagramImage({ src, alt, className, ...props }: DiagramImageProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [error, setError] = React.useState(false);
  const [isClient, setIsClient] = React.useState(false);

  React.useEffect(() => {
    setIsClient(true);
  }, []);

  const handleImageError = () => {
    console.error('Failed to load image:', src);
    setError(true);
  };

  if (error) {
    return (
      <div className="p-4 my-4 border border-red-200 rounded-lg bg-red-50 text-red-700">
        <div className="text-sm">Failed to load diagram. Please check if the PlantUML server is accessible.</div>
        <div className="text-xs mt-2 break-all">URL: {src}</div>
      </div>
    );
  }

  const imageContent = (isDialog: boolean) => (
    <div className={cn(
      'flex items-center justify-center',
      !isDialog && 'h-[400px]',
      isDialog && 'w-full h-full'
    )}>
      <img 
        src={src} 
        alt={alt} 
        onError={handleImageError}
        className={cn(
          'rounded-lg object-contain',
          isDialog 
            ? 'min-w-[600px] min-h-[400px] max-w-[calc(95vw-2rem)] max-h-[calc(95vh-2rem)]' 
            : 'max-w-full max-h-full w-auto h-auto',
          !isDialog && isClient && 'cursor-zoom-in',
          className
        )}
        loading='lazy'
        {...props}
      />
    </div>
  );

  if (!isClient) {
    return <div className="my-4">{imageContent(false)}</div>;
  }

  return (
    <div className="my-4">
      <InteractiveWrapper onOpen={() => setIsOpen(true)}>
        {imageContent(false)}
      </InteractiveWrapper>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className='max-w-[95vw] max-h-[95vh] w-[95vw] h-[95vh] p-4'>
          <DialogHeader className="sr-only">
            <DialogTitle>Enlarged Diagram</DialogTitle>
            <DialogDescription>A larger view of the diagram: {alt}</DialogDescription>
          </DialogHeader>
          <div className='w-full h-full flex items-center justify-center'>
            {imageContent(true)}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// EnlargeableTable component
function EnlargeableTable({ children }: EnlargeableTableProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [isClient, setIsClient] = React.useState(false);

  React.useEffect(() => {
    setIsClient(true);
  }, []);

  const tableContent = (isDialog: boolean) => (
    <table className={cn(
      'min-w-full divide-y divide-border my-4',
      isDialog && 'text-lg'
    )}>
      {children}
    </table>
  );

  const baseContent = (
    <div className="overflow-auto">
      {tableContent(false)}
    </div>
  );

  if (!isClient) {
    return baseContent;
  }

  return (
    <div>
      <InteractiveWrapper onOpen={() => setIsOpen(true)}>
        {baseContent}
      </InteractiveWrapper>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className='max-w-[95vw] max-h-[95vh] p-6'>
          <DialogHeader className="sr-only">
            <DialogTitle>Enlarged Table</DialogTitle>
            <DialogDescription>
              A larger view of the table content
            </DialogDescription>
          </DialogHeader>
          <div className='w-full h-full overflow-auto'>
            {tableContent(true)}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// EnlargeableCode component
function EnlargeableCode({ language, children, html }: EnlargeableCodeProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [isClient, setIsClient] = React.useState(false);

  React.useEffect(() => {
    setIsClient(true);
  }, []);

  const codeContent = (
    <div className='my-4'>
      <pre className='overflow-x-auto'>
        <code
          className={`${language ? `hljs language-${language}` : 'hljs'} block`}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </pre>
    </div>
  );

  if (!isClient) {
    return codeContent;
  }

  return (
    <>
      <InteractiveWrapper onOpen={() => setIsOpen(true)}>
        {codeContent}
      </InteractiveWrapper>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className='max-w-[95vw] max-h-[95vh] p-6'>
          <DialogHeader className="sr-only">
            <DialogTitle>Enlarged Code</DialogTitle>
            <DialogDescription>
              A larger view of the {language} code block
            </DialogDescription>
          </DialogHeader>
          <div className='w-full h-full overflow-auto'>
            {codeContent}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

// Update CodeBlock to use EnlargeableCode
function CodeBlock({ className = '', children }: CodeBlockProps) {
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
    <pre className='!p-0 !m-0 !bg-transparent'>
      <EnlargeableCode language={language} html={html} children={children} />
    </pre>
  );
}

async function processPlantUml(content: string): Promise<string> {
  console.log('Starting PlantUML processing');
  const plantUmlRegex = /```plantuml\n([\s\S]*?)```/g;
  let match;
  let processedContent = content;
  let diagramCount = 0;
  
  while ((match = plantUmlRegex.exec(content)) !== null) {
    const [fullMatch, diagramCode] = match;
    console.log('Found PlantUML diagram:', { diagramCode });
    try {
      const svgUrl = await convertPlantUmlToSvg(diagramCode);
      console.log('Generated SVG URL:', svgUrl);
      if (svgUrl) {
        diagramCount++;
        processedContent = processedContent.replace(
          fullMatch,
          `![PlantUML Diagram ${diagramCount}](${svgUrl})`
        );
        console.log(`Replaced diagram ${diagramCount} with markdown image`);
      }
    } catch (error) {
      console.error('Error processing PlantUML diagram:', error);
      processedContent = processedContent.replace(
        fullMatch,
        '> Error: Failed to generate diagram. Please check the PlantUML syntax.'
      );
    }
  }
  
  console.log('Finished processing, found', diagramCount, 'diagrams');
  return processedContent;
}

// Main component with Suspense boundary
export default function SrsDoc() {
  const { doc } = useLoaderData<typeof loader>();

  return (
    <Suspense fallback={
      <MaxWidthWrapper className='py-8'>
        <div className='mb-8'>
          <Button asChild variant='ghost' size='sm'>
            <Link to='/srsdocs' className='flex items-center gap-2'>
              <ChevronLeft className='h-4 w-4' />
              Back to Documents
            </Link>
          </Button>
        </div>
        <div className='animate-pulse'>
          <div className='h-8 w-3/4 bg-muted rounded mb-4'></div>
          <div className='h-4 w-1/4 bg-muted rounded mb-8'></div>
          <div className='space-y-4'>
            <div className='h-4 w-full bg-muted rounded'></div>
            <div className='h-4 w-5/6 bg-muted rounded'></div>
            <div className='h-4 w-4/6 bg-muted rounded'></div>
          </div>
        </div>
      </MaxWidthWrapper>
    }>
      <MaxWidthWrapper className='py-8'>
        <div className='mb-8'>
          <Button asChild variant='ghost' size='sm'>
            <Link to='/srsdocs' className='flex items-center gap-2'>
              <ChevronLeft className='h-4 w-4' />
              Back to Documents
            </Link>
          </Button>
        </div>

        <article className={cn(
          'prose dark:prose-invert max-w-none',
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
          <h1 className='text-4xl font-bold mb-4'>{doc.data.title}</h1>
          {doc.data.date && (
            <p className='text-sm text-muted-foreground mb-8'>
              {new Date(doc.data.date).toLocaleDateString()}
            </p>
          )}
          <Markdown options={markdownOptions}>{doc.content}</Markdown>
        </article>
      </MaxWidthWrapper>
    </Suspense>
  );
} 