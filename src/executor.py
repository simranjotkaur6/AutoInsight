"""
Code Execution Module
Executes generated Python code locally in a temporary directory (no Docker).

NOTE: This is less secure than containerized execution. Do not run untrusted
code or data when using this executor.
"""

import os
import tempfile
import shutil
import subprocess
import sys
from typing import Tuple


class CodeExecutor:
    """Executes Python code in an isolated temporary directory (local process)."""

    def __init__(self):
        """Initialize the code executor (no Docker needed)."""
        pass

    def execute_code(self, code: str, data_file_path: str,
                     timeout: int = 60) -> Tuple[str, str, bool, str]:
        """
        Execute Python code locally.

        Args:
            code: Python code to execute
            data_file_path: Path to the data file
            timeout: Maximum execution time in seconds

        Returns:
            Tuple of (stdout, stderr, success_flag, temp_dir)
        """
        # Create temporary directory for this execution
        temp_dir = tempfile.mkdtemp(prefix="autoinsight_")

        try:
            # Copy data file to temp directory
            data_filename = os.path.basename(data_file_path)
            temp_data_path = os.path.join(temp_dir, data_filename)
            shutil.copy2(data_file_path, temp_data_path)

            # Create outputs directory
            outputs_dir = os.path.join(temp_dir, "outputs")
            os.makedirs(outputs_dir, exist_ok=True)

            # Write code to file
            code_file = os.path.join(temp_dir, "analysis.py")
            with open(code_file, "w", encoding="utf-8") as f:
                f.write(code)

            # Run the code using the current Python interpreter
            try:
                completed = subprocess.run(
                    [sys.executable, code_file],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                stdout = completed.stdout
                stderr = completed.stderr
                success = completed.returncode == 0

                # If visualization exists, copy it to a predictable name
                viz_path = os.path.join(outputs_dir, "visualization.png")
                if os.path.exists(viz_path):
                    final_viz_path = os.path.join(temp_dir, "final_visualization.png")
                    shutil.copy2(viz_path, final_viz_path)

                return stdout, stderr, success, temp_dir

            except subprocess.TimeoutExpired as e:
                return "", f"Execution timeout: {str(e)}", False, temp_dir
            except Exception as e:
                return "", f"Local execution error: {str(e)}", False, temp_dir

        except Exception as e:
            # Cleanup on error
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise Exception(f"Error setting up execution environment: {str(e)}")

    def cleanup(self, temp_dir: str):
        """Clean up temporary directory."""
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

