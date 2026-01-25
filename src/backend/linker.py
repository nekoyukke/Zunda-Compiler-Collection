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

from src.targets import TargetBase
from src.dataobject import hiinstr
import re
from typing import Optional
from src.backend import zirParser

if __name__ == "__main__":
    # テスト
    text = """
define i16:@main() {
    entry:
        %1 = i16:const i16:10
        %A = i16*:alloca i16
        void:store i16:%1, i16*:%A
        %2 = i16:const i16:0
        %3 = i16:const i16:10
        %I = i16*:alloca i16
        void:store i16:%2, i16*:%I
        void:br label:L1FOR
    L1FOR:
        void:br label:L1if
    L1if:
        %5 = i16:load i16*:%I
        %6 = i16:const i16:1
        %4 = i1:icmp eq, i16:%5, i16:%6
        void:br i1:%4, label:L1iftrue, label:L1ifend
    L1iftrue:
        void:br label:L2if
    L2if:
        %8 = i16:load i16*:%I
        %9 = i16:const i16:2
        %7 = i1:icmp eq, i16:%8, i16:%9
        void:br i1:%7, label:L2iftrue, label:L2ifend
    L2iftrue:
        %11 = i16:const i16:1
        %12 = i16:load i16*:%A
        %10 = i16:add i16:%11, i16:%12
        void:store i16:%10, i16*:%A
        void:br label:L2ifend
        void:br label:L2ifend
    L2ifend:
        %14 = i16:const i16:3
        %15 = i16:load i16*:%A
        %13 = i16:add i16:%14, i16:%15
        void:store i16:%13, i16*:%A
        void:br label:L1ifend
        void:br label:L1ifend
    L1ifend:
        void:br label:L1FORNEXT
    L1FORNEXT:
        %16 = i16:load i16*:%I
        %18 = i16:inc i16:%16
        void:store i16:%18, i16*:%I
        %17 = i1:icmp lt, i16:%18, i16:%3
        void:br i1:%17, label:L1FOR, label:L1FOREND
        void:br label:L1FOREND
    L1FOREND:
        %19 = i16:load i16*:%A
        void:ret i16:%19
}
 i16:call @main
    """
    lex = zirParser.ZirLexer(text)
    toks = lex.tokenize()
    print(*toks, sep = "\n")
    parse = zirParser.ZirParser(toks)
    print(*parse.ZirParse(), sep="\n")
    # & C:/Users/garag/AppData/Local/Programs/Python/Python314/python.exe -m src.backend.linker