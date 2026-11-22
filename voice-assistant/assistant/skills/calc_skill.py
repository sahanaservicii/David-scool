from __future__ import annotations
import ast
import operator as op
import re
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext

OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv, ast.Mod: op.mod, ast.Pow: op.pow,
    ast.USub: op.neg, ast.UAdd: op.pos,
}


def safe_eval(expr: str):
    expr = expr.replace(',', '.').replace('^', '**').replace('×', '*').replace('÷', '/')
    node = ast.parse(expr, mode='eval')

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in OPS:
            return OPS[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in OPS:
            return OPS[type(n.op)](_eval(n.operand))
        raise ValueError('Недопустимое выражение')
    return _eval(node)


class CalcSkill(Skill):
    name = "calc"
    description = "Калькулятор (безопасные вычисления)"
    intents = ["calc"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        text = intent.raw
        # try to extract expression
        expr = re.sub(r'^(посчитай|сколько будет|вычисли|калькулятор|calculate)\s*', '', text, flags=re.I).strip()
        expr = expr.rstrip('?=.')
        if not expr:
            expr = text
        # keep math chars
        expr2 = re.findall(r'[\d\s\+\-\*\/\(\)\.\,\^%]+', expr)
        expr = ''.join(expr2).strip() if expr2 else expr
        try:
            res = safe_eval(expr)
            if isinstance(res, float) and res.is_integer():
                res = int(res)
            return SkillResponse(text=f"{expr} = {res}")
        except Exception:
            return SkillResponse(text="Не удалось вычислить. Пример: «посчитай 2+2*3».")
