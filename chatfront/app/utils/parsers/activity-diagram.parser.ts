import { Node, Edge } from 'reactflow';
import { ParseResult, UMLActivityData } from './types';
// Potentially import CLASS_RELATIONSHIPS if needed for default edge type?
// import { CLASS_RELATIONSHIPS } from '../../components/diagrams/diagram-flow';

// Basic Regex Patterns
const startRegex = /^\(\*\)/;
const endRegex = /^(stop|end)$/;
const actionRegex = /^:(.+);/;
const arrowRegex = /->(?:\s*\[(.*)\])?(?:\s*(.*))?/; 
const decisionRegex = /^if\s*\((.*?)\)\s*then(?:\s*\((.*?)\))?/;
const elseRegex = /^else(?:\s*\((.*?)\))?/;
const endifRegex = /^endif/;

export function parseActivityDiagram(code: string): ParseResult {
  console.log('Parsing activity diagram:', code);
  const nodes: Array<Node<UMLActivityData>> = [];
  const edges: Edge[] = [];
  let nodeId = 0;
  const nodeMap: { [key: string]: string } = {}; 
  let lastNodeId: string | null = null; 
  let currentDecisionNodeId: string | null = null;
  let lastBranchNodeId: string | null = null;

  const lines = code
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && !line.startsWith('@') && !line.startsWith('\''));

  try {
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      let match;
      let createdNodeId: string | null = null;
      let labelText: string | undefined = undefined;

      // Start Node
      if (startRegex.test(line)) {
        const id = 'start'; 
        if (!nodeMap[id]) {
          nodes.push({id, type: 'activityStart', position: { x: 300, y: 50 }, data: { type: 'start' } });
          nodeMap[id] = id;
          createdNodeId = id;
        }
      }
      // End Node
      else if (endRegex.test(line)) {
        const id = 'end'; 
        if (!nodeMap[id]) {
            nodes.push({id, type: 'activityEnd', position: { x: 300, y: 50 + (nodes.length * 100) }, data: { type: 'end' } });
            nodeMap[id] = id;
            createdNodeId = id;
        }
      }
      // Action Node
      else if (match = line.match(actionRegex)) {
        const name = match[1].trim();
        const id = name; 
        if (!nodeMap[id]) {
            nodes.push({ id, type: 'activityAction', position: { x: 300, y: 50 + (nodes.length * 100) }, data: { name, type: 'action' } });
            nodeMap[id] = id;
            createdNodeId = id;
        }
      }
      // Decision Node Start
      else if (match = line.match(decisionRegex)) {
        const condition = match[1].trim();
        const thenLabel = match[2]?.trim();
        const id = `decision_${condition.replace(/\s+/g, '_')}`; 
        if (!nodeMap[id]) {
            nodes.push({ id, type: 'activityDecision', position: { x: 300, y: 50 + (nodes.length * 100) }, data: { name: condition, type: 'decision' } });
            nodeMap[id] = id;
            createdNodeId = id;
            currentDecisionNodeId = id; 
            lastBranchNodeId = null; 
            labelText = thenLabel; 
        }
      }
      // Decision Else Branch
      else if (match = line.match(elseRegex)) {
          if (currentDecisionNodeId) {
              lastBranchNodeId = null; 
              labelText = match[1]?.trim(); 
          } else {
              console.warn('Found "else" without corresponding "if":', line);
          }
      }
       // Decision End
      else if (endifRegex.test(line)) {
          if (currentDecisionNodeId) { /* ... */ }
          currentDecisionNodeId = null;
          lastBranchNodeId = null; 
      }

      // Edge Creation Logic (Contains type errors)
      if (createdNodeId) { 
         let sourceId = lastNodeId; 
         if (currentDecisionNodeId) {
             if (sourceId === currentDecisionNodeId) { /* Edge from decision */ }
             else if (lastBranchNodeId) { sourceId = lastBranchNodeId; }
         }
         let edgeLabel = labelText;
         if (i + 1 < lines.length) {
            const nextLineMatch = lines[i+1].match(arrowRegex);
            if(nextLineMatch) { /* ... consume label/target from next line ... */ i++; }
         }
         if (sourceId && sourceId !== createdNodeId) { 
            edges.push({
                id: `e${sourceId}-${createdNodeId}`,
                source: sourceId,
                target: createdNodeId,
                type: 'umlEdge', 
                label: edgeLabel || '',
                data: { type: 'association' }, // Default type
            });
         } 
         // Update tracking - THIS IS WHERE THE LINTER ERRORS WERE
         if (currentDecisionNodeId) {
            lastBranchNodeId = createdNodeId; // Error: Type 'string' is not assignable to type 'null'
         } else {
            lastNodeId = createdNodeId; 
         }
      } else if (lastNodeId && line.match(arrowRegex)) {
          // ... handle arrows on separate lines ...
      }
    }

    console.log('[Activity Parser] Completed parsing. Nodes:', nodes.length, 'Edges:', edges.length);
    return { nodes, edges };

  } catch (error) {
    console.error('Error parsing activity diagram:', error);
    throw error;
  }
} 