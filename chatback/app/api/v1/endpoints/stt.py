import io
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from openai import AsyncOpenAI

from app.api.deps import get_current_user
from app.core.config import settings
from app.models import User

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize OpenAI client (use async version for FastAPI)
# Ensure OPENAI_API_KEY is set in your environment/settings
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


@router.post("/transcribe", response_model=dict)
async def transcribe_audio(
    *, file: UploadFile = File(...), current_user: User = Depends(get_current_user)
):
    """
    Receives an audio file and returns its transcription using OpenAI Whisper.
    """
    logger.info(
        f"Received audio file for transcription from user {current_user.id}. Filename: {file.filename}, Content-Type: {file.content_type}"
    )

    if not file.content_type or not file.content_type.startswith("audio/"):
        logger.warning(f"Invalid file content type received: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload an audio file.",
        )

    try:
        # Read file content into memory
        audio_data = await file.read()
        audio_stream = io.BytesIO(audio_data)

        # Ensure the filename is passed to the API if needed for format detection
        # Use a generic name if the original filename might be problematic
        audio_stream.name = file.filename or "audio.webm"

        # Construct a prompt to potentially improve accuracy for known names
        prompt = f"The user's name is {current_user.username}."
        logger.info(f"Using prompt for Whisper: '{prompt}'")

        logger.info(f"Sending audio ({len(audio_data)} bytes) to OpenAI Whisper API...")

        # Call OpenAI Whisper API for transcription
        # Use the 'whisper-1' model
        # TODO: move these to a config file or environment variable
        transcription_response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_stream.name, audio_stream, file.content_type),
            prompt=prompt,
            response_format="json",
        )

        transcribed_text = transcription_response.text
        logger.info(
            f"Successfully transcribed audio for user {current_user.id}. Transcription length: {len(transcribed_text)}"
        )

        return {"transcription": transcribed_text}

    except Exception as e:
        logger.error(
            f"Error during audio transcription for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transcribe audio: {e}",
        )
    finally:
        await file.close()
