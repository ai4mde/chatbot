import { Node, Edge, Position, MarkerType } from 'reactflow';
import { ParseResult, UMLSequenceData } from './types';

// Basic Regex Patterns
// Captures: 1=type (actor, participant, etc.), 2=name (quoted or unquoted), 4=alias (optional)
const participantRegex = /^\s*(actor|participant|boundary|control|entity|database|collections|queue)\s+((?:\"([^\"]+)\")|([^\s]+))\s*(?:as\s+(\w+))?\s*$/;
// Captures: 1=source, 2=arrow, 3=target, 4=message text (optional)
const messageRegex = /^\s*([\w\"\/]+)\s*(-[->>>x]+)\s*([\w\"\/]+)\s*(?::\s*(.*))?$/;

export function parseSequenceDiagram(code: string): ParseResult {
    console.log('Attempting to parse sequence diagram...');
    const nodes: Array<Node<UMLSequenceData>> = []; // Or Node<{ label: string }> initially
    const edges: Edge[] = [];
    const lines = code.split('\n');

    const participants: Map<string, { id: string; name: string; x: number; type: string }> = new Map();
    let participantIndex = 0;
    const participantSpacing = 200; // Horizontal spacing between participants
    const initialY = 50; // Initial Y position for participant nodes

    // --- First Pass: Identify Participants ---
    lines.forEach(line => {
        const match = line.match(participantRegex);
        if (match) {
            const pumlType = match[1]; // Store the plantuml keyword type
            const name = match[3] || match[4]; // Quoted name or unquoted name
            const alias = match[5] || name; // Use alias if provided, otherwise use name

            if (!participants.has(alias)) {
                const participantId = `participant-${alias.replace(/[^a-zA-Z0-9]/g, '_')}`; // Use alias for ID
                const xPos = participantIndex * participantSpacing;
                // Store pumlType, not type
                participants.set(alias, { id: participantId, name: name, x: xPos, type: pumlType }); 
                participants.set(name, { id: participantId, name: name, x: xPos, type: pumlType }); 

                nodes.push({
                    id: participantId,
                    type: 'sequenceParticipant', 
                    position: { x: xPos, y: initialY },
                    // Conform to UMLSequenceData & add pumlKeyword
                    data: { 
                        name: name, 
                        type: 'participant', // Set the required type field
                        pumlKeyword: pumlType // Populate the new optional field
                    },
                    sourcePosition: Position.Bottom,
                    targetPosition: Position.Top,
                });
                participantIndex++;
                 console.log(`Found participant: ${name} (Alias: ${alias}, ID: ${participantId}, Type: ${pumlType}, x: ${xPos})`);
            }
        }
    });

    // --- Second Pass: Identify Messages ---
    let yPos = initialY + 150; // Start messages below participants
    const messageSpacing = 80; // Vertical spacing between messages

    lines.forEach(line => {
        const match = line.match(messageRegex);
        if (match) {
             const sourceAliasOrName = match[1].replace(/\"/g, ''); // Remove quotes if any
             const targetAliasOrName = match[3].replace(/\"/g, ''); // Remove quotes if any
             const messageText = match[4] ? match[4].trim() : '';
             const arrowType = match[2];

             const sourceParticipant = participants.get(sourceAliasOrName);
             const targetParticipant = participants.get(targetAliasOrName);

             if (sourceParticipant && targetParticipant) {
                 const edgeId = `msg-${sourceParticipant.id}-to-${targetParticipant.id}-${edges.length}`;

                 // Basic edge styling - can be expanded based on arrowType
                 let edgeStyle = {};
                 let animated = false;
                 if (arrowType.includes('-->')) { // Dashed line for return/reply
                     edgeStyle = { strokeDasharray: '5,5' };
                 }
                 if (arrowType.includes('>>')) { // Async message
                     // Could use a different markerEnd or style if needed
                 }

                 edges.push({
                     id: edgeId,
                     source: sourceParticipant.id,
                     target: targetParticipant.id,
                     label: messageText,
                     type: 'default', 
                     animated: animated, 
                     style: edgeStyle,
                     markerEnd: { 
                         type: MarkerType.ArrowClosed, // Use MarkerType enum
                         width: 20,
                          height: 20,
                     },
                 });
                 console.log(`Found message: ${sourceAliasOrName} -> ${targetAliasOrName} : ${messageText} (ID: ${edgeId})`);

                 // Increment yPos for the next potential message/element
                 // This simple increment might need refinement for complex diagrams (e.g., activations)
                 yPos += messageSpacing;

             } else {
                 console.warn(`Could not find participants for message: ${line.trim()}`);
                 if (!sourceParticipant) console.warn(`  -> Source not found: ${sourceAliasOrName}`);
                 if (!targetParticipant) console.warn(`  -> Target not found: ${targetAliasOrName}`);
             }
        }
    });


    console.log('Sequence diagram parsing (basic) complete.');
    return { nodes, edges };
} 