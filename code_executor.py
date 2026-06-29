import ast
import traceback
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


class UnsafeCodeError(Exception):
    pass


class CodeExecutor:
    """Executes LLM-generated analysis code with basic guardrails.

    Note: This is safer than raw exec but not a hardened sandbox. For production,
    execute in an isolated container or restricted service.
    """

    FORBIDDEN_NAMES = {
        "open", "input", "eval", "exec", "compile", "__import__",
        "globals", "locals", "vars", "dir", "getattr", "setattr", "delattr",
        "os", "sys", "subprocess", "socket", "requests", "pathlib", "shutil",
    }
    FORBIDDEN_NODES = (ast.Import, ast.ImportFrom, ast.With, ast.AsyncWith, ast.Lambda)

    SAFE_BUILTINS = {
        "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict, "enumerate": enumerate,
        "float": float, "int": int, "len": len, "list": list, "max": max, "min": min,
        "range": range, "round": round, "set": set, "sorted": sorted, "str": str, "sum": sum,
        "tuple": tuple, "zip": zip,
    }

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def _clean_code(self, code: str) -> str:
        code = code.strip()
        if "```python" in code:
            code = code.split("```python", 1)[1].split("```", 1)[0]
        elif "```" in code:
            code = code.split("```", 1)[1].split("```", 1)[0]
        return code.strip()

    def _validate_ast(self, code: str):
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, self.FORBIDDEN_NODES):
                raise UnsafeCodeError(f"Disallowed syntax: {type(node).__name__}")
            if isinstance(node, ast.Name) and node.id in self.FORBIDDEN_NAMES:
                raise UnsafeCodeError(f"Disallowed name: {node.id}")
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                raise UnsafeCodeError("Dunder attribute access is not allowed")
        return tree

    def execute(self, code: str) -> dict:
        code = self._clean_code(code)
        local_vars = {
            "df": self.df.copy(),
            "pd": pd,
            "np": np,
            "px": px,
            "go": go,
            "fig": None,
            "result": "",
        }
        global_vars = {"__builtins__": self.SAFE_BUILTINS}

        try:
            tree = self._validate_ast(code)
            exec(compile(tree, filename="<llm_analysis>", mode="exec"), global_vars, local_vars)
            return {
                "success": True,
                "fig": local_vars.get("fig"),
                "result": str(local_vars.get("result", "")),
                "code": code,
                "error": None,
            }
        except Exception:
            return {
                "success": False,
                "fig": None,
                "result": "",
                "code": code,
                "error": traceback.format_exc(),
            }
