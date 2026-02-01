"""
ElevenLabs service for voice cloning and text-to-speech
"""
import os
import base64
import io
from types import SimpleNamespace
import requests

from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from .config import Config


class ElevenLabsService:
    """Handle ElevenLabs API operations"""

    def __init__(self):
        """Initialize ElevenLabs client"""
        from elevenlabs.client import ElevenLabs
        from elevenlabs import VoiceSettings

        self.client = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)
        self.voice_settings_class = VoiceSettings

    def _clone_voice(self, voice_name: str, files: list, description: str = ""):
        """
        Internal helper to clone a voice using the ElevenLabs SDK.

        Supports multiple SDK versions by checking available methods.
        """
        if not Config.ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY is required to clone voices.")

        voices = getattr(self.client, "voices", None)

        if voices and hasattr(voices, "add"):
            return voices.add(name=voice_name, files=files, description=description)

        if voices and hasattr(voices, "create"):
            return voices.create(name=voice_name, files=files, description=description)

        if hasattr(self.client, "clone_voice"):
            return self.client.clone_voice(name=voice_name, files=files, description=description)

        response = requests.post(
            "https://api.elevenlabs.io/v1/voices/add",
            headers={"xi-api-key": Config.ELEVENLABS_API_KEY},
            data={"name": voice_name, "description": description},
            files=[("files", (file.name, file, "application/octet-stream")) for file in files],
            timeout=60,
        )
        if not response.ok:
            raise RuntimeError(
                f"ElevenLabs voice clone failed: {response.status_code} {response.text}"
            )

        payload = response.json()
        voice_id = payload.get("voice_id")
        if not voice_id:
            raise ValueError("ElevenLabs voice clone succeeded but no voice_id was returned.")

        return SimpleNamespace(voice_id=voice_id)

    def clone_voice_from_bytes(self, voice_name: str, audio_data_list: list, description: str = "") -> str:
        """
        Clone a voice using audio data from API endpoints (bytes or base64)

        This method accepts audio data directly without requiring local files.
        Perfect for handling uploads from API endpoints.

        Args:
            voice_name: Name for the cloned voice
            audio_data_list: List of audio data in one of these formats:
                Format 1 - Dict with base64:
                    [
                        {"filename": "audio1.mp3", "data": "base64_encoded_string"},
                        {"filename": "audio2.mp3", "data": "base64_encoded_string"}
                    ]
                Format 2 - Dict with bytes:
                    [
                        {"filename": "audio1.mp3", "data": b"raw_bytes"},
                        {"filename": "audio2.mp3", "data": b"raw_bytes"}
                    ]
                Format 3 - Just bytes (filename will be auto-generated):
                    [b"raw_bytes_1", b"raw_bytes_2"]
            description: Optional description for the voice

        Returns:
            voice_id: The ID of the created voice
        """
        try:
            # Prepare file-like objects for upload
            files = []

            for idx, audio_data in enumerate(audio_data_list):
                # Handle different input formats
                if isinstance(audio_data, dict):
                    # Format 1 or 2: Dictionary with filename and data
                    filename = audio_data.get('filename', f'audio_{idx}.mp3')
                    data = audio_data.get('data')

                    # Check if data is base64 string
                    if isinstance(data, str):
                        # Decode base64
                        audio_bytes = base64.b64decode(data)
                    else:
                        # Already bytes
                        audio_bytes = data

                elif isinstance(audio_data, bytes):
                    # Format 3: Just raw bytes
                    filename = f'audio_{idx}.mp3'
                    audio_bytes = audio_data

                else:
                    raise ValueError(f"Invalid audio data format at index {idx}")

                # Create a file-like object
                file_obj = io.BytesIO(audio_bytes)
                file_obj.name = filename
                files.append(file_obj)

            if not files:
                raise ValueError("No audio files provided")

            # Clone the voice using the file-like objects
            voice = self._clone_voice(voice_name=voice_name, files=files, description=description)
            voice_id = getattr(voice, "voice_id", None) or getattr(voice, "id", None)
            if not voice_id:
                raise ValueError("Voice cloning succeeded but voice_id was not returned")

            print(f"✓ Voice cloned successfully: {voice_name}")
            print(f"✓ Voice ID: {voice_id}")

            return voice_id

        except Exception as e:
            raise Exception(f"Failed to clone voice from bytes: {str(e)}")
        finally:
            for f in files:
                if not f.closed:
                    f.close()

    def clone_voice(self, voice_name: str, audio_files: list[str], description: str = "") -> str:
        """
        Clone a voice using instant voice cloning from local files

        Args:
            voice_name: Name for the cloned voice
            audio_files: List of paths to audio files for voice cloning (1-25 files)
            description: Optional description for the voice

        Returns:
            voice_id: The ID of the created voice
        """
        try:
            # Prepare files for upload
            files = []
            for file_path in audio_files:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Audio file not found: {file_path}")
                files.append(open(file_path, 'rb'))

            # Clone the voice
            voice = self._clone_voice(voice_name=voice_name, files=files, description=description)
            voice_id = getattr(voice, "voice_id", None) or getattr(voice, "id", None)
            if not voice_id:
                raise ValueError("Voice cloning succeeded but voice_id was not returned")

            print(f"✓ Voice cloned successfully: {voice_name}")
            print(f"✓ Voice ID: {voice_id}")

            return voice_id

        except Exception as e:
            raise Exception(f"Failed to clone voice: {str(e)}")
        finally:
            for f in files:
                if not f.closed:
                    f.close()

    def text_to_speech(self, text: str, voice_id: str, output_path: str = "output.mp3") -> str:
        """
        Convert text to speech using a cloned voice

        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID to use
            output_path: Path where to save the audio file

        Returns:
            output_path: Path to the generated audio file
        """
        try:
            # Generate speech
            audio = self.client.generate(
                text=text,
                voice=voice_id,
                model="eleven_multilingual_v2",  # Best model for cloned voices
                voice_settings=self.voice_settings_class(
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.0,
                    use_speaker_boost=True
                )
            )

            # Save audio to file
            with open(output_path, 'wb') as f:
                for chunk in audio:
                    f.write(chunk)

            print(f"✓ Audio generated successfully: {output_path}")
            return output_path

        except Exception as e:
            raise Exception(f"Failed to generate speech: {str(e)}")

    def text_to_speech_bytes(self, text: str, voice_id: str) -> bytes:
        """
        Convert text to speech and return as bytes (for API responses)

        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID to use

        Returns:
            audio_bytes: Audio data as bytes
        """
        try:
            # Generate speech
            audio = self.client.generate(
                text=text,
                voice=voice_id,
                model="eleven_multilingual_v2",
                voice_settings=self.voice_settings_class(
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.0,
                    use_speaker_boost=True
                )
            )

            # Collect all chunks into bytes
            audio_bytes = b""
            for chunk in audio:
                audio_bytes += chunk

            print(f"✓ Audio generated successfully: {len(audio_bytes)} bytes")
            return audio_bytes

        except Exception as e:
            raise Exception(f"Failed to generate speech: {str(e)}")

    def get_voice_info(self, voice_id: str) -> dict:
        """
        Get information about a voice

        Args:
            voice_id: ElevenLabs voice ID

        Returns:
            Dictionary with voice information
        """
        try:
            voice = self.client.voices.get(voice_id)
            return {
                'voice_id': voice.voice_id,
                'name': voice.name,
                'category': voice.category,
                'description': voice.description
            }
        except Exception as e:
            raise Exception(f"Failed to get voice info: {str(e)}")

    def delete_voice(self, voice_id: str) -> bool:
        """
        Delete a cloned voice

        Args:
            voice_id: ElevenLabs voice ID to delete

        Returns:
            True if successful
        """
        try:
            self.client.voices.delete(voice_id)
            print(f"✓ Voice deleted: {voice_id}")
            return True
        except Exception as e:
            raise Exception(f"Failed to delete voice: {str(e)}")
