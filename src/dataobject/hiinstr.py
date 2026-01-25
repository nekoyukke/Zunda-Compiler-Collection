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
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum, auto


class TypeKind(Enum):
    INT = auto()     # 整数
    FLOAT = auto()   # 浮動小数点
    VOID = auto()    # 戻り値なし
    LABEL = auto()   # ラベル

@dataclass
class DataType:
    kind: TypeKind
    bits: Optional[int]          # 8, 16, 32, 64, 128
    is_signed: bool = True
    ptr_depth: int = 0 # 0なら値、1ならポインタ(*)

    def get_bytes(self):
        """バイトサイズを計算（16bitなら2）"""
        if (self.bits is None):
            return 0
        return self.bits // 8

    def __repr__(self):
        if self.kind == TypeKind.LABEL:
            return "label"
        if self.kind == TypeKind.INT:
            prefix = "u" if not self.is_signed else "i"
            suffix = "*" * self.ptr_depth
            return f"{prefix}{self.bits}{suffix}"
        elif self.kind == TypeKind.FLOAT:
            suffix = "*" * self.ptr_depth
            return f"f{self.bits}{suffix}"
        return "void"

    @classmethod
    def parse_datatype(cls, string:str) -> DataType:
        if string == "label":
            return DataType(TypeKind.LABEL, 0)
        types = {
            "i":TypeKind.INT,
            "u":TypeKind.INT,
            "f":TypeKind.FLOAT,
            "v":TypeKind.VOID} \
        [string[0]]
        ptrdeep = string.count("*")
        ptrout = string[1:].replace("*", "")
        if types == TypeKind.INT:
            return DataType(types, int(ptrout), True if string[0] == "i" else False, ptrdeep)
        elif types == TypeKind.FLOAT:
            return DataType(types, int(ptrout), True, ptrdeep)
        else:
            return DataType(types, 0, ptr_depth = ptrdeep)

class ElementType(Enum):
    Register = auto()
    Label = auto()
    Immediate = auto()
    CMPType = auto()


@dataclass
class Element:
    type: ElementType
    string: str = ""
    number: int = 0

    @classmethod
    def parse_element(cls, string:str) -> Element:
        # %[a-Z0-9_]+
        # @[a-Z0-9_]+
        # [0-9]+
        # [a-Z0-9_]+
        if string in ("eq", "ne", "gt", "ge", "lt", "le"):
            return Element(ElementType.CMPType, string)
        elif string[0] in ("%", "@"):
            return Element(ElementType.Register, string)
        elif string.isdecimal():
            return Element(ElementType.Immediate, string, int(string))
        else:
            return Element(ElementType.Label, string)
    def __repr__(self) -> str:
        return self.string

class FunctionElementType(Enum):
    nounwind = auto()
    readonly = auto()
    readnone = auto()
    inlinehint = auto()
    alwaysinline = auto()
    noreturn = auto()
    bottleneck = auto()
    nodisco = auto()
    safe = auto()
    warning = auto()
    pure = auto()

@dataclass
class ElementPair:
    src: Optional[Element] = None
    stype: Optional[DataType] = None
    def __repr__(self) -> str:
        res = ""
        if self.stype is not None:
            res += self.stype.__repr__()
            if self.src is not None:
                res += ":"
        if self.src is not None:
            res += self.src.__repr__()
        return res

@dataclass
class HiInstr:
    # dest = i:data_type
    op: str                 # ADD, MOV, etc.
    dest: Optional[Element] = None
    desttype: DataType = field(default_factory=lambda: DataType(TypeKind.INT, 64))
    src: list[ElementPair] = field(default_factory=list[ElementPair])

    def __repr__(self, deep:int = 0):
        # デバッグ時に print(instr) したときに見やすくする
        outstring = "    " * deep # 出力文字
        if self.dest is not None:
            outstring += self.dest.string + " = "
        outstring += f"{self.desttype.__repr__()}:{self.op} "
        outstring += ", ".join(repr(i) for i in self.src)
        return outstring

class BasicBlock():
    def __init__(self, label: str):
        self.label = label
        self.instructions: list[HiInstr] = []

    def __repr__(self, deep:int = 0) -> str:
        res = "\n" + "    " * deep + self.label + ":\n"
        res += f"\n".join(i.__repr__(deep + 1) for i in self.instructions)
        return res

class Function():
    def __init__(self, name: str, return_type: DataType, args: list[ElementPair], attributes: set[FunctionElementType]):
        self.name = name
        self.return_type = return_type # 戻り値のDataType
        
        # インターフェース
        self.args: list[ElementPair] = args # 引数（仮想レジスタ）のリスト
        self.attributes: set[FunctionElementType] = attributes # public, pure, nounwind など
        
        # 構造（Body）
        self.blocks: list[BasicBlock] = [] # 基本ブロック（ラベル＋命令群）のリスト
        
        # バックエンド用メタデータ
        self.local_vars: list[Element] = [] # alloca 等のリスト
        self.total_stack_size_number: int = 0
        self.total_stack_size_byte:int = 0
        # stack_layoutは最終的に管理する。localvarsからの参照
        self.stack_layout: dict[Element, int] = {} # dicr[変数名, スタックオフセット]
    
    def add_stack_var(self, el:Element) -> None:
        self.total_stack_size_number += 1
        self.local_vars += [el]
    
    def __repr__(self, deep:int = 0) -> str:
        res = ""
        res += "    " * deep + f"define {self.return_type}:@{self.name}({", ".join(i.__repr__() for i in self.args)}) " + "{"
        res += "".join([block.__repr__(deep + 1) for block in self.blocks])
        res += "\n"
        res += "    " * deep + "}\n"
        return res

AllElement = HiInstr | Function | BasicBlock