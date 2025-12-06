"""
AutoInsight - Main Streamlit Application
A conversational AI agent for automated data analysis and visualization.
"""

import streamlit as st
import os
import shutil
from pathlib import Path
from src.orchestrator import AutoInsightOrchestrator
from src.data_profiler import DataProfiler

# Page configuration
st.set_page_config(
    page_title="AutoInsight",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None
if "data_file" not in st.session_state:
    st.session_state.data_file = None
if "data_profile" not in st.session_state:
    st.session_state.data_profile = None
if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []
if "temp_dirs" not in st.session_state:
    st.session_state.temp_dirs = []


def initialize_orchestrator():
    """Initialize the orchestrator if not already done."""
    if st.session_state.orchestrator is None:
        try:
            st.session_state.orchestrator = AutoInsightOrchestrator()
        except Exception as e:
            st.error(f"Failed to initialize AutoInsight: {str(e)}")
            st.info("Please ensure:")
            st.info("1. The .env file contains a valid GOOGLE_API_KEY or OPENAI_API_KEY")
            st.info("2. Installed dependencies with `pip install -r requirements.txt`")
            st.stop()


def cleanup_old_temp_dirs():
    """Clean up old temporary directories."""
    for temp_dir in st.session_state.temp_dirs[:]:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                st.session_state.temp_dirs.remove(temp_dir)
            except Exception:
                pass


def main():
    """Main application function."""
    st.title("📊 AutoInsight")
    st.markdown("### Conversational AI Agent for Automated Data Analysis and Visualization")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Data Upload")
        uploaded_file = st.file_uploader(
            "Upload a CSV file",
            type=["csv"],
            help="Upload your dataset to begin analysis"
        )
        
        if uploaded_file is not None:
            # Save uploaded file
            if st.session_state.data_file != uploaded_file.name:
                # New file uploaded
                uploads_dir = Path("uploads")
                uploads_dir.mkdir(exist_ok=True)
                
                file_path = uploads_dir / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                st.session_state.data_file = str(file_path)
                st.session_state.data_profile = None
                st.session_state.analysis_history = []
                
                # Clean up old temp dirs
                cleanup_old_temp_dirs()
                
                st.success(f"✅ File uploaded: {uploaded_file.name}")
        
        st.markdown("---")
        st.header("ℹ️ About")
        st.markdown("""
        **AutoInsight** enables you to:
        - Ask questions in natural language
        - Get automatic data analysis
        - View generated visualizations
        - Read AI-generated insights
        
        **Example Queries:**
        - "What is the distribution of ages?"
        - "Show correlation between price and sales"
        - "Create a bar chart of sales by region"
        - "What are the top 10 products by revenue?"
        """)
        
        st.markdown("---")
        if st.button("🗑️ Clear History"):
            st.session_state.analysis_history = []
            cleanup_old_temp_dirs()
            st.rerun()
    
    # Main content area
    if st.session_state.data_file is None:
        st.info("👈 Please upload a CSV file to begin analysis")
        st.markdown("""
        ### Getting Started
        
        1. **Upload Data**: Use the sidebar to upload a CSV file
        2. **Ask Questions**: Type your analysis questions in natural language
        3. **View Results**: See visualizations and AI-generated insights
        
        ### Example Datasets
        You can use any CSV file. Popular options include:
        - Sales data
        - Customer demographics
        - Product catalogs
        - Survey responses
        - Time series data
        """)
        return
    
    # Initialize orchestrator
    initialize_orchestrator()
    
    # Display data profile
    if st.session_state.data_profile is None:
        with st.spinner("Analyzing dataset..."):
            try:
                profiler = DataProfiler()
                st.session_state.data_profile = profiler.profile_data(st.session_state.data_file)
            except Exception as e:
                st.error(f"Error profiling data: {str(e)}")
                return
    
    # Show data profile
    with st.expander("📋 Dataset Profile", expanded=False):
        profiler = DataProfiler()
        profiler.profile = st.session_state.data_profile
        st.text(profiler.get_profile_summary())
    
    # Query input
    st.markdown("### 💬 Ask a Question")
    user_query = st.text_input(
        "Enter your analysis question:",
        placeholder="e.g., What is the distribution of ages in the dataset?",
        key="query_input"
    )
    
    col1, col2 = st.columns([1, 10])
    with col1:
        analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)
    
    # Process query
    if analyze_button and user_query:
        with st.spinner("🤖 Generating analysis..."):
            try:
                result = st.session_state.orchestrator.analyze(
                    user_query=user_query,
                    data_file_path=st.session_state.data_file
                )
                
                # Store temp dir for cleanup
                if result.get("visualization_path"):
                    temp_dir = os.path.dirname(result["visualization_path"])
                    if temp_dir not in st.session_state.temp_dirs:
                        st.session_state.temp_dirs.append(temp_dir)
                
                # Add to history
                st.session_state.analysis_history.insert(0, {
                    "query": user_query,
                    "result": result
                })
                
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                st.info("Please check the error message above and ensure all dependencies are installed.")
    
    # Display analysis history
    if st.session_state.analysis_history:
        st.markdown("---")
        st.markdown("### 📊 Analysis Results")
        
        for idx, item in enumerate(st.session_state.analysis_history):
            with st.container():
                st.markdown(f"#### Query {idx + 1}: {item['query']}")
                
                result = item["result"]
                
                if result["success"]:
                    # Display visualization
                    if result["visualization_path"] and os.path.exists(result["visualization_path"]):
                        st.image(result["visualization_path"])
                    
                    # Display summary
                    st.markdown("**📝 Summary:**")
                    st.markdown(result["summary"])
                    
                    # Show code (collapsible)
                    with st.expander("🔧 Generated Code"):
                        st.code(result["code"], language="python")
                    
                    # Show execution output (collapsible)
                    if result["stdout"]:
                        with st.expander("📤 Execution Output"):
                            st.text(result["stdout"])
                
                else:
                    st.error("❌ Analysis failed")
                    st.error(result.get("error", "Unknown error"))
                    if result["stderr"]:
                        st.code(result["stderr"], language="text")
                    if result["code"]:
                        with st.expander("🔧 Generated Code (with errors)"):
                            st.code(result["code"], language="python")
                
                st.markdown("---")
    
    # Cleanup on app close (this runs when the app reruns)
    if st.session_state.temp_dirs:
        # Keep only the most recent 5 temp dirs
        for temp_dir in st.session_state.temp_dirs[5:]:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    st.session_state.temp_dirs.remove(temp_dir)
                except Exception:
                    pass


if __name__ == "__main__":
    main()

