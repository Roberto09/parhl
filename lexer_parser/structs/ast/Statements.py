from ..parhl_exceptions import ParhlException
from ..quadruples import Quadruple
from ..parse_context import ParseContext
from .Node import Node
from .Expressions import Assign, Expression
from ...lexer import type_to_token

Statement = Node

class Empty(Statement):
    def __init__(self):
        super().__init__(0)
    def gen_impl(self, ctx: ParseContext):
        pass
    def __bool__(self):
        return False
    
class Seq(Statement):
    def __init__(self, line, stmt, seq=Empty()):
        super().__init__(line)
        self.stmt = stmt
        self.seq = seq

    def gen_impl(self, ctx: ParseContext):
        self.stmt.gen(ctx)
        self.seq.gen(ctx)

    @Node.handle_exception
    def gen_ret_list(self, ctx : ParseContext):
        # TODO : improve complexity, this is O(n^2)
        return [self.stmt.gen(ctx)] + (self.seq.gen_ret_list(ctx) if self.seq else [])

class If(Statement):

    class IfSeqAux(Statement):
        def __init__(self, line, expr, seq, nxt_seq = Empty()):
            super().__init__(line)
            self.expr = expr
            self.seq = seq
            self.nxt_seq = nxt_seq

        def gen_impl(self, ctx: ParseContext):
            var = self.expr.gen(ctx)
            gotof_idx = ctx.add_quadruple(Quadruple('GOTOF', var.mem_dir))
            ctx.func_dir.start_block_stack()
            self.seq.gen(ctx)
            ctx.func_dir.end_block_stack()
            goto_idx = ctx.add_quadruple(Quadruple('GOTO'))
            ctx.set_goto_position(gotof_idx)
            self.nxt_seq.gen(ctx)
            # At this point the quad_idx is the instruction after the if-elseif-else sequence
            ctx.set_goto_position(goto_idx)

        def with_last(self, last):
            if not self.nxt_seq:
                self.nxt_seq = last
            else:
                self.nxt_seq.with_last(last)
            return self

    class ElseAux(Statement):
        def __init__(self, line, seq):
            super().__init__(line)
            self.seq = seq
        
        def gen_impl(self, ctx: ParseContext):
            ctx.func_dir.start_block_stack()
            self.seq.gen(ctx)
            ctx.func_dir.end_block_stack()

    def __init__(self, line, if_aux_seq):
        super().__init__(line)
        self.if_aux_seq = if_aux_seq

    def gen_impl(self, ctx: ParseContext):
        self.if_aux_seq.gen(ctx)

class While(Statement):
    def __init__(self, line, expr, seq):
        super().__init__(line)
        self.expr = expr
        self.seq = seq

    def gen_impl(self, ctx: ParseContext):
        jump_index = ctx.get_next_quadruple_index()
        var = self.expr.gen(ctx)
        gotof_index = ctx.add_quadruple(Quadruple('GOTOF', var.mem_dir))
        ctx.func_dir.start_block_stack()
        self.seq.gen(ctx)
        ctx.func_dir.end_block_stack()
        ctx.add_quadruple(Quadruple('GOTO',result=jump_index))
        ctx.set_goto_position(gotof_index)

class For(Statement):
    def __init__(self, line, var, expr, assign, seq=Empty()):
        super().__init__(line)
        self.var = var
        self.expr = expr
        self.assign = assign
        self.seq = seq

    def gen_impl(self, ctx: ParseContext): 
        ctx.func_dir.start_block_stack()
        self.var.gen(ctx)
        jump_index = ctx.get_next_quadruple_index()
        var = self.expr.gen(ctx)
        gotof_index = ctx.add_quadruple(Quadruple('GOTOF', var.mem_dir))
        self.seq.gen(ctx)
        self.assign.gen(ctx)
        ctx.add_quadruple(Quadruple('GOTO', result=jump_index))
        ctx.set_goto_position(gotof_index)
        ctx.func_dir.end_block_stack()

class VarDecl(Statement):
    def __init__(self, line, id, id_type):
        super().__init__(line)
        self.id = id
        assert Expression in type(id).__mro__
        self.id_type = type_to_token[id_type]
        self.assign = Empty()

    def do_assign(self, expr):
        self.assign = Assign(self.lineno, self.id, expr)

    def gen_impl(self, ctx: ParseContext):
        print('gen decl')
        var = ctx.func_dir.add_var(self.id.id, self.id_type)
        self.assign.gen(ctx)
        return var
        # do stuff

class FuncDecl(Statement):
    def __init__(self, line, id, id_type, params_seq, seq):
        super().__init__(line)
        self.id = id
        assert Expression in type(id).__mro__
        self.id_type = id_type
        self.params_seq = params_seq
        self.seq = seq 

    def gen_impl(self, ctx: ParseContext):
        goto_index = ctx.add_quadruple(Quadruple('GOTO')) # add gotos to skip function on initial execution, only executed once called
        q_index = goto_index+1 # index for starting at func
        ctx.func_dir.start_func_stack(self.id.id, self.id_type, q_index)
        vars = self.params_seq.gen_ret_list(ctx) if self.params_seq else None
        print('decl vars ', vars)
        ctx.func_dir.set_func_params([] if vars == None else vars)
        ctx.add_quadruple(Quadruple('ERA',result=self.id.id)) # on vm lookup func by id
        self.seq.gen(ctx)
        ctx.func_dir.end_func_stack(self.id.id)
        last_q = ctx.get_quadruples()[-1]
        if self.id_type != 'void' and last_q.op != 'RETURN':
            raise ParhlException(f"function {self.id.id} missing return value.")
        ctx.add_quadruple(Quadruple('ENDFUNC'))
        ctx.set_goto_position(goto_index) # fill goto

class Ret(Statement):
    def __init__(self, line, expr):
        super().__init__(line)
        self.expr = expr

    def gen_impl(self, ctx: ParseContext):
        expr_var = self.expr.gen(ctx)
        curr_func = ctx.func_dir.curr_func
        
        if curr_func.type == 'void':
            raise ParhlException(f"function {curr_func.id} void, cannot return value")
        var_type = ctx.semantic_cube.get_type('ASSIG', curr_func.type, expr_var.type)

        prev_func = ctx.func_dir.func_stack[-1]
        func_var = prev_func.vars[curr_func.id]
        ctx.add_quadruple(Quadruple('RETURN', expr_var.mem_dir, result=func_var.mem_dir))



class FuncCall(Statement):
    def __init__(self, line, id, args_seq):
        super().__init__(line)
        self.id = id
        self.args_seq = args_seq
    
    def gen_impl(self, ctx: ParseContext):
        func = ctx.func_dir.get_func(self.id)
        vars = self.args_seq.gen_ret_list(ctx) if self.args_seq else None
        print('vars ', vars)
        print('func.params ', func.params)
        next_q = ctx.get_next_quadruple_index() + 1
        ctx.add_quadruple(Quadruple('GOSUB', next_q, result=func.name))
        assert len(vars) == len(func.params)
        for (i, var) in enumerate([] if vars == None else vars):
            param = func.params[i]
            ctx.semantic_cube.get_type('ASSIG', param.type, var.type)
            ctx.add_quadruple(Quadruple('PARAM', var.mem_dir, result=param.mem_dir))

        if func.type != 'void':
            func_var = ctx.func_dir.get_var(self.id)
            temp_var = ctx.func_dir.new_temp(func.type)
            ctx.add_quadruple(Quadruple('ASSIG', func_var.mem_dir, result=temp_var.mem_dir))
            return temp_var


class IOFunc(FuncCall):
    def __init__(self, line, id, args_seq=Empty()):
        super().__init__(line, id, args_seq)
    
    def gen_impl(self, ctx: ParseContext):
        seq = self.args_seq.gen_ret_list(ctx) if self.args_seq else None
        if self.id in 'read_line':
            new_var = ctx.func_dir.new_temp('STRING_T')
            ctx.add_quadruple(Quadruple('READ_LINE', None, None, new_var.mem_dir))
            return new_var
        if self.id == 'read_file' and seq is not None:
            new_var = ctx.func_dir.new_temp('STRING_T')
            ctx.add_quadruple(Quadruple('READ_FILE', seq[0].mem_dir, None, new_var.mem_dir))
            return new_var
        if seq == None:
            seq = []
        for arg in seq:
            ctx.add_quadruple(Quadruple(self.id.upper(), None, None, arg.mem_dir))
            