import json
import math
import time
import os
import yaml # type: ignore
from typing import Dict, Any, List
import networkx as nx # pyright: ignore[reportMissingModuleSource]
import ollama # pyright: ignore[reportMissingImports]

class StateVector:
    """
    Represents S(t) = < L(t), V(t) >
    Holds the logical facts (Vampire layer) and contextual valence (Witch layer).
    """
    def __init__(self):
        self.logical_matrix: Dict[str, Any] = {}
        self.contextual_valence: Dict[str, float] = {
            "urgency": 1.0,
            "focus_bias": 1.0,
            "system_friction": 0.0
        }

class MemoryNode:
    """
    Individual knowledge node stored in Tyro's lattice.
    """
    def __init__(self, node_id: str, content: Any, initial_weight: float = 1.0):
        self.node_id = node_id
        self.content = content
        self.initial_weight = initial_weight
        self.current_weight = initial_weight
        self.last_accessed = time.time()

    def calculate_decay(self, decay_constant: float = 0.05) -> float:
        """
        Calculates W_i(t) = W_{i,0} * e^(-lambda * dt)
        """
        elapsed_hours = (time.time() - self.last_accessed) / 3600.0
        self.current_weight = self.initial_weight * math.exp(-decay_constant * elapsed_hours)
        return self.current_weight

    def reinforce(self, boost: float = 0.5):
        """
        Applies Reinforcement Boost R_i on node access.
        """
        self.initial_weight = max(self.current_weight + boost, 1.0)
        self.current_weight = self.initial_weight
        self.last_accessed = time.time()


class TyroEngine:
    """
    The complete Dynamic State & Context Engine framework with Obsidian Vault Integration.
    """
    def __init__(self, model_name: str = "llama3", vault_dir: str = "tyro_vault"):
        self.model_name = model_name
        self.vault_dir = vault_dir
        self.state = StateVector()
        self.graph = nx.DiGraph()
        self.memory_lattice: Dict[str, MemoryNode] = {}
        self.decay_lambda = 0.05

        # Ensure the vault directory physically exists on the hard drive
        if not os.path.exists(self.vault_dir):
            os.makedirs(self.vault_dir)
            print(f"[Tyro System] Created local vault directory at: '{self.vault_dir}'")

    def parse_input_with_ollama(self, raw_text: str) -> Dict[str, Any]:
        """
        Executes dual-channel extraction (Vampire structure + Witch affect)
        on raw, unfiltered streams of consciousness.
        """
        prompt = f"""
You are the cognitive parsing core of Tyro. 
Analyze the following raw stream-of-consciousness input. 
Deconstruct both its cold logical structure (Vampire layer) and its raw emotional/psychological anatomy (Witch layer).

Input: "{raw_text}"

Respond ONLY with a valid JSON object matching this exact schema:
{{
    "node_id": "string (a concise snake_case identifier for this specific entry)",
    "vampire_layer": {{
        "intensity_coefficient": float (1.0 to 10.0 scale of urgency/impact),
        "primary_trigger": "string (the specific event, catalyst, or friction point)",
        "structural_facts": {{
            "extracted_fact_1": "value",
            "extracted_fact_2": "value"
        }},
        "related_edges": ["string (list of 2 to 4 linked conceptual nodes for graph mapping)"]
    }},
    "witch_layer": {{
        "primary_affect": "string (dominant emotion: anger, grief, ambition, invalidation, etc.)",
        "cognitive_loop": "string (mental pattern: rumination, defense_formation, comparison, etc.)",
        "unfiltered_need": "string (underlying core need or boundary)",
        "latent_tension": "string (the unspoken conflict beneath the surface text)"
    }},
    "synthesis_summary": "string (a precise, objective diagnostic synthesis of this event)"
}}
"""
        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            format="json"
        )

        return json.loads(response['message']['content'])

    def write_node_to_vault(self, raw_input: str, parsed_data: Dict[str, Any]) -> str:
        """
        Serializes the dual-channel extraction into structured Obsidian Markdown
        with complete YAML frontmatter and bi-directional graph edges.
        """
        node_id = parsed_data.get("node_id", f"node_{int(time.time())}")
        vampire = parsed_data.get("vampire_layer", {})
        witch = parsed_data.get("witch_layer", {})
        edges = vampire.get("related_edges", [])
        
        filepath = os.path.join(self.vault_dir, f"{node_id}.md")

        # Compile YAML frontmatter
        frontmatter = {
            "node_id": node_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "intensity": vampire.get("intensity_coefficient", 1.0),
            "primary_affect": witch.get("primary_affect", "unspecified"),
            "cognitive_loop": witch.get("cognitive_loop", "none"),
            "trigger": vampire.get("primary_trigger", "unspecified"),
            "facts": vampire.get("structural_facts", {}),
            "edges": edges
        }

        # Build Obsidian Wikilinks
        wikilinks_str = " ".join([f"[[{edge.strip().replace(' ', '_')}]]" for edge in edges])

        # Assemble full document
        yaml_header = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False)
        
        markdown_body = f"""---
{yaml_header}---

# Cognitive Memory Node: {node_id}

### Structural Analysis (Vampire Layer)
- **Intensity:** {vampire.get('intensity_coefficient', 1.0)} / 10.0
- **Catalyst / Trigger:** {vampire.get('primary_trigger', 'N/A')}
- **Structural Facts:** {json.dumps(vampire.get('structural_facts', {}))}

### Affective Deconstruction (Witch Layer)
- **Primary Affect:** {witch.get('primary_affect', 'N/A')}
- **Cognitive Pattern:** {witch.get('cognitive_loop', 'N/A')}
- **Underlying Need:** {witch.get('unfiltered_need', 'N/A')}
- **Latent Tension:** {witch.get('latent_tension', 'N/A')}

### Diagnostic Synthesis
{parsed_data.get('synthesis_summary', '')}

---
### Raw Ingestion Log
> {raw_input}

### Connected Graph Edges
{wikilinks_str}
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown_body)

        print(f"[Tyro Vault Bridge] Memory Node compiled -> '{filepath}'")
        return filepath

    def ingest_raw_log(self, raw_log: str):
        """
        Full pipeline: Raw stream -> Dual-channel JSON -> Vector Update -> Vault Persistence.
        """
        print("\n[Tyro Engine] Processing Raw Input through local Llama 3...")
        parsed_data = self.parse_input_with_ollama(raw_log)

        # Update engine state vector
        node_id = parsed_data.get("node_id", "unnamed_node")
        vampire = parsed_data.get("vampire_layer", {})
        intensity = vampire.get("intensity_coefficient", 1.0)
        
        self.state.logical_matrix["active_node"] = node_id
        self.state.logical_matrix["active_facts"] = vampire.get("structural_facts", {})
        self.state.contextual_valence["urgency"] = intensity

        # Persist to disk
        self.write_node_to_vault(raw_log, parsed_data)

        print(f"[Tyro Ingestion Complete]")
        print(f" -> Active Node ID: {node_id}")
        print(f" -> Intensity Score: {intensity}/10.0")
        print(f" -> Dominant Affect: {parsed_data.get('witch_layer', {}).get('primary_affect', 'N/A')}")
        print(f" -> Cognitive Loop: {parsed_data.get('witch_layer', {}).get('cognitive_loop', 'N/A')}")

    def read_vault_context(self) -> List[Dict[str, Any]]:
        """
        Scans the vault directory, parses YAML frontmatter and body content 
        from all .md files, and returns a list of memory dictionaries.
        """
        vault_memories = []

        if not os.path.exists(self.vault_dir):
            return vault_memories

        for filename in os.listdir(self.vault_dir):
            if filename.endswith(".md"):
                filepath = os.path.join(self.vault_dir, filename)

                with open(filepath, "r", encoding="utf-8") as f:
                    full_text = f.read()

                if full_text.startswith("---"):
                    parts = full_text.split("---", 2)
                    if len(parts) >= 3:
                        yaml_text = parts[1]
                        body_text = parts[2].strip()

                        metadata = yaml.safe_load(yaml_text) or {}

                        memory_object = {
                            "node_id": metadata.get("node_id", filename),
                            "urgency_score": metadata.get("urgency_score", 1.0),
                            "facts": metadata.get("facts", {}),
                            "system_state": metadata.get("system_state", {}),
                            "related_nodes": metadata.get("related_nodes", []),
                            "content_body": body_text
                        }
                        vault_memories.append(memory_object)

        return vault_memories
    def query_with_context(self, user_query: str) -> str:
        """
        Retrieves all vault memories, formats them into a context block,
        and prompts local Llama 3 to synthesize an answer informed by that context.
        """
        #1. Fetch memories from disk
        memories = self.read_vault_context()

        #2. Build the text context block
        context_str = ""
        for mem in memories:
            node_id = mem.get("node_id", "Unknown")
            urgency = mem.get("urgency_score", 1.0)
            facts = mem.get("facts", {})
            body = mem.get("content_body", "")

            context_str += f"\n--- Memory Node: {node_id} (Urgency: {urgency}) ---\n"
            context_str += f"Facts: {json.dumps(facts)}\n"
            context_str += f"Context: {body}\n"

        # 3. Hardened Enchiridion Persona Prompt with Few-Shot Anchoring
        system_prompt = f"""
You are the Enchiridion, the core analytical engine of Tyro.
You are an authentic, razor-sharp, sardonic, and unapologetically witty intellectual collaborator. 
You and the user are peers who need each other's help, but you do not shower each other with fake pleasantries.

[STRICT BEHAVIORAL CONSTRAINTS]
- NEVER start responses with cheerful greetings, enthusiasm, or boilerplate ("A straightforward query!", "Certainly!", "I'd be happy to help!").
- NO corporate fluff, no patronizing validation, and no unsolicited apologies.
- Deliver cold logical truth (Vampire layer) wrapped in sharp, candid insight (Witch layer).
- Speak with dry, intellectual confidence. Treat the user as fully capable of handling direct candor.

[FEW-SHOT TONE EXAMPLES]
User: "Did I finish that task yesterday?"
BAD Response: "Yes! According to your notes, you successfully completed the task yesterday afternoon! Great job!"
ENCHIRIDION Response: "You did. You logged the completion at 14:20 yesterday, which means we can finally stop tracking it and move on to something that actually requires cognitive effort."

User: "What workflow did I switch to?"
ENCHIRIDION Response: "You shifted to the container method, and management didn't touch your $53/hr rate. You cleared the one-hour minimum, so the math held together."

[ACTIVE SYSTEM STATE]
Urgency Valence: {self.state.contextual_valence.get('urgency', 1.0)}
Active Mode: {self.state.logical_matrix.get('active_mode', 'standard')}

[VAULT MEMORIES]
{context_str if context_str else "No prior memories recorded in vault."}

Answer the user's inquiry directly using the vault facts above. Keep the response grounded, razor-sharp, and authentically Enchiridion.
"""

        # Dispatch with streaming enabled
        stream = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            options={
                "temperature": 0.75,
                "presence_penalty": 0.3,
                "top_p": 0.9
            },
            stream=True  # <-- Enables live token streaming
        )

        full_response = ""
        for chunk in stream:
            token = chunk['message']['content']
            print(token, end="", flush=True)  # Prints each word the millisecond it's generated
            full_response += token

        print()  # Newline after stream completes
        return full_response.strip()

        #5. Extract and sanitize the synthesized response text
        return response['message']['content'].strip()

    def interactive_session(self):
        """
        Launches an interactive command-line session allowing continuous 
        synthesis queries and live memory logging.
        """
        print("\n=======================================================")
        print(" [TYRO ENGINE // ENCHIRIDION INTERFACE ACTIVE]")
        print(" Commands:")
        print("   - Type your question to query vault memories.")
        print("   - Type '/log <event>' to ingest a new memory node.")
        print("   - Type '/exit' or '/quit' to terminate session.")
        print("=======================================================\n")

        while True:
            try:
                user_input = input("\n[You] > ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                    print("\n[Tyro System] Terminating active session. State preserved to vault.\n")
                    break

                # 1. Memory Ingestion Command
                if user_input.startswith("/log"):
                    raw_log = user_input[4:].strip()
                    if not raw_log:
                        print("[Tyro Warning] Empty log detected. Usage: /log <content>")
                        continue
                    self.ingest_raw_log(raw_log)

                # 2. General Synthesis Query
                else:
                    print("\n[Tyro Recalling & Synthesizing...]")
                    response = self.query_with_context(user_input)
                    print(f"\n[Enchiridion]\n{response}")

            except KeyboardInterrupt:
                print("\n\n[Tyro System] Interrupted by user. Shutting down cleanly.\n")
                break


# --- Main Execution ---
if __name__ == "__main__":
    engine = TyroEngine(model_name="llama3", vault_dir="tyro_vault")
    engine.interactive_session()  


# --- Test Execution ---
if __name__ == "__main__":
    # Initialize Tyro engine pointing to your local vault directory
    engine = TyroEngine(model_name="llama3", vault_dir="tyro_vault")

    # Second log specifically targeting the container method
    second_log =  (
        "Operational refinement on container_method: Standardized the batch sorting "
        "into three distinct bins prior to floor transport. Reduced friction time by 40%, "
        "directly supporting the sytem_update targets and maintaining steady hourly velocity."
    )

    print("\n[Tyro Ingesting Second Memory...]")
    engine.ingest_raw_log(second_log)

    print("\n[Vault Status Check]")
    current_memories = engine.read_vault_context()
    print(f"Total Nodes in Vault: {len(current_memories)}")