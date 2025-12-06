# Quick Start Guide

## Prerequisites

Before you begin, ensure you have:
- **Python 3.9+** installed
- A **Google Gemini API key** (or OpenAI API key)

## Installation Steps

### Option 1: Using the Setup Script (Recommended)

```bash
# Make the setup script executable (if not already)
chmod +x setup.sh

# Run the setup script
./setup.sh
```

### Option 2: Manual Setup

1. **Create a virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Verify installation**:
```bash
# Test that everything is installed correctly
python -c "import pandas, matplotlib, seaborn; print('✅ All dependencies installed')"
```

4. **Configure environment variables**:
```bash
# Create .env file with your Gemini API key
cat > .env << EOF
GOOGLE_API_KEY=your_gemini_api_key_here
LLM_MODEL=gemini-pro
EOF

# Or manually create .env file and add:
# GOOGLE_API_KEY=your_api_key_here
# LLM_MODEL=gemini-pro
```

## Running the Application

1. **Activate your virtual environment** (if not already active):
```bash
source venv/bin/activate
```

2. **Start the Streamlit app**:
```bash
streamlit run app.py
```

3. **Open your browser** to the URL shown (typically `http://localhost:8501`)

## Using AutoInsight

### Step 1: Upload Data
- Click "Browse files" in the sidebar
- Select a CSV file
- Wait for the data profile to be generated

### Step 2: Ask Questions
Type your question in natural language, for example:
- "What is the distribution of ages?"
- "Show me a correlation heatmap"
- "Create a bar chart of sales by region"
- "What are the top 10 products by revenue?"

### Step 3: View Results
- See the generated visualization
- Read the AI-generated summary
- Review the generated code (optional)

## Example Workflow

1. **Upload a dataset** (e.g., `titanic.csv`)
2. **Ask**: "What is the age distribution of passengers?"
3. **View**: 
   - Histogram showing age distribution
   - Summary explaining the findings
   - Generated Python code

## Troubleshooting

### Code Execution Issues
- **Error**: "Module not found"
  - **Solution**: Ensure virtual environment is activated and dependencies are installed: `pip install -r requirements.txt`

- **Error**: "Permission denied" or execution errors
  - **Solution**: Check file permissions and ensure Python has write access to temp directories

### API Key Issues
- **Error**: "No API key found"
  - **Solution**: Create a `.env` file with your API key:
    ```
    GOOGLE_API_KEY=your_gemini_api_key_here
    LLM_MODEL=gemini-pro
    ```
    Or for OpenAI:
    ```
    OPENAI_API_KEY=your_openai_key_here
    LLM_MODEL=gpt-4
    ```

### Import Errors
- **Error**: "Module not found"
  - **Solution**: Ensure virtual environment is activated and dependencies are installed:
    ```bash
    pip install -r requirements.txt
    ```

### Code Execution Errors
- **Error**: "Code execution failed"
  - Check the error message in the stderr output
  - Verify the data file is valid CSV
  - Ensure column names in queries match the dataset

## Getting Help

If you encounter issues:
1. Check the error messages in the application
2. Check the error output in the application interface
3. Verify all prerequisites are installed correctly
4. Ensure your API key is valid and has sufficient credits

