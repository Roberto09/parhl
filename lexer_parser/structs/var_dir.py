
class Typed():
    def __init__(self, name, type):
        self.name = name
        self.type = type
    
    def __repr__(self):
        return f"name: {self.name}, type: {self.type}"
class Var(Typed):
    def __init__(self, name, type, mem_dir, value=None):
        super().__init__(name, type)
        self.mem_dir = mem_dir # "location" in instance memory
        self.value = value

    def __repr__(self):
        return f"({super().__repr__()}, mem_dir: {self.mem_dir}, value: {self.value})"

class Block():
    def __init__(self):
        # its unclear if we would need a name here ... TBD
        self.vars: dict[str, Var] = {} # name : Var
        self.funcs: dict[str, Func] = {} # name : Func
        self.temps: dict[str, Var] = {} # name : var
        self.temp_counters: dict[str, int] = { # type : next_temp/total_temps
            'INT_T': 0,
            'FLOAT_T': 0,
            'BOOL_T': 0,
            'STRING_T': 0,
            'GPU_INT_T': 0,
            'GPU_FLOAT_T': 0,
            'GPU_BOOL_T': 0,
        }
        self.blocks = []
    
    def __repr__(self):
        return f"(block, vars: {list(self.vars.values())}, funcs: {list(self.funcs.values())}, blocks:{self.blocks}))"

class Func(Typed, Block):
    def __init__(self, name, type, q_index):
        super().__init__(name, type)
        super(Typed, self).__init__()
        self.q_index = q_index

    def __repr__(self):
        return f"({super().__repr__()}, q_index: {self.q_index}, vars: {list(self.vars.values())}, funcs: {list(self.funcs.values())}, blocks:{self.blocks})"
    
    def set_params(self, params: list[Var]= []):
        self.params = params

    def set_mem_reg(self, vars, funcs, temps, blocks):
        self.vars = vars
        self.funcs = funcs
        self.temp_counters = temps
        self.blocks = blocks

""" Function Directory abstraction
FuncDir generates a tree of Vars and Funcs which will remain available in the glob_func property.
"""
class FuncDir:
    def __init__(self):
        self.glob_func = Func('glob', 'void', 0)
        self.func_stack = [self.glob_func]

    def start_func_stack(self, name, type, q_index):
        # We only care about the most inner scope when it comes to re-definitions. 
        assert (name not in self.func_stack[-1].vars) and (name not in self.func_stack[-1].funcs)
        nxt_func = Func(name, type, q_index)
        self.func_stack[-1].funcs[name] = nxt_func
        self.func_stack.append(nxt_func)

    def end_func_stack(self, name=None): 
        if name is not None:
            assert self.func_stack[-1].name == name
        self.func_stack.pop()

    def set_func_params(self, params):
        self.func_stack[-1].params = params

    def start_block_stack(self):
        nxt_block = Block()
        self.func_stack[-1].blocks.append(nxt_block)
        self.func_stack.append(nxt_block)

    def end_block_stack(self):
        self.func_stack.pop()

    def add_var(self, name, type):
        # We only care about the most inner scope when it comes to re-definitions.
        assert name not in self.func_stack[-1].vars and name not in self.func_stack[-1].funcs
        # Obtain location of next memory of specified type
        var = Var(name, type, -1)
        self.func_stack[-1].vars[name] = var
        return var

    def new_temp(self, type, value=None):
        temp_var_name = type + str(self.func_stack[-1].temp_counters[type])
        temp_var = Var(temp_var_name, type, -1, value)
        self.func_stack[-1].temps[temp_var_name] = temp_var
        self.func_stack[-1].temp_counters[type] += 1
        return temp_var

    def _find_in_ordered_scopes(self, name, attr):
        """
        This allows us to find an id (name) in an attr of the func_stack.
        This follows the idea of finding the variable prioritizing the most inner scopes.
        """
        for attrs in map(lambda f: getattr(f, attr), reversed(self.func_stack)):
            if name in attrs:
                return attrs[name]
        raise Exception(f"{attr} with id {name} not found")

    def get_var(self, name):
        return self._find_in_ordered_scopes(name, "vars")

    def get_temp(self, name):
        return self.func_stack[-1].temps[name]

    def get_func(self, name):
        return self._find_in_ordered_scopes(name, "funcs")

    def __repr__(self):
        return f"FuncDir - func_stack: {self.func_stack}"


    
