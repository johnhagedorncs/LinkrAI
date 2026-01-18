"""Session management for storing search results between SMS exchanges.

When the agent presents 3 appointment options to a patient, it stores them
in a session so that when the patient replies "1", "2", or "3", the agent
can retrieve the corresponding appointment details for booking.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Session storage directory
SESSION_DIR = Path(__file__).parent / "message_state" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)


class SessionManager:
    """Manages conversation sessions for appointment scheduling.

    Stores search results, preferences, and conversation state so the agent
    can maintain context across multiple SMS exchanges.
    """

    def __init__(self, session_dir: Path = SESSION_DIR):
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def save_search_results(
        self,
        patient_id: str,
        phone_number: str,
        specialty: str,
        options: List[Dict[str, Any]],
        preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save search results for a patient.

        Args:
            patient_id: Athena patient ID
            phone_number: Patient's phone number
            specialty: Medical specialty searched
            options: List of appointment options (up to 3)
            preferences: Patient's preferences (days, times, etc.)

        Returns:
            session_id: Unique session identifier
        """
        session_id = f"{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        session_data = {
            "session_id": session_id,
            "patient_id": patient_id,
            "phone_number": phone_number,
            "specialty": specialty,
            "options": options,
            "preferences": preferences or {},
            "state": "awaiting_selection",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }

        session_file = self.session_dir / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)

        # Also maintain phone number index for quick lookup
        self._update_phone_index(phone_number, session_id)

        logger.info(f"Saved session: {session_id} for patient {patient_id}")
        return session_id

    def get_session_by_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent active session for a patient.

        Args:
            patient_id: Athena patient ID

        Returns:
            Session data if found and not expired, None otherwise
        """
        # Find most recent session for this patient
        patient_sessions = sorted(
            self.session_dir.glob(f"{patient_id}_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for session_file in patient_sessions:
            session_data = self._load_session_file(session_file)
            if session_data and not self._is_expired(session_data):
                return session_data

        return None

    def get_session_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get active session by phone number.

        Args:
            phone_number: Patient's phone number

        Returns:
            Session data if found and not expired, None otherwise
        """
        phone_index_file = self.session_dir / "phone_index.json"
        if not phone_index_file.exists():
            return None

        with open(phone_index_file, 'r') as f:
            phone_index = json.load(f)

        session_id = phone_index.get(phone_number)
        if not session_id:
            return None

        return self.get_session(session_id)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID.

        Args:
            session_id: Unique session identifier

        Returns:
            Session data if found and not expired, None otherwise
        """
        session_file = self.session_dir / f"{session_id}.json"
        if not session_file.exists():
            return None

        session_data = self._load_session_file(session_file)
        if session_data and self._is_expired(session_data):
            logger.info(f"Session expired: {session_id}")
            self.delete_session(session_id)
            return None

        return session_data

    def update_session_state(self, session_id: str, new_state: str) -> bool:
        """Update the state of a session.

        Args:
            session_id: Unique session identifier
            new_state: New state value (e.g., 'booking', 'completed')

        Returns:
            True if updated successfully, False otherwise
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False

        session_data['state'] = new_state
        session_data['updated_at'] = datetime.now().isoformat()

        session_file = self.session_dir / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)

        logger.info(f"Updated session {session_id} state to: {new_state}")
        return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Unique session identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        session_file = self.session_dir / f"{session_id}.json"
        if session_file.exists():
            # Load session to get phone number for index cleanup
            session_data = self._load_session_file(session_file)

            # Delete session file
            session_file.unlink()
            logger.info(f"Deleted session: {session_id}")

            # Clean up phone index
            if session_data and 'phone_number' in session_data:
                self._remove_from_phone_index(session_data['phone_number'], session_id)

            return True

        return False

    def cleanup_expired_sessions(self) -> int:
        """Delete all expired sessions.

        Returns:
            Number of sessions deleted
        """
        deleted_count = 0
        for session_file in self.session_dir.glob("*.json"):
            if session_file.name == "phone_index.json":
                continue

            session_data = self._load_session_file(session_file)
            if session_data and self._is_expired(session_data):
                session_id = session_data.get('session_id')
                if self.delete_session(session_id):
                    deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} expired sessions")
        return deleted_count

    def _load_session_file(self, session_file: Path) -> Optional[Dict[str, Any]]:
        """Load session data from file."""
        try:
            with open(session_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading session file {session_file}: {e}")
            return None

    def _is_expired(self, session_data: Dict[str, Any]) -> bool:
        """Check if a session has expired."""
        expires_at = session_data.get('expires_at')
        if not expires_at:
            return False

        try:
            expiry_time = datetime.fromisoformat(expires_at)
            return datetime.now() > expiry_time
        except Exception as e:
            logger.error(f"Error parsing expiry time: {e}")
            return False

    def _update_phone_index(self, phone_number: str, session_id: str):
        """Update phone number to session ID mapping."""
        phone_index_file = self.session_dir / "phone_index.json"

        phone_index = {}
        if phone_index_file.exists():
            with open(phone_index_file, 'r') as f:
                phone_index = json.load(f)

        phone_index[phone_number] = session_id

        with open(phone_index_file, 'w') as f:
            json.dump(phone_index, f, indent=2)

    def _remove_from_phone_index(self, phone_number: str, session_id: str):
        """Remove phone number from index if it points to this session."""
        phone_index_file = self.session_dir / "phone_index.json"
        if not phone_index_file.exists():
            return

        with open(phone_index_file, 'r') as f:
            phone_index = json.load(f)

        # Only remove if it points to this session (avoid removing newer sessions)
        if phone_index.get(phone_number) == session_id:
            del phone_index[phone_number]

            with open(phone_index_file, 'w') as f:
                json.dump(phone_index, f, indent=2)


# Global session manager instance
session_manager = SessionManager()
