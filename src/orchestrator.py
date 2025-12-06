"""
Orchestration Module
Coordinates the entire data analysis pipeline from query to results.
"""

import os
from typing import Dict, Any, Optional, Tuple
from src.data_profiler import DataProfiler
from src.code_generator import CodeGenerator
from src.executor import CodeExecutor
from src.synthesizer import ResultSynthesizer


class AutoInsightOrchestrator:
    """Orchestrates the complete data analysis pipeline."""
    
    def __init__(self):
        """Initialize all components."""
        self.profiler = DataProfiler()
        self.code_generator = CodeGenerator()
        self.executor = CodeExecutor()
        self.synthesizer = ResultSynthesizer(self.code_generator)
    
    def analyze(self, user_query: str, data_file_path: str) -> Dict[str, Any]:
        """
        Execute the complete analysis pipeline.
        
        Args:
            user_query: Natural language query from user
            data_file_path: Path to the CSV data file
            
        Returns:
            Dictionary containing:
                - success: bool
                - code: str (generated code)
                - stdout: str
                - stderr: str
                - summary: str (natural language summary)
                - visualization_path: str (path to generated visualization)
                - error: str (error message if failed)
        """
        result = {
            "success": False,
            "code": "",
            "stdout": "",
            "stderr": "",
            "summary": "",
            "visualization_path": None,
            "error": None
        }
        
        temp_dir = None
        
        try:
            # Step 1: Data Profiling
            profile = self.profiler.profile_data(data_file_path)
            profile_str = self.profiler.get_profile_for_prompt()
            
            # Step 2: Code Generation
            data_filename = os.path.basename(data_file_path)
            generated_code = self.code_generator.generate_code(
                user_query=user_query,
                data_profile=profile_str,
                file_path=data_filename  # Relative path in container
            )
            result["code"] = generated_code
            
            # Step 3: Code Execution
            stdout, stderr, success, temp_dir = self.executor.execute_code(
                code=generated_code,
                data_file_path=data_file_path
            )
            
            result["stdout"] = stdout
            result["stderr"] = stderr
            result["success"] = success
            
            if not success:
                result["error"] = f"Code execution failed: {stderr}"
                return result
            
            # Step 4: Check for visualization
            if temp_dir:
                viz_path = os.path.join(temp_dir, "final_visualization.png")
                if os.path.exists(viz_path):
                    result["visualization_path"] = viz_path
            
            # Step 5: Result Synthesis
            visualization_exists = result["visualization_path"] is not None
            summary = self.synthesizer.synthesize_results(
                user_query=user_query,
                execution_output=stdout,
                visualization_exists=visualization_exists
            )
            result["summary"] = summary
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            return result
        
        finally:
            # We don't cleanup temp_dir here immediately because
            # the visualization might need to be accessed by the UI.
            # Cleanup should be handled by the calling code after visualization is copied.
            pass
    
    def get_data_profile(self, data_file_path: str) -> Dict[str, Any]:
        """
        Get profile of a data file.
        
        Args:
            data_file_path: Path to the CSV file
            
        Returns:
            Profile dictionary
        """
        return self.profiler.profile_data(data_file_path)
    
    def cleanup_temp_files(self, temp_dir: str):
        """Clean up temporary files."""
        if temp_dir:
            self.executor.cleanup(temp_dir)


