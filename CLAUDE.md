# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Installation & Setup
```bash
# Install in development mode
pip install -e .

# Install all dependencies including AI agent system
pip install -r requirements.txt

# For AI agent features, ensure these are installed:
pip install langchain langchain-openai litellm python-dotenv
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_scanner.py -v
pytest tests/test_suggester.py -v

# Run with coverage
pytest tests/ --cov=kirolinter --cov-report=html

# Run specific phase tests
pytest tests/phase1/ -v  # Pattern memory tests
pytest tests/phase2/ -v  # Enhanced learning tests
pytest tests/phase3/ -v  # Daemon automation tests
pytest tests/phase4/ -v  # Agent orchestration tests
pytest tests/phase5/ -v  # Workflow coordination tests
pytest tests/phase6/ -v  # Advanced learning tests
pytest tests/phase7/ -v  # Integration & performance tests
```

### Code Quality & Linting
```bash
# Run linting
flake8 kirolinter/

# Format code
black kirolinter/

# Type checking
mypy kirolinter/
```

### Core Usage
```bash
# Basic analysis
kirolinter analyze . --format=summary
kirolinter analyze src/main.py --format=json --output=report.json

# AI Agent System (requires AI dependencies)
kirolinter agent review --repo=https://github.com/pallets/flask
kirolinter agent workflow --repo=./my-project --auto-apply --create-pr
kirolinter agent fix --repo=./project --auto-apply
```

## Architecture Overview

KiroLinter is an AI-driven code analysis tool with a multi-layered architecture:

### Core Components
- **CLI Interface** (`cli.py`): Click-based command-line interface
- **Analysis Engine** (`core/engine.py`): Orchestrates the analysis pipeline
- **Code Scanner** (`core/scanner.py`): AST-based Python code analysis
- **Suggestion Engine** (`core/suggester.py`): AI-powered fix recommendations
- **Interactive Fixer** (`core/interactive_fixer.py`): Automated code fixes with user approval

### AI Agent System
- **Coordinator Agent** (`agents/coordinator.py`): Orchestrates multi-agent workflows
- **Reviewer Agent** (`agents/reviewer.py`): Performs comprehensive code reviews
- **Fixer Agent** (`agents/fixer.py`): Applies automated code fixes
- **Integrator Agent** (`agents/integrator.py`): Handles Git operations and PR creation
- **Learner Agent** (`agents/learner.py`): Learns from commit history and adapts to team patterns

### Memory & Learning
- **Pattern Memory** (`memory/pattern_memory.py`): Stores learned coding patterns
- **Redis Pattern Memory** (`memory/redis_pattern_memory.py`): Scalable pattern storage
- **Conversation Memory** (`memory/conversation.py`): Maintains agent conversation context
- **Knowledge Base** (`memory/knowledge_base.py`): Centralized knowledge management

### Integrations
- **GitHub Client** (`integrations/github_client.py`): GitHub API operations
- **CVE Database** (`integrations/cve_database.py`): Security vulnerability detection
- **Repository Handler** (`integrations/repository_handler.py`): Git operations

### Automation & Orchestration
- **Analysis Daemon** (`automation/daemon.py`): Background analysis scheduling
- **Workflow Coordinator** (`orchestration/workflow_coordinator.py`): Complex workflow management

## Key Design Patterns

### Multi-Agent Architecture
The system uses specialized agents that collaborate through the Coordinator:
- Each agent has specific expertise (reviewing, fixing, integrating, learning)
- Agents communicate through structured workflows
- LangChain integration provides conversation memory and tool access

### Learning System
KiroLinter continuously learns and adapts:
- Analyzes Git commit history to understand team patterns
- Stores anonymized patterns in pattern memory
- Adapts analysis rules based on learned preferences
- Cross-repository learning for broader pattern recognition

### Safety & Security
- All code changes create backups before modification
- Sensitive data is automatically anonymized before storage
- Interactive confirmation for all automated fixes
- Comprehensive audit trails for all operations

## Configuration

### Project Configuration
Create `.kirolinter.yaml` in project root:
```yaml
enabled_rules:
  - unused_variable
  - hardcoded_secret
  - sql_injection

min_severity: medium
exclude_patterns:
  - "tests/*"
  - "venv/*"

# AI Integration
openai_api_key: "your-api-key-here"
use_ai_suggestions: true
```

### AI Agent Configuration
Configure LLM providers in environment:
```bash
export OPENAI_API_KEY="your-key"
export XAI_API_KEY="your-grok-key"
```

## Development Notes

### Adding New Analysis Rules
1. Add detection logic to `scanner.py`
2. Create fix template in `config/templates/`
3. Add tests in `tests/`
4. Update rule documentation

### Agent Development
- Agents inherit from base agent classes
- Use LiteLLM for model flexibility (OpenAI, XAI/Grok, Ollama)
- Implement proper error handling and graceful degradation
- Add comprehensive unit tests with mocked LLM calls

### Testing Strategy
- Phase-based testing structure reflects development milestones
- Unit tests for individual components
- Integration tests for end-to-end workflows
- Performance tests for scalability requirements
- Safety tests for security and data protection

### Memory System
- Pattern memory supports both local SQLite and Redis backends
- Automatic anonymization prevents sensitive data storage
- Cross-repository learning enables broader pattern recognition
- Memory cleanup and garbage collection for efficiency

### Performance Considerations
- Concurrent file analysis for large repositories
- Smart caching to avoid redundant operations
- Resource monitoring and adaptive scheduling
- Background daemon for non-blocking analysis