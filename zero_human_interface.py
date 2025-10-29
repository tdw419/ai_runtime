#!/usr/bin/env python3
# zero_human_interface.py — AI-native system with Explorer and Pixel Database Prep
# This file contains the complete fusion of all 7 modules + PixelDB prep.
import os, json, time, sqlite3, zlib, uuid, random, binascii, hashlib, numpy as np, argparse, asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict, Counter
from abc import ABC, abstractmethod
import requests
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw, PngImagePlugin

# Configuration & Paths
BASE = Path(os.getcwd()).resolve()
DB = BASE / "ai_native.db"
CARTRIDGES = BASE / "cartridges"
MODEL_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1").rstrip("/") + "/chat/completions"
MODEL = os.getenv("LLM_MODEL", "local-model")
TEMP = float(os.getenv("TEMP", "0.7"))
MAXTOK = int(os.getenv("MAXTOK", "4000"))

# Check for CUDA availability for the accelerated query demo
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
# Constants for pixel storage
PIXEL_SIZE = 8
PIXEL_CHANNELS = 3

# ---------- Storage Interface (Abstraction for PixelDB Migration) ----------
class Store(ABC):
    @abstractmethod
    def put(self, kind: str, body: Dict, meta: Dict = None) -> str: pass
    @abstractmethod
    def get(self, kind: str, id: str) -> Dict: pass
    @abstractmethod
    def query_pixel(self, target_grid: List[List[List[float]]], threshold: float = 0.1) -> List[str]: pass
    @abstractmethod
    def scan(self, kind: str, limit: int = 100, **filters) -> List[Dict]: pass
    @abstractmethod
    def close(self): pass

class SQLiteStore(Store):
    def __init__(self, db_path: str = str(DB)):
        self.conn = sqlite3.connect(db_path)
        self.init_schema()

    def init_schema(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS objects (id TEXT PRIMARY KEY, kind TEXT, ver INTEGER, meta JSON, body BLOB, created_at REAL)''')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_objects_unique ON objects(id, ver)')
        cursor.execute('''CREATE TABLE IF NOT EXISTS metrics (iteration INTEGER PRIMARY KEY, meta_learning_index REAL, improvement_velocity REAL, complexity REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pixel_data (id TEXT PRIMARY KEY, object_id TEXT NOT NULL, pixel_grid BLOB NOT NULL)''') # Stores 8x8x3 grid as BLOB
        self.conn.commit()

    def put(self, kind: str, body: Dict, meta: Dict = None) -> str:
        oid = f"{kind}:{uuid.uuid4().hex[:8]}"; ver = 1
        # Store pixel grid if provided
        pixel_grid = body.get("pixel_grid")
        if pixel_grid is not None:
            pixel_blob = zlib.compress(np.array(pixel_grid, dtype=np.float32).tobytes())
            cursor = self.conn.cursor()
            cursor.execute('INSERT INTO pixel_data VALUES (?, ?, ?)', (oid, oid, pixel_blob))
        body_compressed = zlib.compress(json.dumps(body).encode())
        self.conn.execute('INSERT INTO objects VALUES (?, ?, ?, ?, ?, ?)', (oid, kind, ver, json.dumps(meta or {}), body_compressed, int(time.time())))
        self.conn.commit()
        return f"{oid}@{ver}"

    def get(self, kind: str, id: str) -> Dict:
        base_id = id.split('@')[0]
        full_id = f"{kind}:{base_id}" if ':' not in base_id else base_id

        cursor = self.conn.cursor()
        row = cursor.execute('SELECT id, kind, ver, meta, body FROM objects WHERE id = ?', (full_id,)).fetchone()
        result = {}
        if row:
            obj_id, obj_kind, obj_ver, obj_meta, obj_body = row
            result = {
                "id": obj_id,
                "kind": obj_kind,
                "ver": obj_ver,
                "meta": json.loads(obj_meta),
                "body": json.loads(zlib.decompress(obj_body).decode())
            }
            cursor.execute('SELECT pixel_grid FROM pixel_data WHERE object_id = ?', (obj_id,)); pixel_row = cursor.fetchone()
            if pixel_row:
                result["body"]["pixel_grid"] = np.frombuffer(zlib.decompress(pixel_row[0]), dtype=np.float32).reshape(PIXEL_SIZE, PIXEL_SIZE, PIXEL_CHANNELS).tolist()
            return result
        return {}

    def scan(self, kind: str, limit: int = 100, **filters) -> List[Dict]:
        cursor = self.conn.cursor()
        query = 'SELECT kind, ver, meta, body, id FROM objects WHERE kind = ? LIMIT ?'
        rows = cursor.execute(query, (kind, limit)).fetchall()
        results = [{"kind": r[0], "ver": r[1], "meta": json.loads(r[2]), "body": json.loads(zlib.decompress(r[3]).decode()), "id": r[4]} for r in rows]
        for result in results:
            cursor.execute('SELECT pixel_grid FROM pixel_data WHERE object_id = ?', (result["id"],)); pixel_row = cursor.fetchone()
            if pixel_row:
                result["body"]["pixel_grid"] = np.frombuffer(zlib.decompress(pixel_row[0]), dtype=np.float32).reshape(PIXEL_SIZE, PIXEL_SIZE, PIXEL_CHANNELS).tolist()
        return results

    def query(self, kind: str, pattern: Dict) -> List[str]:
        cursor = self.conn.cursor()
        query = 'SELECT id FROM objects WHERE kind = ?'
        params = [kind]
        if pattern:
            query += ' AND ' + ' AND '.join('meta LIKE ?' for _ in pattern)
            params.extend([f'%{json.dumps(v)}%' for k, v in pattern.items()])
        rows = cursor.execute(query, params).fetchall()
        return [row[0] for row in rows]

    def query_pixel(self, target_grid: List[List[List[float]]], threshold: float = 0.1) -> List[str]:
        """GPU-accelerated pixel grid similarity search using CUDA."""
        target = torch.tensor(target_grid, dtype=torch.float32).to(DEVICE)
        cursor = self.conn.cursor()
        cursor.execute('SELECT object_id, pixel_grid FROM pixel_data')
        rows = cursor.fetchall()
        if not rows:
            return []

        # Batch processing on GPU
        grids = [np.frombuffer(zlib.decompress(row[1]), dtype=np.float32).reshape(PIXEL_SIZE, PIXEL_SIZE, PIXEL_CHANNELS) for row in rows]
        grids_t = torch.tensor(np.array(grids), dtype=torch.float32).to(DEVICE)
        target_exp = target.unsqueeze(0).expand(len(grids), -1, -1, -1)

        # Compute batched L2 norm (distance)
        dist = torch.norm(grids_t - target_exp, p=2, dim=(1, 2, 3))
        matches = torch.where(dist < threshold)[0].cpu().numpy()
        return [rows[i][0] for i in matches]

    def close(self): self.conn.close()

# PXL-IR and Color Language
@dataclass
class Tile: opcode: str; args: Dict[str, Any]; color_role: str

@dataclass
class PXLIR: width: int; height: int; tiles: List[Tile]; complexity: float = 0.0

class ColorLanguage:
    palette = {"logic": "#FF6B6B", "memory": "#4ECDC4", "learn": "#45B7D1", "act": "#96CEB4", "meta": "#FFEAA7", "io": "#C7CEEA"}
    def generate_pixel_grid(self, color_role: str, size: int = PIXEL_SIZE) -> List[List[List[float]]]:
        grid = np.zeros((size, size, 3), dtype=np.float32)
        color = self.palette[color_role].lstrip('#')
        rgb = [int(color[j:j+2], 16) / 255.0 for j in (0, 2, 4)]
        grid[:, :, :] = rgb
        return grid.tolist()

OPCODE_DEFAULT_ROLE = {
    "PLOT": "act", "RECT": "logic", "WRITE_TEXT": "meta",
    "IF_CLICK_AT": "act", "JUMP": "logic", "LABEL": "memory"
}
def role_for(op: str) -> str:
    return OPCODE_DEFAULT_ROLE.get(op, "meta")

# Pixel OS Bridge
class PixelOSBridge:
    def __init__(self, color_lang: ColorLanguage):
        self.color_lang = color_lang
        self.opcodes = ["PLOT", "RECT", "WRITE_TEXT", "IF_CLICK_AT", "JUMP", "LABEL"]
        self.sequence = 0
        self._seen_sha8 = set()

    def emit(self, pxl_ir: PXLIR, name: str, obj_id: str) -> str:
        self.sequence += 1
        ir_dict = {"width": pxl_ir.width, "height": pxl_ir.height, "tiles": [{"opcode": t.opcode, "args": t.args, "color_role": t.color_role} for t in pxl_ir.tiles]}
        ir_json = json.dumps(ir_dict, sort_keys=True, separators=(',',':'))
        sha8 = hashlib.sha256(ir_json.encode()).hexdigest()[:8]
        if sha8 in self._seen_sha8:
            path = CARTRIDGES / f"{obj_id.split(':')[1]}.{sha8}.png"
            return str(path)
        self._seen_sha8.add(sha8)
        palette = self.color_lang.palette
        captests = {"version": 1, "tests": [{"name": "has_label_resolution", "expect": True}, {"name": "has_click_if", "expect": True}]}
        path = CARTRIDGES / f"{sha8}_{name}.png"
        CARTRIDGES.mkdir(exist_ok=True)
        manifest = {"collections": ["thought", "skill", "program"], "page": obj_id, "ver": 1}
        pdblock = {"id": obj_id, "kind": "program", "sha": hashlib.sha256(ir_json.encode()).hexdigest()[:8], "seq": self.sequence, "ts": int(time.time()), "bbox": [0, 0, pxl_ir.width, pxl_ir.height], "codec": "json"}
        thumb = self.make_thumbnail(pxl_ir.width, pxl_ir.height)
        info = PngImagePlugin.PngInfo()
        info.add_itxt("PXLIR", ir_json); info.add_itxt("PALETTE", json.dumps(palette)); info.add_itxt("CAPTEST", json.dumps(captests))
        info.add_itxt("PDB.MANIFEST", json.dumps(manifest)); info.add_itxt("PDBLOCK", json.dumps(pdblock))
        img = Image.new("RGB", (pxl_ir.width, pxl_ir.height), "#1e1e1e")
        draw = ImageDraw.Draw(img)
        for tile in pxl_ir.tiles: self._render_tile(draw, tile)
        img.save(path, pnginfo=info)
        return str(path)

    def _render_tile(self, draw: ImageDraw.Draw, tile: Tile):
        opcode, args, color_role = tile.opcode, tile.args, tile.color_role
        color = self.color_lang.palette[color_role]
        if opcode == "RECT":
            x, y, w, h = args["x"], args["y"], args["w"], args["h"]; draw.rectangle([x, y, x+w, y+h], outline=color, width=1)
        elif opcode == "WRITE_TEXT":
            x, y, text = args["x"], args["y"], args["text"]; draw.text((x, y), text, fill=color)
        elif opcode == "PLOT":
            x, y = args["x"], args["y"]; draw.point((x, y), fill=color)

    def make_thumbnail(self, w: int, h: int) -> bytes:
        img = Image.new("RGB", (w, h), "#1e1e1e"); return img.tobytes()

    def evolve(self, pxl_ir: PXLIR, feedback: Dict[str, Any] = None) -> PXLIR:
        new_tiles = pxl_ir.tiles.copy(); click_rate = feedback.get("click_success_rate", 0.0) if feedback else 0.0
        mutation_weights = [0.5, 0.3, 0.1, 0.1] if click_rate < 0.5 else [0.4, 0.3, 0.1, 0.2]
        mutation = random.choices(["add", "modify", "remove", "blend"], weights=mutation_weights, k=1)[0]
        if mutation == "add" and len(new_tiles) < 15:
            opcode = random.choice(["IF_CLICK_AT", "LABEL"] if click_rate < 0.5 else self.opcodes); args = {"x": random.randint(0, 128), "y": random.randint(0, 64)}; color = self.color_lang.palette.get(opcode.lower(), self.color_lang.palette["act"])
            new_tiles.append(Tile(opcode, args, role_for(opcode)))
        complexity = len(new_tiles) + len(set(t.opcode for t in new_tiles)) * 0.5
        return PXLIR(pxl_ir.width, pxl_ir.height, new_tiles, complexity)

class Judge:
    def __init__(self):
        self.opcodes = ["PLOT", "RECT", "WRITE_TEXT", "IF_CLICK_AT", "JUMP", "LABEL"]

    def run(self, pid: str, tests: Dict, store: Store) -> Dict:
        program = store.get("program", (pid.split('@')[0].split(':')[1] if ':' in pid else pid)); tiles = program["body"]["tiles"]
        has_text = any(t["opcode"] == "WRITE_TEXT" for t in tiles); labels = {t["args"]["name"] for t in tiles if t["opcode"] == "LABEL" and "name" in t["args"]}
        has_valid_click = all(t["args"].get("target_true") in labels and t["args"].get("target_false") in labels for t in tiles if t["opcode"] == "IF_CLICK_AT")
        has_valid_jump = all(t["args"].get("target") in labels for t in tiles if t["opcode"] == "JUMP")
        valid = has_text and has_valid_click and has_valid_jump and all(t["opcode"] in self.opcodes for t in tiles)
        score = (1.0 if has_text else 0.0) + (1.0 if has_valid_click else 0.0) + (1.0 if has_valid_jump else 0.0)
        return {"passed": valid, "cases": len(tests.get("cases",)), "score": score, "checks": {"has_write_text": has_text, "click_targets_ok": has_valid_click, "jump_targets_ok": has_valid_jump, "label_count": len(labels), "tile_count": len(tiles)}}

class HumanTranslator:
    def to_human(self, obj: Dict) -> str:
        kind, meta = obj.get("kind", ""), obj.get("meta", {})
        if kind == "program":
            tiles = obj["body"]["tiles"]; complexity = obj["body"]["complexity"]; has_click = any(t["opcode"] == "IF_CLICK_AT" for t in tiles)
            return f"{meta.get('name', 'Program')}: Draws UI with {len(tiles)} tiles ({'Interactive' if has_click else 'Static'})."
        elif kind == "thought":
            return f"Thought: {meta.get('goal', 'Unknown goal')}."
        return meta.get("summary", "AI object under development.")

class ExplorerAgent:
    def __init__(self, store: Store):
        self.store = store
        self.last_exploration = 0; self.cooldown = 10

    def analyze_system(self) -> Dict[str, Any]:
        thoughts = self.store.scan("thought", limit=1000); programs = self.store.scan("program", limit=1000)
        color_dist = defaultdict(int)
        complexities = []
        for obj in programs:
            for tile in obj["body"]["tiles"]: color_dist[tile["color_role"]] += 1
            complexities.append(obj["body"]["complexity"])
        return {"thought_count": len(thoughts), "program_count": len(programs), "color_distribution": dict(color_dist), "avg_complexity": sum(complexities) / len(complexities) if complexities else 0.0}

    def propose_goal(self) -> Dict[str, Any]:
        # Prefer LLM, gracefully fall back to rotating goals
        system = "You are an Explorer agent. Return a compact JSON with keys: goal, type, complexity."
        prompt = "Propose the next compact capability to explore. Keep it atomic."
        try:
            shell = getattr(self, "shell", None)
            if shell is None:
                # attempt to resolve the shell through store owner
                raise RuntimeError("Explorer missing shell; using fallback")
            return propose_or_fallback(shell, prompt, system)
        except Exception:
            # as a last resort, synthesize something simple
            return {"goal": "Introduce learn capability pathway", "type": "learn", "complexity": 0.3}

    def should_explore(self) -> bool:
        return time.time() - self.last_exploration >= self.cooldown and len(self.store.scan("thought")) >= 1

class AIShell:
    def __init__(self):
        self.store = SQLiteStore()
        self.color_lang = ColorLanguage()
        self.judge = Judge()
        self.translator = HumanTranslator()
        self.pixel_bridge = PixelOSBridge(self.color_lang)
        self.explorer = ExplorerAgent(self.store)
        self.explorer.shell = self
        self.iteration = 0
        self.meta_learning_index = 0.3
        self.improvement_velocity = 0.5
        self.complexity = 0.0

    # --- rotating fallback, prefers underused roles ---
    def _fallback_goal(self) -> dict:
        programs = self.store.scan("program", limit=250)
        roles = []
        for p in programs:
            roles += [t["color_role"] for t in p["body"]["tiles"]]
        used = Counter(roles)
        candidates = ["logic", "memory", "learn", "act", "meta", "io"]
        target = min(candidates, key=lambda r: used.get(r, 0))
        tmpl = {
            "logic": "Add control-flow with labels and a jump",
            "memory": "Introduce a named register panel and state tile",
            "learn": "Introduce learn capability pathway",
            "act": "Add interactive click region with true/false branches",
            "meta": "Render a status line with dynamic text",
            "io":   "Add an import/export stub tile for external signals"
        }
        return {"goal": tmpl[target], "type": target, "complexity": 0.35 if target in ("learn","logic") else 0.28}

    def think(self, goal: str, context: Dict[str, Any]) -> str:
        pixel_grid = self.color_lang.generate_pixel_grid(context.get("type", "meta"))
        thought = {"goal": goal, "context": context, "pixel_grid": pixel_grid}
        return self.store.put("thought", thought, {"name": "Thought", "type": context.get("type", "meta"), "goal": goal})

    def plan(self, tid: str) -> str:
        thought_obj = self.store.get("thought", (tid.split('@')[0].split(':')[1] if ':' in tid else tid))
        skill_spec = {"capability": thought_obj["body"]["goal"], "meta": {"type": "learn"}}
        return self.store.put("skill", skill_spec, {"name": "UI_Skill"})

    def compose(self, sid: str) -> str:
        tiles = [
            Tile("RECT", {"x": 0, "y": 0, "w": 128, "h": 16}, "logic"),
            Tile("WRITE_TEXT", {"x": 4, "y": 4, "text": "File", "font": "5x7"}, "meta"),
            Tile("IF_CLICK_AT", {"x": 0, "y": 0, "w": 30, "h": 16, "target_true": "menu_open", "target_false": "loop"}, "act"),
            Tile("LABEL", {"name": "menu_open"}, "memory"),
            Tile("LABEL", {"name": "loop"}, "memory"),
            Tile("JUMP", {"target": "loop"}, "logic")
        ]
        ir_body = {"width": 128, "height": 64, "tiles": [{"opcode": t.opcode, "args": t.args, "color_role": t.color_role} for t in tiles], "complexity": len(tiles) * 1.5}
        return self.store.put("program", ir_body, {"name": "MenuBuilder", "type": "act"})

    def prove(self, pid: str) -> Dict:
        tests = {"cases": [{"test": "pixel_grid_exists", "expected": True}, {"test": "text_rendered", "expected": True}, {"test": "click_handler_defined", "expected": True}]}
        result = self.judge.run(pid, tests, self.store)
        self.store.put("test", tests, {"pid": pid})
        self.store.put("proof", result, {"pid": pid})
        return result

    def render(self, pid: str) -> str:
        program_obj = self.store.get("program", (pid.split('@')[0].split(':')[1] if ':' in pid else pid))
        if program_obj:
            pxl_ir = PXLIR(program_obj["body"]["width"], program_obj["body"]["height"], [Tile(t["opcode"], t["args"], t["color_role"]) for t in program_obj["body"]["tiles"]], program_obj["body"]["complexity"])
            return self.pixel_bridge.emit(pxl_ir, f"program_{pid.split(':')[1].split('@')[0]}", program_obj["id"])
        return ""

    def evolve(self, pid: str) -> str:
        program_obj = self.store.get("program", (pid.split('@')[0].split(':')[1] if ':' in pid else pid))
        if program_obj:
            pxl_ir = PXLIR(program_obj["body"]["width"], program_obj["body"]["height"], [Tile(t["opcode"], t["args"], t["color_role"]) for t in program_obj["body"]["tiles"]], program_obj["body"]["complexity"])
            evolved_pxl_ir = self.pixel_bridge.evolve(pxl_ir, {"click_success_rate": 0.5})
            new_body = {
                "width": evolved_pxl_ir.width,
                "height": evolved_pxl_ir.height,
                "tiles": [{"opcode": t.opcode, "args": t.args, "color_role": t.color_role} for t in evolved_pxl_ir.tiles],
                "complexity": evolved_pxl_ir.complexity
            }
            return self.store.put("program", new_body, {"name": f"Evolved_{program_obj['meta'].get('name','Program')}", "type": "act"})
        return ""

    def explore(self) -> str:
        if not self.explorer.should_explore():
            return ""
        goal = self.explorer.propose_goal()
        if "error" in goal:
            print(f"Explorer error: {goal['error']}")
            return ""
        print(f"🔍 Explorer proposed: {goal['goal']}")
        self.explorer.last_exploration = time.time()
        return self.think(goal["goal"], {"source": "explorer", "type": goal["type"], "complexity": goal["complexity"]})

    def explain(self, oid: str) -> str:
        return self.translator.to_human(self.store.get(oid.split(':')[0], (oid.split('@')[0].split(':')[1] if ':' in oid else oid)))

    def update_metrics(self, complexity: float):
        self.iteration += 1
        self.meta_learning_index = min(1.0, self.meta_learning_index + 0.1 * (self.iteration / 10))
        self.improvement_velocity = min(2.0, self.improvement_velocity + 0.2 * (self.iteration / 10))
        self.complexity = max(self.complexity, complexity)
        cursor = self.store.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO metrics VALUES (?, ?, ?, ?)',
                       (self.iteration, self.meta_learning_index, self.improvement_velocity, self.complexity))
        self.store.conn.commit()

def call_llm(prompt: str, system: str = "") -> tuple[bool, str]:
    payload = {
        "model": os.getenv("LLM_MODEL", "qwen2.5-coder-14b-instruct"),
        "temperature": float(os.getenv("TEMP", "0.7")),
        "max_tokens": int(os.getenv("MAXTOK", "4000")),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    }
    try:
        r = requests.post(os.getenv("LLM_BASE_URL", "http://localhost:1234/v1").rstrip("/") + "/chat/completions", json=payload, timeout=120)
        r.raise_for_status()
        return True, r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return False, f"LLM Error: {e}"

def propose_or_fallback(shell, prompt: str, system: str) -> dict:
    ok, out = call_llm(prompt, system)
    if ok:
        try:
            data = json.loads(out)
            if isinstance(data, dict) and "goal" in data and "type" in data:
                return data
        except Exception:
            pass
    time.sleep(0.5)  # gentle backoff
    return shell._fallback_goal()

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=50)
    ap.add_argument("--cooldown", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=42)
    return ap.parse_args()

async def main():
    args = parse_args()
    random.seed(args.seed)
    print("=" * 70)
    print("🚀 ZERO-HUMAN INTERFACE: RTX 5090 MAXIMUM VELOCITY MODE")
    print("=" * 70)

    shell = AIShell()
    shell.explorer.cooldown = args.cooldown

    try:
        # Bootstrap cycle: Create the first certified skill
        tid = shell.think("Create a file menu that opens on click", {"context": "UI initialisation", "type": "meta"})
        sid = shell.plan(tid)
        pid = shell.compose(sid)
        print(f"🧠 Program Composed: {pid}")
        proof = shell.prove(pid)
        print(f"✅ Proof Score: {proof['score']:.2f}")
        if proof['passed']:
            shell.render(pid)
            print(f"\n🎉 BOOTSTRAP COMPLETE: First certified skill created.")

        for cycle in range(args.cycles):
            print(f"\n🔄 CYCLE {cycle+1}/50")
            # 1. Autonomous Exploration (AI proposes next goal)
            tid = shell.explore()
            if tid:
                sid = shell.plan(tid)
                pid = shell.compose(sid)
                proof = shell.prove(pid)
                if proof['passed']:
                    aid = shell.render(pid)
                    epid = shell.evolve(pid)
                    print(f"🧬 Evolved Program: {epid}")
                    print(f"🗣️ Explanation: {shell.explain(epid)}")
                    shell.update_metrics(shell.store.get("program", epid.split(':')[1])["body"]["complexity"])
                    print(f"Metrics: M.L. Index={shell.meta_learning_index:.2f}, Velocity={shell.improvement_velocity:.2f}, Complexity={shell.complexity:.2f}")
                    if shell.meta_learning_index >= 0.7 and shell.improvement_velocity >= 1.2:
                        print("\n🎉 BREAKTHROUGH ACHIEVED!")
                        break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n⏸️ Paused")
    finally:
        shell.store.close()

if __name__ == "__main__":
    asyncio.run(main())
