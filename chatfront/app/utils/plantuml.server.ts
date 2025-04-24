import { encode } from 'plantuml-encoder';

const PLANTUML_SERVER = 'https://www.plantuml.com/plantuml/svg';

const THEME_SETTINGS = `
skinparam backgroundColor transparent
skinparam useBetaStyle false

skinparam defaultFontName Inter
skinparam defaultFontSize 12

skinparam sequence {
  ArrowColor #4B5563
  LifeLineBorderColor #4B5563
  LifeLineBackgroundColor #FFFFFF
  ParticipantBorderColor #4B5563
  ParticipantBackgroundColor #FFFFFF
  ParticipantFontColor #1F2937
  ActorBorderColor #4B5563
  ActorBackgroundColor #FFFFFF
  ActorFontColor #1F2937
}

skinparam class {
  BackgroundColor #FFFFFF
  BorderColor #4B5563
  ArrowColor #4B5563
  FontColor #1F2937
  AttributeFontColor #4B5563
  StereotypeFontColor #6B7280
}

skinparam component {
  BackgroundColor #FFFFFF
  BorderColor #4B5563
  ArrowColor #4B5563
  FontColor #1F2937
}

skinparam interface {
  BackgroundColor #FFFFFF
  BorderColor #4B5563
  FontColor #1F2937
}

skinparam note {
  BackgroundColor #FEF3C7
  BorderColor #D97706
  FontColor #92400E
}
`;

export async function convertPlantUmlToSvg(plantUmlCode: string): Promise<string> {
  try {
    // Remove any ```plantuml and ``` markers
    let cleanCode = plantUmlCode
      .replace(/```plantuml/g, '')
      .replace(/```/g, '')
      .trim();

    // --- Transformation Step (Option 1) ---
    // Define the regex for specific start directives we handle
    const startDirectiveRegex = /^@(startclass|startsequence|startactivity|startusecase)\b/im;

    // Replace the specific directive with @startuml and inject theme
    let codeForServer = cleanCode.replace(startDirectiveRegex, `@startuml\\n${THEME_SETTINGS}`);

    // If no specific directive was found (e.g., already had @startuml or invalid input),
    // handle the theme injection and ensure @startuml/@enduml wrapping.
    if (codeForServer === cleanCode) { // replacement didn't happen
      if (cleanCode.includes('@startuml')) {
         // Already has @startuml, just inject theme after it
         codeForServer = cleanCode.replace('@startuml', `@startuml\\n${THEME_SETTINGS}`);
      } else {
         // Doesn't have any known start directive, wrap it completely (fallback)
         console.warn('PlantUML code did not start with a recognized @start<type> directive. Wrapping with @startuml.');
         codeForServer = `@startuml\\n${THEME_SETTINGS}\\n${cleanCode}\\n@enduml`;
      }
    }

    // Ensure the code ends with @enduml, preventing duplicates
    if (!codeForServer.trim().endsWith('@enduml')) {
        codeForServer += '\\n@enduml';
    }
    // --- End Transformation Step ---


    // Encode the modified PlantUML code
    const encoded = encode(codeForServer); // Use the transformed code

    // Return the URL to the SVG
    return `${PLANTUML_SERVER}/${encoded}`;
  } catch (error) {
    console.error('Error converting PlantUML to SVG:', error);
    // It's better to throw the original error or a new error wrapping it
    // throw new Error(`Failed to generate PlantUML diagram: ${error instanceof Error ? error.message : String(error)}`);
     // Keep original throw for consistency if preferred, but the above is often better
    throw new Error(`Failed to generate PlantUML diagram: ${error.message}`);
  }
} 