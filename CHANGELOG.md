# Changelog

## v1.1.0 - Interactive Multi-Agent Visualization

### New Features

- **Interactive Multi-Agent Visualization**: Added real-time visualization of agent activities and interactions
  - Agent status cards with live updates
  - Interaction flow diagram showing communication between agents
  - Detailed process logs in real-time
  - Visual progress indicators for each step of the workflow

- **Multi-Agent Workflow Improvements**:
  - Added background threading for non-blocking operation
  - Improved error handling and recovery
  - Better status tracking and reporting

### Bug Fixes

- Fixed route conflict between hyphen and underscore formats in URLs:
  - Added proper route handling for both `/start-interactive-multi-agent` and `/start_interactive_multi_agent` 
  - Deprecated the hyphen version in favor of underscore format

- Fixed OpenAI client initialization in MCP:
  - Removed problematic parameters (proxies, timeout, etc.) causing OpenAI client errors
  - Added proper error handling for client initialization failures
  - Improved logging for error diagnostics

- Fixed undefined variable errors in test_connection method

### Documentation

- Updated README with new features and usage instructions
- Added more detailed troubleshooting section
- Updated project structure section with new components
- Translated Chinese documentation to English

### Other Improvements

- Enhanced frontend UI for multi-agent visualization
- Added proper error state handling in the UI
- Improved API response formats for better frontend compatibility
- Added fallback mechanisms for research source handling 