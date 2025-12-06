"""
Result Synthesis Module
Generates natural language summaries of analysis results.
"""

from src.code_generator import CodeGenerator
from typing import Optional


class ResultSynthesizer:
    """Synthesizes analysis results into natural language summaries."""
    
    def __init__(self, code_generator: Optional[CodeGenerator] = None):
        """
        Initialize the result synthesizer.
        
        Args:
            code_generator: CodeGenerator instance to use for summary generation
        """
        self.code_generator = code_generator or CodeGenerator()
    
    def synthesize_results(self, user_query: str, execution_output: str,
                          visualization_exists: bool = True) -> str:
        """
        Generate a natural language summary of the analysis results.
        
        Args:
            user_query: Original user query
            execution_output: Output from code execution
            visualization_exists: Whether a visualization was generated
            
        Returns:
            Natural language summary
        """
        return self.code_generator.generate_summary_code(
            user_query=user_query,
            execution_output=execution_output,
            visualization_exists=visualization_exists
        )


