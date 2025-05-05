#!/usr/bin/env python3
"""
02225-Project  预处理脚本（隔离输出 + 统一字段名）

读取   tasks.csv  /  budgets.csv  /  architecture.csv
输出：
    processed_simulate_data.csv   → 只给 Simulator
    processed_analysis_data.csv   → 只给 Analysis Tool
字段规则：
    • 组件行/任务行都用同一列名  scheduler, priority
    • 组件资源列仍叫  budget(Θ) / period(Π)
    • wcet 已按 speed_factor 折算为 wcet_effective
"""

import argparse
from pathlib import Path
import pandas as pd


# ─────────── 工具函数 ───────────
def dense_rm_rank(series: pd.Series) -> pd.Series:
    return series.rank(method="dense", ascending=True).astype(int) - 1


def ensure_no_nan(df: pd.DataFrame, cols: list, name: str):
    miss = df[cols].isna().any()
    if miss.any():
        raise ValueError(f"{name} 缺失必填列：{miss[miss].index.tolist()}")


# ─────────── 主流程 ───────────
def preprocess(in_dir: Path, out_dir: Path):
    # 1. 读原始 CSV
    tasks   = pd.read_csv(in_dir / "tasks.csv")
    budgets = pd.read_csv(in_dir / "budgets.csv")
    arch    = pd.read_csv(in_dir / "architecture.csv")

    # 2. 硬校验
    ensure_no_nan(tasks,   ["task_name", "wcet", "period", "component_id"],          "tasks.csv")
    ensure_no_nan(budgets, ["component_id", "scheduler", "budget", "period", "core_id"], "budgets.csv")
    ensure_no_nan(arch,    ["core_id", "speed_factor", "scheduler"],                 "architecture.csv")

    # 3. component→core,  core→speed_factor
    comp2core = budgets.set_index("component_id")["core_id"]
    tasks["core_id"] = tasks["component_id"].map(comp2core)

    speed_map = arch.set_index("core_id")["speed_factor"]
    tasks["speed_factor"] = tasks["core_id"].map(speed_map)
    tasks["wcet_effective"] = tasks["wcet"] / tasks["speed_factor"]

    # 4. ---- 自动补齐 RM priority  ----
    comp_sched = budgets.set_index("component_id")["scheduler"]
    tasks = tasks.merge(comp_sched.rename("scheduler_comp"), left_on="component_id", right_index=True)

    mask_rm = tasks["scheduler_comp"].eq("RM") & tasks["priority"].isna()
    for cid, sub in tasks[mask_rm].groupby("component_id"):
        tasks.loc[sub.index, "priority"] = dense_rm_rank(sub["period"])
    tasks.drop(columns="scheduler_comp", inplace=True)
    tasks["priority"] = tasks["priority"].astype("Int64")

    # 顶层 core = RM 时，补 component priority
    core_sched = arch.set_index("core_id")["scheduler"]
    budgets = budgets.merge(core_sched.rename("scheduler_core"), on="core_id")
    mask_core_rm = budgets["scheduler_core"].eq("RM") & budgets["priority"].isna()
    for core, sub in budgets[mask_core_rm].groupby("core_id"):
        budgets.loc[sub.index, "priority"] = dense_rm_rank(sub["period"])
    budgets.drop(columns="scheduler_core", inplace=True)
    budgets["priority"] = budgets["priority"].astype("Int64")

    # 5-A 生成 Simulator 专用 CSV
    sim_df = tasks[[
        "task_name", "component_id", "core_id",
        "period", "wcet_effective", "priority"
    ]]
    sim_path = out_dir / "processed_simulate_data.csv"

    # 5-B 生成 Analysis 专用 CSV
    ana_components = budgets.rename(columns={
        "scheduler": "scheduler",   # 保持原列名
        "budget":    "budget",
        "period":    "period"
    })
    ana_components["alpha"] = pd.NA
    ana_components["delta"] = pd.NA

    ana_tasks = tasks[[
        "task_name", "component_id",
        "period", "wcet_effective", "priority"
    ]]

    ana_df = pd.concat([ana_components, ana_tasks], ignore_index=True, sort=False)
    ana_path = out_dir / "processed_analysis_data.csv"

    # 6. 保存
    out_dir.mkdir(parents=True, exist_ok=True)
    sim_df.to_csv(sim_path, index=False)
    ana_df.to_csv(ana_path, index=False)

    print("✅ 预处理完成")
    print(f"   Simulator 文件 : {sim_path}")
    print(f"   Analysis  文件 : {ana_path}")


# ─────────── CLI ───────────
if __name__ == "__main__":
    # ------- 直接在代码里写死路径 -------
    in_dir = Path("/Users/Zayne/DTU/S2/Distributed Real-Time Systems/02225_DRTS_Project/DRTS_Project-Test-Cases/10-unschedulable-test-case")
    out_dir = Path("/Users/Zayne/DTU/S2/Distributed Real-Time Systems/02225_DRTS_Project/output/10-unschedulable-test-case")

    # 调用主函数
    preprocess(in_dir, out_dir)