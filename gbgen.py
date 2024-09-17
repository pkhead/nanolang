# Goboscript generator
from lexer import Token
from astgen import ValueType, BinaryOperator
import re

# == STACK MECHANISM ==
# nano will use a stack to store the values of variables.
# each stack frame corresponds to a single function call.
#
# there can be multiple stacks allocated simultaneously, since
# scratch is "multithreaded", so each custom block generated from
# a function has an added first argument named "stack_id". this is
# the id of the stack the custom block will be using.
#
# the list stack_ptrs stores the pointers to the beginning of each stack.
# the list stack_heads stores the pointers to the head of each stack.
#
# the first item of each stack (aka the item directly at a stack's stack_ptr)
# is a special value. it represents the pointer to the start of a current stack frame.
# functionally inspired by the usage of the EBP register on x86 architecture.
#
# == STACK FRAMES ==
# one stack frame stores the data for a single function call.
# 
# item 0 of each stack frame is the base of the previous stack frame,
# followed by values of declared variables,
# then finally followed by any temporary stack frame.
#
# -- Return values --
# return values are handled by first allocating some memory by the caller
# that's equivalent to the size of the returned value. (changing the stack ptr)
# then, when the callee wants to return the value, it sets the data starting from the address
# at the pointer of its stack base minus the size of the returned value, thus matching up with
# the space allocated by the caller before the function call. then, the stack frame of the callee gets cleaned up.
# by the callee.
#
# -- Function arguments --
# function arguments are passed to called functions by pushing values to the stack before the
# return value allocation. arguments will then be accessed by the caller from negative offsets of its
# stack base.

# user function prefix: "_"
# internal function prefix: "internal_"

def gs_literal(value):
    if isinstance(value, str):
        out = ['"']
        
        for c in value:
            if c == '"':
                out.append('\\"')
            elif c == '\n':
                out.append('\\n')
            elif c == '\t':
                out.append('\\t')
            elif c == '\r':
                out.append('\\r')
            else:
                out.append(c)
        
        out.append('"')
        return ''.join(out)
    
    else:
        return str(value)

def generate_block(program, file, block):
    file.write("# " + str(block) + "\n")

program_boilerplate = """
onflag {
    delete memory;
    delete stack_ptrs;
    delete stack_heads;
}

proc internal_alloc_stack {
    local i = 1;
    stack_pos = 0;

    repeat length stack_ptrs + 1 {
        if stack_ptrs[i] == "" {
            stack_pos = (i-1) * 1024 + 1;

            if i == length stack_ptrs + 1 {
                add stack_pos to stack_ptrs;
                add stack_pos to stack_heads;
            } else {
                stack_ptrs[i] = stack_pos;
                stack_heads[i] = stack_pos;
            }

            until length memory >= stack_pos + 1023 {
                add "uninit" to memory;
            }

            # this will be the pointer to the start of a stack frame
            memory[stack_pos] = stack_pos + 1;
            stack_heads[i] = stack_pos;

            init_stack_ret = i;
            stop_this_script;
        }

        i += 1;
    }

    init_stack_ret = "error";
}

# macro get_from_stack_base!(stack_id, offset) -> memory[memory[stack_ptrs[stack_id!]] + offset!];
# macro change_stack_base!(stack_id, delta) -> memory[stack_ptrs[stack_id!]] = memory[stack_ptrs[stack_id!]] + delta;
# 
# macro stack_push! stack_id, value {
#     stack_heads[stack_id!] = stack_heads[stack_id!] + 1;
#     memory[stack_heads[stack_id!]] = value!;
# }
# 
# macro stack_pop! stack_id {
#     stack_heads[stack_id!] = stack_heads[stack_id!] - 1;
# }
# 
# macro stack_pop_num! stack_id, num {
#     stack_heads[stack_id!] = stack_heads[stack_id!] - num!;
# }
"""

# for some reason goboscript macros crashed?
# this is probably the worst software i've decided to work with.
# so i've just decided to make functions to inject them manually.

# offset 0 should always be the base of the previous stack frame
def macro_get_from_stack_base(offset):
    return f"memory[memory[stack_ptrs[$stack_id]] + ({offset})]"

def macro_change_stack_base(delta):
    return f"memory[stack_ptrs[$stack_id]] = memory[stack_ptrs[$stack_id]] + ({delta})"

def macro_stack_push(value):
    return f"stack_heads[$stack_id] = stack_heads[$stack_id] + 1;\n" + \
           f"memory[stack_heads[$stack_id]] = {value};\n"

def macro_stack_pop(num):
    return f"stack_heads[$stack_id] = stack_heads[$stack_id] - ({num});\n"

def macro_stack_read(offset):
    return f"memory[stack_heads[$stack_id] - ({offset})]"

class SpriteContext:
    def __init__(self, program, file):
        self.program = program
        self.file = file
        self.function_block_names = {}

class FunctionContext:
    def __init__(self, sprite_ctx):
        self.sprite_ctx = sprite_ctx
        self.nowarp = False
        self.does_return = False
        self.active_variables = []
        self._offset = 0

    def new_variable(self, var_name, size):
        assert(size > 0)
        self.active_variables.insert(0, {
            'name': var_name,
            'size': size,
            'offset': self._offset
        })
        self._offset += size
    
    def remove_variable(self, var_name):
        for v in self.active_variables:
            if v['name'] == var_name:
                self._offset -= v['size']
                del v
                return
        
        raise Exception('could not find variable ' + var_name)
    
    def get_variable_offset(self, var_name):
        for v in self.active_variables:
            if v['name'] == var_name:
                return v['offset']

class ExpressionStack:
    def __init__(self):
        self.stack_size = 0

    def push(self):
        v = self.stack_size
        self.stack_size += 1
        return v
    
    def clear(self, file):
        if self.stack_size > 0:
            file.write(macro_stack_pop(self.stack_size) + '\n')
    
    def _re_replace(self, m):
        return macro_stack_read(self.stack_size - int(m.group(1)))
    
    def finalize_stack_references(self, v):
        return re.sub(r'@<(\d+)>', self._re_replace, v)

def generate_func_call(ctx, func_data):
    file = ctx.sprite_ctx.file
    func_return_type = func_data.type

    # allocate space for return value, if needed
    if not func_return_type.is_a(ValueType.VOID):
        file.write(f"stack_heads[$stack_id] = stack_heads[$stack_id] + {gs_literal(func_return_type.size())};\n")
    
    # proc call
    file.write(ctx.sprite_ctx.function_block_names[func_data.name] + ' $stack_id;\n')

def generate_expression(ctx, expr, stack):
    if expr.op == 'const':
        return gs_literal(expr.value)

    elif expr.op == 'var_get':
        return macro_get_from_stack_base(ctx.get_variable_offset(expr.id) + 1)
    
    elif expr.op == 'func_call':
        generate_func_call(ctx, ctx.sprite_ctx.program['functions'][expr.id])
        return "@<" + str(stack.push()) + ">"

    elif isinstance(expr, BinaryOperator):
        val_a = generate_expression(ctx, expr.left, stack)
        val_b = generate_expression(ctx, expr.right, stack)

        if expr.op == 'op_add':
            return f"({val_a} + {val_b})"

        elif expr.op == 'op_sub':
            return f"({val_a} - {val_b})"
        
        elif expr.op == 'op_mul':
            return f"({val_a} * {val_b})"
        
        elif expr.op == 'op_div':
            return f"({val_a} / {val_b})"
        
        else:
            raise Exception('unknown opcode ' + expr.op)
    
    else:
        raise Exception('unknown opcode ' + expr.op)

# assumes that there is a argument named stack_id
def generate_block(ctx, block):
    file = ctx.sprite_ctx.file

    file.write("# block start\n")

    # parse statement
    scope_size = 0
    declared_variables = []

    for statement in block.statements:
        # opcode var_declare
        if statement['type'] == 'var_declare':
            var_name = statement['var_name']
            declared_variables.append(var_name)
            ctx.new_variable(var_name, 1)
            scope_size += 1

            file.write(f'# {var_name} declaration \n')

            if statement['init'] != None:
                expr_stack = ExpressionStack()
                expr = expr_stack.finalize_stack_references(generate_expression(ctx, statement['init'], expr_stack))

                if expr_stack.stack_size > 0:
                    file.write(f"temp = {expr};\n")
                    expr_stack.clear(file)
                    file.write(macro_stack_push("temp") + "\n")
                else:
                    file.write(macro_stack_push(expr) + "\n")
            else:
                file.write(macro_stack_push('\"\"'))
        
        # opcode func_call
        elif statement['type'] == 'func_call':
            func_data = ctx.sprite_ctx.program['functions'][statement['func_name']]
            generate_func_call(ctx, func_data)

            # drop return value if it exists
            if not func_data.type.is_a(ValueType.VOID):
                file.write(macro_stack_pop(gs_literal(func_data.type.size())))

    # end of function
    if declared_variables:
        for var_name in declared_variables:
            ctx.remove_variable(var_name)
        
        file.write(macro_stack_pop(scope_size))
    
    file.write("# block end\n")
    
# assumes that there is a argument named stack_id
def generate_procedure(func_ctx, definition):
    file = func_ctx.sprite_ctx.file

    # stack frame enter
    file.write("# stack frame enter\n")
    file.write(macro_stack_push("memory[stack_ptrs[$stack_id]]")) # push old frame body
    file.write("memory[stack_ptrs[$stack_id]] = stack_heads[$stack_id];\n") # set current frame body to stack head

    file.write("# function definition follows\n")
    generate_block(func_ctx, definition)

    # stack frame end
    file.write("\n# stack frame end\n")
    file.write("temp = " + macro_get_from_stack_base(0) + ";\n")
    file.write(macro_stack_pop(1) + "\n") # pop base of current stack frame
    file.write("memory[stack_ptrs[$stack_id]] = temp;\n") # restore base of old stack frame

def generate_program(program, file):
    sprite_ctx = SpriteContext(program, file)

    for costume_name in program['costumes']:
        file.write(f"costumes {gs_literal(costume_name)};\n")
    
    for costume_name in program['sounds']:
        file.write(f"sounds {gs_literal(costume_name)};\n")
    
    file.write(program_boilerplate + "\n")

    for func in program['functions'].values():
        func_ctx = FunctionContext(sprite_ctx)
        func_ctx.nowarp = 'nowarp' in func.attributes
        func_ctx.does_return = not func.type.is_a(ValueType.VOID)

        block_name = "_" + func.name
        sprite_ctx.function_block_names[func.name] = block_name
        
        if func_ctx.nowarp:
            file.write("nowarp ")
        file.write(f"proc {block_name} stack_id")
        file.write(" {\n")

        generate_procedure(func_ctx, func.definition)
        file.write("}\n")
    
    event_id = 0
    for event_handler in program['events']:
        func_ctx = FunctionContext(sprite_ctx)
        func_ctx.nowarp = 'nowarp' in event_handler['attributes']
        func_ctx.does_return = False

        block_name = "event" + str(event_id)

        if 'nowarp' in event_handler['attributes']:
            file.write("nowarp ")
        
        file.write(f"proc {block_name} stack_id {{\n")
        generate_procedure(func_ctx, event_handler['definition'])
        file.write("stack_ptrs[$stack_id] = \"\";\n}\n")
        event_id += 1

        event_name = event_handler['event_name']
        
        if event_name == 'flag':
            file.write("onflag")
        elif event_name == 'keypress':
            raise Exception("unimplemented")
        else:
            raise Exception(f"internal: invalid event {event_name}")
        
        file.write(" {\ninternal_alloc_stack;\n" + block_name + " init_stack_ret;\n}\n")

# sample main.gs
"""
costumes "alien-in-suit.png";

proc alloc_stack {
    local i = 1;
    stack_pos = 0;

    repeat length stack_info + 1 {
        if stack_info[i] == "" {
            stack_pos = (i-1) * 1024 + 1;

            if i == length stack_info + 1 {
                add stack_pos to stack_info;
            } else {
                stack_info[i] = stack_pos;
            }

            until length memory >= stack_pos + 1023 {
                add "" to memory;
            }

            init_stack_ret = i;
            stop_this_script;
        }

        i += 1;
    }
    

    stack_pos = (i-1) * 1024 + 1;
    stack_info[i] = stack_pos;

    until length memory >= stack_pos {
        add "" to memory;
    }

    init_stack_ret = i;
}

nowarp proc _main own_stack, stack_id {
    if $own_stack != 0 {
        stack_info[$stack_id] = "";
    }
}

onflag {
    delete memory;
    delete stack_ptrs;

    alloc_stack;
    _main 0, init_stack_ret;
    wait 1;
    alloc_stack;
    _main 1, init_stack_ret;
    wait 1;
    alloc_stack;
    _main 1, init_stack_ret;
}
"""