import { LoaderFunctionArgs, json } from '@remix-run/node';
import { promises as fs } from 'fs';
import { join } from 'path';

export async function loader({ params }: LoaderFunctionArgs) {
  try {
    const { filename } = params;
    if (!filename) {
      throw new Error('Filename is required');
    }

    // Ensure the filename only contains safe characters
    if (!/^[a-zA-Z0-9-_.]+\.puml$/.test(filename)) {
      throw new Error('Invalid filename');
    }

    const diagramsPath = join(process.cwd(), 'diagrams');
    const filePath = join(diagramsPath, filename);
    const content = await fs.readFile(filePath, 'utf-8');
    
    return new Response(content, {
      headers: {
        'Content-Type': 'text/plain',
      },
    });
  } catch (error) {
    console.error('Error reading diagram file:', error);
    throw json({ error: 'Failed to read diagram file' }, { status: 404 });
  }
} 