# TODO: replace all assert calls with a proper exception throw

from lexer import parse_tokens, TokenQueue
from astgen import parse_program
from gbgen import generate_program

if __name__ == '__main__':
    tokens = TokenQueue(parse_tokens('src.sc'))
    program = parse_program(tokens)
    # print(program)

    for f in program['functions'].values():
        pass
        # print(f"function {(f.name)}(): {(f.type)} ")
        # for statement in f.definition.statements:
            # print(statement)
    
    with open('out/main.gs', 'w') as f:
        generate_program(program, f)