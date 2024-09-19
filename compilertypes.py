class ValueType:
    VOID = 0
    NUMBER = 1
    STRING = 2
    BOOL = 3

    POINTER = 4

    def __init__(self, type, base_type=None):
        self.type = type
        self.base_type = base_type
    
    @staticmethod
    def pointer_to(base_type):
        return ValueType(ValueType.POINTER, base_type)
    
    @staticmethod
    def from_string(str):
        base_len = str.find('*')
        if base_len == -1:
            base_len = len(str)
        
        match str[:base_len]:
            case 'void':
                out_type = ValueType(ValueType.VOID)
            case 'bool':
                out_type = ValueType(ValueType.BOOL)
            case 'number':
                out_type = ValueType(ValueType.NUMBER)
            case 'string':
                out_type = ValueType(ValueType.STRING)
            case _:
                raise Exception("could not read type string " + str)
        
        while base_len < len(str) and str[base_len] == '*':
            out_type = ValueType.pointer_to(out_type)
            base_len += 1
        
        return out_type
    
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
    
    # returns true if it is a pointer or an array
    def is_pointer(self):
        return self.type == ValueType.POINTER
    
    def size(self):
        if self.type == ValueType.VOID:
            raise Exception("internal: attempt to get sizeof void")
        
        # TODO: structs can have different sizes
        return 1

    def can_cast(self, to_type):
        if not isinstance(to_type, ValueType):
            to_type = ValueType(to_type)
        
        if self.is_a(ValueType.POINTER) and to_type.is_a(ValueType.POINTER):
            return True
        
        if self.is_same(to_type): return True

        can_cast = False
        if to_type.is_a(ValueType.STRING) or to_type.is_a(ValueType.NUMBER):
            can_cast = True

        elif to_type.is_a(ValueType.BOOL):
            can_cast = self.is_a(ValueType.NUMBER) or self.is_a(ValueType.POINTER)
        
        elif to_type.is_a(ValueType.POINTER):
            can_cast = self.is_a(ValueType.NUMBER) or self.is_a(ValueType.POINTER)
        
        return can_cast
    
    def can_cast_implicit(self, to_type):
        if not isinstance(to_type, ValueType):
            to_type = ValueType(to_type)
        
        if self.is_same(to_type): return True
        
        can_cast = False

        if to_type.is_a(ValueType.BOOL):
            can_cast = self.is_a(ValueType.NUMBER)
        elif to_type.is_a(ValueType.STRING):
            can_cast = self.is_a(ValueType.NUMBER)
        
        return can_cast