from lexer import Token
from compileerror import CompilationException
from compilertypes import ValueType
from builtin_methods import BUILTIN_METHODS
import os
    
class Block:
    def __init__(self, parent=None):
        self.variables = {}
        self.parameters = {}
        self.parent = parent
        self.statements = []
        self.return_type = None
        self.top_level = False

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

class ExpressionNode:
    def __init__(self):
        self._const = False
        self.can_address = False
    
    def is_const(self):
        return self._const    

class ExpressionConstant(ExpressionNode):
    def __init__(self, tok):
        super().__init__()
        self.token = tok
        self.op = 'const'
        self._const = True
        
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
    
    def eval(self):
        return self.value
    
class BinaryOperator(ExpressionNode):
    def __init__(self, op, type, a, b):
        super().__init__()
        self.op = op
        self.type = type
        self.left = a
        self.right = b
        self._const = self.left.is_const() and self.right.is_const()
    
    def __str__(self):
        return f'{(self.op)}<{self.type}>({str(self.left)}, {str(self.right)})'
    
    def eval(self):
        a = self.left.eval()
        b = self.right.eval()

        match self.op:
            case 'op_add':
                return a + b
            case 'op_sub':
                return a - b
            case 'op_mul':
                return a * b
            case 'op_div':
                return a / b
            case 'op_join':
                return a + b
            case 'op_bor':
                return a or b
            case 'op_band':
                return a and b
            case 'op_eq':
                return a == b
            case 'op_neq':
                return a != b
            case 'op_lt':
                return a < b
            case 'op_gt':
                return a > b
            case 'op_lte':
                return a <= b
            case 'op_gte':
                return a >= b
            case _:
                raise Exception('unknown opcode ' + self.op)

class UnaryOperator(ExpressionNode):
    def __init__(self, op, type, expr):
        super().__init__()
        self.op = op
        self.type = type
        self.expr = expr
        self._const = expr.is_const()
    
    def __str__(self):
        return f'{(self.op)}<{self.type}>({str(self.expr)})'
    
    def eval(self):
        v = self.expr.eval()

        match self.op:
            case 'op_cast':
                match self.type.type:
                    case ValueType.NUMBER:
                        return float(v)
                    case ValueType.STRING:
                        return str(v)
                    case ValueType.BOOL:
                        return bool(v)
                    case ValueType.POINTER:
                        return int(v)
                    case _:
                        raise Exception("error while evaluating compile-time expression: invalid value type")
            
            case 'op_neg':
                return -v
            case 'op_bnot':
                return not v

class IdentifierOperator(ExpressionNode):
    def __init__(self, op, type, id, data=None):
        super().__init__()
        self.op = op
        self.type = type
        self.id = id
        self.data = data
        self._const = False
        self.can_address = op == 'var_get'
    
    def __str__(self):
        return f'{(self.op)}<{self.type}>(<{self.id}>, {str(self.data)})'
    
    def eval(self):
        raise Exception("cannot evaluate identifier node")

class Function:
    def __init__(self, name, type, params, attribs):
        self.name = name
        self.type = type
        self.parameters = params
        self.definition = None
        self.attributes = attribs

ATTRIBUTES = ['warp']
HAT_EVENTS = {
    'flag': None,
    'keypressed': 'string',
    'clicked': None,
    'backdrop_switched': 'string',
    'loudness_exceeds': 'number',
    'timer_exceeds': 'number',
    'broadcast': 'string',
    'cloned': None
}

COMPARISON_SYMBOLS = ['<', '>', '<=', '>=']
COMPARISON_SYMBOL_NAMES = ['op_lt', 'op_gt', 'op_lte', 'op_gte']

ARITHMETIC_SYMBOLS = ['+', '-', '*', '/']
ARITHMETIC_SYMBOLS_NAMES = ['op_add', 'op_sub', 'op_mul', 'op_div']

ASSIGNMENT_SYMBOLS = ['=', '+=', '-=']

# returns either an op_cast expression or the expression itself,
# if a type isn't necessary.
# also, raises an exception if the cast is not possible.
def type_cast(program, tok_for_err_msg, expr, output_type):
    if output_type.is_same(expr.type):
        return expr

    # throw error if cast is invalid
    if not expr.type.can_cast(output_type):
        raise CompilationException.from_token(tok_for_err_msg, f"could not cast {str(expr.type)} to {str(output_type)}")

    return UnaryOperator('op_cast', output_type, expr)

# assumes the identifier token was popped off, leaving the
# token queue on the opening parenthesis
def parse_function_call(program, tokens, block, id_token):
    tokens.pop() # pop opening parenthesis
    func_name = id_token.value
    is_builtin = func_name in BUILTIN_METHODS    

    if not (func_name in program['functions']):
        if block.get_variable_info(func_name):
            raise CompilationException.from_token(id_token, f"'{func_name}' is not a function")
        elif not is_builtin:
            raise CompilationException.from_token(id_token, f"'{func_name}' is not a defined function")

    if is_builtin:
        func_data = BUILTIN_METHODS[func_name]
    else:
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
            if not arg_expr.type.can_cast_implicit(param_type):
                raise CompilationException.from_token(next_tok, f"could not cast {str(arg_expr.type)} to {str(param_type)} for argument {arg_index}")
            
            func_args.append(type_cast(program, next_tok, arg_expr, param_type))

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
        'builtin': is_builtin,
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

    next_order = order+1

    if order == 0:
        a = parse_expression(program, tokens, block, next_order)
        op_tok = tokens.peek()
        while op_tok.is_symbol('||'):
            tokens.pop()
            b = parse_expression(program, tokens, block, next_order)

            a = type_cast(program, op_tok, a, ValueType(ValueType.BOOL))
            b = type_cast(program, op_tok, b, ValueType(ValueType.BOOL))
            a = BinaryOperator('op_bor', ValueType(ValueType.BOOL), a, b)
            op_tok = tokens.peek()
        return a
    
    elif order == 1:
        a = parse_expression(program, tokens, block, next_order)
        op_tok = tokens.peek()
        while op_tok.is_symbol('&&'):
            tokens.pop()
            b = parse_expression(program, tokens, block, next_order)

            a = type_cast(program, op_tok, a, ValueType(ValueType.BOOL))
            b = type_cast(program, op_tok, b, ValueType(ValueType.BOOL))
            a = BinaryOperator('op_band', ValueType(ValueType.BOOL), a, b)
            op_tok = tokens.peek()
        return a
    
    elif order == 2:
        a = parse_expression(program, tokens, block, next_order)
        op_tok = tokens.peek()
        while op_tok.is_symbol('==') or op_tok.is_symbol('!='):
            tokens.pop()
            b = parse_expression(program, tokens, block, next_order)
            b = type_cast(program, op_tok, b, a.type)

            a = BinaryOperator('op_eq' if op_tok.value == '==' else 'op_neq', ValueType(ValueType.BOOL), a, b)
            op_tok = tokens.peek()
        return a
    
    elif order == 3: # comparison symbols
        a = parse_expression(program, tokens, block, next_order)
        op_tok = tokens.peek()
        while op_tok.type == Token.TYPE_SYMBOL and op_tok.value in COMPARISON_SYMBOLS:
            tokens.pop()
            b = parse_expression(program, tokens, block, next_order)
            b = type_cast(program, op_tok, b, a.type)

            op_name = COMPARISON_SYMBOL_NAMES[COMPARISON_SYMBOLS.index(op_tok.value)]
            a = BinaryOperator(op_name, ValueType(ValueType.BOOL), a, b)
            op_tok = tokens.peek()
        return a

    elif order == 4: # &
        a = parse_expression(program, tokens, block, next_order)
        op_tok = tokens.peek()
        while op_tok.is_symbol('&'):
            tokens.pop()
            b = parse_expression(program, tokens, block, next_order)

            if not (a.type.can_cast_implicit(ValueType.STRING) and b.type.can_cast_implicit(ValueType.STRING)):
                raise CompilationException.from_token(op_tok, "attempt to concatenate " + str(a.type) + " with " + str(b.type))
            
            a = type_cast(program, op_tok, a, ValueType(ValueType.STRING))
            b = type_cast(program, op_tok, b, ValueType(ValueType.STRING))
            a = BinaryOperator('op_join', ValueType(ValueType.STRING), a, b)
            op_tok = tokens.peek()
        
        return a

    elif order == 5: # + -
        a = parse_expression(program, tokens, block, next_order)
        op_tok = tokens.peek()
        while op_tok.is_symbol('+') or op_tok.is_symbol('-'):
            op_name = ARITHMETIC_SYMBOLS_NAMES[ARITHMETIC_SYMBOLS.index(tokens.pop().value)]
            b = parse_expression(program, tokens, block, next_order)

            out_ptr = a.type.is_pointer()
            if not ((out_ptr or a.type.is_a(ValueType.NUMBER)) and b.type.is_a(ValueType.NUMBER)):
                raise CompilationException.from_token(op_tok, "attempt to add " + str(a.type) + " with " + str(b.type))
            
            a = BinaryOperator(op_name, a.type, a, b)
            op_tok = tokens.peek()
        
        return a
    
    elif order == 6: # * /
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

        # parenthesis
        if tok.is_symbol('('):
            tokens.pop()
            expr = parse_expression(program, tokens, block, 0)
            assert(tokens.pop().is_symbol(')'))
            return expr
        
        # unary negation
        elif tok.is_symbol('-'):
            tokens.pop()
            expr = parse_expression(program, tokens, block, order)
            return UnaryOperator('op_neg', expr.type, expr)

        # binary not
        elif tok.is_symbol('!'):
            tokens.pop()
            expr = parse_expression(program, tokens, block, order)
            return UnaryOperator('op_bnot', ValueType(ValueType.BOOL), expr)

        # address of
        elif tok.is_symbol('&'):
            tokens.pop()
            expr = parse_expression(program, tokens, block, order)
            if not expr.can_address:
                raise CompilationException.from_token(tok, "can only take address of lvalue")
            return UnaryOperator('op_addr', ValueType.pointer_to(expr.type), expr)
        
        # indirect
        elif tok.is_symbol('*'):
            tokens.pop()
            expr = parse_expression(program, tokens, block, order)
            if not expr.type.is_pointer():
                raise CompilationException.from_token(tok, "attempt to use indirection on a non-pointer type")
            
            out = UnaryOperator('op_indirect', expr.type.base_type, expr)
            out.can_address = True
            return out
        
        # type cast
        elif tok.type == Token.TYPE_KEYWORD and tok.value in Token.KEYWORD_TYPES:
            output_type = parse_type(program, tokens)

            # get expression inbetween parentheses
            if not tokens.pop().is_symbol('('):
                raise CompilationException.from_token(tok, 'expected (')
            expr = parse_expression(program, tokens, block, 0)
            if not tokens.pop().is_symbol(')'):
                raise CompilationException.from_token(tok, 'expected )')

            return type_cast(program, tok, expr, output_type)
        
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

                if func_data.type.is_a(ValueType.VOID):
                    raise CompilationException.from_token(tok, f"function '{tok.value}' does not return a value")

                if func_call_data['builtin']:
                    return IdentifierOperator('builtin_func_call', func_data.type, tok.value, func_args)
                else:
                    return IdentifierOperator('func_call', func_data.type, tok.value, func_args)
            else:
                # here, a variable is required
                if var_info == None:
                    raise CompilationException.from_token(tok, f"use of undeclared identifier '{(tok.value)}'")
                
                # TODO: multi-indexing
                if id_op.is_symbol('['):
                    tokens.pop()

                    if not var_info['type'].is_pointer() or var_info['type'].base_type.is_a(ValueType.VOID):
                        raise CompilationException.from_token(tok, "cannot take index of a " + str(var_info['type']))
                    
                    index_expr = parse_expression(program, tokens, block)

                    if not index_expr.type.can_cast_implicit(ValueType.NUMBER):
                        raise CompilationException.from_token(id_op, "expected number for index, got a " + str(index_expr.type))

                    if not tokens.peek().is_symbol(']'):
                        raise CompilationException.from_token(tok, "expected ']', got " + str(tokens.peek()))
                    tokens.pop()

                    return IdentifierOperator('op_index', var_info['type'].base_type, tok.value, index_expr);
                    # raise Exception("arrays not yet supported")
            
                # TODO: structs
                elif id_op.is_symbol('.'):
                    raise Exception("struct indexing not yet supported")

                elif id_op.is_symbol('->'):
                    raise Exception("pointer indirection not yet supported")

                else:
                    return IdentifierOperator('var_get', var_info['type'], var_info['name'])
        
        # true and false
        elif tok.is_keyword('true') or tok.is_keyword('false'):
            tokens.pop()
            return ExpressionConstant(tok)    
        
        # strings and numbers
        elif tok.type == Token.TYPE_STRING or tok.type == Token.TYPE_NUMBER:
            tokens.pop()
            return ExpressionConstant(tok)
        
        else:
            raise CompilationException.from_token(tok, 'unexpected ' + str(tok))
    
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

# parses a code branch. can have both a block form and a single-line statement form.
def parse_branch(program, tokens, block, if_block=False):
    if tokens.peek().is_symbol(':'):
        tokens.pop()
        return {
            'branch': parse_statement(program, tokens, block),
            'single': True
        }

    else:
        return {
            'branch': parse_block(program, tokens, block, if_block),
            'single': False
        }

# recursive if/ifelse/elseif branch parsing
def parse_if_branch(program, tokens, block):
    # if/elseif is already popped from the stack

    tok = tokens.peek()
    cond_expr = type_cast(program, tok, parse_expression(program, tokens, block), ValueType(ValueType.BOOL))
    print("EXPR: " + str(cond_expr))
    if_branch = parse_branch(program, tokens, block, True)
    else_branch = None

    block_end = tokens.peek()

    if block_end.is_keyword('else'):
        tokens.pop()
        else_branch = parse_branch(program, tokens, block)
    elif block_end.is_keyword('elseif'):
        tokens.pop()
        else_branch = {
            'branch': parse_if_branch(program, tokens, block),
            'single': True
        }
    elif block_end.is_keyword('end'):
        if not if_branch['single']: tokens.pop()
    elif not if_branch['single']:
        raise CompilationException.from_token(block_end, "unexpected " + str(block_end))
    
    # pop end statement
    
    return {
        'type': 'if',
        'cond': cond_expr,
        'branch': if_branch,
        'else_branch': else_branch
    }

def parse_assignment(program, tokens, block, id_tok, var_type):
    next_tok = tokens.peek()

    # index assignment
    if next_tok.is_symbol('['):
        tokens.pop()

        if not var_type.is_pointer() or var_type.base_type.is_a(ValueType.VOID):
            raise CompilationException.from_token(next_tok, "cannot take index of a " + str(var_type))

        index_expr = parse_expression(program, tokens, block)

        if not index_expr.type.can_cast_implicit(ValueType.NUMBER):
            raise CompilationException.from_token(next_tok, "expected number for index, got a " + str(index_expr.type))

        if not tokens.peek().is_symbol(']'):
            raise CompilationException.from_token(tokens.peek(), "expected ']', got " + tokens.peek())
        tokens.pop()

        next_tok = tokens.peek()
        if not (next_tok.type == Token.TYPE_SYMBOL and next_tok.value in ASSIGNMENT_SYMBOLS):
            raise CompilationException.from_token(next_tok, "invalid statement")

        return {
            'type': 'index',
            'index': index_expr,
            'assignment': parse_assignment(program, tokens, block, next_tok, var_type.base_type)
        }
    
    elif next_tok.type == Token.TYPE_SYMBOL and next_tok.value in ASSIGNMENT_SYMBOLS:
        # pop equals sign
        tokens.pop()

        # read expression
        expr = parse_expression(program, tokens, block)
        
        assign_type = 'set'
        statement_value = expr

        if next_tok.is_symbol('+='):
            assign_type = 'inc'
        elif next_tok.is_symbol('-='):
            assign_type = 'inc'
            statement_value = UnaryOperator('op_neg', expr.type, expr)

        # type check
        if not (assign_type == 'inc' and var_type.is_pointer() and expr.type.can_cast_implicit(ValueType.NUMBER)) \
        and not expr.type.is_same(var_type):
            raise CompilationException.from_token(id_tok, f"attempt to assign a {str(expr.type)} to a {str(var_type)}")
        
        return {
            'type': assign_type,
            'value': statement_value
        }
    
    else:
        raise CompilationException.from_token(id_tok, "invalid assignment")

def parse_statement(program, tokens, block):
    tok = tokens.pop()
    
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
        
        return statement
    
    elif tok.is_keyword('deleteclone'):
        return {
            'type': 'deleteclone'
        }
    
    elif tok.is_keyword('var'):
        var_name = tokens.pop().get_identifier()

        # two valid forms: one with a specified type and one without
        if tokens.peek().is_symbol(':'):
            tokens.pop()
            var_type = parse_type(program, tokens)
        else:
            var_type = None

        # variable declaration + assignment in one line
        tok = tokens.peek()
        if tok.is_symbol('='):
            tokens.pop()
            expr = parse_expression(program, tokens, block)

            # if no type was specified, use type inference
            if not var_type:
                var_type = expr.type
            
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
        return statement

    elif tok.is_keyword('if'):
        return parse_if_branch(program, tokens, block)
    
    elif tok.is_keyword('while'):
        cond_expr = type_cast(program, tok, parse_expression(program, tokens, block), ValueType(ValueType.BOOL))
        branch = parse_branch(program, tokens, block)

        # while true loops get converted to forever loops
        if cond_expr.is_const() and cond_expr.eval() == True:
            return {
                'type': 'forever',
                'branch': branch
            }
        else:
            return {
                'type': 'while',
                'cond': cond_expr,
                'branch': branch
            }
    
    elif tok.is_keyword('repeat'):
        count_expr = type_cast(program, tok, parse_expression(program, tokens, block), ValueType(ValueType.NUMBER))
        branch = parse_branch(program, tokens, block)

        return {
            'type': 'repeat',
            'count': count_expr,
            'branch': branch
        }
    
    elif tok.is_keyword('forever'):
        branch = parse_branch(program, tokens, block)

        return {
            'type': 'forever',
            'branch': branch
        }
    
    # since there is no expression-as-statement functionality (partly due to the lack of semicolons)
    # function call and variable assignment statements have to be specifically programmed
    elif tok.type == Token.TYPE_IDENTIFIER:
        next_tok = tokens.peek()

        var_name = tok.get_identifier()
        var_info = block.get_variable_info(var_name)

        if not var_info and not var_name in program['functions'] and not var_name in BUILTIN_METHODS:
            raise CompilationException.from_token(tok, f"use of undeclared identifier '{var_name}'")
        
        # function name
        if not var_info:
            func_call_data = parse_function_call(program, tokens, block, tok)

            return {
                'type': 'builtin_func_call' if func_call_data['builtin'] else 'func_call',
                'func_name': func_call_data['function'].name,
                'args': func_call_data['args']
            }

        # variable assignment
        else:
            return {
                'type': 'var_assign',
                'var_name': var_name,
                'assignment': parse_assignment(program, tokens, block, tok, var_info['type'])
            }
            
    
    else:
        raise CompilationException.from_token(tok, "unexpected " + str(tok))

# if_block is only set to true for if block processing
# if true, it will take "else" or "elseif" as the end of a block,
# and also not pop it off the stack for inspection by the caller.
def parse_block(program, tokens, parent_block=None, if_block=False):
    block = Block(parent_block)
    does_return = False

    while True:
        tok = tokens.peek()

        if tok.is_keyword('end') or (if_block and (tok.is_keyword('else') or tok.is_keyword('elseif'))):
            if not if_block: tokens.pop()

            if block.top_level:
                if not block.return_type.is_void() and not does_return:
                    raise CompilationException.from_token(tok, "not all code paths return a value")
                
                if not does_return:
                    block.statements.append({
                        'type': 'return',
                        'value': None
                    })

            break
        
        else:
            statement = parse_statement(program, tokens, block)

            if not does_return:
                block.statements.append(statement)

            if statement['type'] == 'return' or statement['type'] == 'forever' or statement['type'] == 'deleteclone':
                does_return = True

    return block

def parse_function(program, tokens, function):
    func_block = Block()
    func_block.return_type = function.type
    func_block.top_level = True

    for param in function.parameters:
        func_block.declare_parameter(param['name'], param['type'])
    
    function.definition = parse_block(program, tokens, func_block)

def parse_program(tokens, project_dir_path):
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
            asset_path = os.path.normpath(os.path.join(project_dir_path, asset_name.value))

            asset_path = asset_path.replace('\\', '/') # bruh
            program['costumes'].append(asset_path)
        
        # sounds
        # syntax similar to costumes
        elif tok.is_keyword('sound'):
            if attributes:
                raise CompilationException.from_token(tok, "sound declaration does not take attributes")
            
            asset_name = tokens.pop()
            assert(asset_name.type == Token.TYPE_STRING)
            asset_path = os.path.normpath(os.path.join(project_dir_path, asset_name.value))

            asset_path = asset_path.replace('\\', '/') # bruh
            program['sounds'].append(asset_path)
        
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
            program['functions'][func_name] = Function(func_name, func_type, func_params, attributes[:])
            parse_function(program, tokens, program['functions'][func_name])

            attributes.clear()
        
        # event handler
        elif tok.is_keyword('when'):
            tok = tokens.pop()
            event_name = tok.get_identifier()
            if not event_name in HAT_EVENTS:
                raise CompilationException.from_token(tok, f"invalid event '{event_name}'")
            
            event_param_type = HAT_EVENTS[event_name]
            event_param = None

            # read event parameter
            if event_param_type != None:
                if not tokens.pop().is_symbol('('):
                    raise CompilationException.from_token(tok, f"event '{event_name}' needs parameters")

                # get event parameter expression, and make sure it's a compile-time constant
                # and that it is the required type
                param_expr = parse_expression(program, tokens, None)
                if not param_expr.is_const():
                    raise CompilationException.from_token(tok, f"event parameter must be a constant expression")
                
                if not param_expr.type.is_same(ValueType.from_string(event_param_type)):
                    raise CompilationException.from_token(tok, f"expected {event_param_type} for event parameter, got {str(param_expr.type)}")
                
                event_param = param_expr.eval()

                if not tokens.peek().is_symbol(')'):
                    raise CompilationException.from_token(tokens.peek(), f"expected ')'")
                tokens.pop()
            
            parent_block = Block()
            parent_block.return_type = ValueType(ValueType.VOID)

            program['events'].append({
                'event_name': event_name,
                'event_param': event_param,
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