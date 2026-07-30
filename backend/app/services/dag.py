"""DAG:变量依赖图的构建、拓扑排序与环检测。

用于按公式变量依赖关系排序:formula 变量依赖其它变量(extract/database/formula),
需按依赖顺序求值。依赖以变量 id 表示;禁用变量(enabled=False)不参与 DAG。
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


class CycleError(Exception):
    """DAG 存在环或无效依赖。"""

    def __init__(self, cycles: list[list[str]] | None = None, errors: list[str] | None = None) -> None:
        self.cycles = cycles or []
        self.errors = errors or []
        super().__init__(f"环: {self.cycles}; 错误: {self.errors}")


def build_dag(variables: list[Any]) -> dict[Any, set]:
    """从变量列表构建依赖图 ``{var_id: set(dep_id)}``。只包含启用变量。"""
    enabled_ids = {v.id for v in variables if getattr(v, "enabled", True)}
    graph: dict[Any, set] = {}
    for v in variables:
        if not getattr(v, "enabled", True):
            continue
        deps = getattr(v, "depends_on", []) or []
        # 只保留启用变量内的依赖(外部依赖如 extract 根节点不参与排序)
        graph[v.id] = {d for d in deps if d in enabled_ids}
    return graph


def detect_cycles(variables: list[Any]) -> list[list[str]]:
    """检测环,返回环路径(变量名列表)。禁用变量不参与。

    使用 Tarjan 强连通分量算法:大于 1 个节点的 SCC 即为环;自环也算。
    """
    # id -> name 映射(仅启用变量)
    id_to_name: dict[Any, str] = {
        v.id: v.name for v in variables if getattr(v, "enabled", True)
    }
    graph = build_dag(variables)
    nodes = list(graph.keys())

    index_counter = [0]
    stack: list[Any] = []
    lowlink: dict[Any, int] = {}
    index: dict[Any, int] = {}
    on_stack: dict[Any, bool] = {}
    sccs: list[list[Any]] = []

    def strongconnect(node: Any) -> None:
        index[node] = index_counter[0]
        lowlink[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack[node] = True

        for succ in graph.get(node, set()):
            if succ not in index:
                strongconnect(succ)
                lowlink[node] = min(lowlink[node], lowlink[succ])
            elif on_stack.get(succ):
                lowlink[node] = min(lowlink[node], index[succ])

        if lowlink[node] == index[node]:
            scc: list[Any] = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == node:
                    break
            sccs.append(scc)

    for node in nodes:
        if node not in index:
            strongconnect(node)

    cycles: list[list[str]] = []
    for scc in sccs:
        # SCC 节点数 > 1 是环;单节点但存在自引用也是环
        if len(scc) > 1:
            cycles.append([id_to_name.get(n, str(n)) for n in scc])
        elif len(scc) == 1:
            n = scc[0]
            if n in graph.get(n, set()):
                cycles.append([id_to_name.get(n, str(n))])
    return cycles


def topological_sort(variables: list[Any]) -> list:
    """Kahn 算法拓扑排序(被依赖者在前)。有环抛 CycleError。

    只排序启用变量;引用不存在(非启用)的依赖视为外部根节点,跳过。
    """
    graph = build_dag(variables)
    nodes = list(graph.keys())
    in_degree: dict[Any, int] = {n: 0 for n in nodes}
    dependents: dict[Any, list] = defaultdict(list)
    for node, deps in graph.items():
        for dep in deps:
            in_degree[node] += 1
            dependents[dep].append(node)

    queue = deque([n for n in nodes if in_degree[n] == 0])
    order: list = []
    while queue:
        n = queue.popleft()
        order.append(n)
        for child in dependents.get(n, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(order) != len(nodes):
        cycles = detect_cycles(variables)
        raise CycleError(cycles=cycles)
    return order


def validate_dag(variables: list[Any]) -> dict:
    """完整校验:返回 ``{valid, cycles, errors}``。

    - cycles: 环路径(变量名)
    - errors: 引用不存在变量名的错误信息
    """
    errors: list[str] = []
    enabled = [v for v in variables if getattr(v, "enabled", True)]
    enabled_ids = {v.id for v in enabled}
    enabled_names = {v.name for v in enabled}

    # 检查 depends_on 引用的 id 是否存在(启用集合内)
    for v in enabled:
        deps = getattr(v, "depends_on", []) or []
        for d in deps:
            if d not in enabled_ids:
                errors.append(f"变量 '{v.name}' 依赖了不存在或已禁用的变量(id={d})")

    cycles = detect_cycles(enabled)
    return {"valid": len(cycles) == 0 and len(errors) == 0, "cycles": cycles, "errors": errors}
