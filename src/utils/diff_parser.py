import re
import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """
    Classificação semântica de mudanças em um diff.

    Por que isso existe?
    --------------------
    O problema: quando um PR muda apenas aspas ('' vs ""), o agente
    recebia isso como mudança "significativa" e analisava o código todo.

    A solução: classificar ANTES de passar para os agentes, permitindo
    que eles ignorem mudanças que não afetam a lógica do código.
    """
    COSMETIC = "cosmetic"           # Aspas, espaços, formatação
    COMMENT_ONLY = "comment_only"   # Apenas comentários mudaram
    IMPORT_CHANGE = "import_change" # Mudança em imports
    LOGIC_CHANGE = "logic_change"   # Mudança real na lógica
    UNKNOWN = "unknown"             # Não conseguiu classificar


class DiffParser:
    HUNK_HEADER_PATTERN = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

    @staticmethod
    def parse_diff(diff_text: str) -> Dict[str, any]:
        chunks = []
        line_map = {}

        lines = diff_text.split("\n")
        current_old_line = 0
        current_new_line = 0
        in_hunk = False

        for line in lines:
            match = DiffParser.HUNK_HEADER_PATTERN.search(line)
            if match:
                old_start = int(match.group(1))
                new_start = int(match.group(3))

                current_old_line = old_start
                current_new_line = new_start
                in_hunk = True

                chunks.append(
                    {
                        "old_start": old_start,
                        "new_start": new_start,
                        "header": line,
                        "changes": [],
                    }
                )

                logger.debug(f"Found hunk: old={old_start}, new={new_start}")
                continue

            if not in_hunk:
                continue

            if line.startswith("+") and not line.startswith("+++"):
                content = line[1:].strip()
                if content:
                    line_map[content] = current_new_line
                    chunks[-1]["changes"].append(
                        {"type": "add", "line": current_new_line, "content": content}
                    )
                current_new_line += 1

            elif line.startswith("-") and not line.startswith("---"):
                content = line[1:].strip()
                chunks[-1]["changes"].append(
                    {"type": "remove", "line": current_old_line, "content": content}
                )
                current_old_line += 1

            elif line.startswith(" "):
                current_old_line += 1
                current_new_line += 1

        return {"chunks": chunks, "line_map": line_map, "total_chunks": len(chunks)}

    @staticmethod
    def find_line_for_code(diff_text: str, code_snippet: str) -> Optional[int]:
        parsed = DiffParser.parse_diff(diff_text)

        code_clean = code_snippet.strip()
        if code_clean in parsed["line_map"]:
            return parsed["line_map"][code_clean]

        code_partial = code_clean[:50]
        for content, line_num in parsed["line_map"].items():
            if content.startswith(code_partial):
                return line_num

        return None

    @staticmethod
    def get_changed_line_ranges(diff_text: str) -> List[Tuple[int, int]]:
        parsed = DiffParser.parse_diff(diff_text)
        ranges = []

        for chunk in parsed["chunks"]:
            if chunk["changes"]:
                lines = [c["line"] for c in chunk["changes"] if c["type"] == "add"]
                if lines:
                    ranges.append((min(lines), max(lines)))

        return ranges

    @staticmethod
    def annotate_diff_with_lines(diff_text: str) -> str:
        annotated_lines = []

        lines = diff_text.split("\n")
        current_new_line = 0
        in_hunk = False

        for line in lines:
            match = DiffParser.HUNK_HEADER_PATTERN.search(line)
            if match:
                new_start = int(match.group(3))
                current_new_line = new_start
                in_hunk = True
                annotated_lines.append(line)
                continue

            if not in_hunk:
                annotated_lines.append(line)
                continue

            if line.startswith("+") and not line.startswith("+++"):
                annotated_lines.append(f"[LINE: {current_new_line}] {line}")
                current_new_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                annotated_lines.append(line)
            elif line.startswith(" "):
                annotated_lines.append(f"[LINE: {current_new_line}] {line}")
                current_new_line += 1
            else:
                annotated_lines.append(line)

        return "\n".join(annotated_lines)

    @staticmethod
    def get_line_number_from_annotated_diff(
        code_snippet: str, annotated_diff: str
    ) -> Optional[int]:
        code_clean = code_snippet.strip()

        for line in annotated_diff.split("\n"):
            if "[LINE:" in line:
                match = re.search(r"\[LINE:\s*(\d+)\]", line)
                if match:
                    line_number = int(match.group(1))
                    line_content = (
                        line.split("]", 1)[1].strip() if "]" in line else line
                    )
                    if line_content and len(line_content) > 1:
                        line_content = (
                            line_content[1:].strip()
                            if line_content[0] in ["+", "-", " "]
                            else line_content.strip()
                        )

                    if code_clean in line_content or line_content in code_clean:
                        return line_number

        return None

    # ================================================================
    # CLASSIFICAÇÃO SEMÂNTICA DE MUDANÇAS
    # ================================================================
    #
    # POR QUE ISSO EXISTE?
    # --------------------
    # Problema: O agente recebia diffs como este:
    #   -    placeholder: "Selecione..."
    #   +    placeholder: 'Selecione...'
    #
    # E reportava "problemas de performance" ou "erros" porque
    # analisava o CÓDIGO FINAL, não a MUDANÇA EM SI.
    #
    # Solução: Antes de enviar para os agentes, classificamos
    # cada mudança como COSMETIC, COMMENT_ONLY, ou LOGIC_CHANGE.
    # Isso permite que os agentes ignorem mudanças irrelevantes.
    # ================================================================

    @staticmethod
    def normalize_for_comparison(text: str) -> str:
        """
        Normaliza uma string removendo diferenças cosméticas.

        O QUE FAZ:
        - Remove espaços em branco extras
        - Converte aspas simples para duplas (para comparação)
        - Remove diferenças de indentação

        ANTES vs DEPOIS:
        ----------------
        ANTES: '    const name = "John";'
        DEPOIS: 'const name = "John";'

        Por que isso é útil?
        Se duas linhas são iguais APÓS normalização,
        então a mudança foi apenas cosmética.
        """
        # Remove espaços em branco no início e fim
        normalized = text.strip()

        # Normaliza aspas: converte ' para " para comparação
        # Isso detecta mudanças como: "text" → 'text'
        normalized = normalized.replace("'", '"')

        # Remove espaços múltiplos (    → espaço único)
        normalized = re.sub(r'\s+', ' ', normalized)

        # Remove espaços antes/depois de : e ,
        normalized = re.sub(r'\s*([,:;])\s*', r'\1', normalized)

        return normalized

    @staticmethod
    def is_cosmetic_change(old_line: str, new_line: str) -> bool:
        """
        Verifica se a mudança entre duas linhas é apenas cosmética.

        MUDANÇAS COSMÉTICAS INCLUEM:
        - Troca de aspas: "text" → 'text'
        - Mudança de indentação
        - Espaços extras
        - Trailing commas

        EXEMPLO:
        --------
        old: '    const x = "hello"'
        new: '    const x = 'hello''
        resultado: True (apenas aspas mudaram)

        old: 'const x = 1'
        new: 'const x = 2'
        resultado: False (valor mudou)
        """
        normalized_old = DiffParser.normalize_for_comparison(old_line)
        normalized_new = DiffParser.normalize_for_comparison(new_line)

        return normalized_old == normalized_new

    @staticmethod
    def classify_hunk_changes(hunk_lines: List[str]) -> ChangeType:
        """
        Classifica um "hunk" (bloco de mudanças) do diff.

        COMO FUNCIONA:
        --------------
        1. Extrai linhas removidas (-) e adicionadas (+)
        2. Emparelha linhas que mudaram
        3. Verifica se TODAS as mudanças são cosméticas
        4. Se sim → COSMETIC, se não → LOGIC_CHANGE

        EXEMPLO:
        --------
        hunk_lines = [
            '-    const x = "hello"',
            '+    const x = 'hello'',
        ]
        resultado: COSMETIC (apenas aspas mudaram)

        hunk_lines = [
            '-    const x = 1',
            '+    const x = 2',
        ]
        resultado: LOGIC_CHANGE (valor mudou)
        """
        removed_lines = []
        added_lines = []

        for line in hunk_lines:
            if line.startswith("-") and not line.startswith("---"):
                # Remove o prefixo '-' e mantém o conteúdo
                removed_lines.append(line[1:])
            elif line.startswith("+") and not line.startswith("+++"):
                # Remove o prefixo '+' e mantém o conteúdo
                added_lines.append(line[1:])

        # Caso 1: Apenas adições (arquivo novo ou código novo)
        if not removed_lines and added_lines:
            return ChangeType.LOGIC_CHANGE

        # Caso 2: Apenas remoções (código deletado)
        if removed_lines and not added_lines:
            return ChangeType.LOGIC_CHANGE

        # Caso 3: Mudanças com mesmo número de linhas
        # Comparamos linha a linha
        if len(removed_lines) == len(added_lines):
            all_cosmetic = True
            for old, new in zip(removed_lines, added_lines):
                if not DiffParser.is_cosmetic_change(old, new):
                    all_cosmetic = False
                    break

            if all_cosmetic:
                return ChangeType.COSMETIC

        # Caso 4: Número diferente de linhas = mudança estrutural
        return ChangeType.LOGIC_CHANGE

    @staticmethod
    def classify_file_changes(diff_text: str) -> Dict[str, any]:
        """
        Classifica TODAS as mudanças de um arquivo.

        RETORNA:
        --------
        {
            "overall_type": ChangeType,  # Classificação geral do arquivo
            "hunks": [                   # Detalhes por bloco
                {
                    "header": "@@ -10,5 +10,5 @@",
                    "type": ChangeType.COSMETIC,
                    "lines_changed": 2
                }
            ],
            "summary": {
                "cosmetic_changes": 5,
                "logic_changes": 0,
                "total_changes": 5
            },
            "is_worth_analyzing": bool   # Se vale a pena enviar para agentes
        }

        POR QUE "is_worth_analyzing"?
        -----------------------------
        Se um arquivo tem APENAS mudanças cosméticas (aspas, espaços),
        não faz sentido enviar para os agentes analisarem.
        Isso evita os 32 comentários irrelevantes que você viu!
        """
        result = {
            "overall_type": ChangeType.UNKNOWN,
            "hunks": [],
            "summary": {
                "cosmetic_changes": 0,
                "logic_changes": 0,
                "total_changes": 0
            },
            "is_worth_analyzing": True
        }

        lines = diff_text.split("\n")
        current_hunk_lines = []
        current_header = ""

        for line in lines:
            # Detecta início de um novo hunk
            match = DiffParser.HUNK_HEADER_PATTERN.search(line)
            if match:
                # Processa hunk anterior se existir
                if current_hunk_lines:
                    hunk_type = DiffParser.classify_hunk_changes(current_hunk_lines)
                    result["hunks"].append({
                        "header": current_header,
                        "type": hunk_type,
                        "lines_changed": len([l for l in current_hunk_lines
                                            if l.startswith("+") or l.startswith("-")])
                    })

                    if hunk_type == ChangeType.COSMETIC:
                        result["summary"]["cosmetic_changes"] += 1
                    else:
                        result["summary"]["logic_changes"] += 1
                    result["summary"]["total_changes"] += 1

                current_header = line
                current_hunk_lines = []
                continue

            # Acumula linhas do hunk atual
            if line.startswith("+") or line.startswith("-") or line.startswith(" "):
                current_hunk_lines.append(line)

        # Processa último hunk
        if current_hunk_lines:
            hunk_type = DiffParser.classify_hunk_changes(current_hunk_lines)
            result["hunks"].append({
                "header": current_header,
                "type": hunk_type,
                "lines_changed": len([l for l in current_hunk_lines
                                    if l.startswith("+") or l.startswith("-")])
            })

            if hunk_type == ChangeType.COSMETIC:
                result["summary"]["cosmetic_changes"] += 1
            else:
                result["summary"]["logic_changes"] += 1
            result["summary"]["total_changes"] += 1

        # Determina classificação geral
        summary = result["summary"]
        if summary["total_changes"] == 0:
            result["overall_type"] = ChangeType.UNKNOWN
            result["is_worth_analyzing"] = False
        elif summary["logic_changes"] == 0:
            # TODAS as mudanças são cosméticas!
            result["overall_type"] = ChangeType.COSMETIC
            result["is_worth_analyzing"] = False
        else:
            result["overall_type"] = ChangeType.LOGIC_CHANGE
            result["is_worth_analyzing"] = True

        return result

    @staticmethod
    def filter_cosmetic_changes(diff_text: str) -> str:
        """
        Remove hunks cosméticos do diff, mantendo apenas mudanças reais.

        ANTES (diff original):
        ----------------------
        @@ -10,5 +10,5 @@
        -    const x = "hello"
        +    const x = 'hello'
        @@ -20,5 +20,5 @@
        -    return calculateTotal(items)
        +    return calculateSum(items)

        DEPOIS (diff filtrado):
        -----------------------
        @@ -20,5 +20,5 @@
        -    return calculateTotal(items)
        +    return calculateSum(items)

        O primeiro hunk foi removido porque era apenas mudança de aspas!
        """
        lines = diff_text.split("\n")
        filtered_lines = []
        current_hunk_lines = []
        current_header = ""
        file_headers = []  # Guarda linhas antes do primeiro @@

        in_hunk = False

        for line in lines:
            # Guarda headers de arquivo (---, +++, etc)
            if not in_hunk and not DiffParser.HUNK_HEADER_PATTERN.search(line):
                file_headers.append(line)
                continue

            # Detecta início de novo hunk
            match = DiffParser.HUNK_HEADER_PATTERN.search(line)
            if match:
                in_hunk = True
                # Processa hunk anterior
                if current_hunk_lines:
                    hunk_type = DiffParser.classify_hunk_changes(current_hunk_lines)
                    # Só inclui se NÃO for cosmético
                    if hunk_type != ChangeType.COSMETIC:
                        filtered_lines.append(current_header)
                        filtered_lines.extend(current_hunk_lines)

                current_header = line
                current_hunk_lines = []
                continue

            # Acumula linhas do hunk
            current_hunk_lines.append(line)

        # Processa último hunk
        if current_hunk_lines:
            hunk_type = DiffParser.classify_hunk_changes(current_hunk_lines)
            if hunk_type != ChangeType.COSMETIC:
                filtered_lines.append(current_header)
                filtered_lines.extend(current_hunk_lines)

        # Se não sobrou nenhum hunk, retorna vazio
        if not any(DiffParser.HUNK_HEADER_PATTERN.search(l) for l in filtered_lines):
            return ""

        # Reconstrói o diff com headers de arquivo
        return "\n".join(file_headers + filtered_lines)
