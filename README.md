# Academic Agent Suite

An AI-powered tool for researching, writing, and reviewing academic papers automatically.

## Features

- **Research Agent**: Searches academic sources (ArXiv, Google Scholar, or PubMed) for papers on a given topic
- **Writing Agent**: Generates professional, academic-formatted papers based on research
- **Review Agent**: Reviews and improves the generated papers
- **Multi-Agent Process**: Orchestrates the entire paper creation pipeline
- **Interactive Multi-Agent Visualization**: Real-time visualization of agent interactions and workflow progress
- **Enhanced Paper Formatting**: Papers are formatted in academic style with proper sections and citations

## Recent Improvements

- **Better Paper Formatting**: Improved academic paper styling with proper sections, headings, and citation formatting
- **Enhanced Error Handling**: Improved error handling in the multi-agent process to prevent server crashes
- **Configurable Features**: Added environment variables to control feature visibility (e.g., hide multi-agent functionality)
- **Diagnostic Tools**: Added debug endpoints to diagnose and troubleshoot issues
- **Better UI Responsiveness**: Improved button feedback and user interaction

## Setup

1. Clone this repository
2. Install the requirements:
   ```
   pip install -r requirements.txt
   pip install scholarly  # For free Google Scholar searches
   ```
3. Set up your API keys:
   - Copy `.env.example` to `.env`
   - Fill in your API keys in the `.env` file

## Configuration Options

### Feature Flags

You can enable or disable certain features using environment variables in your `.env` file:

```
# To enable multi-agent interface
ENABLE_MULTI_AGENT=true

# To disable multi-agent interface
ENABLE_MULTI_AGENT=false
```

### Academic Research Integration (Multiple Options)

#### 1. Free Open-Source Option for Google Scholar (Default)
Uses the scholarly library to access Google Scholar without an API key:
- No API key required
- May be less reliable for large queries
- Set in `.env`:
  ```
  USE_SCHOLARLY=True
  DEFAULT_RESEARCH_SOURCE=google_scholar
  ```

#### 2. SerpAPI Option for Google Scholar
Uses SerpAPI service for more reliable Google Scholar access:
- Requires an API key from SerpAPI (they offer a free tier)
- More reliable for large queries
- Set in `.env`:
  ```
  USE_SCHOLARLY=False
  SERPAPI_KEY=your_serpapi_key_here
  DEFAULT_RESEARCH_SOURCE=google_scholar
  ```

#### 3. ArXiv API
ArXiv API is free and requires no API key. Set in `.env`:
```
DEFAULT_RESEARCH_SOURCE=arxiv
```

#### 4. PubMed API
PubMed API is free and requires no API key. Set in `.env`:
```
DEFAULT_RESEARCH_SOURCE=pubmed
```

### Model API Keys

For text generation, you can use:

- **OpenAI API**: Add your key to `OPENAI_API_KEY` in `.env`
- **SiliconFlow API**: Add your key to `SILICONFLOW_API_KEY` in `.env`
- **Anthropic API**: Add your key to `ANTHROPIC_API_KEY` in `.env`

## Running the Application

For the standard version:
```
python app.py
```

For the fixed version (if experiencing route conflicts):
```
python app_fixed.py
```

The web interface will be available at `http://127.0.0.1:5000`

## Usage

1. Create a new paper project by entering a topic
2. Choose your research source (ArXiv, Google Scholar, or PubMed)
3. Choose a workflow method:
   - **Individual Steps**: Run research, writing, and review separately
   - **Multi-Agent Process**: Run the complete workflow automatically
   - **Interactive Multi-Agent**: View real-time visualization of agents working together

## Interactive Multi-Agent Visualization

The interactive multi-agent feature provides:
- Real-time status updates for each agent
- Visualization of agent interactions and communications
- Detailed process logs
- Step-by-step workflow tracking with visual progress indicators

To use this feature:
1. Create a new project
2. Click "Interactive Multi-Agent" button
3. Watch the agents collaborate in real-time with visualizations

## Diagnostic Tools

If you encounter issues, you can use the built-in diagnostic tools:

- `/api/debug/multi-agent-test/<project_id>` - Tests and diagnoses the multi-agent initialization process
- `/api/debug/test-research/<project_id>` - Tests the research agent's functionality with minimal API calls

## Troubleshooting

If you encounter issues:

1. Try using the fixed version (`python app_fixed.py`) if you see route conflicts
2. If Google Scholar integration fails, try the free scholarly method first (default)
3. If scholarly doesn't work well, get a SerpAPI key and use that instead
4. Check the application logs for error messages
5. Try using ArXiv or PubMed as alternative research sources
6. Use the diagnostic endpoints to identify specific issues

## Project Structure

```
AcademicAgentSuite/
├── agents/                 # Agent modules
│   ├── base_agent.py       # Base agent class
│   ├── research_agent.py   # Research agent
│   ├── writing_agent.py    # Writing agent
│   ├── review_agent.py     # Review agent
│   ├── supervisor_agent.py # Supervisor agent
│   ├── mcp.py              # Model Content Provider
│   ├── arxiv.py            # ArXiv API client
│   ├── pubmed.py           # PubMed API client
│   └── scholarly_google.py # Scholarly Google client
├── static/                 # Static resources
├── templates/              # Page templates
├── app.py                  # Flask application
├── app_fixed.py            # Fixed Flask application (resolves route conflicts)
├── requirements.txt        # Dependencies list
└── .env                    # Environment variables
```

## License

MIT 