from typing import Any, Dict, List, Optional
from langchain.callbacks.base import BaseCallbackHandler
from datetime import datetime
import json

try:
    from colorama import Fore, Back, Style, init

    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False

    class Fore:
        CYAN = BLUE = GREEN = YELLOW = RED = MAGENTA = WHITE = ""

    class Style:
        BRIGHT = RESET_ALL = ""


class ToolMonitorCallback(BaseCallbackHandler):
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.tool_calls_history = []
        self.current_llm = None

        if not COLORS_AVAILABLE and verbose:
            print("⚠️  Instale 'colorama' para ter saída colorida: pip install colorama")

    def _print_colored(
        self, text: str, color: str = Fore.WHITE, bright: bool = False
    ) -> None:
        if self.verbose:
            style = Style.BRIGHT if bright else ""
            print(f"{style}{color}{text}{Style.RESET_ALL}")

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        tool_name = serialized.get("name", "unknown_tool")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        call_record = {
            "timestamp": timestamp,
            "llm": self.current_llm,
            "tool": tool_name,
            "query": input_str,
            "result": None,
        }

        self.tool_calls_history.append(call_record)

        self._print_colored("\n" + "─" * 80, Fore.MAGENTA)
        self._print_colored(f"🔧 TOOL CHAMADA: {tool_name}", Fore.GREEN, bright=True)
        self._print_colored(f"📝 QUERY/INPUT:", Fore.YELLOW, bright=True)
        self._print_colored(f"   {input_str}", Fore.YELLOW)
        self._print_colored("─" * 80, Fore.MAGENTA)

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        if self.tool_calls_history:
            self.tool_calls_history[-1]["result"] = output

        self._print_colored(f"✅ RESULTADO:", Fore.GREEN, bright=True)

        try:
            if output.strip().startswith(("{", "[")):
                parsed = json.loads(output)
                formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
                for line in formatted.split("\n"):
                    self._print_colored(f"   {line}", Fore.GREEN)
            else:
                display_output = output[:500]
                for line in display_output.split("\n"):
                    self._print_colored(f"   {line}", Fore.GREEN)

                if len(output) > 500:
                    self._print_colored(
                        f"   ... (truncado, total: {len(output)} caracteres)",
                        Fore.WHITE,
                    )
        except Exception:
            display_output = output[:500]
            for line in display_output.split("\n"):
                self._print_colored(f"   {line}", Fore.GREEN)

            if len(output) > 500:
                self._print_colored(
                    f"   ... (truncado, total: {len(output)} caracteres)", Fore.WHITE
                )

        self._print_colored("─" * 80 + "\n", Fore.MAGENTA)

    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        self._print_colored(f"❌ ERRO NA TOOL:", Fore.RED, bright=True)
        self._print_colored(f"   {str(error)}", Fore.RED)
        self._print_colored("─" * 80 + "\n", Fore.MAGENTA)

        if self.tool_calls_history:
            self.tool_calls_history[-1]["result"] = f"ERROR: {str(error)}"

    def get_history(self) -> List[Dict[str, Any]]:
        return self.tool_calls_history

    def print_summary(self) -> None:
        self._print_colored("\n" + "=" * 80, Fore.CYAN, bright=True)
        self._print_colored("📊 RESUMO DE CHAMADAS DE TOOLS", Fore.CYAN, bright=True)
        self._print_colored("=" * 80, Fore.CYAN, bright=True)
        self._print_colored(
            f"Total de chamadas: {len(self.tool_calls_history)}", Fore.WHITE
        )

        tools_count = {}
        for call in self.tool_calls_history:
            tool = call["tool"]
            tools_count[tool] = tools_count.get(tool, 0) + 1

        self._print_colored("\nChamadas por ferramenta:", Fore.WHITE)
        for tool, count in tools_count.items():
            self._print_colored(f"  • {tool}: {count}x", Fore.GREEN)

        self._print_colored("=" * 80 + "\n", Fore.CYAN, bright=True)
