"""
FastAPI entrypoint for ElevenLabs voice cloning and TTS integration.
"""
from fastapi import FastAPI

from .api_endpoints import app as api_app
from .config import Config
from .elevenlabs_service import ElevenLabsService
from .supabase_service import SupabaseService

app: FastAPI = api_app


def read_text_from_file(file_path: str) -> str:
    """Read text from a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Failed to read text file: {str(e)}")


def clone_voice_from_payload(user_id: str, voice_name: str, audio_data_list: list, voice_description: str = ""):
    """
    Clone voice from audio data received via API endpoints

    Args:
        user_id: User's ID for storing voice_id in Supabase
        voice_name: Name for the cloned voice
        audio_data_list: List of audio data dictionaries with format:
            [
                {"filename": "audio1.mp3", "data": base64_encoded_string},
                {"filename": "audio2.mp3", "data": base64_encoded_string},
            ]
            OR list of bytes objects directly
        voice_description: Optional description for the voice

    Returns:
        dict: {
            "success": bool,
            "voice_id": str,
            "message": str
        }
    """
    try:
        Config.validate()
    except ValueError as e:
        return {
            "success": False,
            "voice_id": None,
            "message": f"Configuration error: {str(e)}"
        }

    # Initialize services
    elevenlabs = ElevenLabsService()
    supabase = SupabaseService()

    print("=" * 60)
    print(f"Cloning voice for user: {user_id}")
    print("=" * 60)

    try:
        # Clone the voice using the audio data from payload
        voice_id = elevenlabs.clone_voice_from_bytes(
            voice_name=voice_name,
            audio_data_list=audio_data_list,
            description=voice_description
        )

        # Store voice_id in Supabase
        supabase.store_voice_id(user_id=user_id, voice_id=voice_id)

        return {
            "success": True,
            "voice_id": voice_id,
            "message": f"Voice cloned successfully and stored for user {user_id}"
        }

    except Exception as e:
        return {
            "success": False,
            "voice_id": None,
            "message": f"Error during voice cloning: {str(e)}"
        }


def generate_speech_for_user(user_id: str, text: str, output_path: str = "output_speech.mp3"):
    """
    Generate speech for a user using their stored voice_id

    Args:
        user_id: User's ID to retrieve voice_id from Supabase
        text: Text to convert to speech
        output_path: Path where to save the audio file

    Returns:
        dict: {
            "success": bool,
            "audio_path": str or None,
            "audio_bytes": bytes or None,
            "message": str
        }
    """
    try:
        Config.validate()
    except ValueError as e:
        return {
            "success": False,
            "audio_path": None,
            "audio_bytes": None,
            "message": f"Configuration error: {str(e)}"
        }

    # Initialize services
    elevenlabs = ElevenLabsService()
    supabase = SupabaseService()

    try:
        # Retrieve voice_id from Supabase
        voice_id = supabase.get_voice_id(user_id=user_id)

        # Generate speech
        audio_path = elevenlabs.text_to_speech(
            text=text,
            voice_id=voice_id,
            output_path=output_path
        )

        # Optionally read the audio as bytes for API response
        with open(audio_path, 'rb') as f:
            audio_bytes = f.read()

        return {
            "success": True,
            "audio_path": audio_path,
            "audio_bytes": audio_bytes,
            "message": "Speech generated successfully"
        }

    except Exception as e:
        return {
            "success": False,
            "audio_path": None,
            "audio_bytes": None,
            "message": f"Error generating speech: {str(e)}"
        }


def main():
    """Main workflow demonstration"""

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nPlease create a .env file with the required variables.")
        print("See .env.example for reference.")
        return

    print("=" * 60)
    print("ElevenLabs Voice Cloning and TTS Integration")
    print("=" * 60)

    # ========================================
    # EXAMPLE 1: Clone voice from payload/endpoint data
    # ========================================
    print("\n📝 EXAMPLE 1: Voice Cloning from Endpoint Payload")
    print("-" * 60)
    print("In a real application, audio data would come from your API endpoint.")
    print("Example payload format:")
    print("""
    {
        "user_id": "user-123",
        "voice_name": "John's Voice",
        "voice_description": "Professional voice",
        "audio_files": [
            {
                "filename": "sample1.mp3",
                "data": "base64_encoded_audio_data_here"
            },
            {
                "filename": "sample2.mp3",
                "data": "base64_encoded_audio_data_here"
            }
        ]
    }
    """)

    # Simulated payload data (in real app, this comes from request)
    # You would decode base64 audio data from your endpoint
    simulated_audio_data = [
        # {"filename": "audio1.mp3", "data": "base64_string_here"},
        # {"filename": "audio2.mp3", "data": "base64_string_here"},
    ]

    print("\n⚠️  For this demo, we're skipping actual voice cloning.")
    print("   In your endpoint, you would call:")
    print("   result = clone_voice_from_payload(user_id, voice_name, audio_data, description)")

    # For testing: Use an existing voice_id
    test_voice_id = input("\nEnter an existing voice_id to test TTS (or press Enter to skip): ").strip()
    if not test_voice_id:
        print("\nSkipping TTS demo. Exiting.")
        return

    # Simulate storing the voice_id
    test_user_id = "test-user-123"
    supabase = SupabaseService()
    try:
        supabase.store_voice_id(user_id=test_user_id, voice_id=test_voice_id)
        print(f"✓ Voice ID stored for testing")
    except Exception as e:
        print(f"⚠️  Could not store voice_id: {e}")

    # ========================================
    # EXAMPLE 2: Text-to-Speech from endpoint
    # ========================================
    print("\n📝 EXAMPLE 2: Generate Text-to-Speech")
    print("-" * 60)

    # In a real application, text would come from your endpoint
    print("Example endpoint call:")
    print("   result = generate_speech_for_user(user_id, text)")

    # Read text from file (simulating backend source)
    text_file = "test_text.txt"
    try:
        text_content = read_text_from_file(text_file)
        print(f"\n✓ Text loaded from: {text_file}")
    except:
        text_content = "Hello! This is a test of text-to-speech with your cloned voice."
        print(f"\n✓ Using fallback text")

    # Generate speech for the user
    result = generate_speech_for_user(
        user_id=test_user_id,
        text=text_content,
        output_path="output_speech.mp3"
    )

    if result["success"]:
        print(f"✓ {result['message']}")
        print(f"✓ Audio saved to: {result['audio_path']}")
        print(f"✓ Audio bytes ready for API response: {len(result['audio_bytes'])} bytes")
    else:
        print(f"❌ {result['message']}")

    print("\n" + "=" * 60)
    print("✅ Demo Complete!")
    print("=" * 60)
    print("\nIntegration Notes:")
    print("• Use clone_voice_from_payload() in your POST endpoint for voice cloning")
    print("• Use generate_speech_for_user() in your POST endpoint for TTS")
    print("• Audio data is automatically handled as bytes/base64")
    print("• Voice IDs are stored and retrieved from Supabase automatically")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.elevenLabs.main:app", host="0.0.0.0", port=8000, reload=True)
