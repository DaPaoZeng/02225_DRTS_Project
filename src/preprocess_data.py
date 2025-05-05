#!/usr/bin/env python3
"""
preprocess_data.py  —  生成单一任务表  preprocessed_tasks.csv
路径全部取自用户自定义的 config.py：
    TASKS_PATH, BUDGETS_PATH, ARCH_PATH, PREPROCESSED_TASKS_PATH
"""
import pandas as pd
from pathlib import Path
import config   # ← 你现有的配置模块


# ────────────────────────── 工具 ──────────────────────────
def dense_rm_rank(series: pd.Series) -> pd.Series:
    return series.rank(method="dense", ascending=True).astype(int) - 1


def must_have(df: pd.DataFrame, cols: list, name: str):
    miss = df[cols].isna().any()
    if miss.any():
        raise ValueError(f"{name} 缺失必填列: {miss[miss].index.tolist()}")


# ────────────────────────── 预处理 ──────────────────────────
def main():
    # 1. 读取原始 CSV
    tasks   = pd.read_csv(config.TASKS_PATH)
    budgets = pd.read_csv(config.BUDGETS_PATH)
    arch    = pd.read_csv(config.ARCH_PATH)

    must_have(tasks,   ["task_name", "wcet", "period", "component_id"],          "tasks.csv")
    must_have(budgets, ["component_id", "scheduler", "core_id"],                 "budgets.csv")
    must_have(arch,    ["core_id", "speed_factor"],                              "architecture.csv")

    # 2. component → core,  core → speed_factor
    tasks["core_id"] = tasks["component_id"].map(
        budgets.set_index("component_id")["core_id"]
    )
    tasks["speed_factor"] = tasks["core_id"].map(
        arch.set_index("core_id")["speed_factor"]
    )

    # 3. WCET 折算
    tasks["wcet"] = tasks["wcet"] / tasks["speed_factor"]

    # 4. 合并调度器类型
    tasks["scheduler"] = tasks["component_id"].map(
        budgets.set_index("component_id")["scheduler"].str.upper()
    )

    # 5. 自动补齐 RM priority
    mask_rm = tasks["scheduler"].eq("RM") & tasks["priority"].isna()
    for cid, sub in tasks[mask_rm].groupby("component_id"):
        tasks.loc[sub.index, "priority"] = dense_rm_rank(sub["period"])
    tasks["priority"] = tasks["priority"].astype("Int64")

    # 6. 选列并保存
    final = tasks[[
        "component_id", "scheduler", "core_id",
        "task_name", "wcet", "period", "priority"
    ]]

    out_path = Path(config.PREPROCESSED_TASKS_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(out_path, index=False)
    print(f"✅ 预处理完成 → {out_path}")


if __name__ == "__main__":
    main()
