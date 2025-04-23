# --- check_solution.py -----------------------------------------
import pandas as pd, sys, pathlib, config

csv_path = pathlib.Path(config.SOLUTION_PATH)
if not csv_path.exists():
    sys.exit(f"❌ 找不到 {csv_path}")

df = pd.read_csv(csv_path)

# 1. 列名适配（忽略大小写）
def find(col, *aliases):
    return next((c for c in df.columns
                 if c.lower() in [a.lower() for a in aliases]), None)

task_ok_col  = find("task_schedulable" , "task_schedulable",  "task_ok",  "sched")
comp_ok_col  = find("component_schedulable",
                    "component_schedulable", "comp_ok", "component_sched")

if task_ok_col is None:
    sys.exit("❌ solution.csv 里找不到 task_schedulable 列")

# 2. 统计
n_task     = len(df)
n_task_bad = (df[task_ok_col] == 0).sum()

if comp_ok_col:
    comp = (df.groupby("component_id")[comp_ok_col].first() == 0)
    n_comp_bad = comp.sum()
else:
    n_comp_bad = '—'

print("─"*60)
print(f"任务总数      : {n_task}")
print(f"❌ deadline-miss 任务数 : {n_task_bad}")
print(f"❌ 不可调组件数     : {n_comp_bad}")

if n_task_bad:
    print("\n前几个 miss 的任务：")
    print(df.loc[df[task_ok_col]==0, ["task_name","component_id"]].head())

print("✓ 全部可调度 🎉" if n_task_bad==0 else "✘ 有任务 miss")
print("─"*60)
# ---------------------------------------------------------------
