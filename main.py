TOKEN_KEYWORD = 0
TOKEN_SYMBOL = 1 
TOKEN_IDENTIFIER = 2
TOKEN_NUMBER = 3
TOKEN_STRING = 4

class Token:
    def __init__(self, token_type, value):
        self.type = token_type
        self.value = value
    
    def __str__(self):
        if self.type == TOKEN_KEYWORD:
            kw_str = "keyword"
        elif self.type == TOKEN_SYMBOL:
            kw_str = "symbol"
        elif self.type == TOKEN_IDENTIFIER:
            kw_str = "identifier"
        elif self.type == TOKEN_NUMBER:
            kw_str = "number"
        elif self.type == TOKEN_STRING:
            kw_str = "string"
        else:
            raise Exception("unknown token type")
            
        return f"<{kw_str} {(self.value)}>"
    
    def is_keyword(self, kw):
        return self.type == TOKEN_KEYWORD and self.value == kw
    
    def is_symbol(self, sym):
        return self.type == TOKEN_SYMBOL and self.value == sym
    
    def get_identifier(self):
        if self.type != TOKEN_IDENTIFIER:
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
    KEYWORDS = [
        'func', 'var',

        'if', 'while', 'for', 'block', 'drop', 'end',

        # asset links
        'costume', 'sound',

        # types
        'void', 'string', 'number',

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
                        tokens.append(Token(TOKEN_NUMBER, word))
                        # print("NUMBER: " + word)
                    elif word in KEYWORDS:
                        tokens.append(Token(TOKEN_KEYWORD, word))
                        # print("KEYWORD: " + word)
                    else:
                        tokens.append(Token(TOKEN_IDENTIFIER, word))
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
                            tokens.append(Token(TOKEN_STRING, word))
                            # print("STRING: \"" + word + "\"")
                            str_buf.clear()
                            break
                        
                        # normal character
                        else:
                            str_buf.append(char)
                
                elif is_symbol:
                    tokens.append(Token(TOKEN_SYMBOL, char))
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

def parse_function(program, name, func_type, tokens):
    while not tokens.pop().is_keyword('end'): pass
    return {
        'name': name,
        'type': func_type
    }

def parse_program(tokens):
    program = {}
    program['costumes'] = []
    program['sounds'] = []
    program['functions'] = {}
    program['events'] = {}

    KEYWORD_TYPES = ['void', 'string', 'number']
    EVENT_NAMES = ['flag', 'keypress', 'click', 'broadcast']

    while tokens:
        tok = tokens.pop()

        # costumes
        # syntax: costume <str1> [, [...]]
        if tok.is_keyword('costume'):
            asset_name = tokens.pop()
            assert(asset_name.type == TOKEN_STRING)
            program['costumes'].append(asset_name.value)
        
        # sounds
        # syntax similar to costumes
        elif tok.is_keyword('sound'):
            asset_name = tokens.pop()
            assert(asset_name.type == TOKEN_STRING)
            program['sounds'].append(asset_name.value)
        
        # events
        # syntax: on <event_name>: <func1> [, [...]]
        elif tok.is_keyword('on'):
            event_name = tokens.pop().get_identifier()
            assert(event_name in EVENT_NAMES)
            assert(tokens.pop().is_symbol(':'))

            if not event_name in program['events']:
                program['events'][event_name] = []
            event_targets = program['events'][event_name]

            fname = tokens.pop().get_identifier()
            assert(fname in program['functions'])

            if not fname in event_targets:
                event_targets.append(fname)

            program['events'][event_name] = event_targets
        
        # function definition
        elif tok.is_keyword('func'):
            func_name = tokens.pop().get_identifier()
            assert(not func_name in program['functions'])
            assert(tokens.pop().is_symbol('('))
            assert(tokens.pop().is_symbol(')'))
            assert(tokens.pop().is_symbol(':'))
            func_type = tokens.pop()
            assert(func_type.type == TOKEN_KEYWORD and func_type.value in KEYWORD_TYPES)

            program['functions'][func_name] = parse_function(program, func_name, func_type.value, tokens)
        
        else:
            raise Exception("unknown token " + str(tok))
    
    return program

def main():
    tokens = TokenQueue(parse_tokens('src.sc'))
    program = parse_program(tokens)
    print(program)

if __name__ == '__main__':
    main()    