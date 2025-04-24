import { Node, Edge } from 'reactflow';

// Specific Node Data Interfaces (can be extended)
export interface UMLClassData { 
    name: string;
    type: 'class' | 'interface' | 'enum';
    isAbstract: boolean;
    stereotypes: string[];
    attributes: Array<{ /* ... details ... */ visibility: string; name: string; type?: string; isStatic: boolean; isAbstract: boolean; }>;
    methods: Array<{ /* ... details ... */ visibility: string; name: string; parameters: Array<{ name: string; type?: string }>; returnType?: string; isStatic: boolean; isAbstract: boolean; }>;
}

export interface UMLUseCaseData { 
    name: string;
    type: 'actor' | 'usecase' | 'system'; 
}

export interface UMLActivityData { 
    name?: string; 
    type: 'start' | 'end' | 'action' | 'decision' | 'fork' | 'join' | 'partition'; 
}

export interface UMLSequenceData {
    name: string;
    type: 'participant' | 'lifeline' | 'activation' | 'message'; 
    pumlKeyword?: string;
}

// Union type for Node data
export type UMLNodeData = UMLClassData | UMLUseCaseData | UMLActivityData | UMLSequenceData;

// Result type for all parsers
export interface ParseResult {
  nodes: Array<Node<UMLNodeData>>; 
  edges: Edge[];
} 