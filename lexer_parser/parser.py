from sly import Parser
from lexer import ParhlLexer

class ParhlParser(Parser):
    # Get the token list from the lexer (required)
    tokens = ParhlLexer.tokens
    
    # Grammar rules and actions
    # """PROGRAM"""
    # @_('PROGRAM ID ";" program2 bloque1')
    # def program1(self, p):
    #     return "program parsed"

    # @_('')
    # def empty(self, p):
    #     pass

    @_('SEMICOLON','NEWLINE')
    def eos(self, p):
        pass
    
    @_('CTE_I','CTE_F', 'CTE_B', 'CTE_S')
    def cte(self, p):
        pass

    @_('LBRACKET expr tens_1')
    def tens(self, p):
        pass

    @_('RBRACKET', 'COMMA expr tens_1')
    def tens_1(self, p):
        pass

    @_('ID tens_id_1')
    def tens_id(self,p):
        pass
    
    @_('LBRACKET expr RBRACKET', 'LBRACKET expr RBRACKET tens_id_1')
    def tens_id_1(self, p):
        pass

    @_('LKEY estatuto RKEY')
    def bloque(self, p):
        pass

    @_('INT', 'FLOAT', 'STRING', 'BOOL', 'GPU_INT', 'GPU_FLOAT','GPU_BOOL')
    def type(self, p):
        pass
    
    @_('t_expr', 't_expr OR expr')
    def expr(self, p):
        pass

    @_('g_expr', 'g_exp AND t_expr')
    def t_expr(self, p):
        pass

    @_('m_expr', 'm_expr comparison m_expr')
    def g_expr(self, p):
        pass

    @_('EQUALS', 'NEQUALS', 'MORE', 'LESS', 'MEQUALS', 'LEQUALS')
    def comparison(self, p):
        pass

    @_('term', 'term PLUS m_expr', 'term MINUS m_expr')
    def m_expr(self, p):
        pass

    @_('exp_factor', 'exp_factor MULT term', 'exp_factor DIV term', 'exp_factor MOD term')
    def term(self, p):
        pass

    @_('factor', 'factor EXP exp_factor')
    def exp_factor(self, p):
        pass

    @_('factor_1', 'NOT factor_1', 'PLUS factor_1', 'MINUS factor_1')
    def factor(self, p):
        pass

    @_('LPAR expr RPAR', 'cte', 'ID', 'func_call', 'tens', 'tens_id')
    def factor_1(self, p):
        pass

    @_('ID LPAR func_call_1')
    def func_call(self, p):
        pass

    @_('RPAR', 'expr RPAR', 'expr COMMA func_call_1')
    def func_call_1(self, p):
        pass
    
    @_('ID ASSIG expr')
    def asignacion(self, p):
        pass
    
    @_('LET var_1')
    def var(self, p):
        pass
    
    @_('var_2', 'var_2 var_3')
    def var_1(self, p):
        pass

    @_('LET var_id COLON type')
    def var_2(self, p):
        pass

    @_('ASSIG expr', 'ASSIG expr COMMA var_1', 'COMMMA var_1')
    def var_3(self, p):
        pass

    @_('ID','ID var_id_1')
    def var_id(self, p):
        pass

    @('LPAR CTE_I RPAR', 'LPAR CTE_I RPAR var_id_1')
    def var_id_1(self, p):
        pass