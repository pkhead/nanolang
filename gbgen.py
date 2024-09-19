# Goboscript generator
import re
from lexer import Token
from compilertypes import ValueType
from astgen import BinaryOperator
from builtin_methods import BUILTIN_METHODS

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
# at the pointer of its stack base, minus the total size of function arguments, minus the size of the returned value,
# thus matching up with the space allocated by the caller before the function call.
#
# -- Function arguments --
# function arguments are passed to called functions by pushing values to the stack after the
# return value allocation. arguments will then be accessed by the caller from negative offsets of its
# stack base. arguments will be cleaned up by the caller.

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
    
    elif value == True:
        return "1"
    
    elif value == False:
        return "0"
    
    else:
        return str(value)

stage_boilerplate = """
proc nano_init {
    delete memory;
    delete stack_ptrs;
    delete stack_heads;

    repeat 2048 {
        add "" to memory;
    }

    memory[1] = 0;
    memory[2] = 0;
    memory[3] = 0;
}

onflag {
    nano_init;
    broadcast "nanoinit"; # initialize sprite variables and such
    broadcast "nanostart";
}
"""
program_boilerplate = """
# struct alloc_cell {
#   next: alloc_cell*,
#   prev: alloc_cell*,
#   size: int
# }

# find a free block of memory
proc nano_malloc size {
    cell_ptr = 1;
    prev_cell_ptr = 0;
    new_cell_ptr = 0;
    memory_skipped = 0;

    if $size <= 0 {
        nano_malloc_return = 0;
        stop_this_script;
    }
    
    until memory[cell_ptr] == 0 or memory_skipped > $size {
        memory_skipped = memory[cell_ptr] - cell_ptr - memory[cell_ptr + 2] - 3;
        prev_cell_ptr = cell_ptr;
        cell_ptr = memory[cell_ptr];
    }

    if cell_ptr == 1 {
        DEBUG_malloc_cond = "first alloc";
        # condition for first allocation
        prev_cell_ptr = 1;
        new_cell_ptr = 4;
        cell_ptr = 0;
    
    } elif $size <= memory_skipped {
        DEBUG_malloc_cond = "found free . memskip: " & memory_skipped;
        # condition when found free memory inbetween two allocations
        new_cell_ptr = prev_cell_ptr + memory[prev_cell_ptr + 2] + 3;
    
    } else {
        DEBUG_malloc_cond = "last alloc";
        # condition when reached last allocation
        new_cell_ptr = cell_ptr + memory[cell_ptr + 2] + 3;
        prev_cell_ptr = cell_ptr;
        cell_ptr = 0;
    }

    # prev_cell_ptr = cell to left of free memory
    # cell_ptr = cell to right of free memory

    # ensure that the list is long enough to store the allocation
    until length memory > new_cell_ptr + 3 + $size {
        add "" to memory;
    }

    # if (prev_cell != NULL) prev_cell->next = new_cell;
    if prev_cell_ptr != 0 {
        memory[prev_cell_ptr] = new_cell_ptr;
    }

    # if (next_cell != NULL) next_cell->prev = new_cell;
    if cell_ptr != 0 {
        memory[cell_ptr + 1] = new_cell_ptr;
    }

    memory[new_cell_ptr] = cell_ptr;
    memory[new_cell_ptr + 1] = prev_cell_ptr;
    memory[new_cell_ptr + 2] = $size;

    nano_malloc_return = new_cell_ptr + 3;
}

proc nano_free ptr {
    if $ptr > 0 {
        cell_ptr = $ptr - 3;

        # cell->prev.next = cell->next;
        # if (cell->next != NULL) cell->next.prev = cell->prev;
        memory[memory[cell_ptr + 1]] = memory[cell_ptr];
        if memory[cell_ptr] != 0 {
            memory[memory[cell_ptr] + 1] = memory[cell_ptr + 1];
        }

        memory[cell_ptr] = 0;
        memory[cell_ptr + 1] = 0;
        memory[cell_ptr + 2] = 0;
    }
}

proc nano_alloc_stack {
    local i = 1;
    stack_pos = 0;
    init_stack_ret = "error";

    repeat length stack_ptrs + 1 {
        if stack_ptrs[i] == "" {
            nano_malloc 512;
            stack_pos = nano_malloc_return;

            if i > length stack_ptrs {
                add stack_pos to stack_ptrs;
                add stack_pos to stack_heads;
            } else {
                stack_ptrs[i] = stack_pos;
                stack_heads[i] = stack_pos;
            }

            # this will be the pointer to the start of a stack frame
            memory[stack_pos] = stack_pos + 1;
            stack_heads[i] = stack_pos;

            init_stack_ret = i;
            stop_this_script;
        }

        i += 1;
    }
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

def macro_set_from_stack_base(offset, value):
    return f"memory[memory[stack_ptrs[$stack_id]] + ({offset})] = {value};"

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
        self.static_variables = {}
        self._next_id = 0
        self.staticalloc = "nano_staticalloc" # name of staticalloc variable - different for stage
    
    def new_var_id(self):
        id = self._next_id
        self._next_id = self._next_id + 1
        return "_" + str(id)


class FunctionContext:
    class Tempvar:
        def __init__(self, size, offset):
            self.size = size
            self.offset = offset
    
    def __init__(self, sprite_ctx, paramlist, return_type):
        self.sprite_ctx = sprite_ctx
        self.warp = False
        self.does_return = False
        self.active_variables = []
        self.active_tempvars = []
        self.recursive = False
        self._offset = 0
        
        # arguments
        argoffset = 0
        self.arguments = []

        for param in reversed(paramlist):
            argoffset -= param['type'].size()
            self.arguments.insert(0, {
                'name': param['name'],
                'size': param['type'].size(),
                'offset': argoffset,
                'id': None
            })
        
        # calculate return value location
        if not return_type.is_void():
            self.return_offset = argoffset - return_type.size()
        else:
            self.return_offset = 0

    def new_variable(self, var_name, size, nostack=False):
        assert(size > 0)

        if nostack:
            assert(size == 1)

            self.active_variables.insert(0, {
                'name': var_name,
                'size': size,
                'offset': None,
                'id': self.sprite_ctx.new_var_id() + "_" + var_name
            })
        else:
            self.active_variables.insert(0, {
                'name': var_name,
                'size': size,
                'offset': self._offset,
                'id': None
            })
            self._offset += size
    
    # non-temporal location on the stack unassociated
    # with a variable
    def new_tempvar(self, size):
        assert(size > 0)
        tempvar = FunctionContext.Tempvar(size, self._offset + 1) # add one to account for the internal data at item 0 of each stack base
        self._offset += size
        self.active_tempvars.append(tempvar)

        return tempvar
    
    def remove_tempvar(self, tempvar):
        if not tempvar in self.active_tempvars:
            raise Exception('could not find tempvar ' + str(tempvar))
        
        self.active_tempvars.remove(tempvar)
        self._offset -= tempvar.size
    
    def remove_variable(self, var_name):
        for i in range(len(self.active_variables)):
            v = self.active_variables[i]

            if v['name'] == var_name:
                if v['offset'] != None:
                    self._offset -= v['size']
                
                del self.active_variables[i]
                return
        
        raise Exception('could not find variable ' + var_name)
    
    ## Get offset of variable on stack.
    def get_variable_location(self, var_name):
        for v in self.active_variables:
            if v['name'] == var_name:
                # add one to account for the internal data at item 0 of each stack base
                return "(memory[stack_ptrs[$stack_id]] + " + str(v['offset'] + 1) + ")"
        
        for v in self.arguments:
            if v['name'] == var_name:
                return "(memory[stack_ptrs[$stack_id]] + " + str(v['offset']) + ")"
        
        for v in self.sprite_ctx.static_variables.values():
            if v['name'] == var_name:
                return v['location']
    
    ## Get offset of variable optimized to not be on the stack.
    def get_variable_id(self, var_name):
        for v in self.active_variables:
            if v['name'] == var_name:
                return v['id']
        
        for v in self.arguments:
            if v['name'] == var_name:
                return v['id']
        
        for v in self.sprite_ctx.static_variables.values():
            if v['name'] == var_name:
                return v['id']

class Scope:
    def __init__(self):
        self.declared_variables = []
        self.size = 0
    
    def register_variable(self, var_name, var_size, nostack):
        self.declared_variables.append(var_name)
        
        if not nostack:
            self.size += var_size

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
        return macro_stack_read(self.stack_size - int(m.group(1)) - 1)
    
    def finalize_stack_references(self, v):
        return re.sub(r'@<(\d+)>', self._re_replace, v)

class ExpressionLvalue:
    def __init__(self, memloc):
        self.value = f"memory[{memloc}]"
        self.memloc = memloc
    
    def __str__(self):
        return str(self.value)

def generate_func_call(ctx, func_data, func_args):
    file = ctx.sprite_ctx.file
    func_return_type = func_data.type

    # allocate space for return value, if needed
    if not func_return_type.is_void():
        file.write(f"stack_heads[$stack_id] = stack_heads[$stack_id] + {gs_literal(func_return_type.size())};\n")
    
    # parse arguments
    total_arg_size = 0
    for arg in func_args:
        total_arg_size += arg.type.size()
        push_expression_result(ctx, arg)
    
    # proc call
    file.write(ctx.sprite_ctx.function_block_names[func_data.name] + ' $stack_id;\n')

    # clean up arguments
    if total_arg_size > 0:
        file.write(macro_stack_pop(total_arg_size) + "\n")
    
    # leaves return value on the stack

def generate_expression(ctx, expr, stack, prefer_lvalue=False):
    if expr.op == 'const':
        return gs_literal(expr.value)

    elif expr.op == 'var_get':
        var_id = ctx.get_variable_id(expr.id)

        if var_id != None:
            return var_id
        else:
            memloc = ctx.get_variable_location(expr.id)
            return ExpressionLvalue(memloc) if prefer_lvalue else ExpressionLvalue(memloc).value
    
    elif expr.op == 'func_call':
        generate_func_call(ctx, ctx.sprite_ctx.program['functions'][expr.id], expr.data)
        return "@<" + str(stack.push()) + ">"

    elif expr.op == 'builtin_func_call':
        func_data = BUILTIN_METHODS[expr.id]

        expr_stack = ExpressionStack()
        arg_exprs = []
        
        for arg in expr.data:
            arg_exprs.append(generate_expression(ctx, arg, expr_stack))
        
        file = ctx.sprite_ctx.file
        out_expr = func_data.generate([expr_stack.finalize_stack_references(x) for x in arg_exprs])

        if func_data.generate_return != None:
            file.write(out_expr + '\n')
            expr_stack.clear(file)
            file.write(macro_stack_push(func_data.generate_return()) + '\n')
            return "@<" + str(stack.push()) + ">"
        else:
            expr_stack.clear(file)
            return out_expr
    
    elif expr.op == 'op_cast':
        value = generate_expression(ctx, expr.expr, stack)

        if expr.type.is_a(ValueType.STRING):
            return f"(({value}) & \"\")"
        else:
            return f"(({value}) + 0)"
    
    elif expr.op == 'op_neg':
        value = generate_expression(ctx, expr.expr, stack)
        return f"-({value})"
    
    elif expr.op == 'op_bnot':
        value = generate_expression(ctx, expr.expr, stack)
        return f"({value} == 0)" # for some reason, not (expr) breaks project and !(expr) doesn't emit a not statement.

    elif expr.op == 'op_addr':
        subexpr = generate_expression(ctx, expr.expr, stack, prefer_lvalue=True)
        if not isinstance(subexpr, ExpressionLvalue):
            raise Exception("op_addr error")
        
        return subexpr.memloc
    
    elif expr.op == 'op_indirect':
        memloc = generate_expression(ctx, expr.expr, stack)
        return ExpressionLvalue(memloc) if prefer_lvalue else ExpressionLvalue(memloc).value

    elif expr.op == 'op_index':
        value = generate_expression(ctx, expr.data, stack)

        var_id = ctx.get_variable_id(expr.id)
        if var_id != None:
            var_value = var_id
        else:
            var_value = f"memory[{(ctx.get_variable_location(expr.id))}]"
        
        return f"memory[{var_value} + {value}]"

    elif isinstance(expr, BinaryOperator):
        val_a = generate_expression(ctx, expr.left, stack)
        val_b = generate_expression(ctx, expr.right, stack)

        match expr.op:
            case 'op_add':
                return f"({val_a} + {val_b})"
            case 'op_sub':
                return f"({val_a} - {val_b})"
            case 'op_mul':
                return f"({val_a} * {val_b})"
            case 'op_div':
                return f"({val_a} / {val_b})"  
            case 'op_join':
                return f"({val_a} & {val_b})"
            case 'op_bor':
                return f"({val_a} or {val_b})"
            case 'op_band':
                return f"({val_a} and {val_b})"
            case 'op_eq':
                return f"({val_a} == {val_b})"
            case 'op_neq':
                return f"({val_a} != {val_b})"
            case 'op_lt':
                return f"({val_a} < {val_b})"
            case 'op_gt':
                return f"({val_a} > {val_b})"
            case 'op_lte':
                return f"({val_a} <= {val_b})"
            case 'op_gte':
                return f"({val_a} >= {val_b})"
            case _:
                raise Exception('unknown opcode ' + expr.op)
    
    else:
        raise Exception('unknown opcode ' + expr.op)

def push_expression_result(ctx, expr, to_temp=False):
    file = ctx.sprite_ctx.file

    expr_stack = ExpressionStack()
    expr = expr_stack.finalize_stack_references(generate_expression(ctx, expr, expr_stack))

    # set variable to expression result and clear
    # values added to the stack by the expression (if present)
    if expr_stack.stack_size > 0:
        file.write(f"temp = {expr};\n")
        expr_stack.clear(file)

        if not to_temp:
            file.write(macro_stack_push("temp") + "\n")
    else:
        if to_temp:
            file.write(f"temp = {expr};\n")
        else:
            file.write(macro_stack_push(expr) + "\n")

def generate_branch(ctx, scope, branch):
    if branch['single']: generate_statement(ctx, branch['branch'], scope)
    else: generate_block(ctx, branch['branch'])

def get_assignment_location(ctx, loc, expr_stack, assignment):
    if assignment['type'] == 'set' or assignment['type'] == 'inc':
        return [loc, assignment['type'], assignment['value']]
    
    elif assignment['type'] == 'index':
        expr = generate_expression(ctx, assignment['index'], expr_stack)
        res = get_assignment_location(ctx, f"(memory[{loc}] + {expr})", expr_stack, assignment['assignment'])
        return res
    else:
        raise Exception("unknown assignment type " + assignment['type'])

# for nostack variables
# tbh i don't really know what i'm doing lmao
def get_assignment_location2(ctx, ptr, expr_stack, assignment):
    if assignment['type'] == 'set' or assignment['type'] == 'inc':
        return [ptr, assignment['type'], assignment['value']]
    
    elif assignment['type'] == 'index':
        expr = generate_expression(ctx, assignment['index'], expr_stack)
        res = get_assignment_location(ctx, f"({ptr} + {expr})", expr_stack, assignment['assignment'])
        return res
    else:
        raise Exception("unknown assignment type " + assignment['type'])

def generate_statement(ctx, statement, scope):
    file = ctx.sprite_ctx.file
    opcode = statement['type']

    # opcode var_declare
    if opcode == 'var_declare':
        var_name = statement['var_name']
        var_size = statement['var_type'].size()
        nostack = not (ctx.recursive or statement['metadata']['needs_ref'] or var_size != 1)
        ctx.new_variable(var_name, var_size, nostack)
        scope.register_variable(var_name, var_size, nostack)

        file.write(f'# {var_name} declaration \n')

        if nostack:
            if statement['init'] != None:
                push_expression_result(ctx, statement['init'], to_temp=True)
                file.write(f"{(ctx.get_variable_id(var_name))} = temp;\n")
            else:
                file.write(f"{(ctx.get_variable_id(var_name))} = \"\";\n")
        else:

            # write initialization expression if present
            if statement['init'] != None:
                push_expression_result(ctx, statement['init'])
            
            # no initialization expression; initialize to an empty string
            else:
                file.write(macro_stack_push('\"\"') + "\n")
        
    # opcode var_assign
    elif opcode == 'var_assign':
        var_name = statement['var_name']
        expr_stack = ExpressionStack()

        var_id = ctx.get_variable_id(var_name)
        if var_id != None: # variable is not on the stack
            assignment = statement['assignment']

            if assignment['type'] == 'index':
                assignment = get_assignment_location2(ctx, var_id, expr_stack, assignment)
                
                location = assignment[0]
                assign_type = assignment[1]
                assign_value = assignment[2]
                
                expr = generate_expression(ctx, assign_value, expr_stack)
                location = expr_stack.finalize_stack_references(location)
                expr = expr_stack.finalize_stack_references(expr)

                if assign_type == 'inc':
                    file.write(f"memory[{location}] = memory[{location}] + {expr};\n")
                else: # type == 'set'
                    assert(assign_type == 'set')
                    file.write(f"memory[{location}] = {expr};\n")                

            else:
                assert(assignment['type'] == 'set' or assignment['type'] == 'inc')

                assign_type = assignment['type']
                assign_value = assignment['value']

                expr = expr_stack.finalize_stack_references(generate_expression(ctx, assign_value, expr_stack))
                
                if assign_type == 'inc':
                    file.write(f"{var_id} += {expr};\n")
                else:
                    file.write(f"{var_id} = {expr};\n")

        else:
            var_loc = ctx.get_variable_location(var_name)

            assignment = get_assignment_location(ctx, var_loc, expr_stack, statement['assignment'])

            location = assignment[0]
            assign_type = assignment[1]
            assign_value = assignment[2]
            
            expr = generate_expression(ctx, assign_value, expr_stack)
            location = expr_stack.finalize_stack_references(location)
            expr = expr_stack.finalize_stack_references(expr)

            if assign_type == 'inc':
                file.write(f"memory[{location}] = memory[{location}] + {expr};\n")
            else: # type == 'set'
                assert(assign_type == 'set')
                file.write(f"memory[{location}] = {expr};\n")

        expr_stack.clear(file)
    
    # opcode func_call
    elif opcode == 'func_call':
        func_data = ctx.sprite_ctx.program['functions'][statement['func_name']]
        generate_func_call(ctx, func_data, statement['args'])

        # drop return value if it exists
        if not func_data.type.is_void():
            file.write(macro_stack_pop(gs_literal(func_data.type.size())))
    
    # opcode builtin_func_call
    elif opcode == 'builtin_func_call':
        func_data = BUILTIN_METHODS[statement['func_name']]

        expr_stack = ExpressionStack()
        arg_exprs = []
        
        for arg in statement['args']:
            arg_exprs.append(generate_expression(ctx, arg, expr_stack))
        
        file.write(func_data.generate([expr_stack.finalize_stack_references(x) for x in arg_exprs]) + "\n")
        expr_stack.clear(file)
    
    # opcode return
    elif opcode == 'return':
        did_return = True

        file.write("# return\n")

        if statement['value']:
            expr_stack = ExpressionStack()
            expr = expr_stack.finalize_stack_references(generate_expression(ctx, statement['value'], expr_stack))

            # set variable to expression result and clear
            # values added to the stack by the expression (if present)
            if expr_stack.stack_size > 0:
                file.write(f"temp = {expr};\n")
                expr_stack.clear(file)
                file.write(macro_set_from_stack_base(ctx.return_offset, "temp") + "\n")
            else:
                file.write(macro_set_from_stack_base(ctx.return_offset, expr) + "\n")

        # free all variables
        total_stack_size = 0
        for var in ctx.active_variables:
            total_stack_size += var['size']
        
        file.write(macro_stack_pop(total_stack_size))
    
    elif opcode == 'deleteclone':
        did_return = True

        file.write("nano_free stack_ptrs[$stack_id];\n")
        file.write("stack_ptrs[$stack_id] = \"\";\ndelete_this_clone;\n")
    
    # opcode if
    elif opcode == 'if':
        push_expression_result(ctx, statement['cond'], True)
        file.write("if (temp+0) != 0 {\n")

        generate_branch(ctx, scope, statement['branch'])

        if (statement['else_branch']):
            file.write("} else {\n")

            generate_branch(ctx, scope, statement['else_branch'])

        file.write("}\n")
    
    # opcode while
    elif opcode == 'while':
        # create tempvar for the while condition
        # (can't use temp directly due to screen refresh at the end of loop)
        tempvar = ctx.new_tempvar(1)
        file.write(macro_stack_push(gs_literal("")) + "\n")

        push_expression_result(ctx, statement['cond'], True)
        file.write(macro_set_from_stack_base(tempvar.offset, "temp") + "\n")
        file.write(f"until ({macro_get_from_stack_base(tempvar.offset)}+0) == 0 {{\n")

        # while inner loop
        generate_branch(ctx, scope, statement['branch'])

        # re-evaluate while condition again at the end of the loop
        push_expression_result(ctx, statement['cond'], True)
        file.write(macro_set_from_stack_base(tempvar.offset, "temp") + "\n")
        file.write("}\n")

        ctx.remove_tempvar(tempvar)
    
    # opcode repeat
    elif opcode == 'repeat':
        push_expression_result(ctx, statement['count'], True)
        file.write("repeat temp {\n")
        generate_branch(ctx, scope, statement['branch'])
        file.write("}\n")
    
    # opcode forever
    elif opcode == 'forever':
        file.write("forever {\n")
        generate_branch(ctx, scope, statement['branch'])
        file.write("}\n")
    
    else:
        raise Exception("unknown statement opcode " + opcode)

# assumes that there is a argument named stack_id
def generate_block(ctx, block):
    file = ctx.sprite_ctx.file

    file.write("# block start\n")

    # parse statement
    scope = Scope()
    did_return = False
    in_forever = False

    for statement in block.statements:
        if statement['type'] == 'return':
            did_return = True
        elif statement['type'] == 'forever':
            did_return = True # doesn't actually return, but whether or not it does no longer matters
            in_forever = True
        
        generate_statement(ctx, statement, scope)

    # end of block
    if not did_return:
        if scope.declared_variables:
            for var_name in scope.declared_variables:
                ctx.remove_variable(var_name)
            
            file.write(macro_stack_pop(scope.size))
        
        file.write("# block end\n")
    
    return {
        'unescapable': in_forever
    }
    
# assumes that there is a argument named stack_id
def generate_procedure(func_ctx, definition):
    file = func_ctx.sprite_ctx.file

    # stack frame enter
    file.write("# stack frame enter\n")
    file.write(macro_stack_push("memory[stack_ptrs[$stack_id]]")) # push old frame body
    file.write("memory[stack_ptrs[$stack_id]] = stack_heads[$stack_id];\n") # set current frame body to stack head

    file.write("# function definition follows\n")
    block_info = generate_block(func_ctx, definition)

    # stack frame end
    if not block_info['unescapable']:
        file.write("\n# stack frame end\n")
        file.write("temp = " + macro_get_from_stack_base(0) + ";\n")
        file.write(macro_stack_pop(1) + "\n") # pop base of current stack frame
        file.write("memory[stack_ptrs[$stack_id]] = temp;\n") # restore base of old stack frame

# check if given function is recursive
# searches through the tree of function references to see if it loops
def check_if_recursive(functions, func, name):
    for ref in func.func_references:
        if ref in BUILTIN_METHODS: return False
        if ref == name and ref != func.name and check_if_recursive(functions, functions[ref], name):
            return True
    
    return False
        
# static memory initialization
def static_memory_init(ctx, stage_ctx):
    file = ctx.file
    program = ctx.program

    # get size required to store static variables
    static_alloc_size = 0
    for var_name in program['static_order']:
        static_var = program['variables'][var_name]
        if static_var['metadata']['needs_ref']:
            static_alloc_size += static_var['type'].size()
    
    file.write("on \"nanoinit\" {\n")

    # allocate space for static variables
    if static_alloc_size > 0:
        file.write(f"nano_malloc {gs_literal(static_alloc_size)};\n")
        file.write(f"{(ctx.staticalloc)} = nano_malloc_return;\n")
    else:
        file.write(f"{(ctx.staticalloc)} = 0;\n")

    # initialize static variables
    static_variables = ctx.static_variables
    static_offset = 0

    if stage_ctx:
        for var_name in stage_ctx.static_variables:
            static_variables[var_name] = stage_ctx.static_variables[var_name]
    
    for var_name in program['static_order']:
        static_var = program['variables'][var_name]

        if static_var['metadata']['needs_ref']:
            file.write(f"memory[{(ctx.staticalloc)} + {static_offset}] = {gs_literal(static_var['init'])};\n")

            var_size = static_var['type'].size()
            static_variables[var_name] = {
                'name': var_name,
                'size': var_size,
                'location': f"({(ctx.staticalloc)} + {static_offset})",
                'id': None,
            }
            static_offset += var_size
        
        else:
            var_id = ctx.new_var_id() + "_" + var_name
            file.write(f"{var_id} = {gs_literal(static_var['init'])};\n")

            static_variables[var_name] = {
                'name': var_name,
                'size': 1,
                'location': None,
                'id': var_id
            }

    file.write("}\n\n")

def generate_program(program, file, stage=None):
    sprite_ctx = SpriteContext(program, file)

    for costume_name in program['costumes']:
        file.write(f"costumes {gs_literal(costume_name)};\n")
    
    for costume_name in program['sounds']:
        file.write(f"sounds {gs_literal(costume_name)};\n")
    
    if stage == None:
        sprite_ctx.staticalloc = "nano_stagestaticalloc"
        file.write(stage_boilerplate + "\n")
    else:
        sprite_ctx.staticalloc = "nano_staticalloc"
        
    file.write(program_boilerplate + "\n")

    # static variable initialization
    static_memory_init(sprite_ctx, stage)

    for func in program['functions'].values():
        func_ctx = FunctionContext(sprite_ctx, func.parameters, func.type)
        func_ctx.warp = 'warp' in func.attributes
        func_ctx.does_return = not func.type.is_void()
        func_ctx.recursive = check_if_recursive(program['functions'], func, func.name)

        block_name = "_" + func.name
        sprite_ctx.function_block_names[func.name] = block_name
        
        if not func_ctx.warp:
            file.write("nowarp ")
        file.write(f"proc {block_name} stack_id")
        file.write(" {\n")

        generate_procedure(func_ctx, func.definition)
        file.write("}\n")
    
    event_id = 0
    for event_handler in program['events']:
        func_ctx = FunctionContext(sprite_ctx, [], ValueType(ValueType.VOID))
        func_ctx.warp = 'warp' in event_handler['attributes']
        func_ctx.does_return = False

        block_name = "event" + str(event_id)

        if not 'warp' in event_handler['attributes']:
            file.write("nowarp ")
        
        file.write(f"proc {block_name} stack_id {{\n")
        generate_procedure(func_ctx, event_handler['definition'])
        file.write("nano_free stack_ptrs[$stack_id];\n")
        file.write("stack_ptrs[$stack_id] = \"\";\n}\n")
        event_id += 1

        event_name = event_handler['event_name']
        event_param = event_handler['event_param']
        
        if event_name == 'flag':
            file.write("on \"nanostart\"")
        elif event_name == 'keypressed':
            file.write("onkey " + gs_literal(event_param))
        elif event_name == 'clicked':
            file.write("onclick " + gs_literal(event_param))
        elif event_name == 'backdrop_switched':
            file.write("onbackdrop " + gs_literal(event_param))
        elif event_name == 'loudness_exceeds':
            file.write("onloudness " + gs_literal(event_param))
        elif event_name == 'timer_exceeds':
            file.write("ontimer " + gs_literal(event_param))
        elif event_name == 'broadcast':
            file.write("on " + gs_literal(event_param))
        elif event_name == 'cloned':
            file.write("onclone")
        else:
            raise Exception(f"internal: invalid event {event_name}")
        
        file.write(" {\nnano_alloc_stack;\n" + block_name + " init_stack_ret;\n}\n")
    
    sprite_ctx.file = None
    return sprite_ctx