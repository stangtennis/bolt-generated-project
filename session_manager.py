import datetime
import logging
import uuid
from typing import Dict, Set, Optional, List
import traceback

logger = logging.getLogger(__name__)

class Session:
    def __init__(self, client_sid: str, client_name: str):
        self.client_sid = client_sid
        self.client_name = client_name
        self.controllers: Set[str] = set()
        self.start_time = datetime.datetime.now()
        self.last_activity = datetime.datetime.now()
        self.active = True

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.datetime.now()

class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._client_sessions: Dict[str, str] = {}
        self.session_timeout = datetime.timedelta(minutes=30)  # Increase timeout to 30 minutes
        self.cleanup_interval = datetime.timedelta(minutes=5)  # Clean up every 5 minutes
        self.last_cleanup = datetime.datetime.now()

    def create_session(self, client_sid: str, client_name: str) -> str:
        """Create a new session for a client"""
        try:
            # First clean up any existing sessions for this client
            self.remove_client(client_sid)
            
            # Create new session
            session_id = str(uuid.uuid4())[:8]
            self._sessions[session_id] = Session(client_sid, client_name)
            self._client_sessions[client_sid] = session_id
            logger.info(f"Created session {session_id} for {client_name}")
            return session_id
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            traceback.print_exc()
            raise

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        try:
            session = self._sessions.get(session_id)
            if session:
                session.update_activity()
            return session
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None

    def join_session(self, session_id: str, controller_sid: str) -> bool:
        """Add a controller to a session"""
        try:
            # First clean up any existing sessions for this controller
            self.remove_client(controller_sid)
            
            if session_id in self._sessions:
                session = self._sessions[session_id]
                if not session.active:
                    logger.warning(f"Attempted to join inactive session {session_id}")
                    return False
                    
                if controller_sid not in session.controllers:
                    session.controllers.add(controller_sid)
                    self._client_sessions[controller_sid] = session_id
                    session.update_activity()
                    logger.info(f"Controller {controller_sid} joined session {session_id}")
                    return True
                else:
                    logger.warning(f"Controller {controller_sid} already in session {session_id}")
                    return False
            else:
                logger.warning(f"Session {session_id} not found")
                return False
        except Exception as e:
            logger.error(f"Error joining session: {e}")
            traceback.print_exc()
            return False

    def leave_session(self, session_id: str, client_sid: str) -> None:
        """Remove a client from a session"""
        try:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                if client_sid == session.client_sid:
                    # If sharer leaves, end the session
                    logger.info(f"Sharer {client_sid} left session {session_id}, ending session")
                    self._cleanup_session(session_id)
                elif client_sid in session.controllers:
                    # If controller leaves, just remove them
                    session.controllers.remove(client_sid)
                    if client_sid in self._client_sessions:
                        del self._client_sessions[client_sid]
                    logger.info(f"Controller {client_sid} left session {session_id}")
                session.update_activity()
        except Exception as e:
            logger.error(f"Error leaving session: {e}")
            traceback.print_exc()

    def remove_client(self, client_sid: str) -> None:
        """Remove a client and their associated session."""
        try:
            session_id = self._client_sessions.get(client_sid)
            if session_id:
                session = self._sessions.get(session_id)
                if session:
                    if client_sid == session.client_sid:
                        # If sharer disconnects, end the session
                        self._cleanup_session(session_id)
                    else:
                        # If controller disconnects, just remove them
                        session.controllers.discard(client_sid)
                if client_sid in self._client_sessions:
                    del self._client_sessions[client_sid]
                logger.info(f"Removed client {client_sid} from session {session_id}")
            logger.info(f"Active sessions: {len(self._sessions)}")
        except Exception as e:
            logger.error(f"Error removing client {client_sid}: {e}")
            traceback.print_exc()

    def _cleanup_session(self, session_id: str) -> None:
        """Clean up a session and remove all associated clients"""
        try:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                # Mark session as inactive
                session.active = False
                # Remove all clients
                if session.client_sid in self._client_sessions:
                    del self._client_sessions[session.client_sid]
                for controller_sid in session.controllers:
                    if controller_sid in self._client_sessions:
                        del self._client_sessions[controller_sid]
                # Remove session
                del self._sessions[session_id]
                logger.info(f"Cleaned up session {session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up session: {e}")
            traceback.print_exc()

    def _cleanup_old_sessions(self) -> None:
        """Clean up inactive or timed out sessions"""
        try:
            now = datetime.datetime.now()
            sessions_to_cleanup = []
            
            for session_id, session in self._sessions.items():
                if not session.active or (now - session.last_activity) > self.session_timeout:
                    sessions_to_cleanup.append(session_id)
            
            for session_id in sessions_to_cleanup:
                logger.info(f"Cleaning up inactive/timed out session {session_id}")
                self._cleanup_session(session_id)
        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {e}")
            traceback.print_exc()

    def _should_cleanup(self) -> bool:
        """Check if we should run cleanup"""
        now = datetime.datetime.now()
        return (now - self.last_cleanup) > self.cleanup_interval

    def get_sessions(self) -> list:
        """Get list of available sessions"""
        try:
            # Only clean up periodically
            if self._should_cleanup():
                self._cleanup_old_sessions()
                self.last_cleanup = datetime.datetime.now()
            
            # Return active sessions
            active_sessions = []
            for session_id, session in self._sessions.items():
                if session.active:
                    active_sessions.append({
                        'id': session_id,
                        'client_name': session.client_name,
                        'num_controllers': len(session.controllers)
                    })
            logger.info(f"Active sessions: {len(active_sessions)}")
            return active_sessions
        except Exception as e:
            logger.error(f"Error getting sessions: {e}")
            traceback.print_exc()
            return []

    def get_session_controllers(self, session_id: str) -> List[str]:
        """Get list of controller SIDs for a session"""
        try:
            session = self._sessions.get(session_id)
            if session and session.active:
                return list(session.controllers)
            return []
        except Exception as e:
            logger.error(f"Error getting session controllers: {e}")
            return []

    def get_session_sharer(self, session_id: str) -> Optional[str]:
        """Get sharer's SID for a session"""
        try:
            session = self._sessions.get(session_id)
            if session and session.active:
                return session.client_sid
            return None
        except Exception as e:
            logger.error(f"Error getting session sharer: {e}")
            return None

    def get_controller_session(self, controller_sid: str) -> Optional[str]:
        """Get session ID for a controller"""
        try:
            return self._client_sessions.get(controller_sid)
        except Exception as e:
            logger.error(f"Error getting controller session: {e}")
            return None

    def is_controller(self, client_sid: str) -> bool:
        """Check if a client is a controller in any session"""
        try:
            session_id = self._client_sessions.get(client_sid)
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                return client_sid in session.controllers
            return False
        except Exception as e:
            logger.error(f"Error checking if client is controller: {e}")
            return False

    def is_sharer(self, client_sid: str) -> bool:
        """Check if a client is a sharer in any session"""
        try:
            session_id = self._client_sessions.get(client_sid)
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                return client_sid == session.client_sid
            return False
        except Exception as e:
            logger.error(f"Error checking if client is sharer: {e}")
            return False

    def remove_session_by_client(self, client_sid: str) -> Optional[str]:
        """Remove session by client SID and return session ID if found"""
        try:
            for session_id, session in list(self._sessions.items()):
                if session.client_sid == client_sid:
                    del self._sessions[session_id]
                    return session_id
            return None
        except Exception as e:
            logger.error(f"Error removing session by client: {e}")
            return None

    def remove_session(self, session_id: str) -> bool:
        """Remove session by session ID"""
        try:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing session: {e}")
            return False

    def get_all_session_ids(self) -> list:
        """Get list of all active session IDs"""
        try:
            return list(self._sessions.keys())
        except Exception as e:
            logger.error(f"Error getting all session IDs: {e}")
            return []

    def get_session_by_client(self, client_sid: str) -> Optional[str]:
        """Get session ID by client SID"""
        try:
            for session_id, session in self._sessions.items():
                if session.client_sid == client_sid:
                    return session_id
            return None
        except Exception as e:
            logger.error(f"Error getting session by client: {e}")
            return None

    def cleanup_stale_sessions(self, max_age_minutes: int = 60) -> list:
        """Remove sessions older than max_age_minutes"""
        try:
            now = datetime.datetime.now()
            stale_sessions = []
            for session_id, session in list(self._sessions.items()):
                if (now - session.start_time).total_seconds() > max_age_minutes * 60:
                    del self._sessions[session_id]
                    stale_sessions.append(session_id)
            return stale_sessions
        except Exception as e:
            logger.error(f"Error cleaning up stale sessions: {e}")
            return []
