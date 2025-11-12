from typing import Dict
from ..states import PRAnalysisState, FileContext


def group_by_module(state: PRAnalysisState) -> Dict:
    modules: Dict[str, list[FileContext]] = {}

    for file_ctx in state["all_files"]:
        path_parts = file_ctx["path"].split("/")

        if len(path_parts) == 1:
            module_name = "_root"
        elif len(path_parts) == 2:
            module_name = path_parts[0]
        else:
            if path_parts[0] == "src":
                module_name = path_parts[1]
            else:
                module_name = path_parts[0]

        file_ctx["module"] = module_name

        if module_name not in modules:
            modules[module_name] = []

        modules[module_name].append(file_ctx)

    return {"modules": modules}


def count_files_per_module(modules: Dict[str, list[FileContext]]) -> Dict[str, int]:
    return {module: len(files) for module, files in modules.items()}


def get_module_paths(
    modules: Dict[str, list[FileContext]], module_name: str
) -> list[str]:
    if module_name not in modules:
        return []

    return [file["path"] for file in modules[module_name]]
