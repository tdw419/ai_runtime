# ai_runtime/project_templates.py

from pathlib import Path
from typing import Dict

PROJECT_TEMPLATES: Dict[str, Dict] = {
"flask_api": {
"description": "REST API with Flask + SQLAlchemy + .env config",
"files": {
"app.py": """from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app():
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

@app.route("/")
def health():
return {"status": "ok"}

return app

if __name__ == "__main__":
app = create_app()
app.run(debug=True)
""",
"models.py": """from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class BaseModel(db.Model):
__abstract__ = True
id = db.Column(db.Integer, primary_key=True)
created_at = db.Column(db.DateTime, server_default=db.func.now())
updated_at = db.Column(db.DateTime, onupdate=db.func.now())
""",
"config.py": """import os

class Config:
SQLALCHEMY_DATABASE_URI = os.getenv(
"DATABASE_URL",
"sqlite:///app.db"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
""",
"requirements.txt": """flask
flask_sqlalchemy
python-dotenv
"""
},
"post_commands": [
"pip install -r requirements.txt"
],
"notes": [
"App factory pattern is used (create_app).",
"Database is SQLAlchemy; no migrations yet.",
"Health check route is / returning {status:'ok'}."
]
},

"fastapi_api": {
"description": "FastAPI service with pydantic models and uvicorn runner",
"files": {
"main.py": """from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def health():
return {"status": "ok"}
""",
"requirements.txt": """fastapi
uvicorn[standard]
pydantic
"""
},
"post_commands": [
"pip install -r requirements.txt"
],
"notes": [
"Run with: uvicorn main:app --reload",
"Use Pydantic models for request/response validation."
]
}
}

def apply_template(template_name: str, project_root: Path) -> Dict[str, str]:
"""
Materialize a template into the runtime project folder.
Returns a dict with status info.
"""
if template_name not in PROJECT_TEMPLATES:
return {"success": False, "error": f"Unknown template '{template_name}'"}

tpl = PROJECT_TEMPLATES[template_name]
project_root.mkdir(parents=True, exist_ok=True)

for rel_path, content in tpl["files"].items():
file_path = project_root / rel_path
file_path.parent.mkdir(parents=True, exist_ok=True)
file_path.write_text(content)

return {
"success": True,
"message": f"Applied template '{template_name}'",
"post_commands": tpl.get("post_commands", []),
"notes": tpl.get("notes", [])
}
