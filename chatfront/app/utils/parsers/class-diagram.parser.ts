import { Node, Edge } from 'reactflow';
import { ParseResult, UMLClassData } from './types';
import { CLASS_RELATIONSHIPS } from '../../components/diagrams/diagram-flow'; // Keep this import if used directly

// Regex to capture relationship parts (specific to class/general relationships)
// If RELATIONSHIP_TYPES is only used here, move it here too.
const RELATIONSHIP_REGEX = /^([^\s:"']+?)\s*(?:\"([^\"]*)\"|\'([^\']*)\')?\s*([*o<\|]?)([\.\-]+)([\*o\|>]?)\s*(?:\"([^\"]*)\"|\'([^\']*)\')?\s*([^\s:"']+?)\s*(?::\s*(.*))?$/;


// Helper function to determine relationship type string based on PlantUML syntax
// If only used by class diagrams, keep it here. Otherwise, move to a shared utils file.
function determineRelationshipType(
  start: string | undefined,
  line: string,
  end: string | undefined
): typeof CLASS_RELATIONSHIPS[keyof typeof CLASS_RELATIONSHIPS] { 
  const isDotted = line.includes('.');

  // Check specific adornments first
  if (start === '<|' || end === '|>') {
    return isDotted ? CLASS_RELATIONSHIPS.IMPLEMENTATION : CLASS_RELATIONSHIPS.INHERITANCE;
  }
  if (start === '*' || end === '*') {
    return CLASS_RELATIONSHIPS.COMPOSITION;
  }
  if (start === 'o' || end === 'o') {
    return CLASS_RELATIONSHIPS.AGGREGATION;
  }
  if (start === '<' || end === '>') { 
     return isDotted ? CLASS_RELATIONSHIPS.DEPENDENCY : CLASS_RELATIONSHIPS.ASSOCIATION; 
  }
  if (isDotted) {
    return CLASS_RELATIONSHIPS.DEPENDENCY;
  }
  return CLASS_RELATIONSHIPS.ASSOCIATION;
}


export function parseClassDiagram(code: string): ParseResult {
  console.log('Parsing class diagram:', code);
  
  const nodes: Array<Node<UMLClassData>> = [];
  const edges: Edge[] = [];
  let nodeId = 0;
  let currentClass: Node<UMLClassData> | null = null;
  let inClassBlock = false;

  const lines = code
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && !line.startsWith('@'));
    
  // console.log('Filtered lines:', lines);

  try {
    for (const line of lines) {
      // console.log('Processing line:', line);
      let relationshipMatch;
      
      // Package definition
      if (line.startsWith('package ')) {
        continue;
      }

      // Class/Interface/Enum definition
      if (line.match(/^(abstract\s+)?(class|interface|enum)\s+\w+/)) {
        const parts = line.split(/\s+/);
        const isAbstract = parts[0] === 'abstract';
        const type = parts[isAbstract ? 1 : 0];
        const name = parts[isAbstract ? 2 : 1];
        
        currentClass = {
          id: (++nodeId).toString(),
          type: 'umlClass',
          position: { x: 100 + (nodeId * 200), y: 100 },
          data: {
            name,
            attributes: [],
            methods: [],
            type: type as 'class' | 'interface' | 'enum',
            isAbstract,
            stereotypes: []
          },
          draggable: true,
          selectable: true,
        };
        nodes.push(currentClass);
        inClassBlock = line.endsWith('{');
        continue;
      }

      // Member definition
      if (currentClass && inClassBlock && !(relationshipMatch = line.match(RELATIONSHIP_REGEX))) { // Check it's not a relationship
        if (line === '}') {
          inClassBlock = false;
          currentClass = null;
          continue;
        }
        // ... (Keep existing member parsing logic: visibility, static, abstract, methods, attributes) ...
        const visibility = line.charAt(0) === '+' ? 'public' : 
                          line.charAt(0) === '-' ? 'private' : 
                          line.charAt(0) === '#' ? 'protected' : 'package';
        const memberText = line.slice(1).trim();
        if (!memberText) continue;
        const isStatic = memberText.includes('{static}');
        const isAbstract = memberText.includes('{abstract}');
        const cleanMember = memberText.replace(/{static}/g, '').replace(/{abstract}/g, '').trim();

        if (cleanMember.includes('(')) { // Method
          const methodMatch = cleanMember.match(/(\w+)\((.*)\)(\s*:\s*\w+)?/);
          if (methodMatch) {
            const [, name, params, returnType] = methodMatch;
            const parameters = params.split(',').filter(p => p.trim()).map(param => {
              const [pName, pType] = param.trim().split(':').map(p => p.trim());
              return { name: pName || '', type: pType };
            });
            currentClass.data.methods.push({
              visibility, name, parameters, 
              returnType: returnType ? returnType.replace(/:\s*/, '') : undefined, 
              isStatic: Boolean(isStatic), isAbstract: Boolean(isAbstract)
            });
          }
        } else { // Attribute
          const attrMatch = cleanMember.match(/(\w+)(\s*:\s*\w+)?/);
          if (attrMatch) {
            const [, name, type] = attrMatch;
            currentClass.data.attributes.push({
              visibility, name, type: type ? type.replace(/:\s*/, '') : undefined,
              isStatic, isAbstract
            });
          }
        }
        continue;
      }

      // Reset currentClass if necessary (e.g., after a relationship line outside a block)
      if (line === '}' && inClassBlock) {
          inClassBlock = false;
          currentClass = null;
          continue; // Already handled above, but defensive
      }
       if (currentClass && !inClassBlock && !(line.match(/^(abstract\s+)?(class|interface|enum)\s+\w+/))) { // If not starting a new class
           // We might be parsing relationships outside a class block
           currentClass = null; // Assume we are no longer focused on a specific class for members
       }

      // Relationship parsing
      relationshipMatch = line.match(RELATIONSHIP_REGEX);
      if (relationshipMatch) {
         const [, 
           sourceNameRaw, sourceMultLeft, sourceMultRight, 
           startAdornment, lineStyle, endAdornment, 
           targetMultLeft, targetMultRight, targetNameRaw, label 
         ] = relationshipMatch;

         const sourceName = sourceNameRaw.trim();
         const targetName = targetNameRaw.trim();
         const sourceMultiplicity = sourceMultLeft || sourceMultRight;
         const targetMultiplicity = targetMultLeft || targetMultRight;

         // Find nodes based on name (simple lookup for now)
         const sourceNode = nodes.find(n => n.data.name === sourceName);
         const targetNode = nodes.find(n => n.data.name === targetName);

         if (sourceNode && targetNode) {
           const relationshipType = determineRelationshipType(startAdornment, lineStyle, endAdornment);
           const edge: Edge = {
             id: `e${sourceNode.id}-${targetNode.id}-${relationshipType}`,
             source: sourceNode.id,
             target: targetNode.id,
             type: 'umlEdge',
             label: label ? label.trim().replace(/[<>]$/, '').trim() : '',
             data: { type: relationshipType, sourceMultiplicity, targetMultiplicity },
           };
           edges.push(edge);
         } else {
            console.warn(`[Class Parser] Could not find nodes for relationship: ${sourceName} -> ${targetName}`);
         }
         continue;
      }
    }
    
    console.log('[Class Parser] Completed parsing. Nodes:', nodes.length, 'Edges:', edges.length);
    return { nodes, edges };
  } catch (error) {
    console.error('Error parsing class diagram:', error);
    throw error;
  }
} 