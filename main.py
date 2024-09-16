KEYWORDS = [
    # asset links
    'costume', 'sound',

    # types
    'void', 'string', 'number',

    # events
    'on', 'flag', 'keypress', 'click', 'broadcast'
]

SYMBOLS = [';', '{', '}', '(', ')', '[', ']', ':', ',', '"', '\'', '=']
NUMERIC_CHARS = ['.', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
WORD_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_"

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
                        print("NUMBER: " + word)
                    elif word in KEYWORDS:
                        print("KEYWORD: " + word)
                    else:
                        print("IDENTIFIER: " + word)
                    
                    str_buf.clear()
                
                # read entirety of string
                if char == '"' or char == '\'':
                    while True:
                        char = file.read(1)
                        if not char:
                            raise Exception("unterminated string")
                        
                        # end of string
                        if char == '"' or char == '\'':
                            print("STRING: \"" + ''.join(str_buf) + "\"")
                            str_buf.clear()
                            break
                        
                        # normal character
                        else:
                            str_buf.append(char)
                
                elif is_symbol:
                    print("SYMBOL: " + char)
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