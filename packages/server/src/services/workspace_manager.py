"""
Git workspace management module for handling Git operations for goals.
"""
import subprocess
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
WORKSPACE_ROOT = os.path.join(os.path.expanduser("~"), ".grever-workspaces")

def _get_workspace_dir(goal_id: str) -> str:
    """Get the workspace directory for a given goal."""
    return os.path.join(WORKSPACE_ROOT, goal_id)

def _ensure_workspace_root():
    """Ensure the workspace root directory exists."""
    os.makedirs(WORKSPACE_ROOT, exist_ok=True)

def _friendly_error(raw_error: str) -> str:
    """Convert raw git error to user-friendly message."""
    if "Authentication failed" in raw_error or "auth '401'" in raw_error.lower():
        return "Git 认证失败，请检查 token 或 SSH key"
    elif "repository not found" in raw_error.lower() or "not found" in raw_error.lower():
        return "仓库不存在，请检查 URL"
    elif "timeout" in raw_error.lower() or "timed out" in raw_error.lower():
        return "网络超时，请检查网络连接后重试"
    elif "CONFLICT" in raw_error.upper() or "conflict" in raw_error.lower():
        return "本地有未提交的修改，请先 commit 或 stash"
    elif "refusing to merge unrelated histories" in raw_error.lower():
        return "远程仓库与本地仓库历史不相关，无法合并"
    elif "already exists and is not an empty directory" in raw_error.lower():
        return "本地目录已存在且非空，请先清理或选择其他路径"
    elif "Permission denied" in raw_error:
        return "权限不足，请检查目录权限"
    elif "could not read Username" in raw_error or "could not read Password" in raw_error:
        return "Git 凭据配置有问题，请检查用户名密码或 token 设置"
    else:
        return raw_error.strip()

def clone_workspace(git_url: str, goal_id: str) -> Dict[str, Any]:
    """
    Clone a Git repository to the local workspace directory.
    
    Args:
        git_url: URL of the Git repository to clone
        goal_id: ID of the goal to associate with this workspace
        
    Returns:
        Dictionary with success status, message, and error info
    """
    try:
        _ensure_workspace_root()
        workspace_dir = _get_workspace_dir(goal_id)
        
        # Check if directory already exists
        if os.path.exists(workspace_dir):
            if os.listdir(workspace_dir):  # Directory is not empty
                return {
                    "success": False,
                    "message": "本地目录已存在且非空",
                    "error": "Local directory already exists and is not empty"
                }
            else:  # Directory is empty, safe to remove
                shutil.rmtree(workspace_dir)
        
        # Perform git clone
        result = subprocess.run(
            ["git", "clone", git_url, workspace_dir],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"成功克隆仓库到 {workspace_dir}",
                "error": None
            }
        else:
            error_message = _friendly_error(result.stderr)
            return {
                "success": False,
                "message": "克隆仓库失败",
                "error": error_message
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "克隆操作超时",
            "error": "Git clone operation timed out after 30 seconds"
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": "Git 未安装或不可用",
            "error": "Git command not found. Please install Git and ensure it's in PATH."
        }
    except Exception as e:
        error_message = _friendly_error(str(e))
        return {
            "success": False,
            "message": f"克隆过程中发生未知错误: {str(e)}",
            "error": error_message
        }

def pull_workspace(goal_id: str) -> Dict[str, Any]:
    """
    Pull latest changes from the Git repository.
    
    Args:
        goal_id: ID of the goal whose workspace to pull
        
    Returns:
        Dictionary with success status, message, and error info
    """
    try:
        workspace_dir = _get_workspace_dir(goal_id)
        
        # Check if workspace exists
        if not os.path.exists(workspace_dir):
            return {
                "success": False,
                "message": "本地工作目录不存在，需要先克隆",
                "error": "Workspace directory does not exist, please clone first"
            }
        
        # Check if it's a git repository
        git_dir = os.path.join(workspace_dir, ".git")
        if not os.path.exists(git_dir):
            return {
                "success": False,
                "message": "本地目录不是 Git 仓库",
                "error": "Directory is not a Git repository"
            }
        
        # Perform git pull
        result = subprocess.run(
            ["git", "-C", workspace_dir, "pull"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": "成功拉取最新更改",
                "error": None
            }
        else:
            error_message = _friendly_error(result.stderr)
            return {
                "success": False,
                "message": "拉取失败",
                "error": error_message
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "拉取操作超时",
            "error": "Git pull operation timed out after 30 seconds"
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": "Git 未安装或不可用",
            "error": "Git command not found. Please install Git and ensure it's in PATH."
        }
    except Exception as e:
        error_message = _friendly_error(str(e))
        return {
            "success": False,
            "message": f"拉取过程中发生未知错误: {str(e)}",
            "error": error_message
        }

def push_workspace(goal_id: str, commit_msg: str = "Auto-commit from Grever") -> Dict[str, Any]:
    """
    Add, commit, and push changes to the Git repository.
    
    Args:
        goal_id: ID of the goal whose workspace to push
        commit_msg: Commit message to use
        
    Returns:
        Dictionary with success status, message, and error info
    """
    try:
        workspace_dir = _get_workspace_dir(goal_id)
        
        # Check if workspace exists
        if not os.path.exists(workspace_dir):
            return {
                "success": False,
                "message": "本地工作目录不存在，需要先克隆",
                "error": "Workspace directory does not exist, please clone first"
            }
        
        # Check if it's a git repository
        git_dir = os.path.join(workspace_dir, ".git")
        if not os.path.exists(git_dir):
            return {
                "success": False,
                "message": "本地目录不是 Git 仓库",
                "error": "Directory is not a Git repository"
            }
        
        # Add all changes
        add_result = subprocess.run(
            ["git", "-C", workspace_dir, "add", "."],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if add_result.returncode != 0:
            error_message = _friendly_error(add_result.stderr)
            return {
                "success": False,
                "message": "添加更改失败",
                "error": error_message
            }
        
        # Check if there are changes to commit
        status_result = subprocess.run(
            ["git", "-C", workspace_dir, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if not status_result.stdout.strip():
            return {
                "success": True,
                "message": "没有更改需要提交",
                "error": None
            }
        
        # Commit changes
        commit_result = subprocess.run(
            ["git", "-C", workspace_dir, "commit", "-m", commit_msg],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # If commit returns non-zero but it's because there's nothing to commit, that's OK
        if commit_result.returncode != 0:
            if "nothing to commit" in commit_result.stdout.lower() or \
               "nothing added to commit" in commit_result.stderr.lower():
                return {
                    "success": True,
                    "message": "没有更改需要提交",
                    "error": None
                }
            else:
                error_message = _friendly_error(commit_result.stderr)
                return {
                    "success": False,
                    "message": "提交更改失败",
                    "error": error_message
                }
        
        # Push changes
        push_result = subprocess.run(
            ["git", "-C", workspace_dir, "push"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if push_result.returncode == 0:
            return {
                "success": True,
                "message": "成功推送更改",
                "error": None
            }
        else:
            error_message = _friendly_error(push_result.stderr)
            return {
                "success": False,
                "message": "推送失败",
                "error": error_message
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "推送操作超时",
            "error": "Git push operation timed out after 30 seconds"
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": "Git 未安装或不可用",
            "error": "Git command not found. Please install Git and ensure it's in PATH."
        }
    except Exception as e:
        error_message = _friendly_error(str(e))
        return {
            "success": False,
            "message": f"推送过程中发生未知错误: {str(e)}",
            "error": error_message
        }

def get_workspace_status(goal_id: str) -> Dict[str, Any]:
    """
    Get the status of the workspace including whether it's cloned, 
    current branch, and last commit hash.
    
    Args:
        goal_id: ID of the goal whose workspace status to check
        
    Returns:
        Dictionary with cloned status, branch, last commit, and directory info
    """
    try:
        workspace_dir = _get_workspace_dir(goal_id)
        
        # Check if workspace exists and is a git repository
        cloned = os.path.exists(workspace_dir) and os.path.exists(os.path.join(workspace_dir, ".git"))
        
        if not cloned:
            return {
                "cloned": False,
                "branch": None,
                "last_commit": None,
                "dir": workspace_dir
            }
        
        # Get current branch
        branch_result = subprocess.run(
            ["git", "-C", workspace_dir, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
        
        # Get last commit hash
        commit_result = subprocess.run(
            ["git", "-C", workspace_dir, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        last_commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown"
        
        return {
            "cloned": True,
            "branch": branch,
            "last_commit": last_commit,
            "dir": workspace_dir
        }
        
    except Exception as e:
        logger.error(f"Error getting workspace status for goal {goal_id}: {str(e)}")
        return {
            "cloned": False,
            "branch": None,
            "last_commit": None,
            "dir": _get_workspace_dir(goal_id)
        }