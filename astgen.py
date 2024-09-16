from lexer import Token

class Block:
    def __init__(self, parent=None):
        self.variables = {}
        self.parent = parent
        self.statements = []
    
    def declare_variable(self, var_name, var_type):
        self.variables.append({
            'name': var_name,
            'type': var_type
        })
    
    def get_variable_info(self, var_name):
        if var_name in self.variables:
            return self.variables[var_name]
        
        return False if self.parent == None else self.parent.get_variable_info(var_name)

def parse_expression(program, tokens):
    tok = tokens.pop()
    assert(tok.type == Token.TYPE_NUMBER or tok.type == Token.TYPE_STRING)
    return {}

def parse_block(program, tokens, parent_block=None):
    block = Block(parent_block)

    while True:
        tok = tokens.pop()
        if tok.is_keyword('end'): break
        
        if tok.is_keyword('drop'):
            raise Exception("drop command not implemented")
        
        elif tok.is_keyword('var'):
            var_name = tokens.pop().get_identifier()
            assert(tokens.pop().is_symbol(':'))
            var_type_token = tokens.pop()
            assert(var_type_token.type == Token.TYPE_KEYWORD and var_type_token.value in Token.KEYWORD_TYPES)
            var_type = var_type_token.value

            # variable declaration + assignment in one line
            if tokens.peek().is_symbol('='):
                tokens.pop()
                expr = parse_expression(program, tokens)
                statement = {
                    'type': 'var_declare',
                    'var_name': var_name,
                    'var_type': var_type,
                    'init': expr
                }
            
            # variable declaration without initial assignment
            else:
                expr = parse_expression(program, tokens)
                statement = {
                    'type': 'var_declare',
                    'var_name': var_name,
                    'var_type': var_type,
                    'init': None
                }
            
            block.statements.append(statement)
        
        else:
            raise Exception("unexpected " + str(tok))

    return block

class Function:
    def __init__(self, name, type, definition):
        self.name = name
        self.type = type
        self.definition = definition

def parse_function(program, tokens, name, func_type):
    block = parse_block(program, tokens)
    return Function(name, func_type, block)

def parse_program(tokens):
    program = {}
    program['costumes'] = []
    program['sounds'] = []
    program['functions'] = {}
    program['events'] = {}

    while tokens:
        tok = tokens.pop()

        # costumes
        # syntax: costume <str1> [, [...]]
        if tok.is_keyword('costume'):
            asset_name = tokens.pop()
            assert(asset_name.type == Token.TYPE_STRING)
            program['costumes'].append(asset_name.value)
        
        # sounds
        # syntax similar to costumes
        elif tok.is_keyword('sound'):
            asset_name = tokens.pop()
            assert(asset_name.type == Token.TYPE_STRING)
            program['sounds'].append(asset_name.value)
        
        # events
        # syntax: on <event_name>: <func1> [, [...]]
        elif tok.is_keyword('on'):
            event_name = tokens.pop().get_identifier()
            assert(event_name in Token.EVENT_NAMES)
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
            assert(func_type.type == Token.TYPE_KEYWORD and func_type.value in Token.KEYWORD_TYPES)

            program['functions'][func_name] = parse_function(program, tokens, func_name, func_type.value)
        
        else:
            raise Exception("unexpected " + str(tok))
    
    return program