"""
Data Profiling Module
Analyzes CSV files and generates comprehensive profiles including column names,
data types, basic statistics, and sample data.
"""

import pandas as pd
import json
from typing import Dict, Any, Optional


class DataProfiler:
    """Profiles CSV data files and generates structured summaries."""
    
    def __init__(self):
        self.profile = None
    
    def profile_data(self, file_path: str, sample_rows: int = 5) -> Dict[str, Any]:
        """
        Generate a comprehensive profile of the CSV file.
        
        Args:
            file_path: Path to the CSV file
            sample_rows: Number of sample rows to include
            
        Returns:
            Dictionary containing profile information
        """
        try:
            # Try reading with UTF-8 first, fallback to other encodings if needed
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16', 'windows-1252']
            df = None
            encoding_used = None
            last_error = None
            
            for encoding in encodings:
                try:
                    # Try with default engine first
                    df = pd.read_csv(
                        file_path, 
                        encoding=encoding,
                        on_bad_lines='skip'  # Skip problematic lines
                    )
                    encoding_used = encoding
                    break
                except (UnicodeDecodeError, UnicodeError) as e:
                    last_error = e
                    continue
                except Exception as e:
                    # Try with Python engine as fallback
                    try:
                        df = pd.read_csv(
                            file_path, 
                            encoding=encoding,
                            engine='python',
                            error_bad_lines=False,  # Old pandas parameter
                            warn_bad_lines=False
                        )
                        encoding_used = encoding
                        break
                    except Exception:
                        # Try with errors='ignore' to skip problematic bytes
                        try:
                            with open(file_path, 'rb') as f:
                                content = f.read()
                            content_clean = content.decode(encoding, errors='ignore').encode('utf-8')
                            import io
                            df = pd.read_csv(io.StringIO(content_clean.decode('utf-8')))
                            encoding_used = f"{encoding} (with errors ignored)"
                            break
                        except Exception:
                            last_error = e
                            continue
            
            if df is None:
                # Last resort: try with errors='ignore' to skip problematic bytes
                try:
                    # Read file as binary, decode with error handling, then parse
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    # Try to decode with errors='ignore' and re-encode
                    content_str = content.decode('utf-8', errors='ignore')
                    import io
                    df = pd.read_csv(io.StringIO(content_str), on_bad_lines='skip')
                    encoding_used = 'utf-8 (with errors ignored)'
                except Exception as final_error:
                    raise Exception(f"Could not read CSV file with any supported encoding. Last error: {str(last_error)}. Final attempt error: {str(final_error)}")
            
            profile = {
                "file_path": file_path,
                "shape": {
                    "rows": len(df),
                    "columns": len(df.columns)
                },
                "columns": [],
                "sample_data": df.head(sample_rows).to_dict(orient='records'),
                "missing_values": df.isnull().sum().to_dict(),
                "memory_usage": df.memory_usage(deep=True).sum()
            }
            
            # Detailed column information
            for col in df.columns:
                col_info = {
                    "name": col,
                    "dtype": str(df[col].dtype),
                    "null_count": df[col].isnull().sum(),
                    "null_percentage": (df[col].isnull().sum() / len(df)) * 100
                }
                
                # Add statistics based on data type
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_info["statistics"] = {
                        "mean": float(df[col].mean()) if df[col].notna().any() else None,
                        "median": float(df[col].median()) if df[col].notna().any() else None,
                        "std": float(df[col].std()) if df[col].notna().any() else None,
                        "min": float(df[col].min()) if df[col].notna().any() else None,
                        "max": float(df[col].max()) if df[col].notna().any() else None,
                        "unique_count": int(df[col].nunique())
                    }
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    col_info["statistics"] = {
                        "min_date": str(df[col].min()) if df[col].notna().any() else None,
                        "max_date": str(df[col].max()) if df[col].notna().any() else None,
                        "unique_count": int(df[col].nunique())
                    }
                else:
                    # Categorical/string columns
                    col_info["statistics"] = {
                        "unique_count": int(df[col].nunique()),
                        "most_frequent": df[col].mode().tolist()[:5] if len(df[col].mode()) > 0 else []
                    }
                
                profile["columns"].append(col_info)
            
            self.profile = profile
            return profile
            
        except Exception as e:
            raise Exception(f"Error profiling data: {str(e)}")
    
    def get_profile_summary(self) -> str:
        """
        Generate a human-readable summary of the profile.
        
        Returns:
            String summary of the data profile
        """
        if not self.profile:
            return "No profile available. Please profile data first."
        
        summary = f"Dataset Overview:\n"
        summary += f"- Rows: {self.profile['shape']['rows']:,}\n"
        summary += f"- Columns: {self.profile['shape']['columns']}\n"
        summary += f"- Memory Usage: {self.profile['memory_usage'] / 1024 / 1024:.2f} MB\n\n"
        
        summary += "Columns:\n"
        for col in self.profile['columns']:
            summary += f"\n{col['name']} ({col['dtype']}):\n"
            summary += f"  - Null values: {col['null_count']} ({col['null_percentage']:.1f}%)\n"
            
            if 'statistics' in col:
                stats = col['statistics']
                if 'mean' in stats and stats['mean'] is not None:
                    summary += f"  - Mean: {stats['mean']:.2f}\n"
                    summary += f"  - Min: {stats['min']:.2f}, Max: {stats['max']:.2f}\n"
                elif 'unique_count' in stats:
                    summary += f"  - Unique values: {stats['unique_count']}\n"
        
        return summary
    
    def get_profile_for_prompt(self) -> str:
        """
        Generate a formatted profile string optimized for LLM prompts.
        
        Returns:
            Formatted string for prompt engineering
        """
        if not self.profile:
            return "No profile available."
        
        prompt = "DATASET PROFILE:\n"
        prompt += f"Shape: {self.profile['shape']['rows']} rows × {self.profile['shape']['columns']} columns\n\n"
        
        prompt += "COLUMNS:\n"
        for col in self.profile['columns']:
            prompt += f"- {col['name']}: {col['dtype']}"
            if col['null_count'] > 0:
                prompt += f" ({col['null_count']} null values)"
            prompt += "\n"
            
            # Add key statistics
            if 'statistics' in col:
                stats = col['statistics']
                if 'mean' in stats and stats['mean'] is not None:
                    prompt += f"  Statistics: mean={stats['mean']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}, unique={stats['unique_count']}\n"
                elif 'unique_count' in stats:
                    prompt += f"  Unique values: {stats['unique_count']}\n"
        
        prompt += f"\nSAMPLE DATA (first {len(self.profile['sample_data'])} rows):\n"
        for i, row in enumerate(self.profile['sample_data'][:3], 1):
            prompt += f"Row {i}: {row}\n"
        
        return prompt


