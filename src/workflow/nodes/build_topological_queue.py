"""Node 5: Topological Sort & Dependency Queue Builder Node.

Extracts import dependencies across testable_files using language_rules.import_export_patterns
and uses Python's graphlib.TopologicalSorter with cycle-resolution to group independent files into parallel execution level batches (topological_levels) with 0 LLM tokens.
"""

from graphlib import TopologicalSorter, CycleError
import re
from pathlib import Path
from typing import Any, Dict, List, Set

from src.services.checkpoint_service import checkpoint_service
from src.services.logger_service import logger
from src.workflow.state import QAState


def extract_file_dependencies(
    file_path: Path,
    workspace_dir: Path,
    testable_files_set: Set[str],
    import_export_patterns: List[str]
) -> List[str]:
    """Extract relative import dependencies of file_path matching testable_files_set.

    Args:
        file_path: Path to target source file.
        workspace_dir: Path to project root directory.
        testable_files_set: Set of relative testable file paths.
        import_export_patterns: List of import/export pattern strings from language_rules.

    Returns:
        List of relative testable file paths that file_path imports.
    """
    dependencies: List[str] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return dependencies

    rel_source_path = str(file_path.relative_to(workspace_dir)).replace("\\", "/")
    source_dir = file_path.parent

    extracted_specifiers: Set[str] = set()

    for pattern in import_export_patterns:
        try:
            for match in re.finditer(pattern, content, re.MULTILINE):
                if match.groups():
                    spec = match.group(1).strip()
                    if spec and len(spec) > 1:
                        extracted_specifiers.add(spec)
        except Exception:
            pass

    for specifier in extracted_specifiers:
        if len(specifier) < 2:
            continue

        candidates: List[str] = []
        if specifier.startswith("."):
            resolved = (source_dir / specifier).resolve()
            try:
                cand_rel = str(resolved.relative_to(workspace_dir)).replace("\\", "/")
                candidates.append(cand_rel)
            except ValueError:
                pass
        else:
            norm_spec = specifier.replace(".", "/").replace("::", "/").lstrip("/")
            candidates.append(norm_spec)
            candidates.append(specifier)

        for cand_base in candidates:
            for target_file in testable_files_set:
                if target_file == rel_source_path:
                    continue

                target_no_ext = target_file.rsplit(".", 1)[0] if "." in target_file else target_file
                target_dir_index = target_no_ext.replace("/index", "").replace("/__init__", "")

                if (
                    cand_base == target_file
                    or cand_base == target_no_ext
                    or cand_base == target_dir_index
                    or target_no_ext.endswith("/" + cand_base)
                    or target_file.endswith("/" + cand_base)
                ):
                    if target_file not in dependencies:
                        dependencies.append(target_file)

    return dependencies


def build_topological_queue_node(state: QAState) -> Dict[str, Any]:
    """Node 5: Build topological execution level queue for testable_files using graphlib.TopologicalSorter.

    Args:
        state: Active QAState dictionary.

    Returns:
        State update dictionary containing topological_levels.
    """
    logger.info("[Node 5: TopologicalSort] Building parallel topological execution queue using graphlib...")

    ws_dir_str = state.get("workspace_dir", "")
    workspace_dir = Path(ws_dir_str).resolve() if ws_dir_str else Path(".temp").resolve()

    raw_testable_files = state.get("testable_files") or []
    testable_files = [str(Path(f)).replace("\\", "/") for f in raw_testable_files]
    testable_files_set = set(testable_files)

    language_rules = state.get("language_rules") or {}
    import_export_patterns = language_rules.get("import_export_patterns") or []

    if not testable_files:
        logger.warning("[Node 5: TopologicalSort] No testable files found in state. Returning empty topological queue.")
        update_payload = {"topological_levels": []}
        checkpoint_service.save_checkpoint(workspace_dir, {**state, **update_payload})
        return update_payload

    # 1. Build initial dependency graph
    dependency_graph: Dict[str, List[str]] = {}
    for rel_path in testable_files:
        abs_path = workspace_dir / rel_path
        deps = extract_file_dependencies(
            file_path=abs_path,
            workspace_dir=workspace_dir,
            testable_files_set=testable_files_set,
            import_export_patterns=import_export_patterns,
        )
        dependency_graph[rel_path] = deps

    # 2. Build safe_graph mapping file -> dependencies in testable_files
    safe_graph: Dict[str, List[str]] = {file: [] for file in testable_files}
    for file, imps in dependency_graph.items():
        if file in safe_graph:
            safe_graph[file] = [imp for imp in imps if imp in testable_files_set]

    # 3. Resolve direct two-way cycles so graphlib.TopologicalSorter never fails
    for node, deps in list(safe_graph.items()):
        for dep in list(deps):
            if dep in safe_graph and node in safe_graph[dep]:
                if node < dep:
                    safe_graph[node].remove(dep)

    # 4. Perform topological sort using graphlib.TopologicalSorter
    topological_queue: List[str] = []
    try:
        ts = TopologicalSorter(safe_graph)
        topological_queue = list(ts.static_order())
    except CycleError:
        logger.warning("[Node 5: TopologicalSort] Cycle detected. Using deterministic fallback sorting.")
        topological_queue = sorted(testable_files)
    except Exception as e:
        logger.error(f"[Node 5: TopologicalSort] Error during graphlib sorting: {e}.")
        topological_queue = sorted(testable_files)

    # Ensure all testable files are present and normalized POSIX forward slashes
    placed_set = set(topological_queue)
    for file in testable_files:
        if file not in placed_set:
            topological_queue.append(file)

    topological_queue = [f.replace("\\", "/") for f in topological_queue]

    logger.success(
        f"[Node 5: TopologicalSort] Successfully built topological queue of {len(topological_queue)} files using graphlib."
    )

    update_payload: Dict[str, Any] = {
        "topological_levels": topological_queue,
    }

    # Persist updated snapshot to state.json via CheckpointService
    full_updated_state = {**state, **update_payload}
    checkpoint_service.save_checkpoint(workspace_dir, full_updated_state)

    logger.table_summary(
        title="Topological Dependency Queue Results",
        items={
            "Total Testable Files": len(testable_files),
            "Topological Queue Size": len(topological_queue),
            "First File to Test": topological_queue[0] if topological_queue else "None",
            "LLM Tokens Consumed": 0,
        }
    )

    return update_payload

