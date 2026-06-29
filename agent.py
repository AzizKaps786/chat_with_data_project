import os
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

from data_profiler import DataProfiler
from code_executor import CodeExecutor
from utils.prompts import SYSTEM_PROMPT, SUGGESTION_PROMPT

load_dotenv()


class DataAnalysisAgent:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.profiler = DataProfiler(df)
        self.executor = CodeExecutor(df)
        self.conversation_history = []
        self.system_prompt = SYSTEM_PROMPT.format(
            data_profile=self.profiler.get_summary_string()
        )

    def _complete(self, messages, temperature=0.1):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content

    def chat(self, user_message: str) -> dict:
        self.conversation_history.append({"role": "user", "content": user_message})

        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.conversation_history[-10:],
        ]
        llm_response = self._complete(messages, temperature=0.1)
        execution = self.executor.execute(llm_response)

        # One retry if code failed; pass error back to the model for repair.
        if not execution["success"]:
            repair_messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": llm_response},
                {"role": "user", "content": f"The code failed. Fix it and return code only. Error:\n{execution['error']}"},
            ]
            llm_response = self._complete(repair_messages, temperature=0.05)
            execution = self.executor.execute(llm_response)

        suggestion = self.get_suggestion(user_message, execution.get("result", "")) if execution["success"] else "Try asking for a simpler summary of the dataset."

        self.conversation_history.append({
            "role": "assistant",
            "content": execution.get("result") or llm_response,
        })

        return {
            "fig": execution["fig"],
            "insight": execution["result"],
            "suggestion": suggestion,
            "success": execution["success"],
            "error": execution["error"],
            "code": execution.get("code", llm_response),
        }

    def get_suggestion(self, question: str, result: str) -> str:
        try:
            return self._complete([
                {"role": "system", "content": SUGGESTION_PROMPT},
                {"role": "user", "content": f"Question: {question}\nResult: {result}"},
            ], temperature=0.7).strip()
        except Exception:
            return "What should we analyze next?"
