import logging
import sys
from termcolor import colored

# Define colors for different log levels
LOG_LEVEL_COLORS = {
    logging.DEBUG: 'grey',
    logging.INFO: 'cyan',
    logging.WARNING: 'yellow',
    logging.ERROR: 'red',
    logging.CRITICAL: 'red',
}

# Define attributes for critical logs
LOG_LEVEL_ATTRS = {
    logging.CRITICAL: ['bold', 'underline']
}

class ColoredFormatter(logging.Formatter):
    """A logging formatter that adds colors based on log level."""

    def __init__(self, fmt=None, datefmt=None, style='%', use_colors=True):
        super().__init__(fmt, datefmt, style)
        self.use_colors = use_colors and sys.stdout.isatty() # Only use colors if stdout is a TTY

    def format(self, record):
        # Get the original formatted message
        log_message = super().format(record)

        if self.use_colors:
            # Apply color based on log level
            log_level = record.levelno
            color = LOG_LEVEL_COLORS.get(log_level)
            attrs = LOG_LEVEL_ATTRS.get(log_level)

            if color:
                log_message = colored(log_message, color, attrs=attrs)

        return log_message

def setup_logging(log_level: str = "INFO"):
    """Configures the root logger with a colored console handler."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Define the log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Create the custom colored formatter
    formatter = ColoredFormatter(fmt=log_format, datefmt=date_format)

    # Create a console handler and set the formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Get the root logger, set its level, and add the handler
    root_logger = logging.getLogger()
    
    # Clear existing handlers (important if setup_logging might be called multiple times)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)

    logging.info(f"Logging configured with level: {logging.getLevelName(level)}")

# Example basic setup if this file is run directly (optional)
if __name__ == "__main__":
    setup_logging(log_level="DEBUG")
    logging.debug("This is a debug message.")
    logging.info("This is an info message.")
    logging.warning("This is a warning message.")
    logging.error("This is an error message.")
    logging.critical("This is a critical message.") 