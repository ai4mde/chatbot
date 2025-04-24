import { Node, Edge } from 'reactflow';
import { ParseResult, UMLUseCaseData } from './types';
import { CLASS_RELATIONSHIPS } from '../../components/diagrams/diagram-flow'; // Keep if needed for edge types

// Regex patterns for Use Case elements
const actorRegex = /^\s*actor\s+"?([^\"]+)"?\s*(?:as\s+(\w+))?/;
const actorColonRegex = /^\s*:([^:]+):\s*(?:as\s+(\w+))?/;
const useCaseRegex = /^\s*usecase\s+"?([^\"]+)"?\s*(?:as\s+(\w+))?/;
const useCaseParenRegex = /^\s*\(([^)]+)\)\s*(?:as\s+(\w+))?/;
// Relationship Regex (can potentially be shared or made more specific)
const relationshipRegex = /^\s*(\S+)\s*(?:\"([^\"]*)\"|\'([^\']*)\')?\s*([*o<|.]?)([\.-]+)([*>|.]?)\s*(?:\"([^\"]*)\"|\'([^\']*)\')?\s*(\S+)\s*(?::\s*(.*))?$/;


export function parseUseCaseDiagram(code: string): ParseResult {
  console.log('Parsing use-case diagram:', code);
  const nodes: Array<Node<UMLUseCaseData>> = []; 
  const edges: Edge[] = [];
  let nodeId = 0;
  const nodeMap: { [key: string]: string } = {}; 

  const lines = code
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && !line.startsWith('@') && !line.startsWith('\''));

  try {
    for (const line of lines) {
      let match;

      // Actor Definitions
      if (match = line.match(actorRegex) || line.match(actorColonRegex)) {
        const [, name, alias] = match;
        const id = (++nodeId).toString();
        const cleanName = name.trim();
        nodes.push({
          id,
          type: 'useCaseActor', 
          position: { x: 100, y: 50 + nodeId * 100 }, 
          data: { name: cleanName, type: 'actor' },
        });
        nodeMap[cleanName] = id;
        if (alias) nodeMap[alias.trim()] = id;
        continue;
      }

      // Use Case Definitions
      if (match = line.match(useCaseRegex) || line.match(useCaseParenRegex)) {
        const [, name, alias] = match;
        const id = (++nodeId).toString();
        const cleanName = name.trim();
        nodes.push({
          id,
          type: 'useCase', 
          position: { x: 400, y: 50 + nodeId * 80 }, 
          data: { name: cleanName, type: 'usecase' },
        });
        nodeMap[cleanName] = id;
        if (alias) nodeMap[alias.trim()] = id;
        continue;
      }

      // Relationship Definitions
      if (match = line.match(relationshipRegex)) {
         const [,
           sourceRaw, , , 
           startAdornment, 
           lineStyle,
           endAdornment, , , 
           targetRaw,
           label
         ] = match;

         const sourceClean = sourceRaw.replace(/^:|:$/g, '').replace(/^\(|\)$/g, '').trim();
         const targetClean = targetRaw.replace(/^:|:$/g, '').replace(/^\(|\)$/g, '').trim();

         const sourceId = nodeMap[sourceClean];
         const targetId = nodeMap[targetClean];

         if (sourceId && targetId) {
           let relType: string = CLASS_RELATIONSHIPS.ASSOCIATION; 
           const isDotted = lineStyle.includes('.');
           const labelLower = label?.toLowerCase() || '';

           if (isDotted) {
               if (labelLower.includes('include')) relType = 'include'; 
               else if (labelLower.includes('extend')) relType = 'extend';
               else relType = CLASS_RELATIONSHIPS.DEPENDENCY; 
           } else { 
               relType = CLASS_RELATIONSHIPS.ASSOCIATION;
           }
           
           const displayLabel = label ? label.trim().replace(/[<>]$/, '').replace(/:?\s*(include|extend)\s*$/i, '').trim() : '';

           const edge = {
             id: `e${sourceId}-${targetId}-${relType}`,
             source: sourceId,
             target: targetId,
             type: 'umlEdge',
             label: displayLabel, 
             data: { type: relType },
           };
           // console.log('[Use Case Parser] Creating edge:', edge);
           edges.push(edge);
         } else {
            console.warn(`[Use Case Parser] Could not map relationship: ${sourceClean} -> ${targetClean}`);
         }
         continue;
      }
      // TODO: Add rectangle parsing
    }
    console.log('[Use Case Parser] Completed parsing. Nodes:', nodes.length, 'Edges:', edges.length);
    return { nodes, edges };

  } catch (error) {
    console.error('Error parsing use-case diagram:', error);
    throw error;
  }
} 