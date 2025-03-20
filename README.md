# Academic Agent Suite

An AI-powered tool for researching, writing, and reviewing academic papers automatically.

## Features

- **Research Agent**: Searches academic sources (ArXiv or Google Scholar) for papers on a given topic
- **Writing Agent**: Generates academic paper drafts based on research
- **Review Agent**: Reviews and improves the generated papers
- **Multi-Agent Process**: Orchestrates the entire paper creation pipeline

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

## API Keys

### Google Scholar Integration (Two Options)

#### 1. Free Open-Source Option (Default)
Uses the scholarly library to access Google Scholar without an API key:
- No API key required
- May be less reliable for large queries
- Set in `.env`:
  ```
  USE_SCHOLARLY=True
  DEFAULT_RESEARCH_SOURCE=google_scholar
  ```

#### 2. SerpAPI Option
Uses SerpAPI service for more reliable Google Scholar access:
- Requires an API key from SerpAPI (they offer a free tier)
- More reliable for large queries
- Set in `.env`:
  ```
  USE_SCHOLARLY=False
  SERPAPI_KEY=your_serpapi_key_here
  DEFAULT_RESEARCH_SOURCE=google_scholar
  ```

### ArXiv API

ArXiv API is free and requires no API key. Set in `.env`:
```
DEFAULT_RESEARCH_SOURCE=arxiv
```

### Model API Keys

For text generation, you can use:

- **OpenAI API**: Add your key to `OPENAI_API_KEY` in `.env`
- **SiliconFlow API**: Add your key to `SILICONFLOW_API_KEY` in `.env`

## Running the Application

Start the application with:

```
python app.py
```

The web interface will be available at `http://127.0.0.1:5000`

## Usage

1. Create a new paper project by entering a topic
2. Choose your research source (ArXiv or Google Scholar)
3. Start the research process
4. Once research is complete, generate the paper draft
5. Review and finalize the paper

## Troubleshooting

If you have issues with the Google Scholar integration:

1. Try the free scholarly method first (default)
2. If scholarly doesn't work well, get a SerpAPI key and use that instead
3. Check the application logs for error messages
4. Try using ArXiv as an alternative research source

## 项目结构

```
AcademicAgentSuite/
├── agents/             # 代理模块
│   ├── base_agent.py   # 基础代理类
│   ├── research_agent.py  # 研究代理
│   ├── writing_agent.py   # 写作代理
│   └── review_agent.py    # 审阅代理
├── static/             # 静态资源
├── templates/          # 页面模板
├── app.py              # Flask应用
├── main.py             # 入口点
├── requirements.txt    # 依赖清单
└── .env                # 环境变量
```

## 简化说明

本项目为简化版本，主要特点：

1. 使用SiliconFlow API进行模型请求
2. 研究代理默认生成模拟数据
3. 写作和审阅基于简化逻辑实现
4. 移除了复杂的嵌套函数和条件分支

## 许可证

MIT 