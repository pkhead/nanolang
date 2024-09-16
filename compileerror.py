class CompilationException(Exception):
    def __init__(self, lineno, linecol, message):
        super().__init__(f"{lineno}:{linecol}: " + message)
    
    @staticmethod
    def from_token(token, message):
        return CompilationException(token.lineno, token.linecol, message)