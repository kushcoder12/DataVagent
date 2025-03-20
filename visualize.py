import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
import seaborn as sns
from io import BytesIO
import base64
import re
import requests
from typing import List, Dict, Any, Tuple

# Set style for matplotlib
plt.style.use('dark_background')

# LLM API interaction
def get_llm_response(prompt: str, api_key: str) -> Dict:
    """
    Get response from Groq API using the provided prompt and API key
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": """You are a data visualization expert and data analyst. 
            Your primary goals are:
            1. Answer questions about the data clearly and accurately
            2. Create precise, high-quality visualizations based on the data provided
            
            When responding:
            - First answer any questions about the data directly
            - Then recommend appropriate visualizations with explanations
            - Finally, provide Python code for creating these visualizations
            
            IMPORTANT: When working with dates in pandas, always use pd.to_datetime with parameters 
            format='mixed', dayfirst=True to handle various date formats.
            
            Use matplotlib, plotly, or altair - with a preference for interactive visualizations where appropriate.
            Focus on clarity, accuracy, and aesthetic appeal in dark mode.
            All visualizations should have proper titles, labels, and legends."""},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 4096
    }
    
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")

def extract_code_blocks(text: str) -> List[str]:
    """
    Extract code blocks from markdown text
    """
    pattern = r"```python(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return [match.strip() for match in matches]

def fix_date_parsing_in_code(code: str) -> str:
    """
    Modify code to handle date parsing more robustly
    """
    # Find pd.to_datetime calls and add format='mixed', dayfirst=True
    pattern = r"pd\.to_datetime\((.*?)\)"
    
    def replacement(match):
        content = match.group(1)
        if 'format' not in content and 'dayfirst' not in content:
            if content.strip().endswith(')'):
                # Handle nested parentheses
                return f"pd.to_datetime({content}, format='mixed', dayfirst=True)"
            else:
                return f"pd.to_datetime({content}, format='mixed', dayfirst=True)"
        return match.group(0)
    
    fixed_code = re.sub(pattern, replacement, code)
    
    # Also handle strptime calls
    strptime_pattern = r"datetime\.strptime\((.*?),\s*['\"]([^'\"]*?)['\"]\)"
    fixed_code = re.sub(strptime_pattern, r"pd.to_datetime(\1, format='mixed', dayfirst=True)", fixed_code)
    
    # Import datetime if needed
    if "import datetime" not in fixed_code and "from datetime import" in fixed_code:
        fixed_code = "import datetime\n" + fixed_code
    
    return fixed_code

def execute_code_block(code: str, dataframes: Dict[str, pd.DataFrame]) -> Any:
    """
    Execute a code block that might contain analysis or questions about the data
    """
    # Fix date parsing issues in the code
    modified_code = fix_date_parsing_in_code(code)
    
    # Create a modified version of the code with dataframes injected
    for df_name, df in dataframes.items():
        # Replace file loading with direct dataframe access
        modified_code = re.sub(
            rf"pd\.read_csv\(['\"].*{df_name}['\"]\)", 
            f"dataframes['{df_name}']", 
            modified_code
        )
        modified_code = re.sub(
            rf"pd\.read_excel\(['\"].*{df_name}['\"]\)", 
            f"dataframes['{df_name}']", 
            modified_code
        )
        
        # Also replace any direct variable assignments that might use the filename
        safe_df_name = df_name.replace('.', '_').replace(' ', '_')
        modified_code = re.sub(
            rf"{safe_df_name}\s*=\s*pd\.read_csv\(['\"].*{df_name}['\"]\)", 
            f"{safe_df_name} = dataframes['{df_name}']", 
            modified_code
        )
        modified_code = re.sub(
            rf"{safe_df_name}\s*=\s*pd\.read_excel\(['\"].*{df_name}['\"]\)", 
            f"{safe_df_name} = dataframes['{df_name}']", 
            modified_code
        )
        
        # For cases where the dataframe is assigned to a generic name like 'df'
        modified_code = re.sub(
            rf"df\s*=\s*pd\.read_csv\(['\"].*{df_name}['\"]\)", 
            f"df = dataframes['{df_name}'].copy()", 
            modified_code
        )
        modified_code = re.sub(
            rf"df\s*=\s*pd\.read_excel\(['\"].*{df_name}['\"]\)", 
            f"df = dataframes['{df_name}'].copy()", 
            modified_code
        )
    
    # Add a print statement to capture data analysis results
    if "print(" not in modified_code and "fig" not in modified_code and "plt" not in modified_code:
        # This might be a data analysis block
        modified_code += "\n\nresult_value = None\n"
        modified_code += "for var_name, var_value in locals().items():\n"
        modified_code += "    if var_name not in ['pd', 'np', 'plt', 'px', 'go', 'alt', 'sns', 'dataframes'] and not var_name.startswith('_'):\n"
        modified_code += "        if isinstance(var_value, (pd.DataFrame, pd.Series)):\n"
        modified_code += "            result_value = var_value\n"
        modified_code += "            break\n"
    
    # Create a local namespace for code execution
    local_namespace = {
        "pd": pd,
        "np": np,
        "plt": plt,
        "px": px,
        "go": go,
        "alt": alt,
        "sns": sns,
        "dataframes": dataframes,
        "datetime": __import__('datetime')
    }
    
    # Execute the code
    try:
        exec(modified_code, globals(), local_namespace)
        return local_namespace
    except Exception as e:
        # Add preprocessing for date columns if date error occurs
        if "doesn't match format" in str(e) and "time data" in str(e):
            # Try preprocessing date columns in all dataframes
            for df_name, df in dataframes.items():
                # Make a copy to avoid modifying the original
                df_copy = df.copy()
                
                # Try to identify and convert date columns
                for col in df_copy.columns:
                    if 'date' in col.lower() or 'time' in col.lower() or 'day' in col.lower():
                        try:
                            df_copy[col] = pd.to_datetime(df_copy[col], format='mixed', dayfirst=True, errors='coerce')
                        except:
                            pass
                
                dataframes[df_name] = df_copy
            
            # Try executing again with preprocessed dataframes
            try:
                local_namespace = {
                    "pd": pd,
                    "np": np,
                    "plt": plt,
                    "px": px,
                    "go": go,
                    "alt": alt,
                    "sns": sns,
                    "dataframes": dataframes,
                    "datetime": __import__('datetime')
                }
                exec(modified_code, globals(), local_namespace)
                return local_namespace
            except Exception as new_e:
                raise Exception(f"Error after date preprocessing: {str(new_e)}")
        else:
            raise Exception(f"Error executing code: {str(e)}")

def create_visualization(local_namespace: Dict) -> Tuple[str, Any]:
    """
    Extract visualization from the namespace after code execution
    """
    # Check for different types of visualizations
    if "fig" in local_namespace:
        fig = local_namespace["fig"]
        if isinstance(fig, plt.Figure):
            # Matplotlib figure
            buffer = BytesIO()
            fig.savefig(buffer, format='png', bbox_inches='tight', dpi=300, facecolor='#121212')
            buffer.seek(0)
            plt.close(fig)  # Close the figure to prevent memory leaks
            return "figure", buffer
        elif "plotly" in str(type(fig)):
            # Plotly figure
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#121212",
                plot_bgcolor="#1E1E1E"
            )
            return "plotly", fig
    
    # Check for Altair chart
    if "chart" in local_namespace:
        chart = local_namespace["chart"]
        if "altair" in str(type(chart)):
            return "altair", chart
    
    # Check for current matplotlib figure
    if plt.get_fignums():
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300, facecolor='#121212')
        buffer.seek(0)
        plt.close()  # Close all figures
        return "figure", buffer
    
    # Check for data analysis results
    if "result_value" in local_namespace and local_namespace["result_value"] is not None:
        result = local_namespace["result_value"]
        if isinstance(result, (pd.DataFrame, pd.Series)):
            return "text", f"```\n{result.to_string()}\n```"
    
    return None, None

def process_visualization_request(prompt: str, files: Dict, api_key: str) -> List[Dict]:
    """
    Process a visualization request and return the responses
    """
    responses = []
    
    # Preprocess date columns in all dataframes
    for file_name, file_data in files.items():
        df = file_data['data'].copy()
        
        # Try to identify and convert date columns
        for col in df.columns:
            if 'date' in col.lower() or 'time' in col.lower() or 'day' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col], format='mixed', dayfirst=True, errors='coerce')
                except:
                    pass
        
        files[file_name]['data'] = df
    
    # Prepare data information for the prompt
    data_info = ""
    dataframes = {}
    
    for file_name, file_data in files.items():
        df = file_data['data']
        dataframes[file_name] = df
        
        # Create data summary
        data_info += f"\nFile: {file_name}\n"
        data_info += f"Shape: {df.shape}\n"
        data_info += f"Columns: {', '.join(df.columns.tolist())}\n"
        data_info += f"Data types:\n{df.dtypes}\n"
        data_info += f"First few rows:\n{df.head(3).to_string()}\n"
    
    # Construct the full prompt
    full_prompt = f"""
    I need to analyze and visualize data from the following files:
    {data_info}
    
    User request: {prompt}
    
    Please:
    1. Answer any questions about the data
    2. Suggest appropriate visualizations
    3. Provide Python code for creating these visualizations
    
    IMPORTANT: When working with dates in the data, use pd.to_datetime with parameters 
    format='mixed', dayfirst=True to handle various date formats.
    
    Make sure to adapt the code to dark mode (dark background, light text/elements).
    """
    
    # Get LLM response
    try:
        llm_response = get_llm_response(full_prompt, api_key)
        response_text = llm_response['choices'][0]['message']['content']
        
        # Add the analysis text (excluding code blocks)
        analysis_text = re.sub(r'```python.*?```', '', response_text, flags=re.DOTALL)
        analysis_text = re.sub(r'```.*?```', '', analysis_text, flags=re.DOTALL)
        analysis_text = analysis_text.strip()
        
        if analysis_text:
            responses.append({
                "type": "text",
                "content": analysis_text
            })
        
        # Extract and execute code blocks
        code_blocks = extract_code_blocks(response_text)
        
        for code in code_blocks:
            try:
                # Execute the code
                local_namespace = execute_code_block(code, dataframes)
                
                # Try to create visualization
                viz_type, viz_content = create_visualization(local_namespace)
                
                if viz_type is not None:
                    responses.append({
                        "type": viz_type,
                        "content": viz_content
                    })
                
                # Add code as text
                responses.append({
                    "type": "text",
                    "content": f"```python\n{code}\n```"
                })
            except Exception as e:
                responses.append({
                    "type": "text",
                    "content": f"Error executing code: {str(e)}\n\nCode attempted:\n```python\n{code}\n```"
                })
    
    except Exception as e:
        responses.append({
            "type": "text",
            "content": f"Error: {str(e)}"
        })
    
    return responses

# Helper function to improve dark mode visualizations
def set_dark_mode_style():
    """Set dark mode styles for matplotlib plots"""
    plt.style.use('dark_background')
    plt.rcParams.update({
        'axes.facecolor': '#1E1E1E',
        'figure.facecolor': '#121212',
        'text.color': 'white',
        'axes.labelcolor': 'white',
        'axes.edgecolor': 'white',
        'xtick.color': 'white',
        'ytick.color': 'white',
        'grid.color': '#333333',
        'legend.facecolor': '#1E1E1E',
        'legend.edgecolor': 'white',
    })

# Set dark mode style at module import
set_dark_mode_style()
