from __future__ import annotations
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
"""
IR設計を見直したためもう一度作成する

"""
import sys
from src.compiler.basix_sharp.lexer import Token
from pathlib import Path
from typing import Optional
from src.Zir.zir import *
class ParseError(Exception):
    def __init__(self, message: str, line: int, column: int, source: str, name: str) -> None:
        self.message = message
        self.line = line
        self.column = column
        self.source = source
        self.name = name
        super().__init__(self.__str__())

    def __str__(self) -> str:
        # 行テキストを抽出
        line_text = self.source.splitlines()[self.line - 1]
        # カーソル位置に ^ を置く
        pointer = " " * (self.column - 1) + "^"
        return (
            f'\nTraceback: {self.name}'
            f'\n  File "<source>", line {self.line}\n'
            f"    {line_text}\n"
            f"    {pointer}\n"
            f"ParseError basix-sharp: {self.message}"
        )
    
def CallError(tok:Token, message:str, name:str, source:str):
    raise ParseError(message, tok.lineno,tok.col,source, name)

def parse(tokens:list[Token], source:str, size:int):
    """
    size -1 : anyi
    size n : i n
    """
    pos = 0
    labeldict:dict[str,dict[str,int]] = {"Global":{}} # Scope:{name : addr}
    llabelpos = 0
    glabelpos = 0
    iflevel = 0
    forlevel = 0
    Scope:list[str] = ["Global"]
    nowtab:int = 0
    Function:list[str] = []
    current_function:Optional[FunctionInstr] = None
    current_block:Optional[BlockInstr] = None
    assembly:list[Zir] = []

    sz:DataType = InstrType.iany if size == -1 else DataType(kind=TypeKind.INT, bits=size)
    psz:DataType = DataType.toptr(sz)

    def usepos() -> int:
        nonlocal llabelpos, glabelpos
        if Scope[-1] == "Global" and len(Scope) == 1:
            glabelpos += 1
            return glabelpos
        llabelpos += 1
        return llabelpos
    
    def addlabel(name:Token, namefunc:str) -> None:
        if name.value in labeldict[Scope[-1]]:
            CallError(name, f"variable {name.value} is duplicated.", namefunc, source)
            raise
        labeldict[Scope[-1]][name.value] = 0
    
    def uselabel(name:Token, namefunc:str) -> None:
        if name.value in labeldict[Scope[0]]:
            labeldict[Scope[0]][name.value] += 1
            return
        if not name.value in labeldict[Scope[-1]]:
            CallError(name, f"Variable {name.value} does not exist", namefunc, source)
            raise
        labeldict[Scope[-1]][name.value] += 1

    def isglobal() -> bool:
        return Scope[-1] == "Global" and len(Scope) == 1
    
    def Getlabel() -> dict[str,int]:
        return labeldict[Scope[-1]]
    
    def Addlabel(name:str, tok:Token, call:str):
        nonlocal Scope, Function
        if name in labeldict:
            CallError(tok, "Duplicate function declaration name.", call, source)
            raise
        labeldict[name] = {}
        Scope += [name]
        Function += [name]
        return

    def delllabel(name:str, call:str):
        if name not in labeldict:
            CallError(cu(), "Function declaration name not found.", call, source)
            raise
        labeldict.pop(name)
        Scope.pop(-1)
        return
            
    
    def ad(name:str):
        nonlocal pos
        pos += 1
        if len(tokens) <= pos:
            print(f"out of range of pos. now pos token:{tokens[pos-1]}")
            CallError(tokens[pos-1], "Error! Out of range", name, source)

    def cu():
        return tokens[pos]
    
    def ex(tt:str, message:str, name:str):
        if tt != cu().type:
            CallError(cu(), message, name, source)
        res = cu()
        ad(name)
        return res
    
    def stmt() -> list[Zir]:
        nonlocal assembly, current_function
        while cu().type != "EOF":
            if cu().type == "NEWLINE":
                ad("stmt-skip-newline")
                continue
            expr()
        if current_block is not None and current_function is not None:
            current_function.blocks += [current_block]
        if current_function is not None:
            assembly += [current_function]
        return assembly
    
    def next_label(name:str) -> None:
        nonlocal current_block, current_function
        if current_function is None or current_block is None:
            raise ParseError("program Block Error: this is bug. Please contact us with the program on github.", cu().lineno, cu().col, source, "NONE:Parser")  
        current_block.instr += [
            BranchInStr(
                None,
                InstrType.void,
                Label(name),
                Immediate(1),
                InstrType.i1
            )
        ]
        current_function.blocks += [current_block]
        current_block = BlockInstr(name)
        return
    
    # 副作用のみ
    def expr() -> None:
        # ZIR
        nonlocal nowtab, iflevel, forlevel, current_function, current_block, assembly
        if (cu().type == "NEWLINE"):
            ad("NEWLINE?PASS")
            return
        match (cu().type):
            case "IDENT":
                # 関数 or 代入
                # function or ASSGIN
                if tokens[pos+1].type == "LPAREN":
                    # 関数呼び出しを comp() に委譲
                    call = comp("CallStmt")
                    if isglobal():
                        assembly += call[0]
                    else:
                        if current_block is None:
                            raise ParseError("program Block Error: this is bug. Please contact us with the program on github.", cu().lineno, cu().col, source, "NONE:Parser")
                        current_block.instr += call[0]
                    ex("NEWLINE", "Error", "CallStmt")
                    return
                Ident:Token = ex("IDENT", "An identifier is required.", "Let")
                # ASS
                if cu().type == "ASS":
                    # ASSGIN
                    uselabel(Ident, "Ident ASS")
                    ex("ASS", "??", "Ident ASS")
                    # com sep
                    com = comp("Let")
                    if isglobal():
                        assembly += com[0]
                        assembly += [
                            StoreInStr(
                                None,
                                InstrType.void,
                                Register(str(com[1]), tRegister.GLOBAL),
                                sz,
                                Register(Ident.value, tRegister.GLOBAL),
                                psz,
                            )
                        ]
                    else:
                        if current_block is None:
                            raise ParseError("program Block Error: this is bug. Please contact us with the program on github.", cu().lineno, cu().col, source, "NONE:Parser")
                        current_block.instr += com[0]
                        assembly += [
                        StoreInStr(
                                None,
                                InstrType.void,
                                Register(str(com[1]), tRegister.LOCAL),
                                sz,
                                Register(Ident.value, tRegister.LOCAL),
                                psz,
                            )
                        ]
                    ex("NEWLINE", "Error", "let")
                    return
                pass
            case _:
                pass
        match (cu().value):
            case "LET":
                ad("Let")
                # letを分析
                # analyze let
                Ident:Token = ex("IDENT", "An identifier is required.", "Let")
                # ASS
                ex("ASS", "The = operator is unknown", "Let")
                # numbers
                com = comp("Let")
                addlabel(Ident, "Let")
                if isglobal():
                    assembly += com[0]
                    assembly += [
                        GlobalInstr(
                            Register(Ident.value, tRegister.GLOBAL),
                            psz,
                            sz
                        ),
                        StoreInStr(
                            None,
                            InstrType.void,
                            Register(str(com[1]), tRegister.GLOBAL),
                            sz,
                            Register(Ident.value, tRegister.GLOBAL),
                            psz
                        )
                    ]
                else:
                    if current_block is None:
                        raise ParseError("program Block Error: this is bug. Please contact us with the program on github.", cu().lineno, cu().col, source, "NONE:Parser")
                    current_block.instr += com[0]
                    alloca = AllocaInstr(
                        Register(Ident.value, tRegister.LOCAL),
                        psz,
                        sz
                    )
                    
                    if (current_function is not None):
                        current_function.add_local(Element(ElementType.Register, f"%{Ident.value}"))
                        current_function.add_local(Ident.value, Register(Ident.value, tRegister.LOCAL), alloca=alloca)
                    current_block.instr += [HiInstr(
                        "store",
                        None,
                        DataType(TypeKind.VOID, 0),
                        [
                            ElementPair(Element(ElementType.Register, f"%{com[1]}"), sz),
                            ElementPair(Element(ElementType.Register, f"%{Ident.value}"), psz)
                        ]
                    )]
                ex("NEWLINE", "Error", "let")
                print(labeldict[Scope[-1]])
                return
            case "FUNC":
                ad("Func")
                # Funcを分析
                # analyze func
                Ident:Token = ex("IDENT", "No function identifier", "Func")
                # Function Args
                ex("LPAREN", "The syntax for naming function arguments is not complete", "Func")
                # name onlry
                Args:list[Token] = []
                while cu().type != "RPAREN":
                    tok:Token = ex("IDENT", "The function arguments have not been declared", "Func")
                    Args.append(tok)
                    if cu().type == "RPAREN":
                        break
                    ex("COMMA", "The function arguments have not COMMA", "Func")
                ex("RPAREN", "The syntax for naming function arguments is not complete", "Func")
                Addlabel(Ident.value, Ident, "Func")
                current_function = hifuntction(
                    Ident.value,
                    sz,
                    [ElementPair(Element(ElementType.Register, f"%{i.value}"), psz) for i in Args],
                    set())
                current_block = BasicBlock("entry")
                for i in Args:
                    addlabel(i, "Let")
                ex("NEWLINE", "Error", "Func")
                print(labeldict)
                print(Scope[-1])
                while cu().type != "KEYWORD" or cu().value != "RET":
                    # RET検索
                    expr()
                ad("RET")
                # Ret
                com = comp("RET")
                current_block.instr += com[0]
                current_block.instr += [HiInstr(
                    "ret",
                    None,
                    DataType(TypeKind.VOID, 0),
                    [ElementPair(Element(ElementType.Register, f"%{com[1]}"), sz)]
                )]
                ex("NEWLINE", "Error", "Func")
                delllabel(Scope[-1], "Ret")
                return
            case "IF":
                # if func
                ad("IF")
                if isglobal():
                    raise ParseError("is not `if` in global", cu().lineno, cu().col, source, "sys")
                # 比較
                if current_function is None or current_block is None:
                    raise ParseError("program Block Error: this is bug. Please contact us with the program on github.", cu().lineno, cu().col, source, "NONE:Parser")  
                iflevel += 1
                nowlevel = iflevel
                next_label(f"L{nowlevel}if")
                addr = usepos()
                com = comp("IF")
                if cu().type == "CMPOP":
                    cmp = ex("CMPOP", "Conditional branching requires an operator", "IF")
                    com2 = comp("IF")
                    cmpdict:dict[str, str] = {"==":"eq", "!=":"ne", ">":"gt", ">=":"ge", "<":"lt", "<=":"le"}
                    current_block.instr += com[0]
                    current_block.instr += com2[0]
                    current_block.instr += [HiInstr(
                        "icmp",
                        Element(ElementType.Register, f"%{addr}"),
                        DataType(TypeKind.INT, 1),
                        [
                            ElementPair(Element(ElementType.CMPType, cmpdict.get(cmp.value, "eq"))),
                            ElementPair(Element(ElementType.Register, f"%{com[1]}"), sz),
                            ElementPair(Element(ElementType.Register, f"%{com2[1]}"), sz),
                        ]
                    )]
                else:
                    current_block.instr += com[0]
                    current_block.instr += [HiInstr(
                        "bitcast",
                        Element(ElementType.Register, f"%{addr}"),
                        DataType(TypeKind.INT, 1),
                        [
                            ElementPair(Element(ElementType.Register, f"%{com[1]}"), sz)
                        ]
                    )]
                # main
                tok:Token = ex("KEYWORD", "THEN does not exist.", "IF")
                if tok.value != "THEN":
                    CallError(tok, "THEN does not exist.", "IF", source)
                    raise
                next_label(f"L{nowlevel}iftrue")
                ex("NEWLINE", "Error", "IF")
                # next funcs
                while cu().type != "KEYWORD" or cu().value != "END":
                    expr()
                ex("KEYWORD", "END dose not exist.", "IF")
                current_block.instr += [HiInstr(
                    "br",
                    None,
                    DataType(TypeKind.VOID, 0),
                    [
                        ElementPair(Element(ElementType.Label, f"L{nowlevel}ifend"), DataType(TypeKind.LABEL, None))
                    ]
                )]
                ex("NEWLINE", "Error", "IF")
                if cu().value == "ELSE" and cu().type == "KEYWORD":
                    ad("IF")
                    next_label(f"L{nowlevel}iffalse")
                    ex("NEWLINE", "Error", "IF")
                    # next funcs
                    while cu().type != "KEYWORD" and cu().value != "END":
                        expr()
                    ex("KEYWORD", "END dose not exist.", "IF")
                    current_block.instr += [HiInstr(
                        "br",
                        None,
                        DataType(TypeKind.VOID, 0),
                        [
                            ElementPair(Element(ElementType.Label, f"L{nowlevel}ifend"), DataType(TypeKind.LABEL, None))
                        ]
                    )]
                    ex("NEWLINE", "Error", "IF")
                    next_label(f"L{nowlevel}ifend")
                    res = HiInstr(
                        "br",
                        None,
                        DataType(TypeKind.VOID, 0),
                        [
                            ElementPair(Element(ElementType.Register, f"%{addr}"), DataType(TypeKind.INT, 1)),
                            ElementPair(Element(ElementType.Label, f"L{nowlevel}iftrue"), DataType(TypeKind.LABEL, None)),
                            ElementPair(Element(ElementType.Label, f"L{nowlevel}iffalse"), DataType(TypeKind.LABEL, None))
                        ]
                    )
                else:
                    next_label(f"L{nowlevel}ifend")
                    res = HiInstr(
                        "br",
                        None,
                        DataType(TypeKind.VOID, 0),
                        [
                            ElementPair(Element(ElementType.Register, f"%{addr}"), DataType(TypeKind.INT, 1)),
                            ElementPair(Element(ElementType.Label, f"L{nowlevel}iftrue"), DataType(TypeKind.LABEL, None)),
                            ElementPair(Element(ElementType.Label, f"L{nowlevel}ifend"), DataType(TypeKind.LABEL, None))
                        ]
                    )
                current_function.blocks[[i.label for i in current_function.blocks].index(f"L{nowlevel}if")].instructions.pop()
                current_function.blocks[[i.label for i in current_function.blocks].index(f"L{nowlevel}if")].instructions += [res]
                return
            case "FOR":
                addr = usepos()
                addr = usepos()
                addr = usepos()
                if isglobal():
                    CallError(cu(), "The for syntax cannot be used in a global environment.", "FOR", source)
                    raise
                if current_function is None or current_block is None:
                    raise ParseError("program Block Error: this is bug. Please contact us with the program on github.", cu().lineno, cu().col, source, "NONE:Parser")  
                # FOR I 0 TO numbers

                ad("FOR")
                forlevel += 1
                nowlevel = forlevel
                Ident = ex("IDENT", "The Ident is unclear", "FOR")
                com = comp("FOR")
                tok = ex("KEYWORD", "The 'TO' is unclear", "FOR")
                if tok.value != "TO":
                    CallError(tok, "The 'TO' is unclear", "FOR", source)
                    raise
                com2 = comp("FOR")
                current_block.instr += com[0]
                current_block.instr += com2[0]
                current_block.instr += [HiInstr(
                    "alloca",
                    Element(ElementType.Register, f"%{Ident.value}"),
                    psz,
                    [ElementPair(None, sz)]
                )]
                current_function.add_stack_var(Element(ElementType.Register, f"%{Ident.value}"))
                current_block.instr += [HiInstr(
                    "store",
                    None,
                    DataType(TypeKind.VOID, 0),
                    [
                        ElementPair(Element(ElementType.Register, f"%{com[1]}"), sz),
                        ElementPair(Element(ElementType.Register, f"%{Ident.value}"), psz)
                    ]
                )]
                # はじめ
                next_label(f"L{nowlevel}FOR")
                # stmt処理
                addlabel(Ident, "For")
                ex("NEWLINE", "Error", "IF")
                # ifと同じ
                while cu().type != "KEYWORD" or cu().value != "NEXT":
                    expr()
                ad("for")
                # next切り替え部
                next_label(f"L{nowlevel}FORNEXT")
                # NEXT処理
                current_block.instr += [
                    HiInstr(
                        "load",
                        Element(ElementType.Register, f"%{addr - 2}"),
                        sz,
                        [ElementPair(Element(ElementType.Register, f"%{Ident.value}"), psz)]
                    ),
                    HiInstr(
                        "inc",
                        Element(ElementType.Register, f"%{addr}"),
                        sz,
                        [ElementPair(Element(ElementType.Register, f"%{addr- 2}"), sz)]
                    ),
                    HiInstr(
                        "store",
                        None,
                        DataType(TypeKind.VOID, 0),
                        [
                            ElementPair(Element(ElementType.Register, f"%{addr}"), sz),
                            ElementPair(Element(ElementType.Register, f"%{Ident.value}"), psz)
                        ]
                    ),
                    HiInstr(
                        "icmp",
                        Element(ElementType.Register, f"%{addr - 1}"),
                        DataType(TypeKind.INT, 1),
                        [
                            ElementPair(Element(ElementType.CMPType, "lt")),
                            # inc した後の結果である %{addr} と比較する
                            ElementPair(Element(ElementType.Register, f"%{addr}"), sz), 
                            ElementPair(Element(ElementType.Register, f"%{com2[1]}"), sz)
                        ]
                    ),
                    HiInstr(
                        "br",
                        None,
                        DataType(TypeKind.VOID, 0),
                        [
                            ElementPair(Element(ElementType.Register, f"%{addr - 1}"), DataType(TypeKind.INT, 1)),
                            ElementPair(Element(ElementType.Label, f"L{nowlevel}FOR"), DataType(TypeKind.LABEL, None)),
                            ElementPair(Element(ElementType.Label, f"L{nowlevel}FOREND"), DataType(TypeKind.LABEL, None)),
                        ]
                    )
                ]
                # 終了
                next_label(f"L{nowlevel}FOREND")
                ex("NEWLINE", "Error", "IF")
                return
            case _:
                CallError(cu(), f"unkonw token {cu()}", "expr-end", source)
                raise

    def comp(name:str) -> tuple[list[Instruction], int]:
        addr:int = usepos()
        print(f"comp addr:{addr}")
        isglobal_ = isglobal()
        cur = cu()
        scope = Getlabel()
        ad("Compute")
        # 数字
        #Number
        if cur.type == "NUMBER":
            if isglobal_:
                return [HiInstr(
                    "const",
                    Element(ElementType.Register, f"%{addr}"),
                    sz,
                    [
                        ElementPair(Element(ElementType.Immediate, cur.value), sz)
                    ]
                )], addr
            return [HiInstr(
                "const",
                Element(ElementType.Register, f"%{addr}"),
                sz,
                [
                    ElementPair(Element(ElementType.Immediate, cur.value), sz)
                ]
            )], addr
        elif cur.type == "IDENT":
            if isglobal_:
                CallError(cur, "Variable usage is only allowed within the scope.", f"Compute-{name}",source)
                raise
            if cur.value in scope:
                return [HiInstr(
                    "load",
                    Element(ElementType.Register, f"%{addr}"),
                    sz,
                    [
                        ElementPair(Element(ElementType.Immediate, f"%{cur.value}"), psz)
                    ]
                )], addr
            if cur.value in labeldict["Global"]:
                return [HiInstr(
                    "load",
                    Element(ElementType.Register, f"%{addr}"),
                    sz,
                    [
                        ElementPair(Element(ElementType.Immediate, f"@{cur.value}"), psz)
                    ]
                )], addr
            if cur.value in Function:
                ex("LPAREN", "The syntax for naming function arguments is not complete", "callFunc")
                # anarlyz args
                Args:list[Token] = []
                while cu().type != "RPAREN":
                    tok:Token = ex("IDENT", "The function arguments have not been declared", "callFunc")
                    Args.append(tok)
                    if cu().type == "RPAREN":
                        break
                    ex("COMMA", "The function arguments have not COMMA", "callFunc")
                ex("RPAREN", "The syntax for naming function arguments is not complete", "callFunc")
                return [HiInstr(
                    "call",
                    Element(ElementType.Register, f"%{addr}"),
                    sz,
                    [
                        ElementPair(Element(ElementType.Register, f"@{cur.value}")),
                        *[ElementPair(Element(ElementType.Register, f"%{i.value}"), psz)
                        for i in Args]
                    ]
                )], addr
            CallError(cur, "The identifier could not be found", f"Compute-{name}",source)
            raise
        elif cur.type == "LPAREN":
            res:list[HiInstr] = []
            # 関数または演算子
            # Function or Op
            if cu().type == "OP":
                # Op
                cur = cu()
                ad(f"Compute-{name}")
                match (cur.value):
                    case "+":
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        com1 = comp(f"Compute-{name}")
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        print(com1)
                        while cu().type != "RPAREN":
                            com2 = comp(f"Compute-{name}")
                            res += com1[0]
                            res += com2[0]
                            addr = usepos()
                            print(f"comp addr:{addr}")
                            print(f"comp addr1:{com1[0]}")
                            print(f"comp addr2:{com2[0]}")
                            if isglobal_:
                                res += [HiInstr(
                                    "add",
                                    Element(ElementType.Register, f"@{addr}"),
                                    sz,
                                    [
                                        ElementPair(Element(ElementType.Register, f"@{com1[1]}"), sz),
                                        ElementPair(Element(ElementType.Register, f"@{com2[1]}"), sz)
                                    ]
                                )]
                            else:
                                res += [HiInstr(
                                    "add",
                                    Element(ElementType.Register, f"%{addr}"),
                                    sz,
                                    [
                                        ElementPair(Element(ElementType.Register, f"%{com1[1]}"), sz),
                                        ElementPair(Element(ElementType.Register, f"%{com2[1]}"), sz)
                                    ]
                                )]
                            com1 = ([], com2[1]) # type: ignore
                            if cu().type == "RPAREN":
                                break
                            ex("COMMA", ", does not exist", f"Compute-{name}")
                        ex("RPAREN", "RPAREN missing; expression must be closed", f"Compute-{name}")
                        return res, addr
                    case "-":
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        com1 = comp(f"Compute-{name}")
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        print(com1)
                        while cu().type != "RPAREN":
                            com2 = comp(f"Compute-{name}")
                            res += com1[0]
                            res += com2[0]
                            if isglobal_:
                                res += [HiInstr(
                                    "sub",
                                    Element(ElementType.Register, f"@{addr}"),
                                    sz,
                                    [
                                        ElementPair(Element(ElementType.Register, f"@{com1[1]}"), sz),
                                        ElementPair(Element(ElementType.Register, f"@{com2[1]}"), sz)
                                    ]
                                )]
                            else:
                                res += [HiInstr(
                                    "sub",
                                    Element(ElementType.Register, f"%{addr}"),
                                    sz,
                                    [
                                        ElementPair(Element(ElementType.Register, f"%{com1[1]}"), sz),
                                        ElementPair(Element(ElementType.Register, f"%{com2[1]}"), sz)
                                    ]
                                )]
                            com1 = ([], com2[1]) # type: ignore
                            if cu().type == "RPAREN":
                                break
                            ex("COMMA", ", does not exist", f"Compute-{name}")
                            addr = usepos()
                        ex("RPAREN", "RPAREN missing; expression must be closed", f"Compute-{name}")
                        return res, addr
                    case "*":
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        com1 = comp(f"Compute-{name}")
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        print(com1)
                        while cu().type != "RPAREN":
                            com2 = comp(f"Compute-{name}")
                            res += com1[0]
                            res += com2[0]
                            if isglobal_:
                                res += [HiInstr(
                                    "mul",
                                    Element(ElementType.Register, f"@{addr}"),
                                    sz,
                                    [
                                        ElementPair(Element(ElementType.Register, f"@{com1[1]}"), sz),
                                        ElementPair(Element(ElementType.Register, f"@{com2[1]}"), sz)
                                    ]
                                )]
                            else:
                                res += [HiInstr(
                                    "mul",
                                    Element(ElementType.Register, f"%{addr}"),
                                    sz,
                                    [
                                        ElementPair(Element(ElementType.Register, f"%{com1[1]}"), sz),
                                        ElementPair(Element(ElementType.Register, f"%{com2[1]}"), sz)
                                    ]
                                )]
                            com1 = ([], com2[1]) # type: ignore
                            if cu().type == "RPAREN":
                                break
                            ex("COMMA", ", does not exist", f"Compute-{name}")
                            addr = usepos()
                        ex("RPAREN", "RPAREN missing; expression must be closed", f"Compute-{name}")
                        return res, addr
                    case "/":
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        com1 = comp(f"Compute-{name}")
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        print(com1)
                        while cu().type != "RPAREN":
                            com2 = comp(f"Compute-{name}")
                            res += com1[0]
                            res += com2[0]
                            if isglobal_:
                                res += [HiInstr(
                                    "divv",
                                    Element(ElementType.Register, f"@{addr}"),
                                    sz,
                                    [
                                        ElementPair(Element(ElementType.Register, f"@{com1[1]}"), sz),
                                        ElementPair(Element(ElementType.Register, f"@{com2[1]}"), sz)
                                    ]
                                )]
                            else:
                                res += [HiInstr(
                                    "divv",
                                    Element(ElementType.Register, f"%{addr}"),
                                    sz,
                                    [
                                        ElementPair(Element(ElementType.Register, f"%{com1[1]}"), sz),
                                        ElementPair(Element(ElementType.Register, f"%{com2[1]}"), sz)
                                    ]
                                )]
                            com1 = ([], com2[1]) # type: ignore
                            if cu().type == "RPAREN":
                                break
                            ex("COMMA", ", does not exist", f"Compute-{name}")
                            addr = usepos()
                        ex("RPAREN", "RPAREN missing; expression must be closed", f"Compute-{name}")
                        return res, addr
                    case "%":
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        com1 = comp(f"Compute-{name}")
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        print(com1)
                        while cu().type != "RPAREN":
                            com2 = comp(f"Compute-{name}")
                            res += com1[0]
                            res += com2[0]
                            if isglobal_:
                                res += [HiInstr(
                                    "divv",
                                    Element(ElementType.Register, f"@{addr}"),
                                    sz,
                                    [
                                        ElementPair(Element(ElementType.Register, f"@{com1[1]}"), sz),
                                        ElementPair(Element(ElementType.Register, f"@{com2[1]}"), sz)
                                    ]
                                )]
                            else:
                                res += [HiInstr(
                                    "divv",
                                    Element(ElementType.Register, f"%{addr}"),
                                    sz,
                                    [
                                        ElementPair(Element(ElementType.Register, f"%{com1[1]}"), sz),
                                        ElementPair(Element(ElementType.Register, f"%{com2[1]}"), sz)
                                    ]
                                )]
                            com1 = ([], com2[1]) # type: ignore
                            if cu().type == "RPAREN":
                                break
                            ex("COMMA", ", does not exist", f"Compute-{name}")
                            addr = usepos()
                        ex("RPAREN", "RPAREN missing; expression must be closed", f"Compute-{name}")
                        return res, addr
                    case "addr":
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        com1 = comp(f"Compute-{name}")
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        print(com1)
                        while cu().type != "RPAREN":
                            com2 = comp(f"Compute-{name}")
                            res += com1[0]
                            res += com2[0]
                            if isglobal_:
                                res += [HiInstr(
                                    "gep",
                                    Element(ElementType.Register, f"@{addr}"),
                                    sz,
                                    [
                                        ElementPair(Element(ElementType.Register, f"@{com1[1]}"), sz),
                                        ElementPair(Element(ElementType.Register, f"@{com2[1]}"), sz)
                                    ]
                                )]
                            else:
                                res += [HiInstr(
                                    "gep",
                                    Element(ElementType.Register, f"%{addr}"),
                                    sz,
                                    [
                                        ElementPair(Element(ElementType.Register, f"%{com1[1]}"), sz),
                                        ElementPair(Element(ElementType.Register, f"%{com2[1]}"), sz)
                                    ]
                                )]
                            com1 = ([], com2[1]) # type: ignore
                            if cu().type == "RPAREN":
                                break
                            ex("COMMA", ", does not exist", f"Compute-{name}")
                            addr = usepos()
                        ex("RPAREN", "RPAREN missing; expression must be closed", f"Compute-{name}")
                        return res, addr
                    case _:
                        CallError(cur, f"unkwon Token {cur}", f"Compute-{name}", source)
                        raise
            CallError(cur, "unkwon", f"Compute-{name}",source)
            raise
        CallError(cur, "unkwon", f"Compute-{name}",source)
        raise
    return stmt() + [HiInstr(
        "call",
        None,
        sz,
        [ElementPair(Element(ElementType.Register, f"@main"))]
    )]