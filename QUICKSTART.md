# 🚀 Quick Start Guide

Get the AI Runtime System up and running in 5 minutes!

## Step 1: Install LM Studio

1. Download LM Studio from https://lmstudio.ai/
2. Install and open LM Studio
3. Click "Search" in the left sidebar
4. Download a coding model (recommended):
   - **Qwen2.5-Coder-7B** (good balance of speed and quality)
   - **DeepSeek-Coder-6.7B** (fast and capable)
   - **CodeLlama-13B** (more powerful, slower)

## Step 2: Start LM Studio Server

1. Click the "↔" icon on the left (Local Server)
2. Select your downloaded model
3. Click "Start Server"
4. Note the server URL (usually http://localhost:1234)

## Step 3: Install Python Dependencies

```bash
cd ai_runtime_system
pip install requests
```

## Step 4: Launch the Runtime

```bash
python launch_runtime.py
```

You should see:
```
=========================================
   🤖 AI RUNTIME LAUNCHER
   Persistent Memory + Local Model + Sandboxed Builder
=========================================

🔍 Connecting to LM Studio...
🧠 Using only available model: qwen2.5-coder-7b

📂 Project workspace: ./ai_runtime_project
💾 Database: ./ai_runtime_project/runtime_state.db

🎯 Runtime session is LIVE!
```

## Step 5: Try Your First Build

Type a command:

```
you> Create a Flask web server with a hello world endpoint
```

The AI will:
1. Create `app.py` with Flask code
2. Install Flask via pip
3. Test that the code works
4. Show you the results

## Step 6: Build Something More Complex

```
you> Add user authentication with login and registration

you> Create a SQLite database to store users

you> Add password hashing with bcrypt

you> Create HTML templates for login and register pages
```

## Step 7: Protect Your Code

Once something works, freeze it:

```
you> freeze auth
🔒 Module 'auth' is now frozen
```

Now the AI can't accidentally break your working authentication!

## Step 8: Check Status

```
you> status
```

See:
- All modules and their freeze status
- Active steps being worked on
- Recent actions and results

## Common Commands

```bash
# Development
you> Create a [feature]
you> Add [functionality] to [module]
you> Fix the bug in [file]
you> Refactor [module] to use [pattern]

# Management
you> status          # Show everything
you> tree            # Show files
you> modules         # List all modules
you> freeze [name]   # Protect a module
you> unfreeze [name] # Allow edits again

# Exit
you> exit
```

## Troubleshooting

### "No models found"
- Make sure LM Studio is running
- Check that you've started the Local Server
- Verify it's on http://localhost:1234

### "Failed to parse AI response"
- Try a different model (some work better than others)
- Make the request more specific
- Check LM Studio's console for errors

### "Module is frozen" error
- Check which modules are frozen: `you> modules`
- Unfreeze if needed: `you> unfreeze [module_name]`

### AI creates wrong code
- Be more specific in your request
- Break the task into smaller steps
- Check the generated files and provide feedback

## Next Steps

1. **Read the full README.md** for advanced features
2. **Check examples.py** for programmatic usage
3. **Experiment!** The system learns from execution results

## Example Session

```
you> Create a todo list application

🤖 AI creates basic structure...

you> Add database support with SQLite

🤖 AI adds database models...

you> Create REST API endpoints for CRUD operations

🤖 AI implements /api/todos endpoints...

you> Add HTML frontend with forms

🤖 AI creates templates...

you> Add CSS styling with a modern theme

🤖 AI adds styles...

you> status

📊 Modules: 3 (todo_core, api, frontend)
📋 Steps: All completed
🔄 Recent: 15 actions, all successful

you> freeze todo_core
you> freeze api

🔒 Core modules are now protected!

you> Add user authentication
🤖 AI adds auth module without touching frozen code...
```

## Tips for Best Results

1. **Start small** - Build incrementally
2. **Test often** - The AI will test after creating files
3. **Freeze working code** - Protect what works
4. **Be specific** - Clear requests get better results
5. **Use modules** - Organize code into logical areas
6. **Check status** - See what's been built and what's pending

---

**You're ready!** Start building and let the AI handle the heavy lifting while you stay in control.
