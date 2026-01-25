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

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
# パース
import re
from dataclasses import dataclass
from src.targets import TargetBase
from src.dataobject import hiinstr
from typing import Optional
@dataclass
class Token:
    type: str   # 'REGISTER', 'TYPE', 'OP', 'COLON', 'EQUAL', 'NUMBER' など
    value: str
    line: int

class ZirLexer:
    def __init__(self, source_code: str):
        self.source_code:str = source_code
        self.tokens:list[Token] = []
        self.line_num = 1

        # トークン定義（順序が重要：長いものや特殊なものを先に）
        self.rules = [
            ('COMMENT',  r';.*'),
            ('ID', r'(@|%)[a-zA-Z0-9_]+'), 
            # 型 (i32, f64, void, str とポインタ)
            ('TYPE',     r'(label|(?:[fi][0-9]+|void|str)(?:\*+)?)'),
            ('CMPTYPE',  r'eq|ne|gt|ge|lt|le'),
            ('LABEL', r'[a-zA-Z0-9_]+:'), 
            # 命令 (define, add, ret, global 等)
            ('OP',       r'[a-z][a-z0-9_]*'),
            # 記号類
            ('LBRACE',   r'\{'),
            ('RBRACE',   r'\}'),
            ('LPAREN',   r'\('),
            ('RPAREN',   r'\)'),
            ('EQUAL',    r'='),
            ('COLON',    r':'),
            ('COMMA',    r','),
            ('NUMBER',   r'[0-9]+'),
            ('NEWLINE',  r'\n'),
            ('SKIP',     r'[ \t]+'),
            ('VALUELABEL', r'[a-zA-Z0-9_]+'), 
            ('MISMATCH', r'.'),
        ]
    def get_tokenizelist(self) -> list[Token]:
        if self.source_code == "": return []
        if self.tokens is []:
            self.tokenize()
        return self.tokens

    def tokenize(self) -> list[Token]:
        # すべてのルールを結合して一つの正規表現にする
        regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.rules)
        
        for mo in re.finditer(regex, self.source_code):
            kind = mo.lastgroup
            value = mo.group()
            
            if kind == 'SKIP' or kind == 'COMMENT':
                continue
            elif kind == 'NEWLINE':
                self.line_num += 1
            elif kind == 'MISMATCH':
                raise SyntaxError(f'Unexpected character {value} at line {self.line_num}')
            
            if kind is None:
                raise RuntimeError("What Error")

            # トークンオブジェクトをリストに追加
            self.tokens.append(Token(kind, value, self.line_num))
        self.tokens.append(Token("EOF", "", self.line_num))
        return self.tokens

class ZirParser():
    def __init__(self, Tokens:list[Token]):
        self.tokens = Tokens
        self.pos = 0
        self.toklen = len(Tokens)

    def posadd(self):
        self.pos += 1

    def consume(self, tt:str) -> bool:
        if self.peek().type == tt:
            self.posadd()
            return True
        return False
    
    def expect(self, tt:str) -> Token:
        peek = self.peek()
        if self.peek().type == tt:
            self.posadd()
            return peek
        raise RuntimeError

    def peek(self, cnt:list[int]=[0]) -> Token:
        cnt[0] += 1
        if (self.pos == self.toklen):
            return Token("", "", -1)
        print(f"count:{cnt[0]} {self.pos}:{self.tokens[self.pos]}")
        return self.tokens[self.pos]

    def ZirParse(self) -> list[hiinstr.AllElement]:
        hiiinstrs:list[hiinstr.AllElement] = []
        while (self.peek().type != "EOF"):
            # stmt
            hiiinstrs += self.stmt()
            print(self.pos)
        return hiiinstrs
    
    def stmt(self) -> list[hiinstr.AllElement]:
        # function, block以外の場合のみ通常処理
        # if BasicBlock
        while self.consume("NEWLINE"):
            pass
        if (self.peek().type == "OP" and self.peek().value == "define"):
            # function
            return [self.parse_function()]
        elif (self.peek().type == "LABEL"):
            return [self.parse_block()]
        else:
            instr = self.op()
            while self.consume("NEWLINE"):
                pass
            return [instr]
        
    def parse_block(self) -> hiinstr.BasicBlock:
        while self.consume("NEWLINE"):
            pass
        label: Token = self.expect("LABEL")
        while self.consume("NEWLINE"):
            pass
        label.value = label.value[:-1]
        block: hiinstr.BasicBlock = hiinstr.BasicBlock(label.value)
        while True:
            while self.consume("NEWLINE"):
                pass
            tok = self.peek()  # 次のトークンを確認
            if tok.type in ("LABEL", "RBRACE", "EOF"): # 終端条件
                break
            instr = self.op()
            block.instructions.append(instr)
        return block

    def parse_function(self) -> hiinstr.Function:
        self.expect("OP") # 'define'
        type_token = self.expect("TYPE")
        self.expect("COLON")
        name_token = self.expect("ID") # @main
        self.expect("LPAREN")
        # 引数 type:src
        args: list[hiinstr.ElementPair] = []
        while self.peek().type != "RPAREN":
            types = self.expect("TYPE")
            self.expect(":")
            ids =self.expect("ID")
            args.append(hiinstr.ElementPair(
                hiinstr.Element.parse_element(types.value),
                hiinstr.DataType.parse_datatype(ids.value)
            ))
        self.expect("RPAREN")
        self.expect("LBRACE")
        func = hiinstr.Function(
            name_token.value[1:],
            hiinstr.DataType.parse_datatype(type_token.value),
            args,
            set()
        )
        # ブロック等
        block:list[hiinstr.BasicBlock] = []
        while self.peek().type != "RBRACE":
            block += [self.parse_block()]
        func.blocks = block
        self.expect("RBRACE")
        return func

    def op(self) -> hiinstr.HiInstr:
        # 値破棄しない場合
        if self.peek().type != "TYPE":
            idtok = self.expect("ID")
            self.expect("EQUAL")
            # 型
            typetok = self.expect("TYPE")
            self.expect("COLON")
            optok = self.expect("OP")
            hiin = hiinstr.HiInstr(optok.value,
                                   hiinstr.Element(hiinstr.ElementType.Register, idtok.value),
                                   hiinstr.DataType.parse_datatype(typetok.value))
        else:
            # 型
            typetok = self.expect("TYPE")
            self.expect("COLON")
            optok = self.expect("OP")
            hiin = hiinstr.HiInstr(optok.value, None, hiinstr.DataType.parse_datatype(typetok.value))
        # 型またはValue
        while (self.peek().type != "NEWLINE" and self.peek().type != "EOF"):
            if self.peek().type == "CMPTYPE":
                hiin.src.append(hiinstr.ElementPair((hiinstr.Element.parse_element(self.peek().value))))
                self.expect("CMPTYPE")
            else:
                if self.peek().type == "ID":
                    hiin.src.append(hiinstr.ElementPair(hiinstr.Element.parse_element(self.peek().value)))
                    self.expect("ID")
                else:
                    types = self.expect("TYPE")
                    if self.peek().type != "COLON":
                        hiin.src.append(hiinstr.ElementPair(stype=hiinstr.DataType.parse_datatype(types.value)))
                    else:
                        self.expect("COLON")
                        if self.peek().type == "VALUELABEL":
                            values = self.expect("VALUELABEL")
                        elif self.peek().type == "NUMBER":
                            values = self.expect("NUMBER")
                        else:
                            values = self.expect("ID")
                        hiin.src.append(hiinstr.ElementPair(hiinstr.Element.parse_element(values.value), hiinstr.DataType.parse_datatype(types.value)))
            if self.peek().type == "NEWLINE":
                continue
            self.consume("COMMA")
        return hiin