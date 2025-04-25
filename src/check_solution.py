import pandas as pd, sys, pathlib, config
from datetime import datetime

output_path = pathlib.Path(__file__).resolve().parent.parent / "output" / "result_check_solution.txt"
case_name = sys.argv[1] if len(sys.argv) > 1 else "未指定Case名称"
#以“追加”写入
with open(output_path, "a", encoding="utf-8") as f:
    f.write("\n" + "="*60 + "\n")
    f.write(f"📂 Test Case：{case_name}\n")
    f.write(f"🧪 Runtime of check_solutiond: {datetime.now()}\n")
    f.write("="*60 + "\n")

    csv_path = pathlib.Path(config.SOLUTION_PATH)
    if not csv_path.exists():
        f.write(f"❌ can't find {csv_path}\n")
        sys.exit(1)

    df = pd.read_csv(csv_path)

#用于根据多个候选名称在列名中查找匹配列（忽略大小写）
    def find(*aliases):
        return next((c for c in df.columns
                     if c.lower() in [a.lower() for a in aliases]), None)

    task_ok_col  = find("task_schedulable", "task_ok", "sched")
    comp_ok_col  = find("component_schedulable", "comp_ok", "component_sched")
    if task_ok_col is None:
        f.write("Column 'task_schedulable' not found in solution.csv\n")
        f.write(f"Current columns are: {list(df.columns)}\n")  # for debugging
        sys.exit(1)

    n_task     = len(df)
    n_task_bad = (df[task_ok_col] == 0).sum()
    task_success_rate = round(100.0 * (1 - n_task_bad / n_task), 2) #输出调度成功率（任务维度）

    if comp_ok_col:
        comp = (df.groupby("component_id")[comp_ok_col].first() == 0)
        n_comp_bad = comp.sum()
    else:
        n_comp_bad = '—'

    f.write(f"Total number of tasks        : {n_task}\n")
    f.write(f"Number of deadline-miss tasks: {n_task_bad}\n")
    f.write(f"Number of unschedulable components: {n_comp_bad}\n")
    f.write(f"Task scheduling success rate : {task_success_rate:.2f}%\n")

    if n_task_bad:
        f.write("\nFirst few tasks that missed their deadlines:\n")
        f.write(df.loc[df[task_ok_col] == 0, ["task_name", "component_id"]]
                .head().to_string(index=False) + "\n")
    f.write("\nTask scheduling success rate per component:\n") #输出每个组件的调度成功率（组件内任务平均），可以判断是哪个组件出了问题，尤其是多个任务的组件
    component_rates = df.groupby("component_id")[task_ok_col].mean()
    for cid, rate in component_rates.items():
        f.write(f"  - {cid:<20} : {rate:.2%}\n")


    f.write("All tasks schedulable 🎉\n" if n_task_bad == 0 else "✘ Some tasks missed their deadlines\n")


# 向 stdout 打印当前 case 的 Markdown 汇总行（供 main.py 捕获）
print(f"[SUMMARY] | {case_name} | {n_task} | {n_task_bad} | {100.0 * (1 - n_task_bad / n_task):.2f}% | {n_comp_bad} |")