class Conversation:
    def __init__(self):
        self.messages = []

    def add(self, role: str, content: str, fig=None, suggestion: str | None = None):
        self.messages.append({
            "role": role,
            "content": content,
            "fig": fig,
            "suggestion": suggestion,
        })

    def clear(self):
        self.messages = []
