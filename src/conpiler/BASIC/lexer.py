# BASIC lexer implementation (Python)
# This lexer is simple but practical for a BASIC-like language.
# Token types: LINE_NUM, NUMBER, IDENT, KEYWORD, STRING, OP, COMMA, COLON, NEWLINE, EOF
# Supports comments starting with REM (case-insensitive) or single-quote ('), and ignores whitespace.
# Keywords: LET, IF, THEN, GOTO, FOR, NEXT, PRINT, INPUT, DIM, END, GOSUB, RETURN, STEP, TO, ELSE, REM
# Example usage: run the file or call Lexer().tokenize(basic_source)

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

    # Ordered list of token specifications (longer/priority patterns first)
    token_specification = [
        ("NUMBER",   r'\d+(\.\d+)?'),              # Integer or decimal number
        ("CMPOP",    r'<=|>=|!=|==|<|>'),       # Operators
        ("ASS",      r'='),
        ("OP",       r'\+|-|\*|/|%|addr'),            # Operators
        ("STRING",   r'"([^"]*)"'),                # "string literal"
        ("IDENT",    r'[A-Za-z_][A-Za-z0-9_]*'),   # Identifiers and keywords
        ("COMMA",    r','),                        # Comma
        ("COLON",    r':'),                        # Colon (also used for label separator)
        ("LPAREN",   r'\('),
        ("RPAREN",   r'\)'),
        ("WS",       r'[ \t]+'),                   # Whitespace (skipped)
        ("NEWLINE",  r'\n'),                       # Line endings
        ("MISMATCH", r'.'),                        # Any other single character
    ]

    def __init__(self):
        parts = []
        for name, pattern in self.token_specification:
            parts.append(f"(?P<{name}>{pattern})")
        self.master_re = re.compile("|".join(parts), re.IGNORECASE | re.MULTILINE)

        # regex for REM-style comment: either starting with REM or '
        self.rem_re = re.compile(r"^\s*(?:REM\b|')", re.IGNORECASE)

    def tokenize(self, code: str) -> List[Token]:
        tokens: List[Token] = []
        lines = code.splitlines(keepends=True)
        lineno = 1
        for line in lines:
            pos = 0
            line_len = len(line)

            # handle REM/comments at start or later: find first REM or ' that is not in a string
            # We'll handle comments by truncating the line at the first occurrence of " REM " or starting "'"
            # But be careful not to cut inside a string literal.
            truncated = self._strip_comment(line)
            if truncated is None:
                # entire line is comment; emit NEWLINE token only
                tokens.append(Token("NEWLINE", "\\n", lineno, 1))
                lineno += 1
                continue

            line_to_scan = truncated
            # If the line begins with a line number, we want to capture it as a single token (LINE_NUM)
            m = re.match(r'^[ \t]*(\d+)', line_to_scan)
            # scan the rest of the line
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
                elif kind == "MISMATCH":
                    raise LexerError(f"Unexpected character {value!r} at line {lineno} col {col}")
                else:
                    tokens.append(Token(kind, value, lineno, col))
                pos = mo.end()
            # if line did not end with NEWLINE token, append one (we keep line-level semantics)
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
                # check for single-quote comment
                if ch == "'":
                    # if it's at beginning or after whitespace, treat as comment start
                    # truncate from here
                    prefix = line[:i]
                    if prefix.strip() == "":
                        return None if i == 0 else prefix
                    return prefix
                # check for REM keyword (case-insensitive), ensure it's a separate word
                rem_match = re.match(r'REM\b', line[i:], re.IGNORECASE)
                if rem_match:
                    # ensure REM is either at column 0 / after whitespace or after separators
                    prefix = line[:i]
                    if prefix.strip() == "":
                        # entire rest is comment
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
