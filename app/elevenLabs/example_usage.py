"""
Example usage scripts for individual functions
"""
from .config import Config
from .elevenlabs_service import ElevenLabsService
from .supabase_service import SupabaseService


def example_clone_voice():
    """Example: Clone a voice"""
    print("\n" + "=" * 60)
    print("Example: Clone Voice")
    print("=" * 60)

    Config.validate()
    elevenlabs = ElevenLabsService()

    voice_id = elevenlabs.clone_voice(
        voice_name="John's Voice",
        audio_files=["path/to/audio1.mp3", "path/to/audio2.mp3"],
        description="Professional voice for presentations"
    )

    print(f"Voice ID: {voice_id}")
    return voice_id


def example_text_to_speech(voice_id: str):
    """Example: Convert text to speech"""
    print("\n" + "=" * 60)
    print("Example: Text-to-Speech")
    print("=" * 60)

    Config.validate()
    elevenlabs = ElevenLabsService()

    text = "This is an example of text-to-speech conversion."
    output_file = elevenlabs.text_to_speech(
        text=text,
        voice_id=voice_id,
        output_path="example_output.mp3"
    )

    print(f"Audio saved to: {output_file}")


def example_store_voice_id(user_id: str, voice_id: str):
    """Example: Store voice ID in Supabase"""
    print("\n" + "=" * 60)
    print("Example: Store Voice ID")
    print("=" * 60)

    Config.validate()
    supabase = SupabaseService()

    profile = supabase.store_voice_id(
        user_id=user_id,
        voice_id=voice_id
    )

    print(f"Updated profile: {profile}")


def example_get_voice_id(user_id: str):
    """Example: Retrieve voice ID from Supabase"""
    print("\n" + "=" * 60)
    print("Example: Get Voice ID")
    print("=" * 60)

    Config.validate()
    supabase = SupabaseService()

    voice_id = supabase.get_voice_id(user_id=user_id)
    print(f"Retrieved voice_id: {voice_id}")
    return voice_id


def example_complete_workflow():
    """Example: Complete workflow from cloning to TTS"""
    print("\n" + "=" * 60)
    print("Example: Complete Workflow")
    print("=" * 60)

    Config.validate()

    # Initialize services
    elevenlabs = ElevenLabsService()
    supabase = SupabaseService()

    # 1. Clone voice
    voice_id = elevenlabs.clone_voice(
        voice_name="User Voice",
        audio_files=["audio1.mp3"],
        description="User's cloned voice"
    )

    # 2. Store in database
    user_id = "user-abc-123"
    supabase.store_voice_id(user_id, voice_id)

    # 3. Later... retrieve and use for TTS
    stored_voice_id = supabase.get_voice_id(user_id)

    # 4. Generate speech
    elevenlabs.text_to_speech(
        text="Hello, this is my cloned voice!",
        voice_id=stored_voice_id,
        output_path="final_output.mp3"
    )

    print("\n✅ Complete workflow finished!")


if __name__ == "__main__":
    # Run examples (uncomment the ones you want to test)

    # Example 1: Clone a voice
    # voice_id = example_clone_voice()

    # Example 2: Generate speech with a voice ID
    # example_text_to_speech("your-voice-id-here")

    # Example 3: Store voice ID
    # example_store_voice_id("user-123", "voice-id-here")

    # Example 4: Retrieve voice ID
    # example_get_voice_id("user-123")

    # Example 5: Complete workflow
    # example_complete_workflow()

    print("Uncomment the examples you want to run in example_usage.py")
