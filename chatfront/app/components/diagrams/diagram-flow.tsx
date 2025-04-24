import * as React from 'react';
import ReactFlow, {
  Background,
  Controls,
  Node,
  Edge,
  NodeTypes,
  useNodesState,
  useEdgesState,
  ConnectionLineType,
  MarkerType,
  BaseEdge,
  EdgeProps,
  getSmoothStepPath,
  Connection,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  EdgeLabelRenderer,
  useReactFlow,
  ConnectionMode,
} from 'reactflow';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { Button } from '../ui/button';
import { ChevronDown, Trash2 } from 'lucide-react';
import 'reactflow/dist/style.css';
import { ClassNode } from './uml-nodes/class-node';
import { 
  ActivityActionNode, 
  ActivityDecisionNode, 
  ActivityStartNode, 
  ActivityEndNode 
} from './uml-nodes/activity-nodes';
import {
  ActorNode,
  UseCaseNode,
  SystemBoundaryNode,
} from './uml-nodes/usecase-nodes';
import {
  LifelineNode,
  ActivationNode,
  MessageNode,
} from './uml-nodes/sequence-nodes';

const nodeTypes: NodeTypes = {
  umlClass: ClassNode,
  umlEnum: ClassNode,
  activityAction: ActivityActionNode,
  activityDecision: ActivityDecisionNode,
  activityStart: ActivityStartNode,
  activityEnd: ActivityEndNode,
  useCaseActor: ActorNode,
  useCase: UseCaseNode,
  useCaseSystem: SystemBoundaryNode,
  sequenceLifeline: LifelineNode,
  sequenceActivation: ActivationNode,
  sequenceMessage: MessageNode,
} as const;

// Define relationship types
export const CLASS_RELATIONSHIPS = {
  INHERITANCE: 'inheritance',
  IMPLEMENTATION: 'implementation',
  ASSOCIATION: 'association',
  AGGREGATION: 'aggregation',
  COMPOSITION: 'composition',
  DEPENDENCY: 'dependency',
} as const;

type RelationshipType = typeof CLASS_RELATIONSHIPS[keyof typeof CLASS_RELATIONSHIPS];

interface UMLEdgeProps extends EdgeProps {
  type?: RelationshipType;
  selected?: boolean;
  data?: any;
}

interface EdgeMarker {
  type: MarkerType;
  width: number;
  height: number;
  color?: string;
  strokeWidth?: number;
  stroke?: string;
}

// Custom edge components
function UMLEdge({ 
  id, 
  sourceX, 
  sourceY, 
  targetX, 
  targetY, 
  style = {}, 
  label,
  selected,
  data = {},
}: UMLEdgeProps) {
  console.log(`[UMLEdge] Rendering edge id: ${id}, data:`, data);
  const { getEdges, setEdges, deleteElements } = useReactFlow();
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  });
  const actualType = data.type || CLASS_RELATIONSHIPS.ASSOCIATION;
  let edgeStyle = { 
    ...style,
    stroke: selected ? '#374151' : '#000000',
    strokeWidth: selected ? 3 : 2,
  };
  const handleTypeChange = (newType: RelationshipType) => {
    const edges = getEdges();
    const newEdges = edges.map((edge) => {
      if (edge.id === id) {
        return {
          ...edge,
          data: { 
            ...edge.data,
            type: newType 
          },
        };
      }
      return edge;
    });
    setEdges(newEdges);
  };
  const handleDelete = () => {
    deleteElements({ edges: [{ id }] });
  };

  return (
    <>
      <defs>
        {/* Inheritance/Implementation Arrow */}
        <marker
          id={`${id}-inheritance-arrow`}
          viewBox='0 0 12 12'
          refX='11'
          refY='6'
          markerWidth='12'
          markerHeight='12'
          orient='auto'
        >
          <path
            d='M 0 0 L 12 6 L 0 12 L 4 6 z'
            fill={actualType === CLASS_RELATIONSHIPS.IMPLEMENTATION ? 'white' : edgeStyle.stroke}
            stroke={edgeStyle.stroke}
            strokeWidth='1'
          />
        </marker>

        {/* Association/Dependency Arrow */}
        <marker
          id={`${id}-arrow`}
          viewBox='0 0 12 12'
          refX='11'
          refY='6'
          markerWidth='12'
          markerHeight='12'
          orient='auto'
        >
          <path
            d='M 0 0 L 10 6 L 0 12'
            fill='none'
            stroke={edgeStyle.stroke}
            strokeWidth='1'
          />
        </marker>

        {/* Diamond */}
        <marker
          id={`${id}-diamond`}
          viewBox='0 0 12 12'
          refX='12'
          refY='6'
          markerWidth='12'
          markerHeight='12'
          orient='auto'
        >
          <path
            d='M 0 6 L 6 0 L 12 6 L 6 12 z'
            fill={actualType === CLASS_RELATIONSHIPS.AGGREGATION ? 'white' : edgeStyle.stroke}
            stroke={edgeStyle.stroke}
            strokeWidth='1'
          />
        </marker>
      </defs>

      <path
        id={id}
        className='react-flow__edge-path'
        d={edgePath}
        style={{
          ...edgeStyle,
          strokeWidth: selected ? 2 : 1,
          strokeDasharray: actualType === CLASS_RELATIONSHIPS.IMPLEMENTATION || actualType === CLASS_RELATIONSHIPS.DEPENDENCY ? '3 2' : undefined,
          cursor: 'pointer'
        }}
        markerEnd={
          actualType === CLASS_RELATIONSHIPS.INHERITANCE || actualType === CLASS_RELATIONSHIPS.IMPLEMENTATION
            ? `url(#${id}-inheritance-arrow)`
            : actualType === CLASS_RELATIONSHIPS.ASSOCIATION || actualType === CLASS_RELATIONSHIPS.DEPENDENCY
            ? `url(#${id}-arrow)`
            : undefined
        }
        markerStart={
          actualType === CLASS_RELATIONSHIPS.AGGREGATION || actualType === CLASS_RELATIONSHIPS.COMPOSITION
            ? `url(#${id}-diamond)`
            : undefined
        }
      />
      
      <path
        d={edgePath}
        style={{
          stroke: 'transparent',
          strokeWidth: 12,
          cursor: 'pointer',
          fill: 'none'
        }}
      />

      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'all',
            zIndex: 1000,
          }}
          className='nodrag nopan flex items-center gap-2'
        >
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant='ghost' 
                size='sm'
                className={`h-6 ${!selected ? 'hidden' : ''} bg-background border shadow-sm`}
              >
                {actualType}
                <ChevronDown className='h-3 w-3 ml-1' />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align='start' className='w-48 bg-background'>
              {Object.entries(CLASS_RELATIONSHIPS).map(([key, value]) => (
                <DropdownMenuItem
                  key={key}
                  onClick={() => handleTypeChange(value)}
                  className='capitalize'
                >
                  {value}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {selected && (
            <Button
              variant='ghost'
              size='icon'
              onClick={handleDelete}
              className='h-6 w-6 hover:bg-red-100 text-red-500 bg-background border shadow-sm'
            >
              <Trash2 className='h-3 w-3' />
            </Button>
          )}
        </div>
      </EdgeLabelRenderer>
      {label && (
        <text
          x={labelX}
          y={labelY - 20}
          className='fill-current text-sm'
          textAnchor='middle'
          alignmentBaseline='middle'
        >
          {label}
        </text>
      )}
    </>
  );
}

// Restore the missing interface and component export
interface DiagramFlowProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: (nodes: Node[]) => void;
  onEdgesChange: (edges: Edge[]) => void;
}

export function DiagramFlow({ 
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
}: DiagramFlowProps) {
  const [reactFlowInstance, setReactFlowInstance] = React.useState<any>(null);

  // Process edges to add correct styles
  const styledEdges = edges.map(edge => ({
    ...edge,
    type: 'default', // Always use default to ensure our custom edge component is used
    data: { 
      ...edge.data,
      type: edge.data?.type || CLASS_RELATIONSHIPS.ASSOCIATION 
    },
  }));

  const onConnect = React.useCallback(
    (params: Connection) => {
      // Ensure the connection is valid
      if (!params.source || !params.target) return;

      onEdgesChange(addEdge(
        {
          ...params,
          type: 'default', // Use default type for custom edge
          data: { type: CLASS_RELATIONSHIPS.ASSOCIATION }, // Default new connections to association
          style: { 
            strokeWidth: 2,
          },
        },
        edges // Pass current edges to addEdge
      ));
    },
    [edges, onEdgesChange]
  );

  const handleNodesChange = React.useCallback(
    (changes: any) => {
      onNodesChange(applyNodeChanges(changes, nodes));
    },
    [nodes, onNodesChange]
  );

  const handleEdgesChange = React.useCallback(
    (changes: any) => {
      const updatedEdges = applyEdgeChanges(changes, edges);
      onEdgesChange(updatedEdges);
    },
    [edges, onEdgesChange]
  );

  return (
    <div className='w-full h-full bg-background'>
      <ReactFlow
        nodes={nodes}
        edges={styledEdges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={onConnect}
        onInit={setReactFlowInstance}
        nodeTypes={nodeTypes}
        edgeTypes={{ default: UMLEdge }}
        defaultEdgeOptions={{
          type: 'default',
          data: { type: CLASS_RELATIONSHIPS.ASSOCIATION },
        }}
        fitView
        className='bg-gray-50'
        snapToGrid={true}
        snapGrid={[15, 15]}
        connectionMode={ConnectionMode.Loose}
        proOptions={{ hideAttribution: true }}
        selectNodesOnDrag={false}
      >
        <Background />
        <Controls className='bg-background border' />
      </ReactFlow>
    </div>
  );
}