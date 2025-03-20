import streamlit as st
import pandas as pd
import base64
import os
from PIL import Image
import io
import time
from visualize import process_visualization_request
import altair as alt


# Set page configuration
st.set_page_config(
    page_title="Data Analyst Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply dark theme
st.markdown("""
<style>
    .stApp {
        background-color: #121212;
        color: #FFFFFF;
    }
    .stSidebar {
        background-color: #1E1E1E;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
    }
    .stTextInput>div>div>input {
        background-color: #2C2C2C;
        color: white;
    }
    .stTextArea>div>div>textarea {
        background-color: #2C2C2C;
        color: white;
    }
    .stHeader {
        color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("Data Analyst Assistant")
st.markdown("#### High-precision data visualization with LLM")

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'files' not in st.session_state:
    st.session_state.files = {}
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

# Sidebar
with st.sidebar:
    st.header("Settings")
    
    # API Key input
    api_key = st.text_input("Enter your Groq API key", 
                          type="password", 
                          value=st.session_state.api_key)
    if api_key:
        st.session_state.api_key = api_key
    
    # Model info
    st.info("Model: llama3-70b-8192")
    
    # File uploader
    uploaded_files = st.file_uploader("Upload data files", 
                                    accept_multiple_files=True,
                                    type=['csv', 'xlsx', 'xls'])
    
    if uploaded_files:
        for file in uploaded_files:
            file_extension = file.name.split('.')[-1].lower()
            
            if file.name not in st.session_state.files:
                if file_extension == 'csv':
                    try:
                        df = pd.read_csv(file)
                        st.session_state.files[file.name] = {
                            'data': df,
                            'type': 'csv'
                        }
                        st.success(f"File {file.name} uploaded successfully!")
                    except Exception as e:
                        st.error(f"Error reading {file.name}: {e}")
                        
                elif file_extension in ['xlsx', 'xls']:
                    try:
                        # Try with different engines for Excel files
                        try:
                            # First try with openpyxl (for .xlsx)
                            if file_extension == 'xlsx':
                                df = pd.read_excel(file, engine='openpyxl')
                            else:
                                # For .xls files, use xlrd
                                df = pd.read_excel(file, engine='xlrd')
                        except Exception:
                            # If that fails, try alternative engines
                            try:
                                df = pd.read_excel(file, engine='xlrd')
                            except Exception:
                                try:
                                    df = pd.read_excel(file, engine='odf')
                                except Exception:
                                    # Final attempt with auto detection
                                    df = pd.read_excel(file)
                        
                        st.session_state.files[file.name] = {
                            'data': df,
                            'type': 'excel'
                        }
                        st.success(f"File {file.name} uploaded successfully!")
                    except Exception as e:
                        st.error(f"Error reading {file.name}: {e}")
                        st.error("Try converting the file to CSV format and uploading again.")
    
    # Display uploaded files
    if st.session_state.files:
        st.subheader("Uploaded files:")
        for file_name in st.session_state.files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(file_name)
            with col2:
                if st.button("View", key=f"view_{file_name}"):
                    st.session_state.selected_file = file_name
                    
    # Clear data button
    if st.button("Clear all data"):
        st.session_state.files = {}
        st.session_state.messages = []
        st.experimental_rerun()

# Helper function for downloading visualizations
def get_download_link(fig, filename, fig_type):
    """Generate a download link for a figure"""
    if fig_type == "figure":
        # For PIL/matplotlib images (already in BytesIO format)
        if isinstance(fig, io.BytesIO):
            fig.seek(0)
            b64 = base64.b64encode(fig.read()).decode()
            href = f'<a href="data:image/png;base64,{b64}" download="{filename}.png">Download PNG</a>'
            return href
    elif fig_type == "plotly":
        # For Plotly figures
        buffer = io.BytesIO()
        fig.write_image(buffer, format="png")
        buffer.seek(0)
        b64 = base64.b64encode(buffer.read()).decode()
        href = f'<a href="data:image/png;base64,{b64}" download="{filename}.png">Download PNG</a>'
        return href
    elif fig_type == "altair":
        # For Altair charts
        try:
            # Save as HTML string
            html_str = fig.to_html()
            b64 = base64.b64encode(html_str.encode()).decode()
            href = f'<a href="data:text/html;base64,{b64}" download="{filename}.html">Download HTML</a>'
            return href
        except:
            # Fallback - try to get PNG
            try:
                png_data = fig.to_dict()
                buffer = io.BytesIO()
                alt.Chart.from_dict(png_data).save(buffer, format="png")
                buffer.seek(0)
                b64 = base64.b64encode(buffer.read()).decode()
                href = f'<a href="data:image/png;base64,{b64}" download="{filename}.png">Download PNG</a>'
                return href
            except:
                return None
    return None

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    # Chat interface
    st.subheader("Data Visualization Assistant")
    
    # Display chat messages with download buttons for visualizations
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message["type"] == "text":
                st.markdown(message["content"])
            elif message["type"] in ["figure", "plotly", "altair"]:
                # Show the visualization
                if message["type"] == "figure":
                    st.image(message["content"])
                elif message["type"] == "plotly":
                    st.plotly_chart(message["content"], use_container_width=True)
                elif message["type"] == "altair":
                    st.altair_chart(message["content"], use_container_width=True)
                
                # Add download button
                download_link = get_download_link(
                    message["content"], 
                    f"visualization_{i}", 
                    message["type"]
                )
                if download_link:
                    st.markdown(download_link, unsafe_allow_html=True)
    
    # Input prompt
    if prompt := st.chat_input("What visualization would you like to create?"):
        # Check if API key is provided
        if not st.session_state.api_key:
            st.error("Please enter your Groq API key in the sidebar.")
            st.stop()
        
        # Check if files are uploaded
        if not st.session_state.files:
            st.error("Please upload at least one data file.")
            st.stop()
            
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "type": "text", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Show typing indicator
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.text("Thinking...")
            
            # Process request
            try:
                responses = process_visualization_request(
                    prompt, 
                    st.session_state.files, 
                    st.session_state.api_key
                )
                
                # Clear typing indicator
                message_placeholder.empty()
                
                # Display responses with download buttons for visualizations
                for response in responses:
                    if response["type"] == "text":
                        st.markdown(response["content"])
                    elif response["type"] in ["figure", "plotly", "altair"]:
                        # Show the visualization
                        if response["type"] == "figure":
                            st.image(response["content"])
                        elif response["type"] == "plotly":
                            st.plotly_chart(response["content"], use_container_width=True)
                        elif response["type"] == "altair":
                            st.altair_chart(response["content"], use_container_width=True)
                        
                        # Add download button
                        viz_index = len(st.session_state.messages)
                        download_link = get_download_link(
                            response["content"], 
                            f"visualization_{viz_index}", 
                            response["type"]
                        )
                        if download_link:
                            st.markdown(download_link, unsafe_allow_html=True)
                
                # Add to session state
                st.session_state.messages.extend([
                    {"role": "assistant", "type": r["type"], "content": r["content"]} 
                    for r in responses
                ])
                
            except Exception as e:
                message_placeholder.error(f"Error: {str(e)}")
                st.session_state.messages.append(
                    {"role": "assistant", "type": "text", "content": f"Error: {str(e)}"}
                )

with col2:
    # Preview selected file
    if st.session_state.files and hasattr(st.session_state, 'selected_file'):
        file_name = st.session_state.selected_file
        file_data = st.session_state.files[file_name]
        
        st.subheader(f"Preview: {file_name}")
        st.dataframe(file_data['data'].head(10), use_container_width=True)
        
        # Display data info
        st.subheader("Data Info")
        buffer = io.StringIO()
        file_data['data'].info(buf=buffer)
        info_str = buffer.getvalue()
        st.text(info_str)
        
        # Display basic statistics
        st.subheader("Basic Statistics")
        st.dataframe(file_data['data'].describe(), use_container_width=True)

# Footer
st.markdown("---")
st.markdown("*Data Analyst Assistant - Powered by Groq*")

# Run the app
if __name__ == "__main__":
    pass