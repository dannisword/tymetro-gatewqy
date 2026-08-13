import os
import sys
import json
import subprocess

# 確保直接執行腳本時能正確尋找到 app 模組
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from app.core.logger import logger

VERSION_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "git_version.json")

def get_git_info_from_command() -> dict:
    """嘗試透過 git 指令獲取目前版本資訊"""
    try:
        # 定位到 git 專案根目錄
        cwd = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Git commit hash
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=cwd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        # Git branch
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        # Git commit date
        date = subprocess.check_output(["git", "log", "-1", "--format=%cd", "--date=iso"], cwd=cwd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        # Git dirty status
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=cwd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        is_dirty = len(status) > 0
        
        version_info = {
            "commit": commit,
            "branch": branch,
            "date": date,
            "dirty": is_dirty,
            "version": f"{branch}-{commit}" + ("-dirty" if is_dirty else "")
        }
        return version_info
    except Exception:
        return {}

def load_git_version() -> dict:
    """載入 Git 版本資訊，若有 git 指令且在開發環境則自動更新 json 檔案"""
    git_info = get_git_info_from_command()
    
    if git_info:
        # 成功讀取到 git 資訊，更新/寫入 json 檔案以供發佈後（無 git 環境）讀取
        try:
            with open(VERSION_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(git_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write git_version.json: {e}")
        return git_info
    
    # 若無法執行 git 指令，則嘗試讀取現有的 json 檔案
    if os.path.exists(VERSION_FILE_PATH):
        try:
            with open(VERSION_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read git_version.json: {e}")
            
    return {
        "commit": "unknown",
        "branch": "unknown",
        "date": "unknown",
        "dirty": False,
        "version": "unknown"
    }

git_version_info = load_git_version()

if __name__ == "__main__":
    print(f"Git version updated: {git_version_info}")
