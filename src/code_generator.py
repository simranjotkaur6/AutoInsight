"""
Code Generation Module
Uses LLM to generate Python code for data analysis based on natural language queries.
Supports both OpenAI and Google Gemini models.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Conditional import for LangChain (only needed for fallback)
try:
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Create simple message classes for direct API use
    class SystemMessage:
        def __init__(self, content):
            self.content = content
    class HumanMessage:
        def __init__(self, content):
            self.content = content

load_dotenv()


class CodeGenerator:
    """Generates Python code for data analysis using LLM."""
    
    def __init__(self, model_name: Optional[str] = None, temperature: float = 0.1):
        """
        Initialize the code generator.
        
        Args:
            model_name: Name of the LLM model to use (defaults to env variable)
            temperature: Temperature for code generation (lower = more deterministic)
        """
        self.model_name = model_name or os.getenv("LLM_MODEL", "gemini-2.5-flash")
        self.temperature = temperature
        
        gemini_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if gemini_api_key:
            try:
                # Use direct google-generativeai
                import google.generativeai as genai
                genai.configure(api_key=gemini_api_key)
                model_name = self.model_name if "gemini" in self.model_name.lower() else "gemini-2.5-flash"
                self.genai_model = genai.GenerativeModel(model_name)
                self.provider = "gemini-direct"
            except ImportError:
                raise ImportError("Please install google-generativeai: pip install google-generativeai")
            except Exception as e:
                # Fallback to LangChain if direct method fails
                try:
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    model_name = self.model_name if "gemini" in self.model_name.lower() else "gemini-2.5-flash"
                    self.llm = ChatGoogleGenerativeAI(
                        model=model_name,
                        temperature=self.temperature,
                        google_api_key=gemini_api_key,
                        convert_system_message_to_human=True
                    )
                    self.provider = "gemini"
                except Exception as e2:
                    raise Exception(f"Failed to initialize Gemini: Direct method error: {str(e)}, LangChain error: {str(e2)}")
        elif openai_api_key:
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    api_key=openai_api_key
                )
                self.provider = "openai"
            except ImportError:
                raise ImportError("Please install langchain-openai: pip install langchain-openai")
        else:
            raise ValueError("No API key found. Please set GOOGLE_API_KEY or OPENAI_API_KEY in environment variables")
    
    def generate_code(self, user_query: str, data_profile: str, file_path: str) -> str:
        """
        Generate Python code to answer the user's query.
        
        Args:
            user_query: Natural language query from the user
            data_profile: Formatted data profile string
            file_path: Path to the data file (relative to execution context)
            
        Returns:
            Generated Python code as a string
        """
        system_prompt = """You are an expert data analyst and Python programmer. Your task is to generate Python code that answers a user's data analysis question.

REQUIREMENTS:
1. Load the CSV file using pandas with encoding handling:
   - Try: df = pd.read_csv('{file_path}', encoding='utf-8', on_bad_lines='skip')
   - If that fails, try: df = pd.read_csv('{file_path}', encoding='latin-1', on_bad_lines='skip')
   - Or use: df = pd.read_csv('{file_path}', encoding='utf-8', errors='ignore', on_bad_lines='skip')
2. Perform the analysis requested by the user
3. Create appropriate visualizations using matplotlib or seaborn
4. Save the visualization to 'outputs/visualization.png' (relative to the script directory)
5. Print key findings to stdout (these will be used for summary generation)
6. Use clear, readable code with comments
7. Handle missing values appropriately
8. Use appropriate chart types (bar, line, scatter, histogram, etc.) based on the data

IMPORTANT:
- Always import necessary libraries at the top
- Assume the script is run locally with pandas, matplotlib, seaborn, numpy installed
- Handle CSV encoding issues by using encoding parameters or error handling
- Save plots with: plt.savefig('outputs/visualization.png', dpi=150, bbox_inches='tight')
- Always call plt.close() after saving to free memory
- Print results using print() statements - these will be captured for summary generation
- For seaborn: When using palette, always assign it to 'hue' parameter or use 'color' instead
- For pandas Series: Use .to_string() without formatters, or convert to DataFrame first if formatting needed
- For printing Series with formatting: Use print(series) or convert to DataFrame: print(series.to_frame().to_string())
- Avoid deprecated pandas/seaborn parameters that cause warnings or errors

DATA PROFILE:
{data_profile}

Generate ONLY the Python code, no explanations or markdown formatting."""

        user_prompt = f"""User Query: {user_query}

Generate Python code that:
1. Loads the data from '{file_path}'
2. Performs the requested analysis
3. Creates a visualization and saves it to 'outputs/visualization.png'
4. Prints key findings and statistics

Code:"""

        messages = [
            SystemMessage(content=system_prompt.format(
                file_path=file_path,
                data_profile=data_profile
            )),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            if self.provider == "gemini-direct":
                # Use direct Google Generative AI
                prompt_text = f"{messages[0].content}\n\n{messages[1].content}"
                response = self.genai_model.generate_content(prompt_text)
                # Handle different response formats
                if hasattr(response, 'text'):
                    code = response.text.strip()
                elif hasattr(response, 'candidates') and response.candidates:
                    # Alternative response format
                    code = response.candidates[0].content.parts[0].text.strip()
                else:
                    code = str(response).strip()
            else:
                # Use LangChain
                response = self.llm.invoke(messages)
                code = response.content.strip()
            
            # Clean up code if it's wrapped in markdown code blocks
            if code.startswith("```python"):
                code = code[9:]
            elif code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
            
            return code.strip()
            
        except KeyError as e:
            raise Exception(f"Error generating code: Missing key '{e}' in response. Response structure may have changed.")
        except AttributeError as e:
            raise Exception(f"Error generating code: Attribute error - {str(e)}. Response may not have expected structure.")
        except Exception as e:
            raise Exception(f"Error generating code: {str(e)}")
    
    def generate_summary_code(self, user_query: str, execution_output: str, 
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
        system_prompt = """You are a data analyst who explains findings in clear, concise natural language. 
Your task is to summarize the results of a data analysis in a way that's easy to understand for non-technical users.

Focus on:
- Key findings and insights
- Important statistics or patterns
- What the visualization shows
- Actionable takeaways

Keep the summary concise (2-4 paragraphs) and avoid technical jargon."""

        user_prompt = f"""Original Question: {user_query}

Code Execution Output:
{execution_output}

Visualization Generated: {'Yes' if visualization_exists else 'No'}

Provide a clear, concise summary of the analysis results:"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            if self.provider == "gemini-direct":
                # Use direct Google Generative AI
                prompt_text = f"{messages[0].content}\n\n{messages[1].content}"
                response = self.genai_model.generate_content(prompt_text)
                # Handle different response formats
                if hasattr(response, 'text'):
                    return response.text.strip()
                elif hasattr(response, 'candidates') and response.candidates:
                    # Alternative response format
                    return response.candidates[0].content.parts[0].text.strip()
                else:
                    return str(response).strip()
            else:
                # Use LangChain
                response = self.llm.invoke(messages)
                return response.content.strip()
        except KeyError as e:
            raise Exception(f"Error generating summary: Missing key '{e}' in response. Response structure may have changed.")
        except AttributeError as e:
            raise Exception(f"Error generating summary: Attribute error - {str(e)}. Response may not have expected structure.")
        except Exception as e:
            raise Exception(f"Error generating summary: {str(e)}")

