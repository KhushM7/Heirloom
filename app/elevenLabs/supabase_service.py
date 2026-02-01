"""
Supabase service for database operations
"""
import uuid
from supabase import create_client, Client
from .config import Config


class SupabaseService:
    """Handle Supabase database operations"""

    def __init__(self):
        """Initialize Supabase client"""
        self.client: Client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_KEY
        )

    @staticmethod
    def _validate_user_id(user_id: str) -> None:
        """Ensure user_id is a valid UUID string before querying Supabase."""
        try:
            uuid.UUID(str(user_id))
        except (TypeError, ValueError):
            raise ValueError("User ID must be a valid UUID.")

    def store_voice_id(self, user_id: str, voice_id: str) -> dict:
        """
        Store ElevenLabs voice_id in the profiles table

        Args:
            user_id: User's ID (primary key in profiles table)
            voice_id: ElevenLabs voice ID to store

        Returns:
            Updated profile data
        """
        self._validate_user_id(user_id)
        try:
            # Update the voice_id field in the profiles table
            response = self.client.table('profiles').update({
                'voice_id': voice_id
            }).eq('id', user_id).execute()

            if response.data:
                print(f"✓ Voice ID stored for user: {user_id}")
                return response.data[0]
            else:
                raise Exception("No profile found for user")

        except Exception as e:
            raise Exception(f"Failed to store voice_id: {str(e)}")

    def get_voice_id(self, user_id: str) -> str:
        """
        Retrieve ElevenLabs voice_id from the profiles table

        Args:
            user_id: User's ID

        Returns:
            voice_id: ElevenLabs voice ID
        """
        self._validate_user_id(user_id)
        try:
            response = self.client.table('profiles').select('voice_id').eq('id', user_id).execute()

            if response.data and len(response.data) > 0:
                voice_id = response.data[0].get('voice_id')
                if voice_id:
                    return voice_id
                else:
                    raise Exception("No voice_id found for this user")
            else:
                raise Exception("User profile not found")

        except Exception as e:
            raise Exception(f"Failed to retrieve voice_id: {str(e)}")

    def get_profile(self, user_id: str) -> dict:
        """
        Get full profile data for a user

        Args:
            user_id: User's ID

        Returns:
            Profile data dictionary
        """
        self._validate_user_id(user_id)
        try:
            response = self.client.table('profiles').select('*').eq('id', user_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            else:
                raise Exception("User profile not found")

        except Exception as e:
            raise Exception(f"Failed to get profile: {str(e)}")

    def create_profile(self, user_id: str, voice_id: str = None, **kwargs) -> dict:
        """
        Create a new profile (if your application needs this)

        Args:
            user_id: User's ID
            voice_id: Optional ElevenLabs voice ID
            **kwargs: Additional profile fields

        Returns:
            Created profile data
        """
        self._validate_user_id(user_id)
        try:
            profile_data = {'id': user_id}

            if voice_id:
                profile_data['voice_id'] = voice_id

            # Add any additional fields
            profile_data.update(kwargs)

            response = self.client.table('profiles').insert(profile_data).execute()

            if response.data:
                print(f"✓ Profile created for user: {user_id}")
                return response.data[0]
            else:
                raise Exception("Failed to create profile")

        except Exception as e:
            raise Exception(f"Failed to create profile: {str(e)}")
