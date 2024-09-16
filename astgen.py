from lexer import Token

class Block:
    def __init__(self, parent=None):
        self.variables = {}
        self.parent = parent
        self.statements = []
    
    def declare_variable(self, var_name, var_type):
        self.variables[var_name] = {
            'name': var_name,
            'type': var_type
        }
    
    def get_variable_info(self, var_name):
        if var_name in self.variables:
            return self.variables[var_name]
        
        return None if self.parent == None else self.parent.get_variable_info(var_name)
    
class BinaryOperator:
    def __init__(self, type, a, b):
        self.type = type
        self.left = a
        self.right = b
    
    def __str__(self):
        return f'{(self.type)}({str(self.left)}, {str(self.right)})'

class UnaryOperator:
    def __init__(self, type, expr):
        self.type = type
        self.expr = expr
    
    def __str__(self):
        return f'{(self.type)}({str(self.expr)})'

class IdentifierOperator:
    def __init__(self, type, output_type, id, data=None):
        self.type = type
        self.output_type = output_type
        self.id = id
        self.data = data
    
    def __str__(self):
        return f'{(self.type)}(<{self.id}>, {str(self.data)})'
    
COMPARISON_SYMBOLS = ['<', '>', '<=', '>=', '!=', '==']
COMPARISON_SYMBOL_NAMES = ['op_lt', 'op_gt', 'op_lte', 'op_gte', 'op_neq', 'op_eq']

ARITHMETIC_SYMBOLS = ['+', '-', '*', '/']
ARITHMETIC_SYMBOLS_NAMES = ['op_add', 'op_sub', 'op_mul', 'op_div']

def parse_expression(program, tokens, block, order=0):
    # TODO:
    # order 0: or
    # order 1: and
    # order 2: == !=
    # order 3: < > <= >=
    # order 4: ..
    # order 5: + -
    # order 6: * / %
    # order 7: not - (unary)
    # last order: func call, array subscript, struct member access, parentheses, raw values

    # FOR NOW:
    # order 0: + -
    # order 1: * /
    # + last order

    next_order = order+1

    if order == 0: # + -
        a = parse_expression(program, tokens, block, next_order)
        op_tok = tokens.peek()
        while op_tok.is_symbol('+') or op_tok.is_symbol('-'):
            op_name = ARITHMETIC_SYMBOLS_NAMES[ARITHMETIC_SYMBOLS.index(tokens.pop().value)]

            b = parse_expression(program, tokens, block, next_order)
            a = BinaryOperator(op_name, a, b)
            op_tok = tokens.peek()
        
        return a
    
    elif order == 1: # * /
        a = parse_expression(program, tokens, block, next_order)
        op_tok = tokens.peek()
        while op_tok.is_symbol('*') or op_tok.is_symbol('/'):
            op_name = ARITHMETIC_SYMBOLS_NAMES[ARITHMETIC_SYMBOLS.index(tokens.pop().value)]

            b = parse_expression(program, tokens, block, next_order)
            a = BinaryOperator(op_name, a, b)
            op_tok = tokens.peek()
        
        return a
    
    # assume that this is the last order - parentheses or raw values
    else:
        tok = tokens.peek()

        if tok.is_symbol('('):
            tokens.pop()
            expr = parse_expression(program, tokens, block, 0)
            assert(tokens.pop().is_symbol(')'))
            return expr
        
        elif tok.type == Token.TYPE_IDENTIFIER:
            tokens.pop()

            id_op = tokens.peek()

            # TODO: function calls
            if id_op.is_symbol('('):
                raise Exception("function calls not yet supported")
            
            # TODO: arrays
            elif id_op.is_symbol('['):
                raise Exception("arrays not yet supported")
        
            # TODO: structs
            elif id_op.is_symbol('.'):
                raise Exception("struct indexing not yet supported")

            elif id_op.is_symbol('->'):
                raise Exception("pointer indirection not yet supported")

            else:
                var_info = block.get_variable_info(tok.value)
                if var_info == None:
                    raise Exception(f"use of undeclared identifier '{(tok.value)}'")
                return IdentifierOperator('var_get', var_info['type'], var_info['name'])
        
        elif tok.type == Token.TYPE_STRING or tok.type == Token.TYPE_NUMBER:
            tokens.pop()
            return tok
    
    raise Exception('parse_expression: unreachable code')

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
                expr = parse_expression(program, tokens, block)
                statement = {
                    'type': 'var_declare',
                    'var_name': var_name,
                    'var_type': var_type,
                    'init': expr
                }
                print(expr)
            
            # variable declaration without initial assignment
            else:
                statement = {
                    'type': 'var_declare',
                    'var_name': var_name,
                    'var_type': var_type,
                    'init': None
                }
            
            block.declare_variable(var_name, var_type)
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