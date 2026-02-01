"""
FastAPI endpoint examples for ElevenLabs voice cloning and TTS

Install FastAPI with: pip install fastapi uvicorn python-multipart
Run with: uvicorn app.elevenLabs.main:app --reload
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List
import uuid
import io

from .config import Config
from .elevenlabs_service import ElevenLabsService
from .supabase_service import SupabaseService

# Initialize FastAPI app
app = FastAPI(title="ElevenLabs Voice Cloning API")

elevenlabs_service = None
supabase_service = None


def get_services(require_supabase: bool = True):
    global elevenlabs_service, supabase_service

    try:
        Config.validate()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")

    if elevenlabs_service is None:
        elevenlabs_service = ElevenLabsService()

    if require_supabase and supabase_service is None:
        supabase_service = SupabaseService()

    return elevenlabs_service, supabase_service


def is_valid_uuid(user_id: str) -> bool:
    try:
        uuid.UUID(str(user_id))
        return True
    except (TypeError, ValueError):
        return False


@app.post("/api/voice/clone")
async def clone_voice_endpoint(
        user_id: str = Form(...),
        voice_name: str = Form(...),
        voice_description: str = Form(""),
        audio_files: List[UploadFile] = File(...)
):
    """
    Clone a user's voice from uploaded audio files

    Args:
        user_id: User's unique ID
        voice_name: Name for the cloned voice
        voice_description: Optional description
        audio_files: 1-25 audio files (MP3, WAV, etc.)

    Returns:
        JSON with voice_id and success status
    """
    elevenlabs_service, supabase_service = get_services()

    try:
        # Read all uploaded files into memory
        audio_data_list = []
        for file in audio_files:
            file_bytes = await file.read()
            audio_data_list.append({
                "filename": file.filename,
                "data": file_bytes
            })

        # Clone the voice
        voice_id = elevenlabs_service.clone_voice_from_bytes(
            voice_name=voice_name,
            audio_data_list=audio_data_list,
            description=voice_description
        )

        # Store voice_id in Supabase when the user ID matches expected UUID format.
        if is_valid_uuid(user_id):
            supabase_service.store_voice_id(user_id=user_id, voice_id=voice_id)
            message = "Voice cloned and stored successfully"
        else:
            message = "Voice cloned successfully (skipped storing voice_id for non-UUID user_id)"

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "voice_id": voice_id,
                "user_id": user_id,
                "message": message
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clone voice: {str(e)}")


@app.post("/api/voice/clone-base64")
async def clone_voice_base64_endpoint(
        user_id: str,
        voice_name: str,
        voice_description: str = "",
        audio_files: List[dict] = None
):
    """
    Clone a user's voice from base64-encoded audio data

    Expected JSON body:
    {
        "user_id": "user-123",
        "voice_name": "John's Voice",
        "voice_description": "Professional voice",
        "audio_files": [
            {
                "filename": "audio1.mp3",
                "data": "base64_encoded_audio_data"
            },
            {
                "filename": "audio2.mp3",
                "data": "base64_encoded_audio_data"
            }
        ]
    }
    """
    elevenlabs_service, supabase_service = get_services()

    if not audio_files:
        raise HTTPException(status_code=400, detail="No audio files provided")

    try:
        # Clone the voice (the service handles base64 decoding)
        voice_id = elevenlabs_service.clone_voice_from_bytes(
            voice_name=voice_name,
            audio_data_list=audio_files,
            description=voice_description
        )

        # Store voice_id in Supabase when the user ID matches expected UUID format.
        if is_valid_uuid(user_id):
            supabase_service.store_voice_id(user_id=user_id, voice_id=voice_id)
            message = "Voice cloned and stored successfully"
        else:
            message = "Voice cloned successfully (skipped storing voice_id for non-UUID user_id)"

        return {
            "success": True,
            "voice_id": voice_id,
            "user_id": user_id,
            "message": message
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clone voice: {str(e)}")


@app.post("/api/tts/generate")
async def generate_speech_endpoint(
        user_id: str = Form(...),
        text: str = Form(...)
):
    """
    Generate speech using a user's cloned voice

    Args:
        user_id: User's unique ID (to retrieve voice_id)
        text: Text to convert to speech

    Returns:
        Audio file (MP3) as streaming response
    """
    elevenlabs_service, supabase_service = get_services()

    try:
        if not is_valid_uuid(user_id):
            raise ValueError("User ID must be a valid UUID.")
        # Get user's voice_id from Supabase
        voice_id = supabase_service.get_voice_id(user_id=user_id)

        # Generate speech as bytes
        audio_bytes = elevenlabs_service.text_to_speech_bytes(
            text=text,
            voice_id=voice_id
        )

        # Return as streaming audio response
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=speech_{user_id}.mp3"
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate speech: {str(e)}")


@app.post("/api/tts/generate-with-voice-id")
async def generate_speech_with_voice_id_endpoint(
        voice_id: str = Form(...),
        text: str = Form(...)
):
    """
    Generate speech using a specific voice_id (doesn't require user lookup)

    Args:
        voice_id: ElevenLabs voice ID
        text: Text to convert to speech

    Returns:
        Audio file (MP3) as streaming response
    """
    elevenlabs_service, _ = get_services(require_supabase=False)

    try:
        # Generate speech as bytes
        audio_bytes = elevenlabs_service.text_to_speech_bytes(
            text=text,
            voice_id=voice_id
        )

        # Return as streaming audio response
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=speech_{voice_id}.mp3"
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate speech: {str(e)}")


@app.get("/api/voice/{user_id}")
async def get_user_voice_endpoint(user_id: str):
    """
    Get voice information for a user

    Args:
        user_id: User's unique ID

    Returns:
        JSON with voice_id and profile info
    """
    _, supabase_service = get_services()

    try:
        if not is_valid_uuid(user_id):
            raise ValueError("User ID must be a valid UUID.")
        voice_id = supabase_service.get_voice_id(user_id=user_id)

        # Optionally get voice info from ElevenLabs
        voice_info = None
        if elevenlabs_service:
            try:
                voice_info = elevenlabs_service.get_voice_info(voice_id)
            except:
                pass

        return {
            "success": True,
            "user_id": user_id,
            "voice_id": voice_id,
            "voice_info": voice_info
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Voice not found: {str(e)}")


@app.delete("/api/voice/{user_id}")
async def delete_user_voice_endpoint(user_id: str):
    """
    Delete a user's cloned voice

    Args:
        user_id: User's unique ID

    Returns:
        JSON with success status
    """
    elevenlabs_service, supabase_service = get_services()

    try:
        if not is_valid_uuid(user_id):
            raise ValueError("User ID must be a valid UUID.")
        # Get voice_id
        voice_id = supabase_service.get_voice_id(user_id=user_id)

        # Delete from ElevenLabs
        elevenlabs_service.delete_voice(voice_id)

        # Clear voice_id in Supabase (set to null)
        supabase_service.store_voice_id(user_id=user_id, voice_id=None)

        return {
            "success": True,
            "message": "Voice deleted successfully",
            "user_id": user_id,
            "voice_id": voice_id
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete voice: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    elevenlabs_ready = elevenlabs_service is not None
    supabase_ready = supabase_service is not None

    return {
        "status": "healthy",
        "elevenlabs_configured": elevenlabs_ready,
        "supabase_configured": supabase_ready
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
