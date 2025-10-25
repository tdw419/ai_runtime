# How It Works - Internal Mechanics

This document explains the internal workings of the AI Runtime System.

## 📊 System Flow

```
┌──────────────────────────────────────────────────────────┐
│  1. USER INPUT                                           │
│  "Create a Flask web server with authentication"        │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│  2. MISSION INTAKE (First time only)                     │
│                                                          │
│  • AI analyzes request                                   │
│  • Creates/identifies MODULE (e.g., "auth")             │
│  • Creates STEP in database                             │
│  • Sets module status to "active"                       │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│  3. CONTEXT BUILDING                                     │
│                                                          │
│  Query database for:                                     │
│  • All modules and their freeze status                   │
│  • Active/pending steps                                  │
│  • Recent actions and results                            │
│  • Human notes/guidance                                  │
│                                                          │
│  Build context summary:                                  │
│  """                                                     │
│  === PROJECT STATE ===                                   │
│  MODULES:                                                │
│    🔒 core (frozen) - Basic structure                   │
│    ✅ auth (active) - User authentication               │
│  ACTIVE STEPS:                                           │
│    • [in_progress] Add login functionality              │
│  RECENT ACTIONS:                                         │
│    ✅ create_file: auth.py                              │
│    ❌ run_python: Import error                          │
│  """                                                     │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│  4. PROMPT CONSTRUCTION                                  │
│                                                          │
│  System Prompt:                                          │
│  "You are an AI development agent in a RUNTIME.         │
│   Respond ONLY with JSON directives.                     │
│   Do NOT edit frozen modules.                            │
│   Available actions: create_file, modify_file, etc."    │
│                                                          │
│  + Context Summary (from step 3)                         │
│  + User Request                                          │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│  5. LLM CALL (LM Studio)                                 │
│                                                          │
│  POST /v1/chat/completions                               │
│  {                                                       │
│    "model": "qwen2.5-coder-7b",                         │
│    "messages": [                                         │
│      {"role": "system", "content": "..."},              │
│      {"role": "user", "content": "..."}                 │
│    ]                                                     │
│  }                                                       │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│  6. RESPONSE PARSING                                     │
│                                                          │
│  LLM returns JSON:                                       │
│  {                                                       │
│    "reasoning": "I need to create auth.py...",          │
│    "directives": [                                       │
│      {                                                   │
│        "action": "create_file",                         │
│        "parameters": {                                   │
│          "filepath": "auth.py",                         │
│          "content": "from flask import..."             │
│        }                                                 │
│      },                                                  │
│      {                                                   │
│        "action": "run_shell",                           │
│        "parameters": {                                   │
│          "command": "pip install flask-login"           │
│        }                                                 │
│      }                                                   │
│    ],                                                    │
│    "next_steps": "Test the login functionality"         │
│  }                                                       │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│  7. DIRECTIVE EXECUTION                                  │
│                                                          │
│  For each directive:                                     │
│    a. Safety check (frozen modules, path escape, etc.)  │
│    b. Execute action (create file, run code, etc.)      │
│    c. Capture result (success/failure, output, errors)  │
│    d. Log to database                                    │
│                                                          │
│  Example: create_file directive                         │
│  ┌──────────────────────────────────────────────┐      │
│  │ 1. Check: Is path in frozen module?          │      │
│  │    → No: Proceed                              │      │
│  │ 2. Check: Does path escape project root?     │      │
│  │    → No: Proceed                              │      │
│  │ 3. Check: Is file size OK?                   │      │
│  │    → Yes: Proceed                             │      │
│  │ 4. Create parent directories                 │      │
│  │ 5. Write file                                 │      │
│  │ 6. Return {success: true, filepath: "..."}   │      │
│  │ 7. Log action to database                    │      │
│  └──────────────────────────────────────────────┘      │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│  8. RESULT AGGREGATION                                   │
│                                                          │
│  Collect all execution results:                          │
│  [                                                       │
│    {                                                     │
│      "directive": {"action": "create_file", ...},       │
│      "result": {"success": true, "filepath": "..."}     │
│    },                                                    │
│    {                                                     │
│      "directive": {"action": "run_shell", ...},         │
│      "result": {"success": true, "stdout": "..."}       │
│    }                                                     │
│  ]                                                       │
│                                                          │
│  Check if step is complete:                              │
│  • All actions successful? → Mark step "done"           │
│  • Any failures? → Keep step "in_progress"              │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│  9. USER FEEDBACK                                        │
│                                                          │
│  Display to user:                                        │
│  • AI's reasoning                                        │
│  • Next steps planned                                    │
│  • Each action's result (✅/❌)                          │
│  • File outputs, errors, stdout                          │
│  • Updated project tree                                  │
└──────────────────────────────────────────────────────────┘
```

## 🗄️ Database Schema Deep Dive

### Modules Table

```sql
modules
├── id              (Primary Key)
├── name            "auth", "core", "api"
├── path            "./auth", "./", "./api"
├── status          "frozen" | "active" | "staging"
├── priority        1-10 (higher = more important)
├── description     "User authentication system"
└── updated_at      "2025-10-25T10:30:00.000Z"
```

**Purpose:** Tracks logical areas of codebase and their edit policies.

**Example Row:**
```python
{
    "id": 1,
    "name": "auth",
    "path": "./auth",
    "status": "frozen",  # AI cannot edit
    "priority": 10,
    "description": "User authentication with JWT",
    "updated_at": "2025-10-25T10:30:00"
}
```

### Steps Table

```sql
steps
├── id              (Primary Key)
├── module_id       (Foreign Key → modules.id)
├── title           "Add login endpoint"
├── detail          Full description from user
├── status          "pending" | "in_progress" | "done" | "blocked"
├── created_at      Timestamp
└── updated_at      Timestamp
```

**Purpose:** Tracks work items/milestones.

**Lifecycle:**
1. Created with status "pending"
2. AI starts working → "in_progress"
3. All actions succeed → "done"
4. Cannot proceed → "blocked"

### Actions Table

```sql
actions
├── id              (Primary Key)
├── step_id         (Foreign Key → steps.id, nullable)
├── action_type     "create_file", "modify_file", etc.
├── params_json     JSON blob of parameters
├── result_json     JSON blob of execution result
├── success         0 or 1 (boolean)
└── created_at      Timestamp
```

**Purpose:** Logs every single action attempt and result.

**Example Row:**
```python
{
    "id": 42,
    "step_id": 5,
    "action_type": "create_file",
    "params_json": '{"filepath": "auth.py", "content": "..."}',
    "result_json": '{"success": true, "filepath": "auth.py"}',
    "success": 1,
    "created_at": "2025-10-25T10:30:15"
}
```

### Notes Table

```sql
notes
├── id              (Primary Key)
├── module_id       (Foreign Key → modules.id)
├── note            Human guidance text
└── created_at      Timestamp
```

**Purpose:** Store human notes/guidance for modules.

**Example:**
```python
{
    "module_id": 1,
    "note": "Don't change the password hashing algorithm",
    "created_at": "2025-10-25T09:00:00"
}
```

## 🛡️ Safety Mechanisms

### 1. Module Freezing

```python
# Check before any edit operation
if memory.is_path_frozen(filepath):
    return {
        "success": False,
        "error": f"Module containing {filepath} is frozen"
    }
```

**SQL Query:**
```sql
SELECT status FROM modules
WHERE 'auth/login.py' LIKE path || '%'
  AND status = 'frozen'
```

If match found → Action blocked

### 2. Path Safety

```python
# Ensure file stays in project root
try:
    full_path.resolve().relative_to(project_root.resolve())
except ValueError:
    # Path escapes project! Block it.
    return {"success": False, "error": "Path escapes project root"}
```

**Prevents:**
- `../../../etc/passwd`
- `/tmp/malicious.py`
- Symbolic link attacks

### 3. Size Limits

```python
MAX_FILE_SIZE = 50000  # 50KB
MAX_LINE_CHANGES = 500

if len(content) > MAX_FILE_SIZE:
    return {"success": False, "error": "File too large"}
```

**Prevents:**
- Accidentally creating huge files
- Memory exhaustion attacks
- Runaway generation

### 4. Docker Sandbox

The runtime uses a stateful Docker container for secure, isolated execution.

**Key Features:**
- **Stateful Container:** A container is started at the beginning of a session and persists until the session is closed.
- **Volume Mounting:** The project directory is mounted into the container at `/app`. This allows the AI to modify files directly, and the changes are immediately reflected on the host. This is highly performant as it avoids image rebuilding.
- **Isolation:** All shell and Python commands are run inside this container, preventing any impact on the host system.
- **Consistent Environment:** The Dockerfile defines a consistent environment with all necessary dependencies, ensuring that code runs the same way every time.

## 🔄 Iteration Loop

The system supports iterative development:

```
User: "Create auth"
  → AI creates auth.py
  → Tests it
  → Works! ✅

User: "Add password hashing"
  → AI reads current auth.py (via read_file)
  → Modifies it to add bcrypt
  → Tests it
  → Works! ✅

User: "Add rate limiting"
  → AI reads current auth.py
  → Modifies it to add rate limiting
  → Tests it
  → Error! ❌ Missing dependency
  → User sees error
  
User: "Install the dependency and try again"
  → AI runs pip install flask-limiter
  → Modifies auth.py again
  → Tests it
  → Works! ✅

User: "freeze auth"
  → Module marked frozen in database

User: "Add email verification"
  → AI creates email.py (new module)
  → Doesn't touch frozen auth.py ✅
```

## 🧠 LLM Prompting Strategy

### System Prompt Forces Behavior

```
You are an AI development agent in a RUNTIME ENVIRONMENT.
You do NOT respond with chat. You respond ONLY with JSON directives.
```

**Key Points:**
1. **Constraint:** JSON only, no explanations
2. **Actions:** Specific list of available operations
3. **Rules:** What to do before/after actions
4. **Context:** Current project state injected

### Context Injection

Every request includes full project state:
- Which modules are frozen
- What steps are active
- Recent successes/failures

**This allows AI to:**
- Remember what exists
- Avoid frozen areas
- Learn from past mistakes
- Build incrementally

## 📈 Scaling Strategy

### For Small Projects (< 10 files)
- Single module "main"
- Simple steps
- Fast iteration

### For Medium Projects (10-100 files)
- Multiple modules (auth, api, frontend, etc.)
- Some frozen, some active
- Prioritized steps

### For Large Projects (100+ files)
- Many modules with clear boundaries
- Most frozen (only edit active areas)
- Step queue with priorities
- Periodic database cleanup

## 🔮 Future Enhancements

### 1. Rollback System
```python
# Before making changes
snapshot = memory.create_snapshot()

# Make changes
...

# If failed
memory.rollback_to(snapshot)
```

### 2. Multi-Model Support
```python
# Use different models for different tasks
coder_model = "qwen2.5-coder-7b"  # For writing code
reviewer_model = "deepseek-33b"    # For reviewing
```

### 3. Test Generation
```python
# AI automatically creates tests
session.step("Create auth.py with tests")
# → Creates auth.py AND auth_test.py
```

### 4. Git Integration (Implemented)
```python
# Auto-commit after successful steps
if all_actions_successful:
    git.commit("AI: Added authentication system")
```

## 💡 Key Insights

1. **Memory is the differentiator** - Without database, AI is a goldfish
2. **Constraints create quality** - JSON-only forces structured thinking
3. **Execution validates instantly** - No guessing if code works
4. **Freezing protects progress** - Build without fear of breaking
5. **Incremental beats big-bang** - Small steps compound faster

---

This architecture transforms AI from a code suggester into a persistent, memory-backed development partner that can build, test, iterate, and protect working code across sessions.
