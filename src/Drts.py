import pandas as pd
from dataclasses import dataclass, field
from typing import List
import config

# === 定义 Task 和 Component 类 ===
@dataclass
class Task:
    name: str
    wcet: int
    period: int
    component_id: str
    priority: int

@dataclass
class Component:
    id: str
    scheduler: str
    core_id: str
    tasks: List[Task] = field(default_factory=list)

# === 读取 CSV 文件 ===
tasks_df = pd.read_csv(config.TASKS_PATH)
budgets_df = pd.read_csv(config.BUDGETS_PATH)  # 提供 component 的 scheduler 和 core
architecture_df = pd.read_csv(config.ARCH_PATH)  # 提供 core 的性能参数（可选）

# === 构建组件对象 ===
components = {}
for _, row in budgets_df.iterrows():
    comp = Component(
        id=row['component_id'],
        scheduler=row['scheduler'],
        core_id=row['core_id']
    )
    components[comp.id] = comp

# === 把任务塞进组件 ===
for _, row in tasks_df.iterrows():
    task = Task(
        name=row['task_name'],
        wcet=row['wcet'],
        period=row['period'],
        component_id=row['component_id'],
        priority=row['priority']
    )
    if task.component_id in components:
        components[task.component_id].tasks.append(task)

# === 打印结构查看 ===
for comp in components.values():
    print(f"Component: {comp.id}, Scheduler: {comp.scheduler}, Core: {comp.core_id}")
    for task in comp.tasks:
        print(f"  Task: {task.name}, WCET: {task.wcet}, Period: {task.period}, Priority: {task.priority}")

        # === 保存为 CSV 文件（扁平结构）===
        output_rows = []

        for comp in components.values():
            for task in comp.tasks:
                output_rows.append({
                    "component_id": comp.id,
                    "scheduler": comp.scheduler,
                    "core_id": comp.core_id,
                    "task_name": task.name,
                    "wcet": task.wcet,
                    "period": task.period,
                    "priority": task.priority
                })

        # 保存为 CSV
        output_df = pd.DataFrame(output_rows)
        output_df.to_csv(config.PREPROCESSED_TASKS_PATH, index=False)

        print(f"✅ 已保存为 preprocessed_tasks.csv，路径为 {config.PREPROCESSED_TASKS_PATH}")


