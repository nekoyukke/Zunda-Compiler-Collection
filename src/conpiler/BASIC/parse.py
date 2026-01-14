"""
IR設計を見直したためもう一度作成する

"""
from __future__ import annotations
import sys
from lexer import Token
from pathlib import Path

# When this module is executed directly the import `src.util` may fail because
# the parent of the `src` directory isn't on sys.path. Find the project root
# (the directory that contains the `src` folder) and add it to sys.path.
_p = Path(__file__).resolve()
repo_root = None
for a in ([_p] + list(_p.parents)):
    if (a / 'src').is_dir():
        repo_root = a
        break
if repo_root is None:
    # fallback: two levels up (best-effort)
    repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
import src.util as util

def CallError(tok:Token, message:str, name:str, source:str):
    raise util.ParseError(message, tok.lineno,tok.col,source, name)

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

    sz = "anyi" if size == -1 else f"i{size}"

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
    
    def stmt() -> str:
        assembly = ""
        while cu().type != "EOF":
            exp = expr()
            assembly += exp
        return assembly
    
    def expr() -> str:
        # YkIR
        nonlocal nowtab, iflevel, forlevel
        res = ""
        match (cu().type):
            case "IDENT":
                # 関数 or 代入
                # function or ASSGIN
                Ident:Token = ex("IDENT", "An identifier is required.", "Let")
                # ASS
                if cu().type == "ASS":
                    # ASSGIN
                    uselabel(Ident, "Ident ASS")
                    ex("ASS", "??", "Ident ASS")
                    # com sep
                    com = comp("Let")
                    res += com[0] + "\n"
                    if isglobal():
                        res += "    "*nowtab + f"void:store {sz}:@{com[1]}, {sz}*:@{Ident.value}\n"
                    else:
                        res += "    "*nowtab + f"void:store {sz}:%{com[1]}, {sz}*:%{Ident.value}\n"
                    ex("NEWLINE", "Error", "let")
                    return res
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
                res += com[0] + "\n"
                addlabel(Ident, "Let")
                if isglobal():
                    res += "    "*nowtab + f"@{Ident.value} = {sz}*:global {sz}\n"
                    res += "    "*nowtab + f"void:store {sz}:@{com[1]}, {sz}*:@{Ident.value}\n"
                else:
                    res += "    "*nowtab + f"%{Ident.value} = {sz}*:alloca {sz}\n"
                    res += "    "*nowtab + f"void:store {sz}:%{com[1]}, {sz}*:%{Ident.value}\n"
                ex("NEWLINE", "Error", "let")
                print(labeldict[Scope[-1]])
                return res
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
                res += "    "*nowtab + f"define {sz}:@{Ident.value}({", ".join([sz+ "*:" + i.value for i in Args])}) "+ "{\n"
                nowtab += 1
                res += "    "*nowtab + "entry:\n"
                nowtab += 1
                for i in Args:
                    addlabel(i, "Let")
                ex("NEWLINE", "Error", "Func")
                print(labeldict)
                print(Scope[-1])
                return res
            case "RET":
                ad("RET")
                # Ret
                com = comp("RET")
                res += com[0] + "\n"
                res += "    "*nowtab + f"void:ret {sz}:%{com[1]}\n"
                nowtab -= 2
                res += "    "*nowtab + "}\n"
                ex("NEWLINE", "Error", "Func")
                delllabel(Scope[-1], "Ret")
                return res
            case "IF":
                # if func
                ad("IF")
                buffer = ""
                # 比較
                iflevel += 1
                addr = usepos()
                com = comp("IF")
                if cu().type == "CMPOP":
                    cmp = ex("CMPOP", "Conditional branching requires an operator", "IF")
                    com2 = comp("IF")
                    cmpdict:dict[str, str] = {"==":"eq", "!=":"ne", ">":"gt", ">=":"ge", "<":"lt", "<=":"le"}
                    buffer += com[0]
                    buffer += com2[0]
                    if isglobal():
                        buffer += "    "*nowtab + f"@{addr} = i1:icmp {cmpdict[cmp.value]} {sz}:@{com[1]}, {sz}:@{com2[1]}\n"
                    else:
                        buffer += "    "*nowtab + f"%{addr} = i1:icmp {cmpdict[cmp.value]} {sz}:%{com[1]}, {sz}:%{com2[1]}\n"
                else:
                    buffer += com[0]
                    # pass
                    if isglobal():
                        buffer += "    "*nowtab + f"@{addr} = i1:bitcast {sz}:@{com[1]}\n"
                    else:
                        buffer += "    "*nowtab + f"%{addr} = i1:bitcast {sz}:%{com[1]}\n"
                # main
                tok:Token = ex("KEYWORD", "THEN does not exist.", "IF")
                if tok.value != "THEN":
                    CallError(tok, "THEN does not exist.", "IF", source)
                    raise
                nowtab -= 1
                res += "    "*nowtab + f"L{iflevel}if:\n"
                nowtab += 1
                ex("NEWLINE", "Error", "IF")
                # next funcs
                while cu().type != "KEYWORD" and cu().value != "END":
                    res += expr()
                ex("KEYWORD", "END dose not exist.", "IF")
                res += "    "*nowtab + f"void:br label L{iflevel}ifend\n"
                ex("NEWLINE", "Error", "IF")
                if cu().value == "ELSE" and cu().type == "KEYWORD":
                    ad("IF")
                    nowtab -= 1
                    res += "    "*nowtab + f"L{iflevel}else:\n"
                    nowtab += 1
                    ex("NEWLINE", "Error", "IF")
                    # next funcs
                    while cu().type != "KEYWORD" and cu().value != "END":
                        res += expr()
                    ex("KEYWORD", "END dose not exist.", "IF")
                    res += "    "*nowtab + f"void:br label L{iflevel}ifend\n"
                    ex("NEWLINE", "Error", "IF")
                    nowtab -= 1
                    res += "    "*nowtab + f"L{iflevel}ifend:\n"
                    nowtab += 1
                    if isglobal():
                        res = buffer + "    "*nowtab + f"void:br i1:@{addr}, label L{iflevel}if, label L{iflevel}else\n" + res
                    else:
                        res = buffer + "    "*nowtab + f"void:br i1:%{addr}, label L{iflevel}if, label L{iflevel}else\n" + res
                else:
                    nowtab -= 1
                    res += "    "*nowtab + f"L{iflevel}ifend:\n"
                    nowtab += 1
                    if isglobal():
                        res = buffer + "    "*nowtab + f"void:br i1:@{addr}, label L{iflevel}if, label L{iflevel}ifend\n" + res
                    else:
                        res = buffer + "    "*nowtab + f"void:br i1:%{addr}, label L{iflevel}if, label L{iflevel}ifend\n" + res
                return res
            case "FOR":
                ad("FOR")
                buffer = ""
                forlevel += 1
                return res
            case _:
                CallError(cu(), f"unkonw token {cu()}", "expr-end", source)
                raise

    def comp(name:str) -> tuple[str, int]:
        addr:int = usepos()
        isglobal_ = isglobal()
        cur = cu()
        scope = Getlabel()
        ad("Compute")
        res = ""
        # 数字
        #Number
        if cur.type == "NUMBER":
            if isglobal_:
                return "    "*nowtab + f"@{addr} = {cur.value}\n",addr
            return "    "*nowtab + f"%{addr} = {cur.value}\n", addr
        elif cur.type == "IDENT":
            if isglobal_:
                CallError(cur, "Variable usage is only allowed within the scope.", f"Compute-{name}",source)
                raise
            if cur.value in scope:
                return "    "*nowtab + f"%{addr} = {sz}:load {sz}*:%{cur.value}\n",addr
            if cur.value in labeldict["Global"]:
                return "    "*nowtab + f"%{addr} = {sz}:load {sz}*:@{cur.value}\n",addr
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
                res += "    "*nowtab + f"%{addr} = {sz}:call @{cur.value}({", ".join([sz+ "*:%" + i.value for i in Args])}) "
                return res, addr
            CallError(cur, "The identifier could not be found", f"Compute-{name}",source)
            raise
        elif cur.type == "LPAREN":
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
                            res += com1[0] + "\n"
                            res += com2[0] + "\n"
                            if isglobal_:
                                res += "    "*nowtab + f"@{addr} = {sz}:add {sz}:@{com1[1]}, {sz}:@{com2[1]}\n"
                            else:
                                res += "    "*nowtab + f"%{addr} = {sz}:add {sz}:%{com1[1]}, {sz}:%{com2[1]}\n"
                            com1 = com2
                            if cu().type == "RPAREN":
                                break
                            ex("COMMA", ", does not exist", f"Compute-{name}")
                            addr = usepos()
                        ex("RPAREN", "RPAREN missing; expression must be closed", f"Compute-{name}")
                        return res, addr
                    case "-":
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        com1 = comp(f"Compute-{name}")
                        ex("COMMA", ", does not exist", f"Compute-{name}")
                        print(com1)
                        while cu().type != "RPAREN":
                            com2 = comp(f"Compute-{name}")
                            res += com1[0] + "\n"
                            res += com2[0] + "\n"
                            if isglobal_:
                                res += "    "*nowtab + f"@{addr} = {sz}:sub {sz}:@{com1[1]}, {sz}:@{com2[1]}\n"
                            else:
                                res += "    "*nowtab + f"%{addr} = {sz}:sub {sz}:%{com1[1]}, {sz}:%{com2[1]}\n"
                            com1 = com2
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
                            res += com1[0] + "\n"
                            res += com2[0] + "\n"
                            if isglobal_:
                                res += "    "*nowtab + f"@{addr} = {sz}:mul {sz}:@{com1[1]}, {sz}:@{com2[1]}\n"
                            else:
                                res += "    "*nowtab + f"%{addr} = {sz}:mul {sz}:%{com1[1]}, {sz}:%{com2[1]}\n"
                            com1 = com2
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
                            res += com1[0] + "\n"
                            res += com2[0] + "\n"
                            if isglobal_:
                                res += "    "*nowtab + f"@{addr} = {sz}:divv {sz}:@{com1[1]}, {sz}:@{com2[1]}\n"
                            else:
                                res += "    "*nowtab + f"%{addr} = {sz}:divv {sz}:%{com1[1]}, {sz}:%{com2[1]}\n"
                            com1 = com2
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
                            res += com1[0] + "\n"
                            res += com2[0] + "\n"
                            if isglobal_:
                                res += "    "*nowtab + f"@{addr} = {sz}:divv {sz}:@{com1[1]}, {sz}:@{com2[1]}\n"
                            else:
                                res += "    "*nowtab + f"%{addr} = {sz}:divv {sz}:%{com1[1]}, {sz}:%{com2[1]}\n"
                            com1 = com2
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
                            res += com1[0] + "\n"
                            res += com2[0] + "\n"
                            if isglobal_:
                                res += "    "*nowtab + f"@{addr} = {sz}:gep {sz}:@{com1[1]}, {sz}:@{com2[1]}\n"
                            else:
                                res += "    "*nowtab + f"%{addr} = {sz}:gep {sz}:%{com1[1]}, {sz}:%{com2[1]}\n"
                            com1 = com2
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
    return stmt() + f"\n{sz}:call @main()"