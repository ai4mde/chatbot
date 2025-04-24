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

// Moved getDocument function up and added groupName parameter
async function getDocument(id: string, groupName: string): Promise<Doc | null> {
  // Use groupName in the path construction
  const docsDir = path.join(process.cwd(), 'data', groupName, 'srsdocs');
  
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

// Moved processPlantUml function up
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

// Updated loader function
export async function loader({ request, params }: LoaderFunctionArgs) {
  try {
    const user = await requireUser(request);
    
    if (!user.group_name) {
      throw new Response('User group not found', { status: 403 });
    }

    // Pass user.group_name to getDocument
    const doc = await getDocument(params.id || '', user.group_name);
    
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
      return redirect(`/login?redirectTo=/srsdocs/${params.id}`);
    }
    throw error;
  }
}

// Simplified markdown options with consistent rendering
const markdownOptions = {
// ... existing code ...
} 