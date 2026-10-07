class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.messages = None
        self.all_messages = []

    def complete_json(self, messages):
        self.messages = messages
        self.all_messages.append(messages)
        return dict(self.response)