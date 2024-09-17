from lexer import Token
from compileerror import CompilationException

class ValueType:
    VOID = 0
    NUMBER = 1
    STRING = 2
    BOOL = 3

    # TODO: pointers
    POINTER = 4

    def __init__(self, type, base_type=None):
        self.type = type
        self.base_type = base_type
    
    @staticmethod
    def pointer_to(base_type):
        return ValueType(ValueType.POINTER, base_type)
    
    def __str__(self):
        if self.type == ValueType.POINTER:
            return str(self.base_type) + "*"
        if self.type == ValueType.NUMBER:
            return "number"
        elif self.type == ValueType.STRING:
            return "string"
        elif self.type == ValueType.BOOL:
            return "bool"
        elif self.type == ValueType.VOID:
            return "void"
        else:
            raise Exception("internal: unknown ValueType value " + str(self.type))
    
    def is_void(self):
        return self.type == ValueType.VOID
    
    def is_a(self, type_id):
        return self.type == type_id
    
    def is_same(self, other):
        if self.type == ValueType.POINTER and other.type == ValueType.POINTER:
            return self.base_type.is_same(other.base_type)
        else:
            return self.type == other.type
    
    def size(self):
        if self.type == ValueType.VOID:
            raise Exception("internal: attempt to get sizeof void")
        
        # TODO: structs can have different sizes
        return 1
    
class Block:
    def __init__(self, parent=None):
        self.variables = {}
        self.parameters = {}
        self.parent = parent
        self.statements = []
        self.return_type = None

        if parent:
            self.return_type = parent.return_type
    
    def declare_variable(self, var_name, var_type):
        self.variables[var_name] = {
            'name': var_name,
            'type': var_type
        }
    
    def declare_parameter(self, var_name, var_type):
        self.parameters[var_name] = {
            'name': var_name,
            'type': var_type
        }
    
    def get_variable_info(self, var_name):
        if var_name in self.variables:
            return self.variables[var_name]
        elif var_name in self.parameters:
            return self.parameters[var_name]
        else:
            return None if self.parent == None else self.parent.get_variable_info(var_name)

class ExpressionConstant:
    def __init__(self, tok):
        self.token = tok
        self.op = 'const'
        
        if tok.type == Token.TYPE_NUMBER:
            self.type = ValueType(ValueType.NUMBER)
            self.value = float(tok.value)
        
        elif tok.type == Token.TYPE_STRING:
            self.type = ValueType(ValueType.STRING)
            self.value = tok.value
        
        elif tok.is_keyword('true'):
            self.type = ValueType(ValueType.BOOL)
            self.value = True
        
        elif tok.is_keyword('false'):
            self.type = ValueType(ValueType.BOOL)
            self.value = False
        
        else:
            raise Exception("internal: could not get type of token for ExpressionConstant")
    
    def __str__(self):
        return f"const<{self.type}>({str(self.value)})"
    
class BinaryOperator:
    def __init__(self, op, type, a, b):
        self.op = op
        self.type = type
        self.left = a
        self.right = b
    
    def __str__(self):
        return f'{(self.op)}<{self.type}>({str(self.left)}, {str(self.right)})'

class UnaryOperator:
    def __init__(self, op, type, expr):
        self.op = op
        self.type = type
        self.expr = expr
    
    def __str__(self):
        return f'{(self.op)}<{self.type}>({str(self.expr)})'

class IdentifierOperator:
    def __init__(self, op, type, id, data=None):
        self.op = op
        self.type = type
        self.id = id
        self.data = data
    
    def __str__(self):
        return f'{(self.op)}<{self.type}>(<{self.id}>, {str(self.data)})'

class Function:
    def __init__(self, name, type, params, definition, attribs):
        self.name = name
        self.type = type
        self.parameters = params
        self.definition = definition
        self.attributes = attribs

ATTRIBUTES = ['nowarp']
EVENT_NAMES = ['flag', 'keypress']

COMPARISON_SYMBOLS = ['<', '>', '<=', '>=', '!=', '==']
COMPARISON_SYMBOL_NAMES = ['op_lt', 'op_gt', 'op_lte', 'op_gte', 'op_neq', 'op_eq']

ARITHMETIC_SYMBOLS = ['+', '-', '*', '/']
ARITHMETIC_SYMBOLS_NAMES = ['op_add', 'op_sub', 'op_mul', 'op_div']

# assumes the identifier token was popped off, leaving the
# token queue on the opening parenthesis
def parse_function_call(program, tokens, block, id_token):
    tokens.pop() # pop opening parenthesis
    func_name = id_token.value
    
    if not (func_name in program['functions']):
        if block.get_variable_info(func_name):
            raise CompilationException.from_token(id_token, f"'{func_name}' is not a function")
        else:
            raise CompilationException.from_token(id_token, f"'{func_name}' is not a defined function")

    func_data = program['functions'][func_name]
    func_args = []

    # read function arguments
    if not tokens.peek().is_symbol(')'):
        while True:
            next_tok = tokens.peek()

            arg_index = len(func_args)
            if arg_index >= len(func_data.parameters):
                raise CompilationException.from_token(id_token, f"too many function arguments for '{func_name}'")
        
            arg_expr = parse_expression(program, tokens, block)
            param_type = func_data.parameters[arg_index]['type']
            if not arg_expr.type.is_same(param_type):
                raise CompilationException.from_token(next_tok, f"expected {str(param_type)} for argument {arg_index}, got {str(arg_expr.type)}")
            
            func_args.append(arg_expr)

            next_tok = tokens.pop()
            if next_tok.is_symbol(')'): break
            elif not next_tok.is_symbol(','):
                raise CompilationException.from_token(next_tok, 'expected , or ), got ' + str(next_tok))
    else:
        assert(tokens.pop().is_symbol(')'))
    
    if len(func_args) != len(func_data.parameters):
        raise CompilationException.from_token(id_token, f"not enough function arguments for '{func_name}'")
    
    return {
        'function': func_data,
        'args': func_args
    }

def parse_expression(program, tokens, block, order=0):
    # TODO:
    # order 0: or
    # order 1: and
    # order 2: == !=
    # order 3: < > <= >=
    # order 4: & (string concatenation)
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

            if not (a.type.is_a(ValueType.NUMBER) and b.type.is_a(ValueType.NUMBER)):
                raise CompilationException.from_token(op_tok, "attempt to add " + str(a.type) + " with " + str(b.type))
            
            a = BinaryOperator(op_name, ValueType(ValueType.NUMBER), a, b)
            op_tok = tokens.peek()
        
        return a
    
    elif order == 1: # * /
        a = parse_expression(program, tokens, block, next_order)
        op_tok = tokens.peek()
        while op_tok.is_symbol('*') or op_tok.is_symbol('/'):
            op_name = ARITHMETIC_SYMBOLS_NAMES[ARITHMETIC_SYMBOLS.index(tokens.pop().value)]
            b = parse_expression(program, tokens, block, next_order)
            
            if not (a.type.is_a(ValueType.NUMBER) and b.type.is_a(ValueType.NUMBER)):
                raise CompilationException.from_token(op_tok, "attempt to multiply " + str(a.type) + " with " + str(b.type))

            a = BinaryOperator(op_name, ValueType(ValueType.NUMBER), a, b)
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
            var_info = block.get_variable_info(tok.value)

            if id_op.is_symbol('('):
                # here, a function is required
                if var_info != None:
                    raise CompilationException.from_token(id_op, "attempt to perform a function call on a variable")
                
                func_call_data = parse_function_call(program, tokens, block, tok)
                func_data = func_call_data['function']
                func_args = func_call_data['args']

                return IdentifierOperator('func_call', func_data.type, tok.value, func_args)
            else:
                # here, a variable is required
                if var_info == None:
                    raise Exception(f"use of undeclared identifier '{(tok.value)}'")
                
                # TODO: arrays
                if id_op.is_symbol('['):
                    raise Exception("arrays not yet supported")
            
                # TODO: structs
                elif id_op.is_symbol('.'):
                    raise Exception("struct indexing not yet supported")

                elif id_op.is_symbol('->'):
                    raise Exception("pointer indirection not yet supported")

                else:
                    return IdentifierOperator('var_get', var_info['type'], var_info['name'])
        
        elif tok.type == Token.TYPE_STRING or tok.type == Token.TYPE_NUMBER:
            tokens.pop()
            return ExpressionConstant(tok)
    
    raise Exception('parse_expression: unreachable code')

def parse_type(program, tokens, allow_void=False):
    tok = tokens.pop()
    if tok.type != Token.TYPE_KEYWORD:
        raise CompilationException.from_token(tok, "expected type, got " + str(tok))
    
    if tok.value == 'number':
        type = ValueType(ValueType.NUMBER)
    elif tok.value == 'string':
        type = ValueType(ValueType.STRING)
    elif tok.value == 'bool':
        type = ValueType(ValueType.BOOL)
    elif tok.value == 'void':
        type = ValueType(ValueType.VOID)
    else:
        raise CompilationException.from_token(tok, "expected type, got " + str(tok))
    
    # accumulate pointer types
    while tokens.peek().is_symbol('*'):
        tokens.pop()
        type = ValueType.pointer_to(type)
    
    if not allow_void and type.type == ValueType.VOID:
        raise CompilationException.from_token(tok, "void type not allowed")

    return type
    

def parse_block(program, tokens, parent_block=None):
    block = Block(parent_block)
    does_return = False

    while True:
        tok = tokens.pop()
        if tok.is_keyword('end'):
            if not block.return_type.is_void() and not does_return:
                raise CompilationException.from_token(tok, "not all code paths return a value")
            
            if not does_return:
                block.statements.append({
                    'type': 'return',
                    'value': None
                })

            break
        
        if tok.is_keyword('drop'):
            raise Exception("drop command not implemented")

        elif tok.is_keyword('return'):
            if not block.return_type.is_void():
                return_expr = parse_expression(program, tokens, block)
                if not return_expr.type.is_same(block.return_type):
                    raise CompilationException.from_token(tok, f"cannot convert {str(return_expr.type)} to {str(block.return_type)}")

                statement = {
                    'type': 'return',
                    'value': return_expr
                }
            
            else:
                statement = {
                    'type': 'return',
                    'value': None
                }
            
            if not does_return:
                block.statements.append(statement)
            
            does_return = True
        
        elif tok.is_keyword('var'):
            var_name = tokens.pop().get_identifier()
            assert(tokens.pop().is_symbol(':'))
            var_type = parse_type(program, tokens)

            # variable declaration + assignment in one line
            tok = tokens.peek()
            if tok.is_symbol('='):
                tokens.pop()
                expr = parse_expression(program, tokens, block)
                if not expr.type.is_same(var_type):
                    raise CompilationException.from_token(tok, f"attempt to assign a {str(expr.type)} to a {str(var_type)}")
                statement = {
                    'type': 'var_declare',
                    'var_name': var_name,
                    'var_type': var_type,
                    'init': expr
                }
                print("EXPR: " + str(expr))
            
            # variable declaration without initial assignment
            else:
                statement = {
                    'type': 'var_declare',
                    'var_name': var_name,
                    'var_type': var_type,
                    'init': None
                }
            
            block.declare_variable(var_name, var_type)

            if not does_return:
                block.statements.append(statement)
        
        # function call
        # since there is no expression-as-statement functionality (partly due to the lack of semicolons)
        # function call statements have to be specifically programmed
        elif tok.type == Token.TYPE_IDENTIFIER:
            func_call_data = parse_function_call(program, tokens, block, tok)

            if not does_return:
                block.statements.append({
                    'type': 'func_call',
                    'func_name': func_call_data['function'].name,
                    'args': func_call_data['args']
                })
        
        else:
            raise CompilationException.from_token(tok, "unexpected " + str(tok))

    return block

def parse_function(program, tokens, name, func_type, func_params, attribs):
    func_block = Block()
    func_block.return_type = func_type
    for param in func_params:
        func_block.declare_parameter(param['name'], param['type'])
    
    block = parse_block(program, tokens, func_block)
    return Function(name, func_type, func_params, block, attribs[:])

def parse_program(tokens):
    program = {}
    program['costumes'] = []
    program['sounds'] = []
    program['functions'] = {}
    program['events'] = []

    attributes = []

    while tokens:
        tok = tokens.pop()

        # costumes
        # syntax: costume <str1> [, [...]]
        if tok.is_keyword('costume'):
            if attributes:
                raise CompilationException.from_token(tok, "costume declaration does not take attributes")
            
            asset_name = tokens.pop()
            assert(asset_name.type == Token.TYPE_STRING)
            program['costumes'].append(asset_name.value)
        
        # sounds
        # syntax similar to costumes
        elif tok.is_keyword('sound'):
            if attributes:
                raise CompilationException.from_token(tok, "sound declaration does not take attributes")
            
            asset_name = tokens.pop()
            assert(asset_name.type == Token.TYPE_STRING)
            program['sounds'].append(asset_name.value)
        
        # function definition
        elif tok.is_keyword('func'):
            tok = tokens.pop()
            func_name = tok.get_identifier()
            if func_name in program['functions']:
                raise CompilationException.from_token(tok, f"function '{func_name}' already defined")
            
            assert(tokens.pop().is_symbol('('))

            # read function parameters
            func_params = []
            if not tokens.peek().is_symbol(')'):
                while True:
                    param_name = tokens.pop().get_identifier()
                    assert(tokens.pop().is_symbol(':'))
                    param_type = parse_type(program, tokens)

                    func_params.append({
                        'name': param_name,
                        'type': param_type
                    })

                    # read either a closing parenthesis or a comma
                    next_tok = tokens.pop()
                    if next_tok.is_symbol(')'): break
                    elif not next_tok.is_symbol(','):
                        raise CompilationException.from_token(next_tok, 'expected , or ), got ' + str(next_tok))
            else:
                assert(tokens.pop().is_symbol(')'))
            
            # read function return type
            assert(tokens.pop().is_symbol(':'))

            func_type = parse_type(program, tokens, True)
            program['functions'][func_name] = parse_function(
                program, tokens,
                name=func_name, func_type=func_type, func_params=func_params, attribs=attributes)

            attributes.clear()
        
        # event handler
        elif tok.is_keyword('on'):
            tok = tokens.pop()
            event_name = tok.get_identifier()
            if not event_name in EVENT_NAMES:
                raise CompilationException.from_token(tok, f"invalid event '{event_name}'")
            
            parent_block = Block()
            parent_block.return_type = ValueType(ValueType.VOID)

            program['events'].append({
                'event_name': event_name,
                'definition': parse_block(program, tokens, parent_block),
                'attributes': attributes[:]
            })
            attributes.clear()
        
        elif tok.is_symbol('@'):
            tok = tokens.pop()
            attr_name = tok.get_identifier()

            if not attr_name in ATTRIBUTES:
                raise CompilationException.from_token(tok, f"unknown attribute '{attr_name}'")

            if attr_name in attributes:
                raise CompilationException.from_token(tok, "same attribute defined more than once")

            attributes.append(attr_name)
        
        else:
            raise Exception("unexpected " + str(tok))
    
    return program