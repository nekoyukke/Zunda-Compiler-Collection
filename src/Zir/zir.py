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
from typing import Any, Optional
from enum import Enum

# Zir定義
# 基底クラス
# memo:ABC継承でも？
class Zir():
    pass

"""
型、レジスタ類
"""


# 型。
class TypeKind(Enum):
    INT = "i" # 整数
    UINT = "u" # 非負整数
    FLOAT = "f" # 浮動小数点
    VOID = "void" # 戻り値なし

# 型。少し特徴的なので定数を実装しておく
@dataclass
class DataType(Zir):
    kind: TypeKind
    bits: Optional[int] # 8, 16, 32, 64, 128
    ptr_depth: int = 0 # 0なら値、1ならポインタ(*)
    # repr
    def __repr__(self) -> str:
        if self.kind == TypeKind.VOID:
            return self.kind.value
        return f"{self.kind.value}{self.bits}{"*"*self.ptr_depth}"

"""
ここに型定義
https://www.youtube.com/watch?v=-UHYj16ar9U
"""
# 型のEnum
class InstrType(Enum):
    i8 = DataType(kind=TypeKind.INT, bits=8, ptr_depth=0)
    i16 = DataType(kind=TypeKind.INT, bits=16, ptr_depth=0)
    i32 = DataType(kind=TypeKind.INT, bits=32, ptr_depth=0)
    i64 = DataType(kind=TypeKind.INT, bits=64, ptr_depth=0)
    u8 = DataType(kind=TypeKind.UINT, bits=8, ptr_depth=0)
    u16 = DataType(kind=TypeKind.UINT, bits=16, ptr_depth=0)
    u32 = DataType(kind=TypeKind.UINT, bits=32, ptr_depth=0)
    u64 = DataType(kind=TypeKind.UINT, bits=64, ptr_depth=0)
    f32 = DataType(kind=TypeKind.FLOAT, bits=32, ptr_depth=0)
    f64 = DataType(kind=TypeKind.FLOAT, bits=64, ptr_depth=0)
    void = DataType(kind=TypeKind.VOID, bits=None, ptr_depth=0)


# 値クラスの規基底
class Value(Zir):
    pass

# レジスタ型
# __repr__で楽するため文字列指定
class tRegister(Enum):
    GLOBAL = "@"
    LOCAL = "%"

# レジスタ
@dataclass
class Register(Value):
    name:str
    rtype:tRegister
    def __repr__(self) -> str:
        return f"{self.rtype.value}{self.name}"

@dataclass
class Immediate(Value):
    value:int
    def __repr__(self) -> str:
        return self.value.__repr__()

@dataclass
class Label(Value):
    name:str
    def __repr__(self) -> str:
        return self.name

"""
命令類
"""
@dataclass
class Instruction(Zir):
    dest:Optional[Register]
    desttype:DataType
    def __repr__(self, deep:int = 0) -> str:
        return ""

# (^▽^)/演算
class BinaryOpType(Enum):
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    SDIV = "sdiv"
    UDIV = "udiv"
    ISDIV = "isdev"
    IUDIV = "iudev"
    MOD = "mod"
    AND = "and"
    OR = "or"
    XOR = "xor"
    NAND = "nand"
    NOR = "nor"
    XNOR = "xnor"
    SHR = "shr"
    LSHR = "lshr"
    ASHR = "ashr"
    GEP = "gep"

# binary
@dataclass
class BinaryInstr(Instruction):
    op:BinaryOpType
    src1:Value
    src1type:DataType
    src2:Value
    src2type:DataType
    def __repr__(self, deep:int = 0) -> str:
        if self.dest is None:
            return f"{"    "*deep}{self.desttype}:{self.op.value} {self.src1type}:{self.src1}, {self.src2type}:{self.src2}"
        return f"{"    "*deep}{self.dest} = {self.desttype}:{self.op.value} {self.src1type}:{self.src1}, {self.src2type}:{self.src2}"

# 単項演算
class UnaryOpType(Enum):
    NOT = "not"

@dataclass
class UnaryInstr(Instruction):
    op:UnaryOpType
    src:Value
    srctype:DataType
    def __repr__(self, deep:int = 0) -> str:
        if self.dest is None:
            return f"{"    "*deep}{self.desttype}:{self.op.value} {self.srctype}:{self.src}"
        return f"{"    "*deep}{self.dest} = {self.desttype}:{self.op.value} {self.srctype}:{self.src}"

# 比較演算子etc
class CmpOpType(Enum):
    CARRY = "carry"
    ZERO = "zero"
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"

# 比較演算子 icmp
@dataclass
class IcmpInstr(Instruction):
    src1:Value
    src1type:DataType
    src2:Value
    src2type:DataType
    cmptype:CmpOpType
    def __repr__(self, deep:int = 0) -> str:
        if self.dest is None:
            return f"{"    "*deep}{self.desttype}:icmp {self.cmptype.value} {self.src1type}:{self.src1}, {self.src2type}:{self.src2}"
        return f"{"    "*deep}{self.dest} = {self.desttype}:icmp {self.cmptype.value} {self.src1type}:{self.src1}, {self.src2type}:{self.src2}"

# alloca, global
@dataclass
class AllocaInstr(Instruction):
    type:DataType
    def __repr__(self, deep:int = 0) -> str:
        if self.dest is None:
            return f"{"    "*deep}{self.desttype}:alloca {self.type}"
        return f"{"    "*deep}{self.dest} = {self.desttype}:alloca {self.type}"

@dataclass
class GlobalInstr(Instruction):
    type:DataType
    def __repr__(self, deep:int = 0) -> str:
        if self.dest is None:
            return f"{"    "*deep}{self.desttype}:global {self.type}"
        return f"{"    "*deep}{self.dest} = {self.desttype}:global {self.type}"

# store
@dataclass
class StoreInStr(Instruction):
    src1:Register
    src1type:DataType
    src2:Value
    src2type:DataType
    def __repr__(self, deep:int = 0) -> str:
        if self.dest is None:
            return f"{"    "*deep}{self.desttype}:store {self.src1type}:{self.src1}, {self.src2type}:{self.src2}"
        return f"{"    "*deep}{self.dest} = {self.desttype}:store {self.src1type}:{self.src1}, {self.src2type}:{self.src2}"

# load
@dataclass
class LoadInStr(Instruction):
    src1:Register
    src1type:DataType
    def __repr__(self, deep:int = 0) -> str:
        if self.dest is None:
            return f"{"    "*deep}{self.desttype}:load {self.src1type}:{self.src1}"
        return f"{"    "*deep}{self.dest} = {self.desttype}:load {self.src1type}:{self.src1}"
# Parms
@dataclass
class Parm(Value):
    reg:Register
    type:DataType
    def __repr__(self) -> str:
        return f"{self.type}:{self.reg}"

# call
@dataclass
class CallInStr(Instruction):
    src:Register
    Parms:list[Parm]
    def __repr__(self, deep: int = 0) -> str:
        if self.dest is None:
            return f"{"    "*deep}{self.desttype}:call {self.src}({", ".join([i.__repr__() for i in self.Parms])})"
        return f"{"    "*deep}{self.dest} = {self.desttype}:call {self.src}({", ".join([i.__repr__() for i in self.Parms])})"

# block
@dataclass
class BlockInstr(Zir):
    name:str
    instr:list[Instruction] = field(default_factory=list[Instruction])
    def __repr__(self, deep:int = 0) -> str:
        if self.instr is []:
            return f"{"    "*deep}{self.name}:"
        return f"{"    "*deep}{self.name}:\n{"\n".join([i.__repr__(deep+1) for i in self.instr])}"

    def add(self, instr:Instruction):
        self.instr.append(instr)

# function
@dataclass
class FunctionInstr(Zir):
    name:Register
    rettype:DataType
    blocks:BlockInstr
    Parms:list[Parm]
    def __repr__(self, deep:int = 0) -> str:
        return f"{"    "*deep}define {self.rettype.__repr__()}:{self.name.__repr__()} ({", ".join([i.__repr__() for i in self.Parms])})" + "{" + f"{self.blocks.__repr__(deep+1)}" + "}"

# すべて
@dataclass
class ModuleInstr(Zir):
    instr:list[Instruction | BlockInstr | FunctionInstr] = field(default_factory=list[Instruction | BlockInstr | FunctionInstr])
    def __repr__(self) -> str:
        return "\n".join([i.__repr__(0) for i in self.instr])
    def addInstr(self, instr:Instruction | BlockInstr | FunctionInstr):
        self.instr.append(instr)