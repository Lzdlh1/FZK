"""公式引擎:词法分析 + 递归下降解析 + 白名单求值。

纯函数实现,不依赖 DB,方便单测与前端镜像对照。
表达式存储时不带前导 ``=``;变量引用形如 ``{变量名}``。
"""

from __future__ import annotations

import re
from collections import namedtuple
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


class FormulaError(Exception):
    """公式错误(词法/语法/求值)。"""


# ----------------------------- AST 节点 -----------------------------

class Num:
    __slots__ = ("value",)

    def __init__(self, value: float) -> None:
        self.value = value


class Str:
    __slots__ = ("value",)

    def __init__(self, value: str) -> None:
        self.value = value


class Var:
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name


class UnaryMinus:
    __slots__ = ("operand",)

    def __init__(self, operand: Any) -> None:
        self.operand = operand


class BinOp:
    __slots__ = ("op", "left", "right")

    def __init__(self, op: str, left: Any, right: Any) -> None:
        self.op = op
        self.left = left
        self.right = right


class Compare:
    __slots__ = ("op", "left", "right")

    def __init__(self, op: str, left: Any, right: Any) -> None:
        self.op = op
        self.left = left
        self.right = right


class FuncCall:
    __slots__ = ("name", "args")

    def __init__(self, name: str, args: list[Any]) -> None:
        self.name = name
        self.args = args


WHITELIST_FUNCS = {"ROUND", "MAX", "MIN", "IF", "ABS", "LEN"}

Token = namedtuple("Token", ["type", "value"])


# ----------------------------- Tokenizer -----------------------------

_TOKEN_RE = re.compile(
    r"""
      \s+                                   # 空白(跳过,无捕获组)
    | (?P<NUMBER>\d+\.\d+|\.\d+|\d+)        # 数值
    | \{(?P<VAR>[^}]*)\}                    # {变量名}
    | "(?P<STRING>[^"]*)"                   # "字符串"
    | (?P<FUNC>[A-Za-z_][A-Za-z0-9_]*)      # 标识符(函数名)
    | (?P<CMP><=|>=|<>|=|<|>)               # 比较运算符
    | (?P<OP>[+\-*/^])                      # 算术运算符
    | (?P<LPAREN>\()
    | (?P<RPAREN>\))
    | (?P<COMMA>,)
    """,
    re.VERBOSE,
)

_VAR_REF_RE = re.compile(r"\{([^}]*)\}")


def tokenize(expr: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    length = len(expr)
    while pos < length:
        m = _TOKEN_RE.match(expr, pos)
        if m is None or m.end() == pos:
            raise FormulaError(f"词法错误:无法识别的字符 '{expr[pos]}'")
        kind = m.lastgroup
        if kind is None:  # 空白分支
            pos = m.end()
            continue
        raw = m.group(kind)
        if kind == "NUMBER":
            tokens.append(Token("NUMBER", float(raw)))
        elif kind == "VAR":
            tokens.append(Token("VAR", raw))
        elif kind == "STRING":
            tokens.append(Token("STRING", raw))
        elif kind == "FUNC":
            tokens.append(Token("FUNC", raw.upper()))
        elif kind == "CMP":
            tokens.append(Token("CMP", raw))
        elif kind == "OP":
            tokens.append(Token("OP", raw))
        elif kind == "LPAREN":
            tokens.append(Token("LPAREN", "("))
        elif kind == "RPAREN":
            tokens.append(Token("RPAREN", ")"))
        elif kind == "COMMA":
            tokens.append(Token("COMMA", ","))
        pos = m.end()
    tokens.append(Token("EOF", None))
    return tokens


# ----------------------------- Parser -----------------------------

class Parser:
    """递归下降解析器,``^`` 右结合。"""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, type_: str) -> Token:
        tok = self._peek()
        if tok.type != type_:
            raise FormulaError(f"语法错误:期望 {type_},得到 {tok.type}")
        return self._advance()

    def parse(self) -> Any:
        node = self._expr()
        if self._peek().type != "EOF":
            raise FormulaError(f"语法错误:多余的 token '{self._peek().value}'")
        return node

    def _expr(self) -> Any:
        return self._comparison()

    def _comparison(self) -> Any:
        node = self._additive()
        while self._peek().type == "CMP":
            op = self._advance().value
            right = self._additive()
            node = Compare(op, node, right)
        return node

    def _additive(self) -> Any:
        node = self._multiplicative()
        while self._peek().type == "OP" and self._peek().value in ("+", "-"):
            op = self._advance().value
            right = self._multiplicative()
            node = BinOp(op, node, right)
        return node

    def _multiplicative(self) -> Any:
        node = self._power()
        while self._peek().type == "OP" and self._peek().value in ("*", "/"):
            op = self._advance().value
            right = self._power()
            node = BinOp(op, node, right)
        return node

    def _power(self) -> Any:
        base = self._unary()
        if self._peek().type == "OP" and self._peek().value == "^":
            self._advance()
            exp = self._power()  # 右结合:递归解析右侧
            return BinOp("^", base, exp)
        return base

    def _unary(self) -> Any:
        if self._peek().type == "OP" and self._peek().value == "-":
            self._advance()
            return UnaryMinus(self._unary())
        return self._primary()

    def _primary(self) -> Any:
        tok = self._peek()
        if tok.type == "NUMBER":
            self._advance()
            return Num(tok.value)
        if tok.type == "STRING":
            self._advance()
            return Str(tok.value)
        if tok.type == "VAR":
            self._advance()
            return Var(tok.value)
        if tok.type == "FUNC":
            name = self._advance().value
            self._expect("LPAREN")
            args: list[Any] = []
            if self._peek().type != "RPAREN":
                args.append(self._expr())
                while self._peek().type == "COMMA":
                    self._advance()
                    args.append(self._expr())
            self._expect("RPAREN")
            return FuncCall(name, args)
        if tok.type == "LPAREN":
            self._advance()
            node = self._expr()
            self._expect("RPAREN")
            return node
        raise FormulaError(f"语法错误:意外的 token '{tok.value}'")


# ----------------------------- 求值 -----------------------------

def _fmt_num(x: Any) -> str:
    """数值格式化为字面量文本:整数值不带 ``.0``。"""
    if isinstance(x, bool):
        return "1" if x else "0"
    if isinstance(x, float):
        if x.is_integer():
            return str(int(x))
        return repr(x)
    if isinstance(x, int):
        return str(x)
    return str(x)


def _round(x: Any, n: Any) -> float:
    try:
        ndig = int(n)
    except (TypeError, ValueError) as exc:
        raise FormulaError(f"ROUND 的位数参数必须为整数: {exc}") from exc
    try:
        quant = Decimal(1).scaleb(-ndig)
        return float(Decimal(str(x)).quantize(quant, rounding=ROUND_HALF_UP))
    except (ValueError, ArithmeticError) as exc:
        raise FormulaError(f"ROUND 求值失败: {exc}") from exc


def _eval_node(node: Any, values: dict[str, float]) -> Any:
    if isinstance(node, Num):
        return node.value
    if isinstance(node, Str):
        return node.value
    if isinstance(node, Var):
        if node.name not in values:
            raise FormulaError(f"未绑定变量: {node.name}")
        return values[node.name]
    if isinstance(node, UnaryMinus):
        return -_eval_node(node.operand, values)
    if isinstance(node, BinOp):
        left = _eval_node(node.left, values)
        right = _eval_node(node.right, values)
        op = node.op
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise FormulaError("除零错误")
            return left / right
        if op == "^":
            try:
                return float(left ** right)
            except (ValueError, OverflowError, TypeError, ZeroDivisionError) as exc:
                raise FormulaError(f"幂运算错误: {exc}") from exc
        raise FormulaError(f"未知运算符: {op}")
    if isinstance(node, Compare):
        left = _eval_node(node.left, values)
        right = _eval_node(node.right, values)
        op = node.op
        if op == ">":
            return 1.0 if left > right else 0.0
        if op == "<":
            return 1.0 if left < right else 0.0
        if op == ">=":
            return 1.0 if left >= right else 0.0
        if op == "<=":
            return 1.0 if left <= right else 0.0
        if op == "=":
            return 1.0 if left == right else 0.0
        if op == "<>":
            return 1.0 if left != right else 0.0
        raise FormulaError(f"未知比较运算符: {op}")
    if isinstance(node, FuncCall):
        return _eval_func(node, values)
    raise FormulaError("未知 AST 节点")


def _eval_func(node: FuncCall, values: dict[str, float]) -> Any:
    name = node.name
    args = node.args
    if name not in WHITELIST_FUNCS:
        raise FormulaError(f"未知函数: {name}")
    if name == "IF":
        if len(args) != 3:
            raise FormulaError("IF 需要 3 个参数")
        cond = _eval_node(args[0], values)
        return _eval_node(args[1], values) if cond != 0 else _eval_node(args[2], values)
    if name == "ROUND":
        if len(args) != 2:
            raise FormulaError("ROUND 需要 2 个参数")
        return _round(_eval_node(args[0], values), _eval_node(args[1], values))
    if name == "MAX":
        if len(args) < 1:
            raise FormulaError("MAX 至少需要 1 个参数")
        return max(_eval_node(a, values) for a in args)
    if name == "MIN":
        if len(args) < 1:
            raise FormulaError("MIN 至少需要 1 个参数")
        return min(_eval_node(a, values) for a in args)
    if name == "ABS":
        if len(args) != 1:
            raise FormulaError("ABS 需要 1 个参数")
        return abs(_eval_node(args[0], values))
    if name == "LEN":
        if len(args) != 1:
            raise FormulaError("LEN 需要 1 个参数")
        val = _eval_node(args[0], values)
        if isinstance(val, str):
            return len(val)
        return len(_fmt_num(val))
    raise FormulaError(f"未知函数: {name}")


def _build_substituted(expression: str, values: dict[str, float]) -> str:
    def repl(m: re.Match[str]) -> str:
        name = m.group(1)
        if name in values:
            return _fmt_num(values[name])
        return m.group(0)

    return _VAR_REF_RE.sub(repl, expression)


def evaluate(expression: str, values: dict[str, float]) -> dict[str, Any]:
    """求值,返回 ``{value, substituted_expression, db_refs}``。

    ``db_refs`` 在本接口始终为空列表(来源信息由解析流水线后续填充)。
    """
    if expression is None or not expression.strip():
        raise FormulaError("表达式为空")
    tokens = tokenize(expression)
    ast = Parser(tokens).parse()
    value = _eval_node(ast, values)
    substituted = _build_substituted(expression, values)
    return {"value": value, "substituted_expression": substituted, "db_refs": []}


def extract_var_refs(expression: str) -> list[str]:
    """提取表达式中 ``{var}`` 引用的变量名,按首次出现顺序去重。"""
    seen: set[str] = set()
    ordered: list[str] = []
    for name in _VAR_REF_RE.findall(expression or ""):
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


__all__ = [
    "FormulaError",
    "evaluate",
    "extract_var_refs",
    "tokenize",
    "Parser",
    "WHITELIST_FUNCS",
]
