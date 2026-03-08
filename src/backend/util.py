class ParseError(Exception):
    def __init__(self, message: str, line: int, column: int, source: str, len:int, name: str) -> None:
        self.message = message
        self.line = line
        self.column = column
        self.source = source
        self.name = name
        self.len = len
        super().__init__(self.__str__())

    def __str__(self) -> str:
        # 行テキストを抽出
        line_text = self.source.splitlines()[self.line - 1]
        # カーソル位置に ^ を置く
        pointer = " " * (self.column - 1) + "^" * self.len
        return (
            f'\nTraceback: {self.name}'
            f'\n  File "<source>", line {self.line}\n'
            f"    {line_text}\n"
            f"    {pointer}\n"
            f"ParseError: {self.message}"
        )