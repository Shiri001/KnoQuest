import uuid
from typing import Dict, List, Optional
from datetime import datetime

class MessageItem:
    def __init__(self, role: str, content: str, sources: Optional[List[dict]] = None):
        self.role = role
        self.content = content
        self.sources = sources or []
        self.timestamp = datetime.utcnow().isoformat()

class ConversationSession:
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.messages: List[MessageItem] = []
        self.session_files: List[str] = []

    def add_message(self, role: str, content: str, sources: Optional[List[dict]] = None):
        self.messages.append(MessageItem(role, content, sources))

    def get_history_context(self, max_turns: int = 5) -> str:
        """Returns recent conversation turns formatted for prompt context."""
        recent = self.messages[-max_turns*2:] if len(self.messages) > max_turns*2 else self.messages
        if not recent:
            return ""
        lines = []
        for msg in recent:
            prefix = "User: " if msg.role == "user" else "Assistant: "
            lines.append(f"{prefix}{msg.content}")
        return "\n".join(lines)

class ConversationManager:
    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = {}

    def get_or_create_session(self, conversation_id: Optional[str] = None) -> ConversationSession:
        if not conversation_id or conversation_id not in self._sessions:
            new_id = conversation_id or str(uuid.uuid4())
            self._sessions[new_id] = ConversationSession(new_id)
            return self._sessions[new_id]
        return self._sessions[conversation_id]

    def clear_session(self, conversation_id: str):
        if conversation_id in self._sessions:
            del self._sessions[conversation_id]

conversation_manager = ConversationManager()
