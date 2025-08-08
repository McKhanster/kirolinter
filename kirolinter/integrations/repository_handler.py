"""
Repository handler for Git operations.
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional


class RepositoryHandler:
    """Handle Git repository operations."""
    
    def __init__(self):
        self.temp_dirs: List[str] = []
    
    def clone_repository(self, repo_url: str, depth: int = 1) -> str:
        """
        Clone a Git repository to a temporary directory.
        
        Args:
            repo_url: Git repository URL
            depth: Clone depth (default: 1 for shallow clone)
        
        Returns:
            Path to the cloned repository
        """
        temp_dir = tempfile.mkdtemp(prefix='kirolinter_repo_')
        self.temp_dirs.append(temp_dir)
        
        try:
            cmd = ['git', 'clone']
            if depth > 0:
                cmd.extend(['--depth', str(depth)])
            cmd.extend([repo_url, temp_dir])
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Git clone failed: {result.stderr}")
            
            return temp_dir
            
        except subprocess.TimeoutExpired:
            self.cleanup_temp_dir(temp_dir)
            raise RuntimeError("Repository clone timed out after 5 minutes")
        except Exception as e:
            self.cleanup_temp_dir(temp_dir)
            raise RuntimeError(f"Failed to clone repository: {str(e)}")
    
    def get_changed_files(self, repo_path: str, commit_range: str = "HEAD~1..HEAD") -> List[str]:
        """
        Get list of files changed in a commit range.
        
        Args:
            repo_path: Path to the Git repository
            commit_range: Git commit range (default: last commit)
        
        Returns:
            List of changed file paths
        """
        try:
            result = subprocess.run([
                'git', 'diff', '--name-only', commit_range
            ], cwd=repo_path, capture_output=True, text=True)
            
            if result.returncode != 0:
                return []
            
            return [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
        except Exception:
            return []
    
    def is_git_repository(self, path: str) -> bool:
        """Check if a directory is a Git repository."""
        try:
            result = subprocess.run([
                'git', 'rev-parse', '--git-dir'
            ], cwd=path, capture_output=True, text=True)
            
            return result.returncode == 0
            
        except Exception:
            return False
    
    def get_repository_info(self, repo_path: str) -> dict:
        """Get basic repository information."""
        info = {
            'is_git_repo': False,
            'current_branch': None,
            'last_commit': None,
            'remote_url': None
        }
        
        if not self.is_git_repository(repo_path):
            return info
        
        info['is_git_repo'] = True
        
        try:
            # Get current branch
            result = subprocess.run([
                'git', 'rev-parse', '--abbrev-ref', 'HEAD'
            ], cwd=repo_path, capture_output=True, text=True)
            if result.returncode == 0:
                info['current_branch'] = result.stdout.strip()
            
            # Get last commit
            result = subprocess.run([
                'git', 'log', '-1', '--format=%H %s'
            ], cwd=repo_path, capture_output=True, text=True)
            if result.returncode == 0:
                info['last_commit'] = result.stdout.strip()
            
            # Get remote URL
            result = subprocess.run([
                'git', 'remote', 'get-url', 'origin'
            ], cwd=repo_path, capture_output=True, text=True)
            if result.returncode == 0:
                info['remote_url'] = result.stdout.strip()
                
        except Exception:
            pass
        
        return info
    
    def cleanup_temp_dir(self, temp_dir: str):
        """Clean up a temporary directory."""
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            if temp_dir in self.temp_dirs:
                self.temp_dirs.remove(temp_dir)
        except Exception:
            pass
    
    def cleanup_all(self):
        """Clean up all temporary directories."""
        for temp_dir in self.temp_dirs[:]:
            self.cleanup_temp_dir(temp_dir)
    
    def __del__(self):
        """Cleanup on destruction."""
        self.cleanup_all()