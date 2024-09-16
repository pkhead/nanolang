class Token:
    TYPE_KEYWORD = 0
    TYPE_SYMBOL = 1 
    TYPE_IDENTIFIER = 2
    TYPE_NUMBER = 3
    TYPE_STRING = 4

    KEYWORD_TYPES = ['void', 'string', 'number']
    EVENT_NAMES = ['flag', 'keypress', 'click', 'broadcast']
    
    def __init__(self, token_type, value):
        self.type = token_type
        self.value = value
    
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
        else:
            raise Exception("unknown token type")
            
        return f"{kw_str} '{(self.value)}'"
    
    def is_keyword(self, kw):
        return self.type == Token.TYPE_KEYWORD and self.value == kw
    
    def is_symbol(self, sym):
        return self.type == Token.TYPE_SYMBOL and self.value == sym
    
    def get_identifier(self):
        if self.type != Token.TYPE_IDENTIFIER:
            raise Exception('expected identifier')
        return self.value

class TokenQueue:
    def __init__(self, p_list):
        self.list = p_list
        self.index = 0
    
    def pop(self):
        value = self.list[self.index]
        self.index += 1
        return value
    
    def peek(self):
        return self.list[self.index]
    
    def __bool__(self):
        return self.index < len(self.list)

def parse_tokens(file_path):
    KEYWORDS = Token.KEYWORD_TYPES + [
        'func', 'var',

        'if', 'while', 'for', 'block', 'drop', 'end',

        # asset links
        'costume', 'sound',

        # events
        'on'
    ]

    SYMBOLS = [
        ';',
        '{', '}', '(', ')', '[', ']',
        ':', ',', '"', '\'',
        '=',

        # operators
        '+', '-', '*', '/', '..'
    ]

    NUMERIC_CHARS = ['.', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    WORD_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_"

    tokens = []

    with open(file_path, 'r') as file:
        str_buf = []
        line_begin = True
        is_number = False

        while True:
            char = file.read(1)
            if not char:
                break
            
            is_symbol = char in SYMBOLS
            if is_symbol or char.isspace() or char == '#':
                if str_buf:
                    word = ''.join(str_buf)

                    if is_number:
                        tokens.append(Token(Token.TYPE_NUMBER, word))
                        # print("NUMBER: " + word)
                    elif word in KEYWORDS:
                        tokens.append(Token(Token.TYPE_KEYWORD, word))
                        # print("KEYWORD: " + word)
                    else:
                        tokens.append(Token(Token.TYPE_IDENTIFIER, word))
                        # print("IDENTIFIER: " + word)
                    
                    str_buf.clear()
                
                # read entirety of string
                if char == '"' or char == '\'':
                    while True:
                        char = file.read(1)
                        if not char:
                            raise Exception("unterminated string")
                        
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
                                raise Exception("invalid escape sequence '\\" + char + "'")
                        
                        # end of string
                        elif char == '"' or char == '\'':
                            word = ''.join(str_buf)
                            tokens.append(Token(Token.TYPE_STRING, word))
                            # print("STRING: \"" + word + "\"")
                            str_buf.clear()
                            break
                        
                        # normal character
                        else:
                            str_buf.append(char)
                
                elif is_symbol:
                    tokens.append(Token(Token.TYPE_SYMBOL, char))
                    # print("SYMBOL: " + char)
            else:
                # determine if word is text or number at the start
                if not str_buf:
                    is_number = char in NUMERIC_CHARS
                
                if is_number and not char in NUMERIC_CHARS:
                    raise Exception(f"unexpected char {char} in number")
                elif not is_number and not char in WORD_CHARS:
                    raise Exception(f"unexpected char {char} in keyword/identifier")
                
                str_buf.append(char)

            # special characters    
            if char == '\n': # newline
                line_begin = True
            elif char == '#': # comment
                while char and char != '\n':
                    char = file.read(1)
    
    return tokens