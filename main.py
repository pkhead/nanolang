KEYWORDS = [
    # asset links
    'costume', 'sound',

    # types
    'void', 'string', 'number',

    # events
    'on', 'flag', 'keypress', 'click', 'broadcast'
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

TOKEN_KEYWORD = 0
TOKEN_SYMBOL = 1 
TOKEN_IDENTIFIER = 2
TOKEN_NUMBER = 3
TOKEN_STRING = 4

class Token:
    def __init__(self, token_type, value):
        self.type = token_type
        self.value = value

def parse_tokens(file_path):
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

if __name__ == '__main__':
    tokens = parse_tokens('src.sc')
    for tok in tokens:
        if tok.type == TOKEN_KEYWORD:
            tokstr = 'KEYWORD'
        elif tok.type == TOKEN_SYMBOL:
            tokstr = 'SYMBOL'
        elif tok.type == TOKEN_IDENTIFIER:
            tokstr = 'IDENTIFIER'
        elif tok.type == TOKEN_NUMBER:
            tokstr = 'NUMBER'
        elif tok.type == TOKEN_STRING:
            tokstr = 'STRING'
        else:
            tokstr = '[ERROR]'
        
        print(f"{tokstr}: {(tok.value)}")