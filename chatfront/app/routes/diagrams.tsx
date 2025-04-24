import * as React from 'react';
import { json, type LoaderFunctionArgs, type ActionFunctionArgs, redirect } from '@remix-run/node';
import { useLoaderData, useRouteError } from '@remix-run/react';
import { useCallback, useState, useRef } from 'react';
import { Node, Edge, applyNodeChanges, applyEdgeChanges, addEdge, NodeChange, EdgeChange } from 'reactflow';
import { promises as fs } from 'fs';
import path from 'path';
import { FileText, Upload, Plus, Layout } from 'lucide-react';
import { getSession } from '../services/session.server';
import { Link } from '@remix-run/react';
import { Button } from '../components/ui/button';
import { isRouteErrorResponse } from '@remix-run/react';
// @ts-ignore 
import ELK from 'elkjs/lib/elk.bundled.js'; // Suppress import error for now
import { parsePlantUML } from '../utils/plantuml-parser';

import { DiagramFlow } from '../components/diagrams/diagram-flow';
import { PlantUMLImport } from '../components/diagrams/plantuml-import';
import { DiagramHeader } from '../components/diagrams/diagram-header';
import { NewDiagramDialog } from '../components/diagrams/new-diagram-dialog';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { useToast } from '../components/ui/use-toast';

export async function loader({ request }: LoaderFunctionArgs) {
  const session = await getSession(request);
  const user = session.get('user');
  
  if (!user) {
    throw new Response('Unauthorized', { status: 401 });
  }

  // For debugging
  console.log('User session:', user);
  
  // Use the group_name from the user session
  const userGroup = user.group_name; // Changed from user.group
  if (!userGroup) {
    throw new Response('No group assigned', { status: 403 });
  }

  const diagramsPath = path.join(process.cwd(), 'data', userGroup, 'diagrams');
  
  try {
    await fs.mkdir(diagramsPath, { recursive: true });
    const files = await fs.readdir(diagramsPath);
    const diagrams = await Promise.all(
      files
        .filter(file => file.endsWith('.puml'))
        .map(async (file) => {
          const content = await fs.readFile(
            path.join(diagramsPath, file),
            'utf-8'
          );
          return {
            name: file.replace('.puml', ''),
            content,
            path: path.join(diagramsPath, file)
          };
        })
    );
    
    return json({ diagrams });
  } catch (error) {
    console.error('Error loading diagrams:', error);
    return json({ diagrams: [] });
  }
}

export async function action({ request }: ActionFunctionArgs) {
  const formData = await request.formData();
  const intent = formData.get('intent');

  switch (intent) {
    case 'create':
      // Handle diagram creation
      break;
    case 'update':
      // Handle diagram update
      break;
    case 'delete':
      // Handle diagram deletion
      break;
  }
  
  return json({ success: true });
}

// Default layout options for ELK. Change as needed.
const elkOptions = {
  'elk.algorithm': 'layered',
  'elk.direction': 'DOWN',
  'elk.layered.spacing.nodeNodeBetweenLayers': '120',
  'elk.spacing.nodeNode': '100',
  'elk.layered.edgeRouting': 'ORTHOGONAL',
};

async function getLayoutedElements(nodes: Node[], edges: Edge[], direction: 'TB' | 'LR' = 'TB'): Promise<Node[]> {
  const elk = new ELK(); // Instantiate ELK inside the function
  const isHorizontal = direction === 'LR';
  const graph = {
    id: 'root',
    layoutOptions: { 
      ...elkOptions,
      'elk.direction': isHorizontal ? 'RIGHT' : 'DOWN',
    },
    children: nodes.map((node) => ({
      ...node,
      width: node.width ?? (node.type === 'umlClass' ? 300 : 150),
      height: node.height ?? (node.type === 'umlClass' ? 
        (node.data.methods?.length || 0) * 30 + 
        (node.data.attributes?.length || 0) * 30 + 100 : 100),
    })),
    edges: edges.map((edge) => ({ ...edge, sources: [edge.source], targets: [edge.target] })),
  };

  try {
    const layoutedGraph = await elk.layout(graph as any); 
    return layoutedGraph.children?.map((node) => ({
      ...nodes.find(n => n.id === node.id)!, 
      position: { x: node.x!, y: node.y! },
    })) || [];
  } catch (error) {
    console.error('ELK layout failed:', error);
    throw error; // Re-throw error to be caught by caller
  }
}

export default function DiagramsPage() {
  const { diagrams } = useLoaderData<typeof loader>();
  const { toast } = useToast();
  const [plantUmlCode, setPlantUmlCode] = useState<string>('');
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);
  const [isNewDialogOpen, setIsNewDialogOpen] = useState(false);
  const [nodeCount, setNodeCount] = React.useState(0);
  const [isDiagramActive, setIsDiagramActive] = useState(false);
  const [diagramType, setDiagramType] = useState<'class' | 'activity' | 'useCase' | 'sequence'>('class');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isLoadingLayout, setIsLoadingLayout] = useState(false);

  const handleImport = useCallback((code: string, importedNodes: Node[], importedEdges: Edge[]) => {
    // Set initial state immediately
    setPlantUmlCode(code);
    let type: 'class' | 'activity' | 'useCase' | 'sequence' = 'class';
    if (code.includes('@startclass')) type = 'class';
    else if (code.includes('@startactivity')) type = 'activity';
    else if (code.includes('@startusecase')) type = 'useCase';
    else if (code.includes('@startsequence')) type = 'sequence';
    
    setDiagramType(type);
    setNodes(importedNodes);
    setEdges(importedEdges);
    setIsImportDialogOpen(false);
    setIsDiagramActive(true);
    toast({ title: 'Import Successful', description: 'Diagram imported. Applying layout...' });

    // Apply layout asynchronously AFTER setting state
    const applyLayout = async () => {
        setIsLoadingLayout(true);
        try {
            // Pass the nodes/edges that were just set
            const layoutedNodes = await getLayoutedElements(importedNodes, importedEdges); 
            // Update nodes again with layout positions
            setNodes(layoutedNodes); 
            // Update toast
            toast({ title: 'Layout Applied', description: 'Diagram has been auto-arranged.' });
        } catch (error) { // Catch layout error specifically
            console.error("Layouting failed during import:", error);
            toast({ title: 'Layout Error', description: 'Could not auto-arrange diagram.', variant: 'destructive' });
        } finally {
            setIsLoadingLayout(false);
        }
    };
    // Use setTimeout to ensure state update has rendered before starting layout
    setTimeout(applyLayout, 0); 
  }, [toast]); // Removed setIsLoadingLayout from deps as it's handled internally

  const handleNew = useCallback((type: 'class' | 'activity' | 'useCase' | 'sequence') => {
    setPlantUmlCode('');
    setNodes([]);
    setEdges([]);
    setNodeCount(0);
    setDiagramType(type);
    setIsDiagramActive(true);
    setIsNewDialogOpen(false);
    toast({
      title: 'New Diagram',
      description: `Created a new ${type} diagram`,
    });
  }, [toast]);

  const handleImportClick = () => {
    setIsImportDialogOpen(true);
  };

  const handleExportClick = () => {
    if (!plantUmlCode) {
      toast({
        title: 'Export Failed',
        description: 'No diagram to export',
        variant: 'destructive',
      });
      return;
    }

    const blob = new Blob([plantUmlCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'diagram.puml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast({
      title: 'Export Successful',
      description: 'Diagram exported as PlantUML file',
    });
  };

  const handleAddClass = useCallback(() => {
    const newNode: Node = {
      id: `${nodeCount + 1}`,
      type: 'umlClass',
      position: { x: 250, y: 100 },
      data: {
        name: `NewClass${nodeCount + 1}`,
        attributes: [],
        methods: [],
        type: 'class',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeCount((count) => count + 1);
  }, [nodeCount]);

  const handleAddEnum = useCallback(() => {
    const newNode: Node = {
      id: `${nodeCount + 1}`,
      type: 'umlEnum',
      position: { x: 250, y: 100 },
      data: {
        name: `NewEnum${nodeCount + 1}`,
        attributes: [],
        methods: [],
        type: 'enum',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeCount((count) => count + 1);
  }, [nodeCount]);

  const handleAddAction = useCallback(() => {
    const newNode: Node = {
      id: `${nodeCount + 1}`,
      type: 'activityAction',
      position: { x: 250, y: 100 },
      data: {
        name: `Action${nodeCount + 1}`,
        type: 'action',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeCount((count) => count + 1);
  }, [nodeCount]);

  const handleAddDecision = useCallback(() => {
    const newNode: Node = {
      id: `${nodeCount + 1}`,
      type: 'activityDecision',
      position: { x: 250, y: 100 },
      data: {
        name: `Decision${nodeCount + 1}`,
        type: 'decision',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeCount((count) => count + 1);
  }, [nodeCount]);

  const handleAddStart = useCallback(() => {
    const newNode: Node = {
      id: `${nodeCount + 1}`,
      type: 'activityStart',
      position: { x: 250, y: 100 },
      data: {
        type: 'start',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeCount((count) => count + 1);
  }, [nodeCount]);

  const handleAddEnd = useCallback(() => {
    const newNode: Node = {
      id: `${nodeCount + 1}`,
      type: 'activityEnd',
      position: { x: 250, y: 100 },
      data: {
        type: 'end',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeCount((count) => count + 1);
  }, [nodeCount]);

  const handleAddActor = useCallback(() => {
    const newNode: Node = {
      id: `${nodeCount + 1}`,
      type: 'useCaseActor',
      position: { x: 250, y: 100 },
      data: {
        name: `Actor${nodeCount + 1}`,
        type: 'actor',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeCount((count) => count + 1);
  }, [nodeCount]);

  const handleAddUseCase = useCallback(() => {
    const newNode: Node = {
      id: `${nodeCount + 1}`,
      type: 'useCase',
      position: { x: 250, y: 100 },
      data: {
        name: `UseCase${nodeCount + 1}`,
        type: 'useCase',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeCount((count) => count + 1);
  }, [nodeCount]);

  const handleAddSystem = useCallback(() => {
    const newNode: Node = {
      id: `${nodeCount + 1}`,
      type: 'useCaseSystem',
      position: { x: 250, y: 100 },
      data: {
        name: `System${nodeCount + 1}`,
        type: 'system',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeCount((count) => count + 1);
  }, [nodeCount]);

  const handleAddLifeline = useCallback(() => {
    const newNode: Node = {
      id: `${nodeCount + 1}`,
      type: 'sequenceLifeline',
      position: { x: 250, y: 100 },
      data: {
        name: `Object${nodeCount + 1}`,
        type: 'lifeline',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeCount((count) => count + 1);
  }, [nodeCount]);

  const handleAddActivation = useCallback(() => {
    const newNode: Node = {
      id: `${nodeCount + 1}`,
      type: 'sequenceActivation',
      position: { x: 250, y: 100 },
      data: {
        type: 'activation',
        isActive: true,
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeCount((count) => count + 1);
  }, [nodeCount]);

  const handleAddMessage = useCallback(() => {
    const newNode: Node = {
      id: `${nodeCount + 1}`,
      type: 'sequenceMessage',
      position: { x: 250, y: 100 },
      data: {
        name: `message${nodeCount + 1}()`,
        type: 'message',
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeCount((count) => count + 1);
  }, [nodeCount]);

  const handleLayout = useCallback(async () => {
    setIsLoadingLayout(true);
    try {
      const layoutedNodes = await getLayoutedElements(nodes, edges);
      setNodes(layoutedNodes);
      toast({
        title: 'Layout Applied',
        description: 'Diagram has been auto-arranged',
      });
    } catch (error) {
       console.error("Layouting failed:", error);
       toast({ title: 'Layout Error', description: 'Could not auto-arrange diagram.', variant: 'destructive' });
    } finally {
      setIsLoadingLayout(false);
    }
  }, [nodes, edges, toast]);

  const handleLoadDiagram = useCallback(async (diagram: { name: string; content: string }) => {
    // No setIsLoadingLayout here, handleImport will manage it
    try {
      const { nodes: parsedNodes, edges: parsedEdges } = parsePlantUML(diagram.content);
      // Call handleImport, which now handles setting initial state + async layout
      handleImport(diagram.content, parsedNodes, parsedEdges); 
      // Toasts are now handled within handleImport
    } catch (error) {
      console.error('Error parsing or initiating load:', error);
      toast({
        title: 'Error',
        description: 'Failed to load diagram. Check format.',
        variant: 'destructive',
      });
      setIsDiagramActive(false); // Ensure state is reasonable on failure
      setIsLoadingLayout(false); // Make sure loading stops if parse fails
    }
  }, [handleImport, toast]);

  if (!isDiagramActive) {
    return (
      <div className='flex flex-col items-center justify-center h-[calc(100vh-4rem)] bg-background'>
        <div className='text-center space-y-6 max-w-2xl px-4'>
          <h1 className='text-4xl font-bold mb-8'>Welcome to UML Diagram Editor</h1>
          
          <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
            <Button
              onClick={() => setIsNewDialogOpen(true)}
              variant='outline'
              size='lg'
              className='relative p-8 h-auto flex flex-col items-center gap-4 border-2'
            >
              <Plus className='h-12 w-12' />
              <div className='text-center'>
                <h2 className='text-xl font-semibold'>Create New Diagram</h2>
              </div>
            </Button>

            <Button
              onClick={handleImportClick}
              variant='outline'
              size='lg'
              className='relative p-8 h-auto flex flex-col items-center gap-4 border-2'
            >
              <Upload className='h-12 w-12' />
              <div className='text-center'>
                <h2 className='text-xl font-semibold'>Load Diagram</h2>
              </div>
            </Button>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-2 gap-6 mt-4'>
            <div className='text-center'>
              <p className='text-sm text-muted-foreground'>
                Start with a blank canvas and create your UML diagram from scratch
              </p>
            </div>
            <div className='text-center'>
              <p className='text-sm text-muted-foreground'>
                Import an existing PlantUML diagram and continue working on it
              </p>
            </div>
          </div>

          {diagrams.length > 0 && (
            <div className='mt-12'>
              <h2 className='text-xl font-semibold mb-4'>Recent Diagrams</h2>
              <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
                {diagrams.map((diagram) => (
                  <Button
                    key={diagram.name}
                    variant='outline'
                    className='p-4 h-auto flex items-center gap-3 justify-start'
                    onClick={() => handleLoadDiagram(diagram)}
                  >
                    <FileText className='h-5 w-5' />
                    <span className='truncate'>{diagram.name}</span>
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>

        <NewDiagramDialog
          open={isNewDialogOpen}
          onOpenChange={setIsNewDialogOpen}
          onSelectType={handleNew}
        />
      </div>
    );
  }

  return (
    <div className='flex flex-col h-[calc(100vh-4rem)]'>
      <DiagramHeader
        title={`UML ${diagramType.charAt(0).toUpperCase() + diagramType.slice(1)} Diagram`}
        onImport={handleImportClick}
        onExport={handleExportClick}
        onNew={() => setIsNewDialogOpen(true)}
        onLayout={handleLayout}
        onAddClass={diagramType === 'class' ? handleAddClass : undefined}
        onAddEnum={diagramType === 'class' ? handleAddEnum : undefined}
        onAddAction={diagramType === 'activity' ? handleAddAction : undefined}
        onAddDecision={diagramType === 'activity' ? handleAddDecision : undefined}
        onAddStart={diagramType === 'activity' ? handleAddStart : undefined}
        onAddEnd={diagramType === 'activity' ? handleAddEnd : undefined}
        onAddActor={diagramType === 'useCase' ? handleAddActor : undefined}
        onAddUseCase={diagramType === 'useCase' ? handleAddUseCase : undefined}
        onAddSystem={diagramType === 'useCase' ? handleAddSystem : undefined}
        onAddLifeline={diagramType === 'sequence' ? handleAddLifeline : undefined}
        onAddActivation={diagramType === 'sequence' ? handleAddActivation : undefined}
        onAddMessage={diagramType === 'sequence' ? handleAddMessage : undefined}
      />
      
      <div className='flex-1 relative'>
        {isLoadingLayout && (
          <div className="absolute inset-0 bg-gray-100 bg-opacity-50 flex items-center justify-center z-50">
             <p className="text-lg font-semibold">Applying layout...</p>
          </div>
        )}
        <DiagramFlow 
          nodes={nodes}
          edges={edges}
          onNodesChange={setNodes}
          onEdgesChange={setEdges}
        />
      </div>

      <Dialog open={isImportDialogOpen} onOpenChange={setIsImportDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Import PlantUML Diagram</DialogTitle>
          </DialogHeader>
          <PlantUMLImport onImport={handleImport} diagrams={diagrams} />
        </DialogContent>
      </Dialog>

      <NewDiagramDialog
        open={isNewDialogOpen}
        onOpenChange={setIsNewDialogOpen}
        onSelectType={handleNew}
      />
    </div>
  );
}