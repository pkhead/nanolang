from compilertypes import ValueType

class BuiltinFunction:
    def __init__(self, name, type, params, generate, generate_return=None):
        self.name = name
        self.type = ValueType.from_string(type)
        self.parameters = [{'name': '', 'type': ValueType.from_string(x)} for x in params]
        self.generate = generate
        self.generate_return = generate_return

BUILTIN_METHODS = {
    'ask': BuiltinFunction(
        name='ask',
        type='string',
        params=['string'],
        generate=lambda args: f"ask ({args[0]});",
        generate_return=lambda: "answer()"
    ),

    'last_answer': BuiltinFunction(
        name='last_answer',
        type='string',
        params=[],
        generate=lambda args: f"answer()"
    ),

    'sprite_say_wait': BuiltinFunction(
        name='sprite_say_wait',
        type='void',
        params=['string', 'number'],
        generate=lambda args: f"say {(args[0])}, {(args[1])};"
    )
}