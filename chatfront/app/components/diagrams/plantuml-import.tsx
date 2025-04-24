import * as React from 'react';
import { useState } from 'react';
import { Node, Edge } from 'reactflow';
import { parsePlantUML } from '../../utils/plantuml-parser';
import { Button } from '../ui/button';

interface PlantUMLImportProps {
  onImport: (code: string, nodes: Node[], edges: Edge[]) => void;
  diagrams: Array<{
    name: string;
    content: string;
    path: string;
  }>;
}

export function PlantUMLImport({ onImport, diagrams }: PlantUMLImportProps) {
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [code, setCode] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = (filename: string) => {
    try {
      setSelectedFile(filename);
      const selectedDiagram = diagrams.find(d => d.name === filename);
      
      if (!selectedDiagram) {
        setCode('');
        return;
      }

      const code = selectedDiagram.content;
      setCode(code);
      setError(null);
    } catch (err) {
      console.error('Error selecting file:', err);
      setError('Failed to select diagram file');
    }
  };

  const handleImport = () => {
    try {
      if (!code.trim()) {
        setError('Please select a diagram file');
        return;
      }

      if (!code.includes('@startuml') || !code.includes('@enduml')) {
        setError('Invalid PlantUML file format');
        return;
      }

      console.log('Attempting to parse PlantUML code:', code);
      const result = parsePlantUML(code);
      console.log('Parse result:', result);
      
      if (!result || !result.nodes || result.nodes.length === 0) {
        setError('No valid UML elements found in the diagram');
        return;
      }

      console.log('Importing diagram with:', {
        nodes: result.nodes.length,
        edges: result.edges.length
      });

      onImport(code, result.nodes, result.edges);
      setError(null);
    } catch (err) {
      console.error('Import error:', err);
      setError(err instanceof Error ? err.message : 'Failed to parse PlantUML code');
    }
  };

  return (
    <div className='w-full space-y-4'>
      <div className='flex flex-col space-y-2'>
        <label className='text-sm font-medium'>Select Diagram</label>
        <select
          className='w-full p-2 border rounded-md'
          value={selectedFile}
          onChange={(e) => handleFileSelect(e.target.value)}
        >
          <option value=''>Select a diagram...</option>
          {diagrams.map((diagram) => (
            <option key={diagram.name} value={diagram.name}>
              {diagram.name}
            </option>
          ))}
        </select>
      </div>

      {code && (
        <div className='flex flex-col space-y-2'>
          <label className='text-sm font-medium'>Preview</label>
          <textarea
            className='w-full h-48 p-2 border rounded-md font-mono text-sm bg-muted'
            value={code}
            readOnly
          />
        </div>
      )}

      {error && (
        <div className='text-sm text-red-500 mt-2'>
          {error}
        </div>
      )}

      <div className='flex justify-end space-x-2 mt-4'>
        <Button
          variant='outline'
          onClick={() => setCode('')}
          disabled={!code.trim()}
        >
          Clear
        </Button>
        <Button
          onClick={handleImport}
          disabled={!code.trim()}
        >
          Import Diagram
        </Button>
      </div>
    </div>
  );
} 