import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import os
import config

# --------------------------------------------------
# Data classes
# --------------------------------------------------

@dataclass
class Task:
    name: str
    wcet: float          # 已按 core speed 缩放
    period: float
    component_id: str
    priority: Optional[int]  # EDF 任务可为 None


@dataclass
class Component:
    id: str
    scheduler: str       # "EDF" / "RM"
    core_id: str
    tasks: List[Task] = field(default_factory=list)

    def sorted_tasks(self) -> List[Task]:
        """RM 组件依 priority 升序，EDF 保持原插入顺序"""
        if self.scheduler.upper() == "RM":
            return sorted(self.tasks, key=lambda t: t.priority if t.priority is not None else 1e9)
        return self.tasks


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def load_architecture() -> Dict[str, Dict[str, float]]:
    arch_df = pd.read_csv(config.ARCH_PATH)
    required = {"core_id", "speed_factor", "scheduler"}
    missing = required - set(arch_df.columns)
    if missing:
        raise ValueError(f"[ARCH] 缺少字段: {', '.join(missing)}")
    print(f"[ARCH] 读取 {len(arch_df)} cores → {config.ARCH_PATH}")
    return arch_df.set_index("core_id").to_dict("index")


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    print("=== Drts 预处理开始 ===")

    tasks_df = pd.read_csv(config.TASKS_PATH)
    budgets_df = pd.read_csv(config.BUDGETS_PATH)
    arch_map = load_architecture()

    print(f"[TASKS] {len(tasks_df)} 行  ←  {config.TASKS_PATH}")
    print(f"[BUDGETS] {len(budgets_df)} 行 ←  {config.BUDGETS_PATH}")

    # ---------- Build components ----------
    components: Dict[str, Component] = {}
    for _, row in budgets_df.iterrows():
        comp = Component(
            id=row["component_id"],
            scheduler=str(row["scheduler"]).strip().upper(),
            core_id=row["core_id"],
        )
        components[comp.id] = comp

    # ---------- Assign tasks ----------
    for _, row in tasks_df.iterrows():
        comp_id = row["component_id"]
        if comp_id not in components:
            raise ValueError(f"在 budgets.csv 中找不到 component_id={comp_id}")

        core_id = components[comp_id].core_id
        if core_id not in arch_map:
            raise ValueError(f"在 architecture.csv 中找不到 core_id={core_id}")

        speed = arch_map[core_id]["speed_factor"]
        adjusted_wcet = float(row["wcet"]) / float(speed)

        task = Task(
            name=row["task_name"],
            wcet=adjusted_wcet,
            period=float(row["period"]),
            component_id=comp_id,
            priority=None if pd.isna(row["priority"]) else int(row["priority"]),
        )
        components[comp_id].tasks.append(task)

    # ---------- Verbose dump ----------
    print("\n---- 组件与任务明细 ----")
    for comp in components.values():
        print(f"[COMP] {comp.id:<15} sched={comp.scheduler:<3} core={comp.core_id}")
        for t in comp.sorted_tasks():
            print(f"       └─ {t.name:<20} WCET={t.wcet:<6.2f}  P={t.period:<5}  prio={t.priority}")

    # ---------- Emit CSV ----------
    output_rows = []
    for comp in components.values():
        for task in comp.sorted_tasks():
            row = {
                "component_id": comp.id,
                "scheduler": comp.scheduler,
                "core_id": comp.core_id,
                "task_name": task.name,
                "wcet": task.wcet,
                "period": task.period,
                "priority": task.priority,
            }
            output_rows.append(row)
            print(f"[CSV] {row}")

    os.makedirs(os.path.dirname(config.PREPROCESSED_TASKS_PATH), exist_ok=True)
    pd.DataFrame(output_rows).to_csv(config.PREPROCESSED_TASKS_PATH, index=False)
    print(f"\n✅ 已保存预处理任务表 → {config.PREPROCESSED_TASKS_PATH}")
    print("=== Drts 预处理结束 ===")


if __name__ == "__main__":
    main()

"""

  | 位置 | 变动 | 目的
1 | Task dataclass | priority: Optional[int] | 允许 EDF 组件的 priority 列为空 (NaN)
2 | import | from typing import List, Dict, Optional | 为可选优先级引入 Optional
3 | 读取 priority | priority=None if pd.isna(row["priority"]) else int(row["priority"]) | 若 CSV 中为空值，不再抛异常
4 | load_architecture() | 检查缺失字段，返回 speed_factor + 顶层 scheduler | 提前暴露输入数据问题
5 | WCET 调整 | adjusted_wcet = wcet / speed_factor | 把核速度折算进 WCET
6 | 写 CSV | 写文件逻辑移到最外层一次完成 | 修复原先重复写 N² 行
7 | 任务排序 | Component.sorted_tasks() | RM 组件按优先级，EDF 保持原顺序
8 | 目录保障 | os.makedirs(..., exist_ok=True) | 输出路径若不存在自动创建
"""