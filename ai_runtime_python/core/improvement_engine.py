"""
Improvement Engine: Orchestrates the self-correction and learning loop.
This closes the recursive feedback loop (the Flywheel).
"""
import asyncio
import random
from typing import Dict, Any, List

from .color_engine import ColorEngine
from .vector_space import VectorColorSpace # For accessing raw vectors
from .pattern_matcher import PatternMatcher # For direct DB interaction

class ImprovementEngine:
    def __init__(self, color_engine: ColorEngine, db_path: str = "./pattern_memory"):
        self.engine = color_engine
        self.matcher = PatternMatcher(self.engine.vector_space, db_path)
        self.learning_cycles = 0

    # --- Core Simulation ---
    async def _simulate_admin_execute(self, pattern: List[List[str]]) -> Dict[str, Any]:
        """Simulates execution of a PPL pattern in the AI Admin environment.
        Returns success and performance metrics (telemetry).
        """
        # Pattern: 🟢 (Success) is always assumed high confidence. 🔴 (Alert) is high risk.
        is_successful = random.random() > 0.35 # Simulate 65% success rate
        execution_time = random.uniform(5, 15) # Simulated time in milliseconds

        # The AI's internal assessment is based on the pattern itself
        for row in pattern:
            if '🔴' in row: # High risk pattern should take longer/fail more often
                is_successful = random.random() > 0.6 # 40% success
                execution_time *= 2
            if '🟢' in row: # Success pattern should be fast/high success
                execution_time *= 0.5

        return {
            'success': is_successful,
            'metrics': {'latency_ms': round(execution_time, 2)},
            'action': "PatternExecuted"
        }

    # --- Flywheel Logic ---
    async def run_improvement_cycle(self, tasks_to_run: int = 10):
        """Runs a set number of tasks, learns from the outcomes, and improves the pattern memory."""
        print("\n" + "="*80)
        print(f"🧠 BEGINNING RECURSIVE IMPROVEMENT CYCLE: {self.learning_cycles}")
        print("="*80)

        successes = 0
        for i in range(tasks_to_run):
            # 1. GENERATE TASK: Create a new pattern based on past success
            task_pattern = self._generate_task_pattern(i)
            print(f"\n[CYCLE {i+1:02d}] Generated Pattern: {task_pattern}")
            
            # 2. EXECUTE & MONITOR: Simulate running the pattern
            outcome = await self._simulate_admin_execute(task_pattern)
            
            is_successful = outcome['success']
            print(f"  STATUS: {'✅ SUCCESS' if is_successful else '❌ FAILURE'} | Latency: {outcome['metrics']['latency_ms']}ms")

            # 3. LEARN & STORE: If successful, reinforce the pattern in the database
            if is_successful:
                self.engine.learn(task_pattern, outcome)
                successes += 1
            
            # 4. ADAPTATION: The next generated pattern will be influenced by this outcome
            await asyncio.sleep(0.01) # Small pause to simulate task completion

        self.learning_cycles += 1
        print(f"\n✅ CYCLE COMPLETE. {successes}/{tasks_to_run} tasks succeeded and were stored.")

    # --- Pattern Generation (Self-Correction/Novelty) ---
    def _generate_task_pattern(self, current_cycle: int) -> List[List[str]]:
        """Generates new PPL patterns by combining successful past patterns (novelty)
        or by modifying existing ones (mutation)."""

        # Check if memory is empty (Initial bootstrap)
        if self.matcher.patterns_table is None or self.matcher.patterns_table.count() < 3:
            # Start with a random combination of simple primitives
            primitives = ['🔵', '🟡', '🟣', '🟢', '🟥']
            pattern = [[random.choice(primitives) for _ in range(3)] for _ in range(2)]
            return pattern

        # 1. Query Past Successes (Pulling from memory)
        # The AI asks: "What patterns were successful before?"
        seed_pattern = [['🟡', '🟣', '🟢']] # Query for a Monitor->Transform->Success pattern
        similar_successes = self.matcher.find_similar(seed_pattern, limit=5)

        if not similar_successes:
            return seed_pattern # Default if memory is too sparse

        # 2. Select and Parse a Base Pattern
        base_pattern_str = random.choice(similar_successes)['pattern']
        base_pattern = eval(base_pattern_str) # Convert string representation back to list of lists

        # 3. Mutate (Introduce Novelty)
        # The AI introduces a new element or modifies an existing one to test optimization
        new_color = random.choice(['⚡', '🔄', '⬆️', '🧠', '💾']) # Introduce a new operational concept
        
        # Modify the middle element to the new color
        if len(base_pattern) > 0 and len(base_pattern[0]) > 1:
            mid_row = len(base_pattern) // 2
            mid_col = len(base_pattern[0]) // 2
            base_pattern[mid_row][mid_col] = new_color
        
        return base_pattern
