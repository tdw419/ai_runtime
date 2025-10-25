# AI Runtime System 🤖

A self-validating AI development environment that connects local LLM models (via LM Studio) to a persistent, sandboxed runtime with memory.

## 🎯 What Problem Does This Solve?

**The Problem:** AI models generate code, but:
- Code often doesn't work
- No way to test or validate automatically
- No memory of what was built
- Can't protect working code from accidental changes
- No persistence across sessions

**The Solution:** This system gives AI:
- ✅ **Real execution environment** - Code runs and is tested immediately
- ✅ **Persistent memory** - SQLite database tracks all modules, steps, and actions
- ✅ **Module protection** - Freeze working code to prevent unwanted changes
- ✅ **Step-by-step building** - Plan, execute, validate, iterate
- ✅ **Action logging** - Every change is recorded with results
- ✅ **Priority management** - Focus AI on what matters most

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Human Input                             │
│              "Build a Flask web server"                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 LM Studio Bridge                            │
│  • Connects to local LLM                                    │
│  • Formats prompts with context                             │
│  • Parses JSON directives                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
           ▼                       ▼
┌──────────────────┐    ┌─────────────────────┐
│  Runtime Memory  │    │  Sandbox Runtime    │
│  (SQLite DB)     │◄───┤  (Code Execution)   │
│                  │    │                     │
│  • Modules       │    │  • File ops         │
│  • Steps         │    │  • Python exec      │
│  • Actions       │    │  • Shell commands   │
│  • Notes         │    │  • Safety checks    │
└──────────────────┘    └─────────────────────┘
           │                       │
           └───────────┬───────────┘
                       │
                       ▼
              ┌────────────────┐
              │  Project Files │
              └────────────────┘
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+** installed
2. **LM Studio** installed and running
   - Download from: https://lmstudio.ai/
   - Load a model (e.g., Qwen, Llama, Mistral)
   - Start the local server (default: http://localhost:1234)

### Installation

```bash
# 1. Install dependencies
pip install requests

# 2. Make launcher executable (optional)
chmod +x launch_runtime.py

# 3. Run the launcher
python launch_runtime.py
```

### First Session

```
you> Create a Flask web server with a hello world endpoint

🤖 AI creates:
   • app.py with Flask server
   • Installs flask via pip
   • Tests the code
   • Shows you the results

you> Add a user authentication system

🤖 AI creates:
   • auth.py module
   • User model
   • Login/logout routes
   • Tests authentication
```

## 📖 Core Concepts

### 1. Modules

**Modules** are logical areas of your codebase with edit policies:

- **🚧 staging** - Fresh module under construction
- **✅ active** - AI can freely build and iterate
- **🔒 frozen** - AI cannot modify without explicit permission

```
you> freeze auth
🔒 Module 'auth' is now frozen

you> unfreeze auth
🔓 Module 'auth' is now unfrozen
```

### 2. Steps/Tasks

**Steps** are concrete goals the AI works on:

```python
# Stored in database:
{
    "title": "Add /login route with password check",
    "status": "in_progress",
    "module": "auth"
}
```

### 3. Actions

Every directive the AI executes is logged:

```python
{
    "action_type": "create_file",
    "parameters": {"filepath": "app.py", "content": "..."},
    "result": {"success": true},
    "timestamp": "2025-10-25T10:30:00"
}
```

### 4. Persistent Memory

All state lives in `runtime_state.db`:

- What modules exist and their status
- What steps are pending/in-progress/done
- What actions were attempted and their results
- Human notes and guidance

The AI can query this database to understand:
- What has already been built
- What needs to happen next
- What's off-limits (frozen)

## 🎮 Commands

### Development Commands

```bash
you> Create a Flask web server
you> Add user authentication
you> Build a REST API for managing tasks
you> Add error handling to the API
```

### Special Commands

```bash
status          # Show modules, steps, and recent actions
tree            # Show project file structure
modules         # List all modules and their status
freeze auth     # Freeze the 'auth' module
unfreeze auth   # Unfreeze the 'auth' module
exit            # Quit the runtime
```

## 📂 Project Structure

```
ai_runtime_system/
├── ai_runtime/
│   ├── __init__.py        # Package initialization
│   ├── memory.py          # RuntimeMemory - SQLite persistence
│   ├── sandbox.py         # SandboxRuntime - Code execution
│   └── lm_bridge.py       # LMStudioRuntimeSession - AI integration
├── launch_runtime.py      # Main launcher script
├── requirements.txt       # Python dependencies
└── README.md             # This file

ai_runtime_project/        # Created on first run
├── runtime_state.db      # Persistent memory database
├── app.py                # Your generated files...
├── auth.py
└── ...
```

## 🔒 Safety Features

### 1. Module Freezing
Protect working code from accidental modification:
```python
session.freeze_module("auth")  # AI can't edit auth module
```

### 2. Path Safety
- Files cannot escape project root
- Frozen module paths are protected

### 3. Size Limits
- Max file size: 50KB
- Max line changes: 500 lines per edit

### 4. Docker Sandbox
- All code is executed within a secure, isolated Docker container.
- The project directory is mounted as a volume, allowing the AI to modify files directly without rebuilding the image.
- This provides a consistent and safe execution environment.

## 💡 Example Session

```bash
$ python launch_runtime.py

🔍 Connecting to LM Studio...
🧠 Using only available model: qwen2.5-coder-7b

📂 Project workspace: ./ai_runtime_project
💾 Database: ./ai_runtime_project/runtime_state.db

🎯 Runtime session is LIVE!

💬 you> Create a Flask web server with a hello world endpoint

🔄 Processing...
🎯 Mission Intake...
✅ Created module 'web_server' and initial step

🤖 AI Reasoning: I'm creating a basic Flask application with a single endpoint
🔜 Next Steps: Test the server by running it

📊 Execution Results (3 actions):

  1. create_file ✅
     File: app.py
     Created app.py

  2. run_shell ✅
     Output: Successfully installed flask-3.0.0...

  3. run_python ✅
     Output: Flask app imported successfully

📂 Updated Project:
  📄 app.py

💬 you> status

📊 RUNTIME STATUS

🗂️  MODULES:
  ✅ web_server (priority 5)
     Path: ./
     Basic Flask web server

📋 ACTIVE STEPS:
  (no active steps - last step completed)

🔄 RECENT ACTIONS:
  ✅ create_file
  ✅ run_shell
  ✅ run_python

💬 you> freeze web_server
🔒 Module 'web_server' is now frozen

💬 you> exit
👋 Shutting down AI Runtime...
```

## 🔧 Advanced Usage

### Custom LM Studio URL

```python
# In launch_runtime.py, change:
LM_STUDIO_URL = "http://localhost:1234"  # Default
# to:
LM_STUDIO_URL = "http://192.168.1.100:8080"  # Custom
```

### Programmatic Usage

```python
from ai_runtime import LMStudioRuntimeSession

session = LMStudioRuntimeSession(
    model_name="qwen2.5-coder-7b",
    lm_base_url="http://localhost:1234",
    project_root="./my_project"
)

# Execute a step
result = session.step("Create a Flask app")

# Get status
status = session.get_status()

# Freeze a module
session.freeze_module("core")

# Close session
session.close()
```

### Database Queries

```python
from ai_runtime import RuntimeMemory

memory = RuntimeMemory("./ai_runtime_project/runtime_state.db")

# List all modules
modules = memory.list_modules()

# Get active steps
steps = memory.get_active_steps()

# Get recent actions
actions = memory.get_recent_actions(limit=20)

# Close connection
memory.close()
```

## 🎯 What Makes This Different?

| Traditional AI Coding | This Runtime System |
|----------------------|---------------------|
| AI suggests code as text | AI **executes** code |
| No validation | **Immediate testing** and feedback |
| No memory | **Persistent state** in database |
| Can't protect code | **Module freezing** |
| No progress tracking | **Step and action logging** |
| One-off responses | **Iterative building** |
| "Did you try...?" | "I tried it and here's what happened" |

## 🚧 Limitations & Future Work

### Current Limitations
- Single-threaded execution
- Limited to Python and shell commands
- Basic error recovery
- No rollback mechanism (yet)

### Planned Features
- [x] Docker container support
- [x] Git integration for versioning
- [ ] Web UI dashboard
- [ ] Multi-model support (switch models mid-session)
- [ ] Rollback/undo functionality
- [ ] Test generation and coverage tracking
- [ ] CI/CD pipeline integration
- [ ] Collaborative sessions (multi-user)

## 🤝 Contributing

This is an experimental project. Contributions, ideas, and feedback are welcome!

## 📄 License

MIT License - Feel free to use and modify for your projects.

## 🙏 Acknowledgments

Built on the shoulders of:
- LM Studio for local LLM hosting
- SQLite for lightweight persistence
- The open-source AI community

---

**Remember:** This system transforms AI from a suggestion tool into an actual development partner that can build, test, and iterate on code with persistent memory and safety guardrails.
