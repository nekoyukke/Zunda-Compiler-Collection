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
import re
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

@dataclass
class Token:
    type: str
    value: str
    lineno: int
    col: int

    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r}, line={self.lineno}, col={self.col})"

class LexerError(Exception):
    pass

class Lexer:
    KEYWORDS = {
        "LET","IF","THEN","GOTO","FOR","NEXT","PRINT","INPUT","DIM","END",
        "GOSUB","RETURN","STEP","TO","ELSE","REM","AND","OR","NOT","FUNC","RET","GOSUB","R"
    }

    token_specification = [
        ("NUMBER",   r'\d+(\.\d+)?'),           
        ("CMPOP",    r'<=|>=|!=|==|<|>'),       
        ("ASS",      r'='),
        ("OP",       r'\+|-|\*|/|%|addr'),      
        ("STRING",   r'"([^"]*)"'),             
        ("IDENT",    r'[A-Za-z_][A-Za-z0-9_]*'),
        ("COMMA",    r','),                     
        ("COLON",    r':'),                     
        ("LPAREN",   r'\('),
        ("RPAREN",   r'\)'),
        ("WS",       r'[ \t]+'),
        ("NEWLINE",  r'\n'),
        ("COMMENT",  r'#.+'),
        ("MISMATCH", r'.'),
    ]

    def __init__(self):
        parts = []
        for name, pattern in self.token_specification:
            parts.append(f"(?P<{name}>{pattern})")
        self.master_re = re.compile("|".join(parts), re.IGNORECASE | re.MULTILINE)

        self.rem_re = re.compile(r"^\s*(?:REM\b|')", re.IGNORECASE)

    def tokenize(self, code: str) -> List[Token]:
        tokens: List[Token] = []
        lines = code.splitlines(keepends=True)
        lineno = 1
        for line in lines:
            pos = 0
            line_len = len(line)

            truncated = self._strip_comment(line)
            if truncated is None:
                tokens.append(Token("NEWLINE", "\\n", lineno, 1))
                lineno += 1
                continue

            line_to_scan = truncated
            m = re.match(r'^[ \t]*(\d+)', line_to_scan)
            for mo in self.master_re.finditer(line_to_scan, pos):
                kind = mo.lastgroup
                value = mo.group(kind)
                col = mo.start() + 1
                if kind == "WS":
                    continue
                if kind == "NEWLINE":
                    tokens.append(Token("NEWLINE", "\\n", lineno, col))
                elif kind == "STRING":
                    # strip surrounding quotes
                    inner = mo.group(kind)[1:-1]
                    tokens.append(Token("STRING", inner, lineno, col))
                elif kind == "IDENT":
                    up = value.upper()
                    if up in self.KEYWORDS:
                        tokens.append(Token("KEYWORD", up, lineno, col))
                    else:
                        tokens.append(Token("IDENT", value, lineno, col))
                elif kind == "NUMBER":
                    tokens.append(Token("NUMBER", value, lineno, col))
                elif kind == "COMMENT":
                    continue
                elif kind == "MISMATCH":
                    raise LexerError(f"Unexpected character {value!r} at line {lineno} col {col}")
                else:
                    tokens.append(Token(kind, value, lineno, col))
                pos = mo.end()
            if not (tokens and tokens[-1].type == "NEWLINE"):
                tokens.append(Token("NEWLINE", "\\n", lineno, line_len))
            lineno += 1

        tokens.append(Token("EOF", "", lineno, 1))
        return tokens

    def _strip_comment(self, line: str) -> Optional[str]:
        """
        Returns the line truncated before an unquoted REM or single-quote comment marker.
        If the whole line is a comment, returns None.
        """
        i = 0
        in_string = False
        while i < len(line):
            ch = line[i]
            if ch == '"':
                in_string = not in_string
                i += 1
                continue
            if not in_string:
                if ch == "'":
                    prefix = line[:i]
                    if prefix.strip() == "":
                        return None if i == 0 else prefix
                    return prefix
                rem_match = re.match(r'REM\b', line[i:], re.IGNORECASE)
                if rem_match:
                    prefix = line[:i]
                    if prefix.strip() == "":
                        return None if i == 0 else prefix
                    return prefix
            i += 1
        return line

# --- Demo ---
if __name__ == "__main__":
    src = '''10 LET A = 5
20 LET B = A + 2
30 IF B > 10 THEN GOTO 10
40 PRINT "HELLO, WORLD"  ' this is a comment
50 REM full line comment
60 FOR I = 0 TO 3
70 NEXT I
80 END
'''
    lexer = Lexer()
    toks = lexer.tokenize(src)
    for t in toks:
        print(t)
