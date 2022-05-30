import json
from sys import argv

class MemoryManager():
    def __init__(self, func_dir):
        # track memory relevant information
        self.mem_stack = [[] for _ in range(len(func_dir))]
        # dormant_mem_stack holds memory for functions which are inactive
        # i.e. which exist between an ERA and GOSUB state
        self.dormant_mem_stack = [[] for _ in range(len(func_dir))]
        self.func_dir = func_dir

    def dereference(self, initial_mem_dir):
        while(initial_mem_dir[2]):
            # Rewriting manually bc tuple doesnt support item assignment
            func_dir = self.mem_stack[initial_mem_dir[0]][-1][initial_mem_dir[1]]
            var_dir = self.mem_stack[initial_mem_dir[0]][-1][initial_mem_dir[1]+1]
            deref = self.mem_stack[initial_mem_dir[0]][-1][initial_mem_dir[1]+2]
            initial_mem_dir = (func_dir, var_dir, deref)
            
        return (initial_mem_dir[0], initial_mem_dir[1])

    def get_mem(self, mem_dir):
        func_id, mem_dir = self.dereference(mem_dir)
        return self.mem_stack[func_id][-1][mem_dir]

    def set_mem_w_val(self, mem_dir_dst, val):
        func_id, mem_dir_dst = self.dereference(mem_dir_dst)
        self.mem_stack[func_id][-1][mem_dir_dst] = val

    def set_mem_w_mem(self, mem_dir_src, mem_dir_dst):
        val = self.get_mem(mem_dir_src)
        self.set_mem_w_val(mem_dir_dst, val)

    def set_dorm_mem_w_mem(self, mem_dir_src, dorm_mem_dir_dst):
        val = self.get_mem(mem_dir_src)
        func_id, dorm_mem_dir_dst = self.dereference(dorm_mem_dir_dst)
        self.dormant_mem_stack[func_id][-1][dorm_mem_dir_dst] = val

    def era_func_stack(self, func_id):
        func_ttl_vars = self.func_dir[func_id][0]
        self.dormant_mem_stack[func_id].append([None] * func_ttl_vars)

    def start_func_stack(self, func_id):
        self.mem_stack[func_id].append(self.dormant_mem_stack[func_id].pop())        

    def end_func_stack(self, func_id):
        self.mem_stack[func_id].pop()

def bin_op(q, mem, op):
    mem.set_mem_w_val(q[3], op(mem.get_mem(q[1]), mem.get_mem(q[2])))

def assig_op(q, mem):
    mem.set_mem_w_mem(q[1], q[3])

def verify_op(q, mem):
    index_val = mem.get_mem(q[3])
    limit = mem.get_mem(q[1]) 
    if  index_val >= limit:
        raise Exception(f"Out of bounds: tensor index with value {index_val} must be lower than {limit}")

def run_func(mem : MemoryManager, quads, q_idx):
    basic_op_handler = {
        "ASSIG" : lambda q : assig_op(q, mem),
        "PARAM" : lambda q : mem.set_dorm_mem_w_mem(q[1], q[3]),
        "PLUS" : lambda q : bin_op(q, mem, lambda x,y:x+y) 
                                if q[2] != None else 
                            mem.set_mem_w_val(q[3], 1 * mem.get_mem(q[1])),
        "MINUS" : lambda q : bin_op(q, mem, lambda x,y:x-y)
                                if q[2] != None else
                            mem.set_mem_w_val(q[3], -1 * mem.get_mem(q[1])),
        "DIV" : lambda q : bin_op(q, mem, lambda x,y:x/y),
        "MULT" : lambda q : bin_op(q, mem, lambda x,y:x*y),
        "EXP" : lambda q : bin_op(q, mem, lambda x,y:x**y),
        "MOD" : lambda q : bin_op(q, mem, lambda x,y:x%y),
        "EQ" : lambda q : bin_op(q, mem, lambda x,y:x==y),
        "NOT_EQ" : lambda q : bin_op(q, mem, lambda x,y:x!=y),
        "GEQT" : lambda q : bin_op(q, mem, lambda x,y:x>=y),
        "LEQT" : lambda q : bin_op(q, mem, lambda x,y:x<=y),
        "GT" : lambda q : bin_op(q, mem, lambda x,y:x>y),
        "LT" : lambda q : bin_op(q, mem, lambda x,y:x<y),
        "OR" : lambda q : bin_op(q, mem, lambda x,y:x or y),
        "AND" : lambda q : bin_op(q, mem, lambda x,y:x and y),
        "NOT" : lambda q : mem.set_mem_w_val(q[3], not mem.get_mem(q[1])),
        "PRINT" : lambda q : print(mem.get_mem(q[3])),
        "CONST" : lambda q : mem.set_mem_w_val(q[3], q[1]),
        "VERIFY": lambda q : verify_op(q, mem),
    }
    try: 
        while(q_idx < len(quads)):
            q = quads[q_idx]
            q_op = q[0]
            nxt_q_idx = q_idx + 1
            # block special quads
            if q_op == "GOTO":
                nxt_q_idx = q[3]
            elif q_op == "GOTOF":
                if(not mem.get_mem(q[1])):
                    nxt_q_idx = q[3]
            elif q_op == "STRTBLK":
                mem.era_func_stack(q[3])
                mem.start_func_stack(q[3])
            elif q_op == "ENDBLK":
                mem.end_func_stack(q[3])
            # function special quads
            elif q_op == "ERA":
                mem.era_func_stack(q[3])
            elif q_op == "GOSUB":
                mem.start_func_stack(q[3])
                run_func(mem, quads, q[1])
                mem.end_func_stack(q[3])
            elif q_op == "RETURN":
                assig_op(q, mem)
                break
            elif q_op == "ENDFUNC":
                break
            else:
                basic_op_handler[q_op](q)
            q_idx = nxt_q_idx
    except Exception as e:
        raise Exception(f"Error executing op: {q_idx} - {quads[q_idx]}") from e

def run_global(func_dir, quads):
    memory_manager = MemoryManager(func_dir)
    memory_manager.era_func_stack(0)
    memory_manager.start_func_stack(0)
    run_func(memory_manager, quads, 0)
    memory_manager.end_func_stack(0)

def main():
    filename = argv[1]
    with open(filename, "r") as ir_file:
        ir = ir_file.read()
        compiler_dict = json.loads(ir)
    func_dir = compiler_dict["func_dir"]
    quads = compiler_dict["quads"]
    run_global(func_dir, quads)

if __name__ == '__main__':
    main()