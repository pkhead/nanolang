# Goboscript generator
from lexer import Token

# user function prefix: "_"
# internal function prefix: "internal_"

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
    file.write("# " + str(block) + "\n")

program_boilerplate = """
onflag {
    delete stacks;
    delete stack_info;
}

proc internal_alloc_stack {
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
"""

def generate_program(program, file):
    for costume_name in program['costumes']:
        file.write(f"costumes {escape_string(costume_name)};\n")
    
    for costume_name in program['sounds']:
        file.write(f"sounds {escape_string(costume_name)};\n")
    
    file.write(program_boilerplate + "\n")

    for func in program['functions'].values():
        block_name = "_" + func.name

        if not 'warp' in func.attributes:
            file.write("nowarp ")
        
        file.write(f"proc {block_name} stack_id")
        file.write(" {\n")
        generate_block(program, file, func.definition)
        file.write("}\n")
    
    event_id = 0
    for event_handler in program['events']:
        block_name = "event" + str(event_id)

        if not 'warp' in event_handler['attributes']:
            file.write("nowarp ")
        
        file.write(f"proc {block_name} stack_id {{\n")
        generate_block(program, file, event_handler['definition'])
        file.write("stack_info[$stack_id] = \"\";\n}\n")
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