import { json, redirect, type ActionFunctionArgs } from '@remix-run/node';
import type { LoaderFunctionArgs, MetaFunction } from '@remix-run/node';
import { Link, useLoaderData, Form, useNavigation } from '@remix-run/react';
import * as React from 'react';
import { promises as fs } from 'fs';
import path from 'path';
import matter from 'gray-matter';
import Markdown from 'markdown-to-jsx';
import hljs from 'highlight.js';
import '@uiw/react-md-editor/markdown-editor.css';
import '@uiw/react-markdown-preview/markdown.css';
import { default as MDEditor } from '@uiw/react-md-editor';
import 'highlight.js/styles/atom-one-dark.css';
import MaxWidthWrapper from '../components/layout/max-width-wrapper';
import { requireUser, getUserFromSession } from '../services/session.server';
import { Button } from '../components/ui/button';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader,
  DialogTitle, 
  DialogDescription 
} from '../components/ui/dialog';
import { ChevronLeft, ZoomIn, FileEdit, Save, XCircle } from 'lucide-react';
import { cn } from '../lib/utils';
import { convertPlantUmlToSvg } from '../utils/plantuml.server';
import { Suspense } from 'react';
import ChatBubble from '../components/chat/chat-bubble';

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
}

interface CodeBlockProps {
  className?: string;
  children: string;
}

// Add new type for user session data (adjust if your User type is different)
interface UserSessionData {
  id: string;
  username: string;
  email: string;
  group_name: string;
  access_token?: string;
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

// Base Markdown options - OUTSIDE component
const baseMarkdownOptionsConfig = {
  forceBlock: true,
  forceWrapper: true,
  wrapper: 'div',
  disableParsingRawHTML: false,
  escapeHtml: false,
  overrides: {
    h1: { props: { className: 'text-3xl font-bold mt-8 mb-4' } },
    h2: { props: { className: 'text-2xl font-semibold mt-6 mb-3' } },
    h3: { props: { className: 'text-xl font-semibold mt-4 mb-2' } },
    h4: { props: { className: 'text-lg font-semibold mt-4 mb-2' } },
    p: { 
      component: ({ children, ...props }: { children: React.ReactNode }) => {
        const childArray = React.Children.toArray(children);
        const hasOnlyCode = childArray.length === 1 && React.isValidElement(childArray[0]) && (childArray[0].type === CodeBlock || childArray[0].type === 'pre' || (childArray[0].type === 'code' && !childArray[0].props.inline));
        if (hasOnlyCode) return childArray[0];
        const hasSpecialComponent = childArray.some(child => React.isValidElement(child) && (child.type === DiagramImage || child.type === EnlargeableTable || child.type === EnlargeableCode || child.type === 'pre' || child.type === CodeBlock || (typeof child.type === 'string' && child.type.startsWith('h'))));
        if (hasSpecialComponent) {
          return <>{childArray.map((child, index) => React.isValidElement(child) && (child.type === DiagramImage || child.type === EnlargeableTable || child.type === EnlargeableCode || child.type === 'pre' || child.type === CodeBlock || (typeof child.type === 'string' && child.type.startsWith('h'))) ? <React.Fragment key={index}>{child}</React.Fragment> : <span key={index} className="text-muted-foreground">{child}</span>)}</>;
        }
        return <p className="text-muted-foreground mb-4" {...props}>{children}</p>;
      }
    },
    ul: { props: { className: 'list-disc list-inside mb-4 ml-4' } },
    ol: { props: { className: 'list-decimal list-inside mb-4 ml-4' } },
    li: { props: { className: 'mb-1' } },
    a: { props: { className: 'text-primary hover:underline' } },
    blockquote: { props: { className: 'border-l-4 border-primary pl-4 italic my-4' } },
    pre: { component: ({ children }: { children: React.ReactNode }) => children },
    // Note: img, table, code overrides will be added INSIDE the component now
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
function EnlargeableCode({ language, children: rawCodeString }: EnlargeableCodeProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [isClient, setIsClient] = React.useState(false);
  const [highlightedCodeHtml, setHighlightedCodeHtml] = React.useState<string | null>(null);

  React.useEffect(() => {
    setIsClient(true); // For Dialog and InteractiveWrapper logic
    // Perform highlighting on the client
    let hlValue;
    if (language && hljs.getLanguage(language)) {
      try {
        hlValue = hljs.highlight(rawCodeString, { language, ignoreIllegals: true }).value;
      } catch (e) {
        console.error("Highlighting error:", e);
        hlValue = hljs.highlightAuto(rawCodeString).value; // Fallback
      }
    } else {
      hlValue = hljs.highlightAuto(rawCodeString).value;
    }
    setHighlightedCodeHtml(hlValue);
  }, [rawCodeString, language]);

  const codeContent = (
    <div className='my-4'>
      <pre className='overflow-x-auto'>
        <code
          className={`${language ? `hljs language-${language}` : 'hljs'} block`}
          // Initially render raw string if no highlighted version yet, then switch to dangerouslySetInnerHTML
          {...(highlightedCodeHtml !== null ? { dangerouslySetInnerHTML: { __html: highlightedCodeHtml } } : { children: rawCodeString })}
        />
      </pre>
    </div>
  );

  if (!isClient) {
    // For SSR and initial client render path before isClient is true (and before highlighting effect runs)
    // It will render with rawCodeString in the <code> tag via the ternary in codeContent
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
            {codeContent} {/* This will show highlighted code once available */}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

// Update CodeBlock to use EnlargeableCode
function CodeBlock({ className = '', children }: CodeBlockProps) { // children here is the raw code string
  const language = className.replace(/language-/, '');
  // No more useMemo for html here. Pass children (rawCodeString) directly.
  return (
    <pre className='!p-0 !m-0 !bg-transparent'>
      <EnlargeableCode language={language} children={children} />
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
  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [modalContent, setModalContent] = React.useState<React.ReactNode>(null);
  const navigation = useNavigation();
  const isSaving = navigation.state === 'submitting' && navigation.formData?.get('_action') === 'saveMarkdown';

  const [isEditing, setIsEditing] = React.useState(false);
  const [editedMarkdown, setEditedMarkdown] = React.useState<string | undefined>(undefined);

  const handleOpenModal = React.useCallback((content: React.ReactNode) => {
    setModalContent(content);
    setIsModalOpen(true);
  }, []);

  // Define the FULL markdown options INSIDE the component
  const markdownOptionsWithModal = React.useMemo(() => ({
    // Define the top-level options expected by Markdown component directly
    forceBlock: baseMarkdownOptionsConfig.forceBlock,
    forceWrapper: baseMarkdownOptionsConfig.forceWrapper,
    wrapper: baseMarkdownOptionsConfig.wrapper as React.ElementType<any> | null | undefined, // Explicitly cast wrapper type
    disableParsingRawHTML: baseMarkdownOptionsConfig.disableParsingRawHTML,
    escapeHtml: baseMarkdownOptionsConfig.escapeHtml,
    overrides: {
      ...baseMarkdownOptionsConfig.overrides, // Base overrides
      // Add modal-specific overrides
      img: { 
        component: DiagramImage, 
        props: { onOpen: handleOpenModal }
      },
      table: { 
        component: EnlargeableTable, 
        props: { onOpen: handleOpenModal }
      },
      code: { 
        component: CodeBlock, 
        props: { onOpen: handleOpenModal }
      },
    }
  }), [handleOpenModal]);

  const handleEdit = async () => {
    setEditedMarkdown(doc.content);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedMarkdown(undefined);
  };

  const onEditorChange = (value?: string) => {
    setEditedMarkdown(value);
  };

  return (
    <MaxWidthWrapper className="py-8 flex flex-col">
      <div className="flex justify-between items-center mb-4 flex-shrink-0">
        <Link to="/srsdocs" className="text-primary hover:underline flex items-center">
          <ChevronLeft className="h-5 w-5 mr-1" />
          Back to SRS Documents
        </Link>
        {/* Edit Button */}
        {!isEditing && (
          <Button variant="outline" onClick={handleEdit} className="flex items-center">
            <FileEdit className="h-4 w-4 mr-2" />
            Edit Document
          </Button>
        )}
      </div>

      <h1 className="text-4xl font-bold tracking-tight text-foreground mb-2">{doc.data.title}</h1>
      <p className="text-sm text-muted-foreground mb-6 flex-shrink-0">
        Last updated: {doc.data.date ? new Date(doc.data.date).toLocaleDateString() : 'N/A'} (Filename: {doc.data.filename})
      </p>

      {isEditing ? (
        <Form method="post" className="flex flex-col">
          <input type="hidden" name="docId" value={doc.data.id} />
          <input type="hidden" name="filename" value={doc.data.filename} /> 
          <input type="hidden" name="markdownContent" value={editedMarkdown || ''} /> 
          <div data-color-mode="light" className="mb-4">
            <MDEditor
              value={editedMarkdown}
              onChange={onEditorChange}
              preview="live"
              className="h-[80vh] min-h-[600px]"
              textareaProps={{
                style: { resize: 'vertical' }
              }}
            />
          </div>
          <div className="flex justify-end space-x-2 flex-shrink-0">
            <Button type="button" variant="outline" onClick={handleCancelEdit} disabled={isSaving}>
              <XCircle className="h-4 w-4 mr-2" />
              Cancel
            </Button>
            <Button type="submit" name="_action" value="saveMarkdown" disabled={isSaving}>
              <Save className="h-4 w-4 mr-2" />
              {isSaving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </Form>
      ) : (
        <article className="prose prose-zinc dark:prose-invert max-w-none flex-grow">
          <Suspense fallback={<div>Loading document content...</div>}>
            <Markdown options={markdownOptionsWithModal}>
              {doc.content}
            </Markdown>
          </Suspense>
        </article>
      )}

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-4xl h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Enlarged Content</DialogTitle>
            <DialogDescription>Scroll to see more.</DialogDescription>
          </DialogHeader>
          <div className="flex-grow overflow-auto p-4">
            {modalContent}
          </div>
        </DialogContent>
      </Dialog>
      {!isEditing && <ChatBubble docId={doc.data.id} />}
    </MaxWidthWrapper>
  );
}

// Action function to handle saving the markdown
export async function action({ request, params }: ActionFunctionArgs) {
  const user = await getUserFromSession(request);
  if (!user) {
    return redirect('/login'); // Or handle unauthorized access appropriately
  }
  
  if (!user.group_name) {
    return json({ error: 'User group not found, cannot save document.' }, { status: 403 });
  }

  const formData = await request.formData();
  const markdownContent = formData.get('markdownContent') as string; // This will be from MDEditor
  const docId = formData.get('docId') as string;
  const filename = formData.get('filename') as string; // We'll use filename directly if docId is not filename
  const intent = formData.get('_action');

  if (intent !== 'saveMarkdown') {
    return json({ error: 'Invalid action' }, { status: 400 });
  }

  if (!markdownContent || typeof markdownContent !== 'string') {
    return json({ error: 'Markdown content is missing or invalid.' }, { status: 400 });
  }
  if (!docId) {
    return json({ error: 'Document ID is missing.' }, { status: 400 });
  }
   if (!filename) {
    return json({ error: 'Filename is missing.' }, { status: 400 });
  }


  // Construct the full path to the document
  // Using /chatfront/data as specified by the user
  const docsDir = path.join('/chatfront/data', user.group_name, 'srsdocs');
  const filePath = path.join(docsDir, filename); // Assuming filename is passed and is correct

  try {
    // Read the existing file to preserve frontmatter
    const existingFileContent = await fs.readFile(filePath, 'utf-8');
    const { data: frontmatter } = matter(existingFileContent);

    // Create the new content with original frontmatter and new markdown body
    const newFileContent = matter.stringify(markdownContent, frontmatter);

    await fs.writeFile(filePath, newFileContent, 'utf-8');
    
    // Successfully saved, potentially redirect or return success
    // To refresh the page with new content, you might revalidate data or redirect
    // For now, just return success. A redirect to the same page forces a loader re-run.
    return redirect(`/srsdoc/${docId}`, {
      headers: {
        'Cache-Control': 'no-cache', // Ensure fresh data is loaded
      }
    });

  } catch (error: any) {
    console.error('Failed to save SRS document:', error);
    return json({ error: `Failed to save document: ${error.message || 'Unknown error'}` }, { status: 500 });
  }
} 