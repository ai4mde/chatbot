import os
import re
import logging
import shutil
from app.core.config import settings

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters and replacing spaces with underscores.

    Args:
        filename: The filename to sanitize

    Returns:
        A sanitized filename
    """
    # Remove invalid characters and replace spaces with underscores
    sanitized = re.sub(r"[^\w\s-]", "", filename)
    sanitized = re.sub(r"[\s]+", "_", sanitized)
    return sanitized.lower()


def ensure_srs_directory(group_name: str, chat_name: str) -> str:
    """
    Ensure the SRS document directory exists for a specific group and chat.

    Args:
        group_name: The name of the group
        chat_name: The name of the chat

    Returns:
        The path to the SRS document directory
    """
    # Create group-specific path
    directory = os.path.join(
        settings.CHATBOT_DATA_PATH, group_name, sanitize_filename(chat_name), "srsdocs"
    )

    # Ensure directory exists
    os.makedirs(directory, exist_ok=True)

    return directory


def load_srs_template() -> str:
    """
    Load the SRS document template.

    Returns:
        The content of the SRS document template
    """
    try:
        # Ensure templates directory exists
        os.makedirs(settings.TEMPLATES_PATH, exist_ok=True)

        template_path = os.path.join(settings.TEMPLATES_PATH, "srsdoc_template.md")

        # If template doesn't exist, copy from app data
        if not os.path.exists(template_path):
            source_template = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "data",
                "templates",
                "srsdoc_template.md",
            )
            if os.path.exists(source_template):
                shutil.copy2(source_template, template_path)
            else:
                raise FileNotFoundError(f"Template not found at {source_template}")

        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()

    except Exception as e:
        logger.error(f"Error loading SRS template: {str(e)}")
        raise
