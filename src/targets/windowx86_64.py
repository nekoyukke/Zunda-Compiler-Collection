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
from src.dataobject import hiinstr

class TargetWindowsX86_64:
    def __init__(self) -> None:
        self.name = "windows_x86_64"
        self.word_size = 8 # 8, 16, 32, 64bitなど
        self.endian = "little"
        self.comment_char = ";"
        self.pointer_size = 64 # ポインタサイズ
        self.stack_map:dict[str, int] = {} # スタック上のレジスタマップ name:int
        self.stack_reg:dict[str, int] = {} # スタックに避難したレジスタ一覧（pop push, その他用）
        self.global_symbols:set[str] = set() # globalシンボル
        self.current_stack_size:int = 0 # スタックサイズ
        self.function:list[hiinstr.Function] = [] # 関数類
        self.uesd_register:list[str] = [] # レジスタ

    # --- レジスタ関連 ---
    def get_all_registers(self) -> dict[int, list[str]]:
        """利用可能な物理レジスタの文字列リストを返す"""
        raise NotImplementedError

    # --- 呼び出し規約関連 ---
    def get_arg_registers(self) -> dict[int, list[str]]:
        """引数渡しに使うレジスタ文字列を順番に返す（空なら全てスタック）"""
        raise NotImplementedError

    def get_return_register(self, data_type:hiinstr.DataType) -> str:
        """戻り値を置くレジスタ名を返す"""
        raise NotImplementedError
    
    # --- stack計算 ---
    def get_stack_offset(self, size:int) -> int:
        """スタックをフラグに応じて演算"""
        raise NotImplementedError
    
    def register_global(self, name:str) -> None:
        """グローバルに追加をする"""
        raise NotImplementedError
    
    # --- ユニーク名生成 ---
    def get_unique_name(self, name:str, data:str) -> str:
        return f"{self.name}_{name}_{data}"
    
    # --- スタック・メモリ関連 ---
    def get_stack_alignment(self) -> int:
        """スタックの境界合わせ"""
        raise NotImplementedError

    def align_to(self, size:int, alignment:int) -> int:
        """サイズを指定された境界に切り上げる計算"""
        return (size + alignment - 1) & ~(alignment - 1)

    # --- 命令変換のメインエントリ ---
    def lower_instr(self, zir_instr:hiinstr.HiInstr, context_func:hiinstr.Function):
        """
        ZIR命令をHiAssembler命令のリストに変換する。
        context_func: 現在処理中のFunctionオブジェクト（スタック情報などの参照用）
        """
        method_name = f"emit_hi_{zir_instr.op}"
        # 命令に応じたメソッドを呼び出す（なければエラー）
        visitor = getattr(self, method_name, None)
        if visitor:
            return visitor(zir_instr, context_func)
        raise NotImplementedError(f"Target [{self.name}] does not support op: '{zir_instr.op}'")

    # --- データ保存バイナリ ---
    def get_data_directive(self, byte_size: int) -> str:
        """
        mapping = {
            1: "db",
            2: "dw",
            4: "dd",
            8: "dq"
        }
        return mapping.get(byte_size, "db")実装案
        """
        raise NotImplementedError
    
    
    # --- セクション生成 ---
    def emit_section_header(self, section_name: str) -> str:
        # return f".{section_name} .data"など
        raise NotImplementedError
    
    # --- ファイルヘッダ ---
    def emit_file_header(self, source_filename: str) -> str:
        """
        セクション生成。いじることないと思う
        いじりたいなら、どうぞ
        """
        return f'.file "{source_filename}_{self.name}"'

    # --- デコレーション ---
    def emit_global_declaration(self, name: str) -> list[str]:
        raise NotImplementedError

    def emit_private_declaration(self, name: str) -> list[str]:
        raise NotImplementedError

    def emit_public_declaration(self, name: str) -> list[str]:
        raise NotImplementedError
    
    def emit_static_declaration(self, name: str) -> list[str]:
        raise NotImplementedError
    
    # アドレス取得
    def resolve_address(self, register_name: str) -> str:
        # リスト参照でも
        raise NotImplementedError
    
    # --- 関数規約 ---
    def emit_function_label(self, func_name: str) -> list[str]:
        raise NotImplementedError
    
    def emit_prologue(self, func_obj:hiinstr.Function) -> list[str]:
        """push rbp; mov rbp, rsp; sub rsp, size などを生成"""
        raise NotImplementedError

    def emit_epilogue(self, func_obj:hiinstr.Function) -> list[str]:
        """leave; ret などを生成"""
        raise NotImplementedError

    def emit_function_begin(self, func_name:hiinstr.Function) -> list[str]:
        # 例: .type main, @function (Linux/GAS)
        raise NotImplementedError

    def emit_function_end(self, func_name:str) -> list[str]:
        # 例: .size main, .-main
        raise NotImplementedError
    
    def format_immediate(self, value:int) -> str:
        """
        即値をフォーマットする
        50h #50 $50 etc..
        """
        raise NotImplementedError
    
    # --- addr ---
    def emit_load_address(self, dest:str, label_name:str) -> list[str]:
        "ラベルのアドレスをレジスタに載せる命令(lea rax, [rel global_var])"
        raise NotImplementedError
    
    def emit_load_value(self, dest:str, label_name:str) -> list[str]:
        "そのアドレスから値を読み込む命令(mov eax, [rax])"
        raise NotImplementedError
    
    # reset
    def prepare_new_function(self) -> None:
        self.stack_map.clear()
        self.current_stack_size = 0
        return None

    # use
    def use_register(self) -> str:
        raise NotImplementedError
    
    def free_register(self, name:str) -> None:
        raise NotImplementedError

    # --- 命令の変換（Lowering） ---
    """命令のHi ASMコード（またはオブジェクト）を生成"""
    def emit_hi_add(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_sub(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_mul(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_div(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_sdiv(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_sdivv(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_udiv(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_udivv(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_mod(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_and(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_or(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_xor(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_nand(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_nor(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_xnor(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_not(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_shl(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_shr(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_lshr(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_ashr(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_icmp(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_load(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_store(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_gep(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_br(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_call(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_ret(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_phi(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_switch(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_select(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_set(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_track(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_breakpoint(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_global(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_alloca(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_typedefine(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_cast(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_bitcast(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_define(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_defined(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_stasic(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_private(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_public(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError
    def emit_hi_constant(self, instr:hiinstr.HiInstr, context_func: hiinstr.Function) -> list[str]:
        raise NotImplementedError