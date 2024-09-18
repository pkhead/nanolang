from compilertypes import ValueType

class BuiltinFunction:
    def __init__(self, name, type, params, generate, generate_return=None):
        self.name = name
        self.type = ValueType.from_string(type)
        self.parameters = [{'name': '', 'type': ValueType.from_string(x)} for x in params]
        self.generate = generate
        self.generate_return = generate_return

def _func(arr):
    dic = {}
    for f in arr:
        dic[f.name] = f
    return dic

BUILTIN_METHODS = _func([
    # MOTION
    BuiltinFunction(
        name='move_steps',
        type='void',
        params=['number'],
        generate=lambda args: f"move {(args[0])};"
    ),

    BuiltinFunction(
        name='turn_cw',
        type='void',
        params=['number'],
        generate=lambda args: f"turn_right {(args[0])};"
    ),

    BuiltinFunction(
        name='turn_ccw',
        type='void',
        params=['number'],
        generate=lambda args: f"turn_left {(args[0])};"
    ),

    BuiltinFunction(
        name='goto_xy',
        type='void',
        params=['number', 'number'],
        generate=lambda args: f"goto {(args[0])}, {(args[1])};"
    ),

    BuiltinFunction(
        name='point_in_direction',
        type='void',
        params=['number'],
        generate=lambda args: f"point_in_direction {(args[0])};"
    ),

    BuiltinFunction(
        name='set_x',
        type='void',
        params=['number'],
        generate=lambda args: f"set_x {(args[0])};"
    ),

    BuiltinFunction(
        name='set_y',
        type='void',
        params=['number'],
        generate=lambda args: f"set_y {(args[0])};"
    ),

    BuiltinFunction(
        name='change_x',
        type='void',
        params=['number'],
        generate=lambda args: f"change_x {(args[0])};"
    ),

    BuiltinFunction(
        name='change_y',
        type='void',
        params=['number'],
        generate=lambda args: f"change_y {(args[0])};"
    ),

    BuiltinFunction(
        name='get_x',
        type='number',
        params=[],
        generate=lambda args: f"x_position()"
    ),

    BuiltinFunction(
        name='get_y',
        type='number',
        params=[],
        generate=lambda args: f"y_position()"
    ),

    BuiltinFunction(
        name='get_direction',
        type='number',
        params=[],
        generate=lambda args: f"direction()"
    ),

    BuiltinFunction(
        name='bounce_on_edge',
        type='void',
        params=[],
        generate=lambda args: f"if_on_edge_bounce();"
    ),

    # LOOKS
    BuiltinFunction(
        name='say_for_secs',
        type='void',
        params=['string', 'number'],
        generate=lambda args: f"say {(args[0])}, {(args[1])};"
    ),

    BuiltinFunction(
        name='say',
        type='void',
        params=['string'],
        generate=lambda args: f"say {(args[0])};"
    ),

    BuiltinFunction(
        name='think_for_secs',
        type='void',
        params=['string', 'number'],
        generate=lambda args: f"think {(args[0])}, {(args[1])};"
    ),

    BuiltinFunction(
        name='think',
        type='void',
        params=['string'],
        generate=lambda args: f"think {(args[0])};"
    ),

    BuiltinFunction(
        name='set_costume_name',
        type='void',
        params=['string'],
        generate=lambda args: f"switch_costume {(args[0])};"
    ),

    BuiltinFunction(
        name='get_costume_name',
        type='string',
        params=[],
        generate=lambda args: f"costume_name"
    ),

    BuiltinFunction(
        name='get_costume_number',
        type='number',
        params=[],
        generate=lambda args: f"costume_number"
    ),

    BuiltinFunction(
        name='set_costume_number',
        type='void',
        params=['number'],
        generate=lambda args: f"switch_costume {(args[0])};"
    ),

    BuiltinFunction(
        name='next_costume',
        type='void',
        params=[],
        generate=lambda args: f"next_costume {(args[0])};"
    ),

    BuiltinFunction(
        name='set_size',
        type='void',
        params=['number'],
        generate=lambda args: f"set_size {(args[0])};"
    ),

    BuiltinFunction(
        name='change_size',
        type='void',
        params=['number'],
        generate=lambda args: f"change_size {(args[0])};"
    ),

    BuiltinFunction(
        name='get_size',
        type='number',
        params=[],
        generate=lambda args: f"size()"
    ),

    BuiltinFunction(
        name='show',
        type='void',
        params=[],
        generate=lambda args: f"show();"
    ),

    BuiltinFunction(
        name='hide',
        type='void',
        params=[],
        generate=lambda args: f"hide();"
    ),

    # SOUND

    # CONTROL

    # SENSING
    BuiltinFunction(
        name='ask',
        type='string',
        params=['string'],
        generate=lambda args: f"ask ({args[0]});",
        generate_return=lambda: "answer()"
    ),

    BuiltinFunction(
        name='last_answer',
        type='string',
        params=[],
        generate=lambda args: f"answer()"
    ),

    BuiltinFunction(
        name='key_pressed',
        type='bool',
        params=['string'],
        generate=lambda args: f"key_pressed({args[0]})"
    ),

    BuiltinFunction(
        name='mouse_down',
        type='bool',
        params=[],
        generate=lambda args: f"mouse_down()"
    ),

    BuiltinFunction(
        name='mouse_x',
        type='number',
        params=[],
        generate=lambda args: f"mouse_x()"
    ),

    BuiltinFunction(
        name='mouse_y',
        type='number',
        params=[],
        generate=lambda args: f"mouse_y()"
    ),

    BuiltinFunction(
        name='reset_timer',
        type='void',
        params=[],
        generate=lambda args: f"reset_timer"
    ),

    BuiltinFunction(
        name='timer',
        type='number',
        params=[],
        generate=lambda args: f"timer"
    ),

    # OPERATORS
    BuiltinFunction(
        name='random',
        type='number',
        params=['number', 'number'],
        generate=lambda args: f"random({args[0]}, {args[1]})"
    ),

    
])