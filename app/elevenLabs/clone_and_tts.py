import os
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# ---- Config ----
HARDCODED_TEXT = "Hello! This is a test of my instant voice clone using ElevenLabs."
OUTPUT_MP3 = "out.mp3"
VOICE_ID_CACHE = ".voice_id.tmp"  # optional local cache (temporary)

# Pick a model (ElevenLabs docs show eleven_multilingual_v2 as a default)
MODEL_ID = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"


def get_client() -> ElevenLabs:
    load_dotenv()
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ELEVENLABS_API_KEY in environment (.env).")
    return ElevenLabs(api_key=api_key)


def resolve_voice_id(provided_voice_id: str | None = None) -> str:
    if provided_voice_id:
        return provided_voice_id
    env_voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    if env_voice_id:
        return env_voice_id
    cache = Path(VOICE_ID_CACHE)
    if cache.exists():
        cached = cache.read_text(encoding="utf-8").strip()
        if cached:
            return cached
    raise RuntimeError("Missing voice_id. Provide ELEVENLABS_VOICE_ID or cache one.")


def clone_voice(client: ElevenLabs, sample_path: str, name: str = "My IVC Voice") -> str:
    p = Path(sample_path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Voice sample not found: {p}")

    audio_bytes = p.read_bytes()

    # Instant Voice Clone create call (SDK)
    voice = client.voices.ivc.create(
        name=name,
        # You can pass multiple files for better quality; start with one.
        files=[BytesIO(audio_bytes)],
    )
    return voice.voice_id


def clone_voice_from_bytes(
    client: ElevenLabs, audio_bytes: bytes, name: str = "My IVC Voice"
) -> str:
    if not audio_bytes:
        raise ValueError("Audio sample is empty.")
    voice = client.voices.ivc.create(
        name=name,
        files=[BytesIO(audio_bytes)],
    )
    return voice.voice_id


def tts_to_file(client: ElevenLabs, voice_id: str, text: str, out_path: str) -> None:
    # Stream endpoint returns audio bytes in chunks (recommended for large outputs)
    audio_stream = client.text_to_speech.stream(
        voice_id=voice_id,
        text=text,
        model_id=MODEL_ID,
        output_format=OUTPUT_FORMAT,
    )

    out = Path(out_path)
    with out.open("wb") as f:
        for chunk in audio_stream:
            if chunk:
                f.write(chunk)


def tts_to_bytes(client: ElevenLabs, voice_id: str, text: str) -> bytes:
    audio_stream = client.text_to_speech.stream(
        voice_id=voice_id,
        text=text,
        model_id=MODEL_ID,
        output_format=OUTPUT_FORMAT,
    )
    output = bytearray()
    for chunk in audio_stream:
        if chunk:
            output.extend(chunk)
    return bytes(output)


def main(sample_path: str):
    load_dotenv()
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ELEVENLABS_API_KEY in environment (.env).")

    client = ElevenLabs(api_key=api_key)

    # 1) Clone voice
    voice_id = clone_voice(client, sample_path)
    print("Created voice_id:", voice_id)

    # Store voice_id "temporarily" (in-memory variable + optional temp file)
    Path(VOICE_ID_CACHE).write_text(voice_id, encoding="utf-8")

    # 2) TTS with hardcoded text
    tts_to_file(client, voice_id, HARDCODED_TEXT, OUTPUT_MP3)
    print(f"Saved TTS audio to: {OUTPUT_MP3}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python clone_and_tts.py /path/to/voice_sample.mp3")
        raise SystemExit(2)

    main(sys.argv[1])
