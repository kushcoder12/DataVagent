# 📊 Streamlit LLM Agent Data Visualizer

This repository provides an interactive Streamlit-based web interface for data visualization and analysis. The app allows users to upload datasets, explore insights, and effortlessly generate visualizations.

## 🚀 Features

- **Upload & Explore**: Upload CSV or Excel files and explore data interactively.
- **Automated Insights**: Uses an LLM-powered API to analyze datasets and suggest visualizations.
- **Interactive Visualizations**: Supports Matplotlib, Plotly, Seaborn, and Altair for interactive graphs.
- **Dark Mode Optimized**: Aesthetic and clear visualizations with a dark theme.
- **Customizable Analysis**: Users can modify and execute code directly.

## 🛠️ Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### 2️⃣ Install Dependencies

Ensure you have Python 3.8+ installed, then run:

```bash
pip install -r requirements.txt
```

### 3️⃣ Run the Streamlit App

```bash
streamlit run llmagent.py
```

## 🖼️ Screenshots

| Upload Data | Interactive Visualization |
| ----------- | ------------------------- |
|             |                           |

## 🔧 Usage

1. Upload your dataset (`.csv` or `.xlsx`).
2. The LLM provides insights and suggests visualizations.
3. Modify or execute code to generate custom visualizations.
4. Download and share insights.

## 📦 Dependencies

- **Streamlit** - Interactive web UI
- **Pandas & NumPy** - Data manipulation
- **Matplotlib & Seaborn** - Static visualizations
- **Plotly & Altair** - Interactive charts
- **Requests** - API communication for LLM analysis

## 🧠 How It Works

- The app preprocesses datasets, handling missing values and date parsing.
- It sends a structured prompt to an LLM API (`llama3-70b-8192`) to generate insights.
- Suggested code blocks are extracted and executed dynamically.
- Visualizations are rendered using various plotting libraries.

## ⚡ API Configuration

To use the LLM API, set your API key as an environment variable:

```bash
export LLM_API_KEY="your-api-key"
```

Or pass it in the application settings.

## 🏗️ Future Improvements

- Support for additional file formats (JSON, Parquet)
- Enhanced LLM responses for deeper insights
- Customizable visualization templates

## 📜 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

