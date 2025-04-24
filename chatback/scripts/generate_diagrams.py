#!/usr/bin/env python3
"""
Generate PNG diagrams from PlantUML files.
This script uses the PlantUML server to generate diagrams.
"""

import os
import sys
import requests
import base64
import zlib
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# PlantUML server URL
PLANTUML_SERVER = "http://www.plantuml.com/plantuml/png/"

def encode_puml_for_url(puml_content):
    """
    Encode PlantUML content for use in the PlantUML server URL.
    """
    # Remove @startuml and @enduml if present
    puml_content = puml_content.replace('@startuml', '').replace('@enduml', '')
    
    # Add @startuml and @enduml
    puml_content = '@startuml\n' + puml_content + '\n@enduml'
    
    # Compress and encode
    zlibbed = zlib.compress(puml_content.encode('utf-8'))
    compressed = zlibbed[2:-4]  # Remove zlib header and checksum
    encoded = base64.b64encode(compressed).decode('utf-8')
    
    # Make URL-safe
    encoded = encoded.replace('+', '-').replace('/', '_')
    
    return encoded

def generate_diagram(puml_file, output_dir):
    """
    Generate a PNG diagram from a PlantUML file.
    
    Args:
        puml_file: Path to the PlantUML file
        output_dir: Directory to save the PNG file
    
    Returns:
        Path to the generated PNG file
    """
    try:
        # Read the PlantUML file
        with open(puml_file, 'r', encoding='utf-8') as f:
            puml_content = f.read()
        
        # Get the filename without extension
        filename = os.path.basename(puml_file)
        filename_without_ext = os.path.splitext(filename)[0]
        
        # Encode the PlantUML content
        encoded = encode_puml_for_url(puml_content)
        
        # Generate the URL
        url = f"{PLANTUML_SERVER}{encoded}"
        
        # Download the PNG
        response = requests.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to generate diagram for {puml_file}: {response.status_code}")
            return None
        
        # Create the output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the PNG
        output_file = os.path.join(output_dir, f"{filename_without_ext}.png")
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Generated diagram: {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"Error generating diagram for {puml_file}: {str(e)}")
        return None

def main():
    """
    Main function to generate diagrams from PlantUML files.
    """
    # Get the base directory
    base_dir = Path(__file__).parent.parent
    
    # Define the directories
    puml_dir = base_dir / "app" / "services" / "chat"
    output_dir = base_dir / "docs" / "diagrams"
    
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all PlantUML files
    puml_files = list(puml_dir.glob("*.puml"))
    
    if not puml_files:
        logger.warning(f"No PlantUML files found in {puml_dir}")
        return
    
    logger.info(f"Found {len(puml_files)} PlantUML files")
    
    # Generate diagrams for each file
    for puml_file in puml_files:
        generate_diagram(puml_file, output_dir)
    
    logger.info(f"Diagrams generated in {output_dir}")

if __name__ == "__main__":
    main() 