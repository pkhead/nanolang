from compileerror import CompilationException

class Token:
    TYPE_KEYWORD = 0
    TYPE_SYMBOL = 1 
    TYPE_IDENTIFIER = 2
    TYPE_NUMBER = 3
    TYPE_STRING = 4
    TYPE_EOF = 5

    KEYWORD_TYPES = ['void', 'string', 'number', 'bool']
    EVENT_NAMES = ['flag', 'keypress', 'click', 'broadcast']
    
    def __init__(self, lineno, linecol, token_type, value):
        self.type = token_type
        self.value = value
        self.lineno = lineno
        self.linecol = linecol
    
    def __str__(self):
        if self.type == Token.TYPE_KEYWORD:
            kw_str = "keyword"
        elif self.type == Token.TYPE_SYMBOL:
            kw_str = "symbol"
        elif self.type == Token.TYPE_IDENTIFIER:
            kw_str = "identifier"
        elif self.type == Token.TYPE_NUMBER:
            return "number"
        elif self.type == Token.TYPE_STRING:
            return "string"
        elif self.type == Token.TYPE_EOF:
            return "eof"
        else:
            raise CompilationException.from_token(self, "INTERNAL: unknown token type")
            
        return f"{kw_str} '{(self.value)}'"
    
    def is_keyword(self, kw):
        return self.type == Token.TYPE_KEYWORD and self.value == kw
    
    def is_symbol(self, sym):
        return self.type == Token.TYPE_SYMBOL and self.value == sym
    
    def get_identifier(self):
        if self.type != Token.TYPE_IDENTIFIER:
            raise CompilationException.from_token(self, "expected identifier")
        return self.value

class TokenQueue:
    def __init__(self, p_list):
        self.list = p_list
        self.index = 0
    
    def eof(self):
        return self.index >= len(self.list) - 1
    
    def pop(self):
        value = self.list[self.index]

        if value.type == Token.TYPE_EOF:
            raise CompilationException.from_token(value, 'unexpected eof')

        self.index += 1
        return value
    
    def peek(self):
        return self.list[self.index]
    
    def __bool__(self):
        return self.index < len(self.list)

class CharacterQueue:
    def __init__(self, file):
        self.file = file
        self.queue = []
    
    def _read_single(self):
        if self.queue:
            v = self.queue[0]
            del self.queue[0]
            return v

        return self.file.read(1)

    def read(self, n):
        assert(n == 1)
        return self._read_single()
    
    def push(self, ch):
        self.queue.append(ch)

SYMBOLS = [
    '@', ';', ':', ',',
    '{', '}', '(', ')', '[', ']',
    '=', '..',

    # operators
    '+', '-', '*', '/', '&',
    '==', '>=', '<=', '>', '<', '!=', '!', '&&', '||',
    '+=', '-=', '*=', '/=',
]

def get_symbol(file, char, lineno, linecol):
    if not any(x[0] == char for x in SYMBOLS):
        return None
    
    # filter out the specific symbol
    candidates = SYMBOLS
    i = 0
    sym = ""

    while True:
        candidates = [x for x in candidates if (i < len(x) and x[i] == char)]

        if not candidates:
            if not sym in SYMBOLS:
                raise CompilationException(lineno, linecol, "unknown symbol")
            file.push(char)

            return Token(lineno, linecol, Token.TYPE_SYMBOL, sym)
        
        if len(candidates) == 1:
            sym += char
            while len(sym) < len(candidates[0]):
                sym += file.read(1)
            
            if sym != candidates[0]:
                for ch in sym[1:]: # cancel symbol read...
                    file.push(ch)
                return None
            else:
                return Token(lineno, linecol, Token.TYPE_SYMBOL, candidates[0])

        if char == '\n' or not char:
            raise CompilationException(lineno, linecol, "unknown symbol")
        
        sym += char
        char = file.read(1)

        i += 1    

def parse_tokens(file_path):
    KEYWORDS = Token.KEYWORD_TYPES + [
        'func', 'var',

        'if', 'else', 'elseif', 'while', 'repeat', 'forever', 'for', 'block', 'drop', 'end', 'return',
        'true', 'false',

        # asset links
        'costume', 'sound',

        # events
        'when',

        'deleteclone',
    ]

    NUMERIC_CHARS = ['.', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    WORD_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_"

    tokens = []

    with open(file_path, 'r') as _f:
        file = CharacterQueue(_f)
        str_buf = []
        line_begin = True
        is_number = False

        lineno = 1
        linecol = 0

        # line number information for potential error messages
        token_lineno = 0
        token_linecol = 0

        eof = False
        while not eof:
            char = file.read(1)
            if not char:
                eof = True
                char = '\n'

            linecol += 1
            
            symbol = get_symbol(file, char, lineno, linecol)
            if symbol or char.isspace() or char == '#' or char == '"' or char == '\'':
                if str_buf:
                    word = ''.join(str_buf)

                    if is_number:
                        tokens.append(Token(token_lineno, token_linecol, Token.TYPE_NUMBER, word))
                        # print("NUMBER: " + word)
                    elif word in KEYWORDS:
                        tokens.append(Token(token_lineno, token_linecol, Token.TYPE_KEYWORD, word))
                        # print("KEYWORD: " + word)
                    else:
                        tokens.append(Token(token_lineno, token_linecol, Token.TYPE_IDENTIFIER, word))
                        # print("IDENTIFIER: " + word)
                    
                    str_buf.clear()
                
                # read entirety of string
                if char == '"' or char == '\'':
                    # for error handling
                    token_lineno = lineno
                    token_linecol = linecol

                    while True:
                        char = file.read(1)
                        linecol += 1
                        if not char:
                            raise CompilationException(token_lineno, token_linecol, "unterminated string")
                        
                        # escape sequence
                        if char == '\\':
                            char = file.read(1)
                            
                            if char == 'n':
                                str_buf.append('\n')
                            elif char == 't':
                                str_buf.append('\t')
                            elif char == 'r':
                                str_buf.append('\r')
                            elif char == '"':
                                str_buf.append('\"')
                            elif char == '\'':
                                str_buf.append('\'')
                            else:
                                raise CompilationException(lineno, linecol, "invalid escape sequence '\\" + char + "'")
                        
                        # end of string
                        elif char == '"' or char == '\'':
                            word = ''.join(str_buf)
                            tokens.append(Token(lineno, linecol, Token.TYPE_STRING, word))
                            # print("STRING: \"" + word + "\"")
                            str_buf.clear()
                            break
                        
                        # normal character
                        else:
                            str_buf.append(char)
                        
                        if char == '\n':
                            lineno += 1
                            linecol = 0
                
                elif symbol:                    
                    linecol += len(symbol.value)
                    tokens.append(symbol)
            else:
                # determine if word is text or number at the start
                if not str_buf:
                    is_number = char in NUMERIC_CHARS
                    token_lineno = lineno
                    token_linecol = linecol
                
                if is_number and not char in NUMERIC_CHARS:
                    raise CompilationException(lineno, linecol, f"unexpected char {char} in number")
                elif not is_number and not char in WORD_CHARS:
                    raise CompilationException(lineno, linecol, f"unexpected char {char} in keyword/identifier")
                
                str_buf.append(char)

            # special characters    
            if char == '\n': # newline
                line_begin = True
                lineno += 1
                linecol = 0
            
            elif char == '#': # comment
                while char and char != '\n':
                    char = file.read(1)
                
                lineno += 1
                linecol = 0
    
        tokens.append(Token(lineno, linecol, Token.TYPE_EOF, None))
    return tokens