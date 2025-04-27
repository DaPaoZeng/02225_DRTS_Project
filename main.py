from pathlib import Path
from datetime import datetime
import re
import subprocess
import sys

# === 路径修改 ===
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
CONFIG_FILE = SRC / "config.py"
CASES_ROOT = ROOT / "DRTS_Project-Test-Cases"
OUTPUT_ROOT = ROOT / "output"

# === 初始化 result_check_solution.txt 文件 ===
RESULT_FILE = OUTPUT_ROOT / "result_check_solution.txt"
if not RESULT_FILE.exists():
    RESULT_FILE.write_text("📄 check_solution.py execution log\n", encoding="utf-8")

# 获取子文件夹列表
def natural_key(f):
    # 提取文件名中的数字部分用于排序（如 "10-case" -> [10]）
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', f.name)]
case_folders = sorted([f for f in CASES_ROOT.iterdir() if f.is_dir()], key=natural_key)[:10]
if not case_folders:
    print("!!! 没有找到任何测试子文件夹！请确认 DRTS_Project-Test-Cases/ 下有内容")
    sys.exit(1)


# 修改 config.py 路径变量
def update_config(base_path: Path, output_dir: Path):
    text = CONFIG_FILE.read_text(encoding="utf-8")

    # 替换 BASE_PATH
    text, n1 = re.subn(
        r'^(BASE_PATH\s*=\s*)(["\']).*?\2',
        rf'\1"{base_path.as_posix()}"',
        text,
        flags=re.MULTILINE
    )

    # 替换 OUTPUT_DIR
    text, n2 = re.subn(
        r'^(OUTPUT_DIR\s*=\s*)(["\']).*?\2',
        rf'\1"{output_dir.as_posix()}"',
        text,
        flags=re.MULTILINE
    )

    CONFIG_FILE.write_text(text, encoding="utf-8")
    print(f"🛠️ 修改 config.py：BASE_PATH={base_path.name}，OUTPUT_DIR={output_dir.name}")

summary_lines = []
# === 脚本 ===
scripts = [
    "Drts.py",
    "analyzer.py",
    "sim.py",
    "simulate_full_auto.py"
]


def run_all_scripts():
    for script in scripts:
        path = SRC / script
        print(f"\n▶ 运行：{script}")
        result = subprocess.run([sys.executable, str(path)])
        if result.returncode != 0:
            print(f"❌ 脚本出错：{script}，中止本轮执行")
            return False

    # 运行 check_solution.py（假设在项目根目录）
    check_script = SRC / "check_solution.py"
    print(f"\n▶ 运行：check_solution.py")

    #result = subprocess.run([sys.executable, str(check_script), folder.name], check=True)
    args = [sys.executable, str(check_script), folder.name]

    # ✅ 捕获 check_solution 的输出
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ check_solution.py 出错")
        return False

    # ✅ 提取 [SUMMARY] 行
    for line in result.stdout.splitlines():
        if line.startswith("[SUMMARY]"):
            summary_lines.append(line.replace("[SUMMARY]", "").strip())




    if result.returncode != 0:
        print("❌ check_solution.py 出错")
        return False
    return True


# === 4) Main Execution Loop ===
for idx, folder in enumerate(case_folders, 1):
    print(f"\n🔁 Running test case folder {idx}: {folder.name}")

    out_dir = OUTPUT_ROOT / folder.name
    out_dir.mkdir(parents=True, exist_ok=True)

    update_config(base_path=folder, output_dir=out_dir)

    success = run_all_scripts()
    if not success:
        print(f"!!! Stopped at test case folder {idx}: {folder.name}")
        break

print("\n✅ All test cases completed!")


with RESULT_FILE.open("a", encoding="utf-8") as f:
    f.write(" \n")
    f.write(" \n")
    f.write("|----------------------------------------------------------------------------------------------------|\n")
    f.write("|                                   Summary of the 10 Test Cases                                     |\n")
    f.write(f"|----------------------------Creation Time: {datetime.now()}-------------------------------|\n")
    f.write("|----------------------------------------------------------------------------------------------------|\n")
    f.write("| Case Name                   | Total Tasks  | Missed Tasks  | Task Success    | Components Missed   |\n")
    f.write("|-----------------------------|--------------|---------------|-----------------|---------------------|\n")
    for line in summary_lines:
        f.write(line + "\n")
    f.write("|----------------------------------------------------------------------------------------------------|\n")
