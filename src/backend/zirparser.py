"""
This file is part of Zunda Compiler Collection.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
z
You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
# パース
import re
from dataclasses import dataclass
from typing import Optional
from src.backend.util import ParseError
from src.Zir.zir import *

@dataclass
class Token:
    type: str # 'REGISTER', 'TYPE', 'OP', 'COLON', 'EQUAL', 'NUMBER' など
    value: str
    line: int
    colum: int
    len: int



class ZirLexer:
    def __init__(self, source_code: str):
        self.source_code:str = source_code
        self.tokens:list[Token] = []
        self.line_num = 1
        self.col = 1

        # トークン定義（順序が重要：長いものや特殊なものを先に）
        self.rules = [
            ('COMMENT',  r';.*'),
            ('GLOBAL',  r'@[A-Za-z0-9_]+'),
            ('LOCAL',  r'%[A-Za-z0-9_]+'),
            ('LABELST',  r'[A-Za-z_][A-Za-z0-9_]*:'),
            ('LABEL',  r'[A-Za-z_][A-Za-z0-9_]*'),
            ('NUMBER',  r'\d+'),
            ('PTR',  r'\*'),
            ('LBRACE',   r'\{'),
            ('RBRACE',   r'\}'),
            ('LPAREN',   r'\('),
            ('RPAREN',   r'\)'),
            ('EQUAL',    r'='),
            ('COLON',    r':'),
            ('COMMA',    r','),
            ('NEWLINE',  r'\n'),
            ('SKIP',     r'[ \t]+'),
            ('MISMATCH', r'.'),
        ]
    def get_tokenizelist(self) -> list[Token]:
        if not self.tokens:
            self.tokenize()
        return self.tokens

    def tokenize(self) -> list[Token]:
        # すべてのルールを結合して一つの正規表現にする
        regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.rules)
        
        for mo in re.finditer(regex, self.source_code):
            kind = mo.lastgroup
            value = mo.group()

            if kind == "NEWLINE":
                self.line_num += 1
                self.col = 1
                continue
            if kind == "SKIP":
                self.col += len(value)
                continue
            
            if kind == 'MISMATCH':
                raise SyntaxError(f'Unexpected character {value} at line {self.line_num}')
            
            if kind is None:
                raise RuntimeError("What Error")

            # トークンオブジェクトをリストに追加
            self.tokens.append(Token(kind, value, self.line_num, self.col, len(value)))
            self.col += len(value)
        self.tokens.append(Token("EOF", "", self.line_num, 0, 0))
        return self.tokens
    

class ZirParser:
    def __init__(self, tokens:list[Token], source:str) -> None:
        self.tokens = tokens
        self.source = source
        self.pos = 0

    def CallError(self, message:str, tok:Token, name:str):
        raise ParseError(message, tok.len, tok.colum, source, tok.len, name)

    def advance(self):
        self.pos += 1
    
    def peek(self) -> Token:
        return self.tokens[self.pos]
    
    def eat(self, tt:str, message:str, name:str) -> Token:
        if self.peek().type == tt:
            pek = self.peek()
            self.advance()
            return pek
        else:
            self.CallError(message, self.peek(), name)
    
    def match(self, tt:str):
        if self.peek().type == tt:
            self.advance()
            return True
        else:
            return False

    def Parse(self):
        AST = ModuleInstr()
        while self.peek().type != "EOF":
            AST.addInstr(self.LogicInstr())
        return AST
    
    def LogicInstr(self) -> Instruction | BlockInstr | FunctionInstr:
        pek = self.peek()
        if pek.type == "LABEL" and pek.value.upper() == "DEFINE":
            return self.Func()
        elif pek.type == "LABELST":
            return self.Block()
        return self.Instr()

    def Instr(self) -> Instruction:
        pek = self.peek()
        if pek.type == "LABEL":
            return self.Stmt()
        elif pek.type in ("GLOBAL", "LOCAL"):
            return self.AssignStmt()
        self.CallError(f"Unkwon Tokens {self.peek()}", self.peek(), "Stmt")

    def AssignStmt(self) -> Instruction:
        # register = type:op type:value...
        reg = self.Parse_Register()
        self.eat("COLON", "Assign Error", "AssignStmt")
        stmt = self.Stmt()
        stmt.dest = reg
        return stmt
    
    def Stmt(self) -> Instruction:
        # type :op type:value...
        dtype = self.Parse_Type()
        op = self.eat("LABEL", "Op", "Stmt")
        match (op.value):
            case _ if op.value in [i.value for i in BinaryOpType]:
                # バイナリー
                src1t = self.Parse_Type()
                self.eat("COLON", "not found :", "Stmt")
                src1 = self.Parse_value()
                src2t = self.Parse_Type()
                self.eat("COLON", "not found :", "Stmt")
                src2 = self.Parse_value()
                return BinaryInstr(dest=None, desttype=dtype, op=BinaryOpType[op.value], src1=src1, src1type=src1t, src2=src2, src2type=src2t)
            case _ if op.value in [i.value for i in UnaryOpType]:
                # 単項
                src1t = self.Parse_Type()
                self.eat("COLON", "not found :", "Stmt")
                src1 = self.Parse_value()
                return UnaryInstr(dest=None, desttype=dtype, op=UnaryOpType[op.value], src=src1, srctype=src1t)
            case "icmp":
                raise
            case "alloca":
                src1t = self.Parse_Type()
                return AllocaInstr(dest=None, desttype=dtype, type=src1t)
            case "global":
                src1t = self.Parse_Type()
                return GlobalInstr(dest=None, desttype=dtype, type=src1t)
            case "store":
                src1t = self.Parse_Type()
                self.eat("COLON", "not found :", "Stmt")
                src1 = self.Parse_Register()
                src2t = self.Parse_Type()
                self.eat("COLON", "not found :", "Stmt")
                src2 = self.Parse_value()
                return StoreInStr(dest=None, desttype=dtype, src1=src1, src1type=src1t, src2=src2, src2type=src2t)
            case "load":
                src1t = self.Parse_Type()
                self.eat("COLON", "not found :", "Stmt")
                src1 = self.Parse_Register()
                return LoadInStr(dest=None, desttype=dtype, src1=src1, src1type=src1t)
            case _:
                self.CallError("Value Check", op, "Stmt")


    def Block(self) -> BlockInstr:
        labelst = self.eat("LABELST", "", "Block")
        block = BlockInstr(labelst.value)
        while not(self.peek().type in ("RBRACE", "LABELST")):
            instr = self.Instr()
            block.add(instr)
        return block

    def Func(self) -> FunctionInstr:
        deftok = self.eat("LABEL", "define", "FUNC")
        if deftok.value != "define":
            self.CallError("define", deftok, "FUNC")
    
    def Parse_Parm(self) -> Parm:


    def Parse_value(self) -> Value:
        tok = self.peek()
        if tok.type == "LOCAL":
            return self.Parse_Register()
        elif tok.type == "GLOBAL":
            return self.Parse_Register()
        elif tok.type == "NUMBER":
            return self.Parse_Immediate()
        elif tok.type == "LABEL":
            return self.Parse_Label()
        self.CallError(f"unkown Value {tok.value}", tok, "Parse_Value")
    
    def Parse_Register(self) -> Register:
        tok = self.peek()
        if self.match("LOCAL"):
            return Register(tok.value[1:], tRegister.LOCAL)
        elif self.match("GLOBAL"):
            return Register(tok.value[1:], tRegister.GLOBAL)
        else:
            self.CallError("not Register", tok, "Parse_Register")
    
    def Parse_Label(self) -> Label:
        tok = self.eat("LABEL", "Not Label", "Parse label")
        return Label(tok.value)

    def Parse_Immediate(self) -> Immediate:
        tok = self.eat("NUMBER", "not Number", "Parse Immediate")
        return Immediate(int(tok.value))

    def Parse_Type(self) -> DataType:
        tok = self.eat("LABEL", "Expected type label", "Parse Type")
        depth = 0
        while self.match("PTR"):
            depth += 1
        t_str = tok.value
        kind = TypeKind.VOID if t_str == "void" else \
               TypeKind.INT if t_str.startswith('i') else \
               TypeKind.UINT if t_str.startswith('u') else TypeKind.FLOAT
        
        match = re.search(r'\d+', t_str)
        bits = int(match.group()) if match else None
        return DataType(kind, bits, depth)



if __name__ == "__main__":
    source = """
%1 = i32:add i32:12, i32:30
"""
    lexer = ZirLexer(source)
    print(lexer.get_tokenizelist())