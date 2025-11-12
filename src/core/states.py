from typing import TypedDict, List, Dict, Any


class FileContext(TypedDict):
    path: str
    diff: str
    module: str


class ModuleAgentAnalysis(TypedDict):
    module_name: str
    files: List[FileContext]
    security_analysis: Dict[str, Any]
    logical_analysis: Dict[str, Any]
    performance_analysis: Dict[str, Any]
    clean_code_analysis: Dict[str, Any]


class HierarchicalPRAnalysisState(TypedDict):
    all_files: List[FileContext]
    modules: Dict[str, List[FileContext]]
    module_analyses: List[ModuleAgentAnalysis]
    final_report: str
