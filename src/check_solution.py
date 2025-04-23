import pandas as pd, sys, pathlib, config
from datetime import datetime

output_path = pathlib.Path(__file__).resolve().parent.parent / "output" / "result_check_solution.txt"
case_name = sys.argv[1] if len(sys.argv) > 1 else "未指定Case名称"
#以“追加”写入
with open(output_path, "a", encoding="utf-8") as f:
    f.write("\n" + "="*60 + "\n")
    f.write(f"📂 测试用例：{case_name}\n")
    f.write(f"🧪 check_solution 运行时间: {datetime.now()}\n")
    f.write("="*60 + "\n")

    csv_path = pathlib.Path(config.SOLUTION_PATH)
    if not csv_path.exists():
        f.write(f"❌ 找不到 {csv_path}\n")
        sys.exit(1)

    df = pd.read_csv(csv_path)

#用于根据多个候选名称在列名中查找匹配列（忽略大小写）
    def find(*aliases):
        return next((c for c in df.columns
                     if c.lower() in [a.lower() for a in aliases]), None)

    task_ok_col  = find("task_schedulable", "task_ok", "sched")
    comp_ok_col  = find("component_schedulable", "comp_ok", "component_sched")
    if task_ok_col is None:
        f.write("❌ solution.csv 里找不到 task_schedulable 列\n")
        f.write(f"📌 当前列名为：{list(df.columns)}\n")  #调试
        sys.exit(1)

    n_task     = len(df)
    n_task_bad = (df[task_ok_col] == 0).sum()

    if comp_ok_col:
        comp = (df.groupby("component_id")[comp_ok_col].first() == 0)
        n_comp_bad = comp.sum()
    else:
        n_comp_bad = '—'

    f.write(f"任务总数          : {n_task}\n")
    f.write(f"❌ deadline-miss 任务数 : {n_task_bad}\n")
    f.write(f"❌ 不可调组件数       : {n_comp_bad}\n")

    if n_task_bad:
        f.write("\n前几个 miss 的任务：\n")
        f.write(df.loc[df[task_ok_col]==0, ["task_name", "component_id"]]
                  .head().to_string(index=False) + "\n")

    f.write("✓ 全部可调度 🎉\n" if n_task_bad == 0 else "✘ 有任务 miss\n")
    f.write("─"*60 + "\n")