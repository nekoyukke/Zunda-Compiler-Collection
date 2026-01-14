from __future__ import annotations
import sys
from pathlib import Path
import parse
import lexer

"""repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
import src.util as util"""

lex = lexer.Lexer()
source = "Func Foo(a,b)\n" \
         "  Let x = (+, b, a)\n" \
         "  RET x\n" \
         "Func main()\n" \
         "  Let x = 2\n" \
         "  Let y = 2\n" \
         "  x = Foo(x,y)\n" \
         "  If x == y THEN\n" \
         "    x = (+, 1, x)\n" \
         "  END\n" \
         "  ELSE\n" \
         "    y = (+, 1, 0)\n" \
         "  END\n" \
         "  RET 0"
toks = lex.tokenize(source)
print(toks)
print(parse.parse(toks, source, 16))
