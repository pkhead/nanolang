# Goboscript generator
from lexer import Token

def escape_string(str):
    out = ['"']
    
    for c in str:
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

def generate_block(program, file, block):
    file.write("{\n")

    file.write("}\n")

program_boilerplate = """
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

            until length stacks >= stack_pos + 1023 {
                add "" to stacks;
            }

            init_stack_ret = i;
            stop_this_script;
        }

        i += 1;
    }
    

    stack_pos = (i-1) * 1024 + 1;
    stack_info[i] = stack_pos;

    until length stacks >= stack_pos {
        add "" to stacks;
    }

    init_stack_ret = i;
}

nowarp proc _main own_stack, stack_id {
    if $own_stack != 0 {
        stack_info[$stack_id] = "";
    }
}

onflag {
    delete stacks;
    delete stack_info;
}
"""

def generate_program(program, file):
    for costume_name in program['costumes']:
        file.write(f"costumes {escape_string(costume_name)};\n")
    
    for costume_name in program['sounds']:
        file.write(f"sounds {escape_string(costume_name)};\n")
    
    file.write(program_boilerplate + "\n")

    for func in program['functions'].values():
        file.write(f"proc _{(func.name)} stack_id")
        generate_block(program, file, func.definition)