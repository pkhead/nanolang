# Goboscript generator
from lexer import Token
from astgen import ValueType, BinaryOperator

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

def generate_expression(ctx, expr):
    if expr.op == 'const':
        ctx.sprite_ctx.file.write(macro_stack_push(gs_literal(expr.value)))

    elif isinstance(expr, BinaryOperator):
        generate_expression(ctx, expr.left)
        generate_expression(ctx, expr.right)
        file = ctx.sprite_ctx.file

        if expr.op == 'op_add':
            file.write('temp = ' + macro_stack_read(1) + ' + ' + macro_stack_read(0) + ';\n')
            file.write(macro_stack_pop(2))
            file.write(macro_stack_push('temp'))

        elif expr.op == 'op_sub':
            file.write('temp = ' + macro_stack_read(1) + ' - ' + macro_stack_read(0) + ';\n')
            file.write(macro_stack_pop(2))
            file.write(macro_stack_push('temp'))
        
        elif expr.op == 'op_mul':
            file.write('temp = ' + macro_stack_read(1) + ' * ' + macro_stack_read(0) + ';\n')
            file.write(macro_stack_pop(2))
            file.write(macro_stack_push('temp'))
        
        elif expr.op == 'op_div':
            file.write('temp = ' + macro_stack_read(1) + ' / ' + macro_stack_read(0) + ';\n')
            file.write(macro_stack_pop(2))
            file.write(macro_stack_push('temp'))
        
        else:
            raise Exception('unknown opcode ' + expr.op)
    
    else:
        raise Exception('unknown opcode ' + expr.op)

# assumes that there is a argument named stack_id
def generate_block(ctx, block):
    file = ctx.sprite_ctx.file

    # parse statement
    scope_size = 0
    declared_variables = []

    for statement in block.statements:
        if statement['type'] == 'var_declare':
            var_name = statement['var_name']
            declared_variables.append(var_name)
            ctx.new_variable(var_name, 1)
            scope_size += 1

            file.write(f'# {var_name} declaration \n')

            if statement['init'] != None:
                generate_expression(ctx, statement['init'])
            else:
                file.write(macro_stack_push('\"\"'))        

    # end of function
    for var_name in declared_variables:
        ctx.remove_variable(var_name)
    
    file.write(macro_stack_pop(scope_size))
    
# assumes that there is a argument named stack_id
def generate_procedure(func_ctx, definition):
    generate_block(func_ctx, definition)

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