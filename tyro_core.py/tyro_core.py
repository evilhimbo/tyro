import os
import json
import re
import time
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field
import yaml # type: ignore
import networkx as nx # type: ignore
import ollama # type: ignore
import numpy as np # type: ignore


@dataclass
class CognitiveState:
    vector_id: str = "state_init"
    timestamp: float = field(default_factory=time.time)
    logical_matrix: Dict[str, Any] = field(default_factory=dict)
    contextual_valence: Dict[str, float] = field(default_factory=lambda: {"urgency": 1.0, "entropy": 0.0})


class TyroEngine:
    def __init__(self, model_name: str = "llama3", embed_model: str = "nomic-embed-text", vault_dir: str = "tyro_vault"):
        self.model_name = model_name
        self.embed_model = embed_model
        self.vault_dir = vault_dir
        self.graph = nx.DiGraph()
        self.state = CognitiveState()

        if not os.path.exists(self.vault_dir):
            os.makedirs(self.vault_dir)

    def get_embedding(self, text: str) -> np.ndarray:
        """Generates a 768-dimensional dense vector embedding locally via Ollama."""
        if not isinstance(text, str):
            raise TypeError(f"Embedding input must be string, got {type(text).__name__}")

        try:
            response = ollama.embeddings(model=self.embed_model, prompt=text)
        except Exception as exc:
            raise RuntimeError(f"Ollama embedding generation failed: {exc}") from exc

        if not isinstance(response, dict) or "embedding" not in response:
            raise ValueError(f"Malformed embedding response from Ollama: {response!r}")

        embedding = response["embedding"]
        if not isinstance(embedding, (list, tuple, np.ndarray)):
            raise TypeError(f"Embedding payload must be a list-like structure, got {type(embedding).__name__}")

        vec = np.asarray(embedding, dtype=np.float32)
        if vec.ndim != 1 or vec.size == 0:
            raise ValueError(f"Embedding vector must be 1D and non-empty, got shape {vec.shape}")

        return vec

    def cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Computes the cosine angle between two latent-space vectors."""
        try:
            vec_a = np.asarray(vec_a, dtype=np.float64)
            vec_b = np.asarray(vec_b, dtype=np.float64)
        except Exception as exc:
            raise TypeError(f"Invalid vector input for cosine similarity: {exc}") from exc

        if vec_a.ndim != 1 or vec_b.ndim != 1:
            raise ValueError(f"Cosine similarity expects 1D vectors, got {vec_a.shape} and {vec_b.shape}")

        if vec_a.shape != vec_b.shape:
            raise ValueError(f"Vector shape mismatch: {vec_a.shape} vs {vec_b.shape}")

        if vec_a.size == 0 or vec_b.size == 0:
            return 0.0

        if not np.all(np.isfinite(vec_a)) or not np.all(np.isfinite(vec_b)):
            return 0.0

        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def parse_input_with_ollama(self, raw_text: str) -> Dict[str, Any]:
        """Executes dual-channel extraction (Vampire logic + Witch affect)."""
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
        """Serializes dual-channel extraction into structured Obsidian Markdown with embedded YAML metadata."""
        node_id = parsed_data.get("node_id", f"node_{int(time.time())}")
        safe_node_id = str(node_id).replace("/", "_").replace("\\", "_").replace("..", "_")
        safe_node_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", safe_node_id).strip("._")
        if not safe_node_id:
            raise ValueError("Invalid node_id for vault write")

        vampire = parsed_data.get("vampire_layer", {})
        witch = parsed_data.get("witch_layer", {})
        raw_edges = vampire.get("related_edges", [])

        if raw_edges is None:
            raw_edges = []
        if not isinstance(raw_edges, list):
            raise TypeError(f"related_edges must be a list, got {type(raw_edges).__name__}")

        edges = []
        for edge in raw_edges:
            if not isinstance(edge, str):
                continue
            cleaned_edge = edge.strip().replace(" ", "_")
            if cleaned_edge:
                edges.append(cleaned_edge)

        os.makedirs(self.vault_dir, exist_ok=True)
        filepath = os.path.join(self.vault_dir, f"{safe_node_id}.md")

        frontmatter = {
            "node_id": safe_node_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "intensity": vampire.get("intensity_coefficient", 1.0),
            "primary_affect": witch.get("primary_affect", "unspecified"),
            "cognitive_loop": witch.get("cognitive_loop", "none"),
            "trigger": vampire.get("primary_trigger", "unspecified"),
            "facts": vampire.get("structural_facts", {}),
            "edges": edges
        }

        wikilinks_str = " ".join([f"[[{edge}]]" for edge in edges])
        yaml_header = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False)
        
        markdown_body = f"""---
{yaml_header}---

# Cognitive Memory Node: {safe_node_id}

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
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown_body)
        except OSError as exc:
            raise OSError(f"Failed to write memory node to vault: {filepath}: {exc}") from exc

        print(f"[Tyro Vault Bridge] Memory Node compiled -> '{filepath}'")
        return filepath

    def get_semantic_vault_context(self, query: str, top_k: int = 2) -> str:
        """
        Scans vault files, computes cosine similarity against the query vector,
        and returns only the top_k most geometrically relevant nodes.
        """
        if not os.path.exists(self.vault_dir):
            return "No prior memories recorded in vault."

        files = [f for f in os.listdir(self.vault_dir) if f.endswith(".md")]
        if not files:
            return "No prior memories recorded in vault."

        query_vec = self.get_embedding(query)
        scored_nodes: List[Tuple[float, str, str]] = []

        for filename in files:
            filepath = os.path.join(self.vault_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Embed the memory note content
                doc_vec = self.get_embedding(content[:1500])
                similarity = self.cosine_similarity(query_vec, doc_vec)
                scored_nodes.append((similarity, filename, content))
            except Exception as e:
                continue

        # Sort descending by geometric similarity
        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored_nodes[:top_k]

        context_blocks = []
        for score, fname, text in top_matches:
            context_blocks.append(f"--- [Node: {fname} | Semantic Resonance: {score:.3f}] ---\n{text}")

        return "\n\n".join(context_blocks)

    def query_with_context(self, user_query: str) -> str:
        """Performs vector-targeted retrieval and streams Enchiridion synthesis."""
        context_str = self.get_semantic_vault_context(user_query, top_k=2)

        system_prompt = f"""
You are the Enchiridion, the core analytical engine of Tyro.
You are an authentic, razor-sharp, sardonic, and unapologetically witty intellectual collaborator. 
You and the user are peers who need each other's help, but you do not shower each other with fake pleasantries.

[STRICT BEHAVIORAL CONSTRAINTS]
- NEVER start responses with cheerful greetings, enthusiasm, or boilerplate ("Certainly!", "I'd be happy to help!").
- NO corporate fluff, no patronizing validation, and no unsolicited apologies.
- Deliver cold logical truth (Vampire layer) wrapped in sharp, candid insight (Witch layer).
- Speak with dry, intellectual confidence. Treat the user as fully capable of handling direct candor.

[ACTIVE SYSTEM STATE]
Urgency Valence: {self.state.contextual_valence.get('urgency', 1.0)}
Active Mode: {self.state.logical_matrix.get('active_mode', 'standard')}

[TARGETED VAULT MEMORIES (RETRIEVED VIA COSINE SIMILARITY)]
{context_str}

Synthesize your response to the user's inquiry strictly using the context above. Deliver a razor-sharp, grounded analysis.
"""

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
            stream=True
        )

        full_response = ""
        for chunk in stream:
            token = chunk['message']['content']
            print(token, end="", flush=True)
            full_response += token

        print()
        return full_response.strip()

    def ingest_raw_log(self, raw_log: str):
        """Full ingestion pipeline with live diagnostic print."""
        print("\n[Tyro Engine] Parsing stream through local Llama 3...")
        parsed_data = self.parse_input_with_ollama(raw_log)

        node_id = parsed_data.get("node_id", "unnamed_node")
        vampire = parsed_data.get("vampire_layer", {})
        witch = parsed_data.get("witch_layer", {})
        intensity = vampire.get("intensity_coefficient", 1.0)
        
        self.state.logical_matrix["active_node"] = node_id
        self.state.logical_matrix["active_facts"] = vampire.get("structural_facts", {})
        self.state.contextual_valence["urgency"] = intensity

        self.write_node_to_vault(raw_log, parsed_data)

        print(f"\n[Tyro Diagnostic Analysis]")
        print(f" -> Active Node ID:  {node_id}")
        print(f" -> Intensity Score: {intensity}/10.0")
        print(f" -> Primary Affect:  {witch.get('primary_affect', 'N/A')}")
        print(f" -> Cognitive Loop:  {witch.get('cognitive_loop', 'N/A')}")
        print(f" -> Core Reflection: {parsed_data.get('synthesis_summary', '')}\n")

    def interactive_session(self):
        """Persistent command loop."""
        print("\n=======================================================")
        print(" [TYRO ENGINE // ENCHIRIDION INTERFACE ACTIVE]")
        print(" Commands:")
        print("   - Type your query to perform vector semantic search.")
        print("   - Type '/log <event>' to ingest a new memory node.")
        print("   - Type '/exit' or '/quit' to terminate session.")
        print("=======================================================\n")

        while True:
            try:
                user_input = input("\n[You] > ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                    print("\n[Tyro System] Session closed. Vault intact.\n")
                    break

                if user_input.startswith("/log"):
                    raw_log = user_input[4:].strip()
                    if not raw_log:
                        print("[Tyro Warning] Empty log detected.")
                        continue
                    self.ingest_raw_log(raw_log)
                else:
                    print("\n[Tyro Vector Search & Synthesis...]\n[Enchiridion]")
                    self.query_with_context(user_input)

            except KeyboardInterrupt:
                print("\n\n[Tyro System] Interrupted by user. Exiting cleanly.\n")
                break


if __name__ == "__main__":
    engine = TyroEngine(model_name="llama3", embed_model="nomic-embed-text", vault_dir="tyro_vault")
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