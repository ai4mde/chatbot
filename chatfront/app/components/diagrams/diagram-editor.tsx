import * as React from 'react';
import { type ReactNode } from 'react';

interface DiagramEditorProps {
  children?: ReactNode;
}

export function DiagramEditor({ children }: DiagramEditorProps) {
  return (
    <div className='w-full h-[600px] border rounded-lg bg-background'>
      <div className='h-full'>
        {/* React Flow will be integrated here */}
        {children}
      </div>
    </div>
  );
} 