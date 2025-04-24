import { Node, Edge } from 'reactflow';
import { parseClassDiagram } from './parsers/class-diagram.parser';
import { parseUseCaseDiagram } from './parsers/use-case-diagram.parser';
import { parseActivityDiagram } from './parsers/activity-diagram.parser';
import { parseSequenceDiagram } from './parsers/sequence-diagram.parser';
import { ParseResult } from './parsers/types';

// Main router function
export function parsePlantUML(code: string): ParseResult {
  const normalizedCode = code.replace(/\r\n/g, '\n').trim();
  // console.log('[Router] Starting detection...'); // Optional: keep or remove this log

  // Check for specific @start directives. This is now the ONLY way to detect type.
  if (normalizedCode.includes('@startsequence')) {
    console.log('[Router] Detected @startsequence'); // Simplified log
    return parseSequenceDiagram(normalizedCode);
  }
  if (normalizedCode.includes('@startactivity')) {
    console.log('[Router] Detected @startactivity'); // Simplified log
    return parseActivityDiagram(normalizedCode);
  }
  if (normalizedCode.includes('@startusecase')) {
    console.log('[Router] Detected @startusecase'); // Simplified log
    return parseUseCaseDiagram(normalizedCode);
  }
  if (normalizedCode.includes('@startclass')) {
    console.log('[Router] Detected @startclass'); // Simplified log
    return parseClassDiagram(normalizedCode);
  }

  // If no valid directive is found, throw an error.
  console.error('[Router] No valid @start<type> directive found in code:', normalizedCode);
  throw new Error('Missing or invalid PlantUML diagram type directive (e.g., @startclass, @startsequence). Please add the correct directive after @startuml.');
} 