"""DAG engine for RePERS plans.

Parses plan.md into a step DAG, validates for cycles and missing
references, identifies ready steps, and writes status back.
"""

import re
import os

class DAGEngine:
    def __init__(self, plan_path):
        self.plan_path = os.path.abspath(plan_path)
        self.steps = {}
        self.content = ""
        self.load()

    def load(self):
        """Reads the plan.md file and parses steps into a DAG."""
        if not os.path.exists(self.plan_path):
            raise FileNotFoundError(f"Plan file not found: {self.plan_path}")
            
        with open(self.plan_path, "r", encoding="utf-8") as f:
            self.content = f.read()
            
        self.steps = self.parse_steps(self.content)
        self.validate_dag()

    def parse_steps(self, content):
        """Parses the steps from the Execution Roadmap section."""
        # Find the Execution Roadmap section
        roadmap_match = re.search(r"## .*Step-by-Step Execution Roadmap\s*(.*?)(?=\n##|$)", content, re.DOTALL)
        if not roadmap_match:
            # Fallback to search without the emoji
            roadmap_match = re.search(r"## Step-by-Step Execution Roadmap\s*(.*?)(?=\n##|$)", content, re.DOTALL)
            
        if not roadmap_match:
            return {}

        roadmap_text = roadmap_match.group(1)
        
        # Split into steps. We match lines starting with "1.", "2.", etc.
        # e.g., "1. **Step 1: Create Database Schema**"
        step_blocks = re.split(r"\n(?=\d+\.\s+\*\*)", "\n" + roadmap_text)
        
        steps = {}
        for block in step_blocks:
            block = block.strip()
            if not block:
                continue
                
            # Match step number and title
            header_match = re.match(r"^(\d+)\.\s+\*\*(.*?)\*\*", block)
            if not header_match:
                continue
                
            step_num = header_match.group(1)
            step_title = re.sub(r"^Step\s+\d+:\s*", "", header_match.group(2).strip(), flags=re.IGNORECASE)
            
            # Extract key-value properties under the step
            # e.g., "* **Action**: Initialize SQLite database"
            properties = {}
            prop_matches = re.findall(r"\*\s+\*\*([^*]+)\*\*:[ \t]*(.*)", block)
            for key, val in prop_matches:
                properties[key.strip().lower().replace(" ", "_")] = val.strip()
                
            # Parse Depends On
            depends_on_raw = properties.get("depends_on", "")
            depends_on = []
            if depends_on_raw and depends_on_raw.lower() not in ["none", "nil", "null", ""]:
                # Split by comma, extract digits
                for item in re.split(r",", depends_on_raw):
                    item = item.strip()
                    # Extract step numbers from e.g., "Step 1", "[1]", "1"
                    digits = re.findall(r"\d+", item)
                    if digits:
                        depends_on.extend(digits)
                    else:
                        # Fallback: if it's a title, we might want to keep it or skip it.
                        # For safety, let's strip and keep non-digits if no digits found
                        if item:
                            depends_on.append(item)
                            
            # Keep dependencies deterministic while removing duplicates.
            depends_on = list(dict.fromkeys(depends_on))
            
            # Parse Status
            status = properties.get("status", "Pending").strip()
            # Normalize status
            if status.lower() in ["pending", "todo"]:
                status = "Pending"
            elif status.lower() in ["in progress", "in-progress", "executing"]:
                status = "In Progress"
            elif status.lower() in ["completed", "complete", "done", "pass", "success"]:
                status = "Completed"
            elif status.lower() in ["failed", "fail", "error"]:
                status = "Failed"
            else:
                status = "Pending"
                
            steps[step_num] = {
                "id": step_num,
                "title": step_title,
                "action": properties.get("action", ""),
                "target_file": properties.get("target_file", ""),
                "verification_command": properties.get("verification_command", ""),
                "expected_outcome": properties.get("expected_outcome", ""),
                "depends_on": depends_on,
                "status": status,
                "raw_block": block # Keep original text block for replacement/updating
            }
            
        return steps

    def validate_dag(self):
        """Checks for invalid dependencies or cycles in the step graph."""
        # Check invalid dependencies (pointing to non-existent steps)
        for step_id, step in self.steps.items():
            for dep in step["depends_on"]:
                if dep not in self.steps:
                    raise ValueError(f"Step {step_id} ('{step['title']}') depends on non-existent step: '{dep}'")
                    
        # Check for cycles using DFS
        visited = {} # None: unvisited, 0: visiting, 1: visited
        
        def has_cycle(node_id):
            visited[node_id] = 0 # visiting
            for dep in self.steps[node_id]["depends_on"]:
                if visited.get(dep) == 0:
                    return True # Cycle detected!
                if visited.get(dep) is None:
                    if has_cycle(dep):
                        return True
            visited[node_id] = 1 # visited
            return False

        for step_id in self.steps:
            if step_id not in visited:
                if has_cycle(step_id):
                    raise ValueError(f"Cycle detected in task dependencies involving Step {step_id}!")

    def get_ready_steps(self):
        """Returns list of steps that are 'Pending' and all their dependencies are 'Completed'."""
        ready = []
        for step_id, step in self.steps.items():
            if step["status"] == "Pending":
                # Check if all dependencies are Completed
                deps_satisfied = True
                for dep in step["depends_on"]:
                    if self.steps[dep]["status"] != "Completed":
                        deps_satisfied = False
                        break
                if deps_satisfied:
                    ready.append(step)
        return ready

    def get_all_steps(self):
        """Returns all steps parsed."""
        return self.steps

    def update_status(self, step_id, new_status, verbose=True):
        """Updates the status of a step in self.steps and writes back to plan.md."""
        step_id = str(step_id)
        if step_id not in self.steps:
            raise KeyError(f"Step ID {step_id} not found in parsed steps.")
            
        old_status = self.steps[step_id]["status"]
        self.steps[step_id]["status"] = new_status
        
        # Read the file content fresh to ensure no concurrent updates are lost
        with open(self.plan_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # We need to find the specific step block in content and replace its Status property.
        # To do this safely and preserve formatting:
        # 1. Locate the step number block (e.g. "1. **Step 1: ...")
        # 2. Within that step block, find the status property line and replace it.
        
        # Build regex to find the step block
        # It starts with "step_id. **" and ends at the next step or section header or end of file
        step_start_pattern = r"(\n" + re.escape(step_id) + r"\.\s+\*\*.*?\n)"
        step_match = re.search(re.escape(step_id) + r"\.\s+\*\*.*?(?=\n\d+\.\s+\*\*|\n##|$)", content, re.DOTALL)
        
        if not step_match:
            raise ValueError(f"Could not locate Step {step_id} text block in plan.md for status update.")
            
        step_block_text = step_match.group(0)
        
        # Now find the * **Status**: ... line in this block
        status_pattern = r"(\*\s+\*\*Status\*\*:\s*)([^\n]*)"
        
        if not re.search(status_pattern, step_block_text, re.IGNORECASE):
            # If Status line doesn't exist, append it to the step block
            updated_step_block = step_block_text.rstrip() + f"\n   * **Status**: {new_status}\n"
        else:
            # Replace the Status value
            updated_step_block = re.sub(status_pattern, r"\g<1>" + new_status, step_block_text, flags=re.IGNORECASE)
            
        # Replace the old step block with the updated step block in the full content
        new_content = content.replace(step_block_text, updated_step_block)
        
        with open(self.plan_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        self.content = new_content
        if verbose:
            print(f"[OK] Step {step_id} status updated from '{old_status}' to '{new_status}' in plan.md")
        return True

if __name__ == "__main__":
    # Small self-test
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "test":
        engine = DAGEngine(sys.argv[2])
        print("Steps parsed:")
        import json
        for sid, step in engine.get_all_steps().items():
            print(f"Step {sid}: title='{step['title']}', status='{step['status']}', depends_on={step['depends_on']}")
        print("\nReady steps:")
        print([s["id"] for s in engine.get_ready_steps()])
