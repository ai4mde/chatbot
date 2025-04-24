import { json, type LoaderFunctionArgs } from '@remix-run/node';
import { getSession } from '../services/session.server';
import fs from 'fs/promises';
import path from 'path';

export async function loader({ request }: LoaderFunctionArgs) {
  const session = await getSession(request);
  const user = session.get('user');
  
  if (!user || !user.group) {
    throw new Response('Unauthorized', { status: 401 });
  }

  const url = new URL(request.url);
  const diagramName = url.searchParams.get('name');

  if (!diagramName) {
    return json({ error: 'Diagram name is required' }, { status: 400 });
  }

  const diagramPath = path.join('data', user.group, 'diagrams', `${diagramName}.puml`);

  try {
    const content = await fs.readFile(diagramPath, 'utf-8');
    return json({ content });
  } catch (error) {
    console.error('Error loading diagram:', error);
    return json({ error: 'Diagram not found' }, { status: 404 });
  }
}

export async function action({ request }: LoaderFunctionArgs) {
  const session = await getSession(request);
  const user = session.get('user');
  
  if (!user || !user.group) {
    throw new Response('Unauthorized', { status: 401 });
  }

  if (request.method !== 'POST') {
    return json({ error: 'Method not allowed' }, { status: 405 });
  }

  const formData = await request.formData();
  const name = formData.get('name')?.toString();
  const content = formData.get('content')?.toString();

  if (!name || !content) {
    return json({ error: 'Name and content are required' }, { status: 400 });
  }

  const diagramPath = path.join('data', user.group, 'diagrams', `${name}.puml`);

  try {
    // Ensure the directory exists
    await fs.mkdir(path.dirname(diagramPath), { recursive: true });
    await fs.writeFile(diagramPath, content, 'utf-8');
    return json({ success: true });
  } catch (error) {
    console.error('Error saving diagram:', error);
    return json({ error: 'Failed to save diagram' }, { status: 500 });
  }
} 