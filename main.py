from pathlib import Path
import re
import subprocess
import sys

# === 路径修改 ===
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
CONFIG_FILE = SRC / "config.py"
CASES_ROOT = ROOT / "DRTS_Project-Test-Cases"
OUTPUT_ROOT = ROOT / "output"

# 获取子文件夹列表
case_folders = sorted([f for f in CASES_ROOT.iterdir() if f.is_dir()])[:10]
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
    result = subprocess.run([sys.executable, str(check_script)])
    if result.returncode != 0:
        print("❌ check_solution.py 出错")
        return False
    return True


# === 4) 主流程 ===
for idx, folder in enumerate(case_folders, 1):
    print(f"\n🔁 第 {idx} 个测试子文件夹：{folder.name}")

    out_dir = OUTPUT_ROOT / folder.name
    out_dir.mkdir(parents=True, exist_ok=True)

    update_config(base_path=folder, output_dir=out_dir)

    success = run_all_scripts()
    if not success:
        print(f"!!! 停止于第 {idx} 个子文件夹 {folder.name}")
        break

print("\n✅ 所有测试完成！")