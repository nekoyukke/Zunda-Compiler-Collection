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
from __future__ import annotations
import sys
from pathlib import Path
from src.compiler.basix_sharp import parse, lexer

text = \
"""
# --- テスト用 Basix-Sharp プログラム（コンマ必須 S式版） ---

# グローバル変数
LET g = 100
LET h = 0

# 関数定義（引数はポインタ）
FUNC add_twice(a, b)
    # a と b はポインタ
    LET temp = (+, a, b)      # S式で加算
    LET temp2 = (+, temp, b)
    RET temp2

FUNC main()
    # ローカル変数
    LET x = 10
    LET y = 5
    LET z = 0

    # IF文（条件あり）
    IF x > y THEN
        z = (+, x, y)
    ELSE
        z = (-, x, y)
    END

    # IF文（条件省略）
    LET flag = 1
    IF flag THEN
        y = (+, y, 1)
    END

    # FOR文（ローカル専用）
    FOR i 0 TO 3
        x = (+, x, i)
        y = (*, y, i)
    NEXT

    # 関数呼び出し（引数は IDENT のみ）
    LET result = add_twice(x, y)

    # 複雑な S式演算
    LET complex = (+, x, (*, y, (-, z, 2), (%, x, 3)))

    # グローバル変数への書き込み
    g = (+, g, result)
    h = (+, h, complex)

    RET h

"""
lex = lexer.Lexer()
toks = lex.tokenize(text)
parses = parse.parse(toks, text, 32)
print(*parses, sep="\n")