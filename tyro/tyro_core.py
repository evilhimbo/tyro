"""
TYRO CORE ENGINE — Phase 1: Ingestion & The Vector Bedrock

This module implements deterministic, LLM-free cognitive state ingestion.
All input is user-provided and validated. The engine makes no inferences.

Architecture:
- VampireLayer: Cold logical facts (intensity, trigger, structural data, edges)
- WitchLayer: Raw emotional anatomy (affect, loop, need, tension)
- LogEntry: Complete memory node (combines both layers + metadata)
- TyroEngine: Orchestrates parsing, validation, vault persistence
"""

import os
import re
import sys
import time
import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import json
import yaml  # type: ignore


# ============================================================================
# PART 1: DATA STRUCTURES
# ============================================================================

@dataclass
class VampireLayer:
    """Cold logical facts extracted from user input."""
    intensity_coefficient: float  # 1.0 to 10.0 scale
    primary_trigger: str          # What happened? The catalyst.
    structural_facts: Dict[str, str] = field(default_factory=dict)  # key:value pairs
    related_edges: List[str] = field(default_factory=list)  # Graph connections


@dataclass
class WitchLayer:
    """Raw emotional/psychological anatomy extracted from user input."""
    primary_affect: str           # anger, grief, ambition, invalidation, trapped, etc.
    cognitive_loop: str           # rumination, defense_formation, comparison, justification, etc.
    unfiltered_need: str          # Core underlying need or boundary
    latent_tension: str           # The unspoken conflict beneath the surface


@dataclass
class LogEntry:
    """A complete, validated cognitive memory node."""
    node_id: str
    timestamp: str
    vampire_layer: VampireLayer
    witch_layer: WitchLayer
    raw_input: str
    synthesis_summary: str = ""  # Optional user reflection


@dataclass
class CognitiveState:
    """The current runtime state of the Tyro engine."""
    vector_id: str = "state_init"
    timestamp: float = field(default_factory=time.time)
    active_node: Optional[str] = None
    vault_node_count: int = 0


# ============================================================================
# PART 2: PARSING & VALIDATION
# ============================================================================

class InputParser:
    """
    Parses structured user input into a validated LogEntry.
    Supports multiline format only (Phase 1).
    
    Expected format:
    intensity: 7
    trigger: memory_leak in container_method
    affect: trapped
    loop: justification_spiral
    need: autonomy and clarity
    tension: losing_control vs defensive_coding
    facts: code_smell=defensive_pattern; context=stressed; outcome=40_pct_reduction
    edges: container_method, system_update, friction_reduction
    """

    REQUIRED_FIELDS = [
        "intensity",
        "trigger",
        "affect",
    ]

    OPTIONAL_FIELDS = [
        "loop",
        "need",
        "tension",
        "facts",
        "edges",
        "summary",
    ]

    @staticmethod
    def validate_intensity(value: str) -> float:
        """Validate intensity is a float between 1.0 and 10.0."""
        try:
            intensity = float(value.strip())
        except ValueError:
            raise ValueError(f"intensity must be a number, got: {value}")

        if not (1.0 <= intensity <= 10.0):
            raise ValueError(f"intensity must be between 1.0 and 10.0, got: {intensity}")

        return intensity

    @staticmethod
    def validate_string_field(value: str, field_name: str, min_length: int = 1) -> str:
        """Validate a string field has content."""
        stripped = value.strip()
        if len(stripped) < min_length:
            raise ValueError(f"{field_name} cannot be empty")
        return stripped

    @classmethod
    def validate_optional_string_field(
        cls, value: str, field_name: str, default: str = "??"
    ) -> str:
        """Return a default for blank optional fields; validate supplied values."""
        if not value.strip():
            return default
        return cls.validate_string_field(value, field_name)

    @staticmethod
    def parse_facts(facts_str: str) -> Dict[str, str]:
        """Parse 'key1=val1; key2=val2' into a dict."""
        if not facts_str.strip():
            return {}

        facts_dict = {}
        pairs = facts_str.split(";")
        for pair in pairs:
            if "=" not in pair:
                continue
            key, val = pair.split("=", 1)
            key = key.strip().replace(" ", "_")
            val = val.strip()
            if key and val:
                facts_dict[key] = val

        return facts_dict

    @staticmethod
    def parse_edges(edges_str: str) -> List[str]:
        """Parse 'edge1, edge2, edge3' into a list of sanitized edges."""
        if not edges_str.strip():
            return []

        edges = []
        for edge in edges_str.split(","):
            cleaned = edge.strip().replace(" ", "_")
            if cleaned and cleaned not in edges:
                edges.append(cleaned)

        return edges

    @classmethod
    def parse_input(cls, raw_input: str) -> Dict[str, Any]:
        """
        Parse multiline structured input into a dictionary of validated fields.
        Raises ValueError if any required field is missing or invalid.
        """
        lines = raw_input.strip().split("\n")
        parsed = {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" not in line:
                raise ValueError(f"Invalid line format (expected 'key: value'): {line}")

            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            parsed[key] = value

        # Validate all required fields are present
        missing = [f for f in cls.REQUIRED_FIELDS if f not in parsed]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        # Build validated data (only validate REQUIRED fields strictly)
        validated = {
            "intensity": cls.validate_intensity(parsed["intensity"]),
            "trigger": cls.validate_string_field(parsed["trigger"], "trigger"),
            "affect": cls.validate_string_field(parsed["affect"], "affect"),
            # Optional fields: use .get() with fallback to empty string, then default to "??" if empty
            "loop": cls.validate_optional_string_field(parsed.get("loop", ""), "loop"),
            "need": cls.validate_optional_string_field(parsed.get("need", ""), "need"),
            "tension": cls.validate_optional_string_field(parsed.get("tension", ""), "tension"),
            "facts": cls.parse_facts(parsed.get("facts", "")),
            "edges": cls.parse_edges(parsed.get("edges", "")),
            "summary": parsed.get("summary", "").strip(),
        }

        return validated


# ============================================================================
# PART 3: VAULT OPERATIONS
# ============================================================================

class VaultBridge:
    """
    Handles all file I/O to the Obsidian vault.
    Responsible for path sanitization, YAML serialization, and markdown writing.
    """

    def __init__(self, vault_dir: str = "tyro_vault") -> None:
        self.vault_dir = vault_dir
        os.makedirs(self.vault_dir, exist_ok=True)

    @staticmethod
    def sanitize_node_id(node_id: str) -> str:
        """
        Sanitize node_id to be safe for filesystem.
        Remove path traversal attempts, illegal chars.
        """
        # Remove path traversal
        safe = node_id.replace("/", "_").replace("\\", "_").replace("..", "_")
        # Remove illegal chars, keep only alphanumeric, underscore, hyphen, dot
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", safe)
        # Strip leading/trailing dots and underscores
        safe = safe.strip("._")

        if not safe:
            raise ValueError(f"Node ID sanitization resulted in empty string: {node_id}")

        return safe

    def write_entry_to_vault(self, entry: LogEntry) -> str:
        """
        Write a LogEntry to vault as a timestamped markdown file.
        Returns the filepath written.
        """
        safe_id = self.sanitize_node_id(entry.node_id)
        filename = f"{entry.timestamp.replace(' ', '_').replace(':', '-')}_{safe_id}.md"
        filepath = os.path.join(self.vault_dir, filename)

        # Build YAML frontmatter
        frontmatter = {
            "node_id": safe_id,
            "timestamp": entry.timestamp,
            "intensity": entry.vampire_layer.intensity_coefficient,
            "trigger": entry.vampire_layer.primary_trigger,
            "primary_affect": entry.witch_layer.primary_affect,
            "cognitive_loop": entry.witch_layer.cognitive_loop,
            "underlying_need": entry.witch_layer.unfiltered_need,
            "latent_tension": entry.witch_layer.latent_tension,
            "edges": entry.vampire_layer.related_edges,
            "facts": entry.vampire_layer.structural_facts,
        }

        yaml_header = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False)
        wikilinks = " ".join([f"[[{edge}]]" for edge in entry.vampire_layer.related_edges])

        markdown_body = f"""---
{yaml_header}---

# Cognitive Memory Node: {safe_id}

## Structural Analysis (Vampire Layer)

**Intensity:** {entry.vampire_layer.intensity_coefficient} / 10.0

**Catalyst / Trigger:** {entry.vampire_layer.primary_trigger}

**Structural Facts:**
```json
{json.dumps(entry.vampire_layer.structural_facts, indent=2)}
```

## Affective Deconstruction (Witch Layer)

**Primary Affect:** {entry.witch_layer.primary_affect}

**Cognitive Pattern:** {entry.witch_layer.cognitive_loop}

**Underlying Need:** {entry.witch_layer.unfiltered_need}

**Latent Tension:** {entry.witch_layer.latent_tension}

## Graph Connections
{wikilinks if wikilinks else "(No edges defined)"}

---
### Raw Ingestion Log
> {entry.raw_input}

### User Reflection
{entry.synthesis_summary if entry.synthesis_summary else "(No synthesis provided)"}
"""

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown_body)
        except OSError as exc:
            raise OSError(f"Failed to write vault node: {filepath}: {exc}") from exc

        return filepath

    def read_vault_stats(self) -> Dict[str, Any]:
        """
        Scan vault and return basic statistics.
        """
        if not os.path.exists(self.vault_dir):
            return {
                "total_nodes": 0,
                "latest_timestamp": None,
                "intensity_min": None,
                "intensity_max": None,
                "intensity_avg": None,
            }

        files = [f for f in os.listdir(self.vault_dir) if f.endswith(".md")]

        if not files:
            return {
                "total_nodes": 0,
                "latest_timestamp": None,
                "intensity_min": None,
                "intensity_max": None,
                "intensity_avg": None,
            }

        intensities = []
        timestamps = []

        for filename in files:
            filepath = os.path.join(self.vault_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Extract frontmatter
                    if content.startswith("---"):
                        end_marker = content.find("---", 3)
                        if end_marker > 0:
                            frontmatter_str = content[3:end_marker]
                            fm = yaml.safe_load(frontmatter_str)
                            if fm and "intensity" in fm:
                                intensities.append(float(fm["intensity"]))
                            if fm and "timestamp" in fm:
                                ts = fm["timestamp"]
                                # Normalize datetime to string (YAML auto-converts date formats)
                                if isinstance(ts, datetime.datetime):
                                    ts = ts.isoformat()
                                timestamps.append(ts)
            except (yaml.YAMLError, UnicodeDecodeError) as exc:
                print(f"[Warning] Failed to parse {filename}: {exc}", file=sys.stderr)
                continue
            except Exception as exc:
                print(f"[Warning] Unexpected error reading {filename}: {exc}", file=sys.stderr)
                raise # Dont't silently swallow unexpected errors
                

        avg_intensity = (
            sum(intensities) / len(intensities) if intensities else None
        )

        return {
            "total_nodes": len(files),
            "latest_timestamp": sorted(timestamps)[-1] if timestamps else None,
            "intensity_min": min(intensities) if intensities else None,
            "intensity_max": max(intensities) if intensities else None,
            "intensity_avg": round(avg_intensity, 2) if avg_intensity else None,
        }


# ============================================================================
# PART 4: TYRO ENGINE (MAIN ORCHESTRATOR)
# ============================================================================

class TyroEngine:
    """
    Main orchestrator for Phase 1 ingestion.
    Manages user input, parsing, validation, and vault persistence.
    """

    def __init__(self, vault_dir: str = "tyro_vault") -> None:
        self.vault_bridge = VaultBridge(vault_dir)
        self.state = CognitiveState()
        self.parser = InputParser()

    def ingest_log(self, raw_input: str) -> LogEntry:
        """
        Parse raw input, validate, create LogEntry, write to vault.
        Returns the LogEntry on success.
        Raises ValueError on invalid input.
        """
        # Parse and validate
        validated = self.parser.parse_input(raw_input)

        # Create data layer objects
        vampire = VampireLayer(
            intensity_coefficient=validated["intensity"],
            primary_trigger=validated["trigger"],
            structural_facts=validated["facts"],
            related_edges=validated["edges"],
        )

        witch = WitchLayer(
            primary_affect=validated["affect"],
            cognitive_loop=validated["loop"],
            unfiltered_need=validated["need"],
            latent_tension=validated["tension"],
        )

        # Generate node ID and timestamp
        node_id = f"{validated['trigger'].replace(' ', '_')[:30]}"
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # Create entry
        entry = LogEntry(
            node_id=node_id,
            timestamp=timestamp,
            vampire_layer=vampire,
            witch_layer=witch,
            raw_input=raw_input,
            synthesis_summary=validated["summary"],
        )

        # Write to vault
        filepath = self.vault_bridge.write_entry_to_vault(entry)

        # Update state
        self.state.active_node = entry.node_id
        try:
            self.state.vault_node_count = len(
                [f for f in os.listdir(self.vault_bridge.vault_dir) if f.endswith(".md")]
            )
        except FileNotFoundError:
            self.state.vault_node_count = 0
            print("[Warning] Vault directory missing: node count reset to 0", file=sys.stderr)

        return entry

    def print_ingestion_result(self, entry: LogEntry) -> None:
        """Pretty-print the result of a successful ingestion."""
        v = entry.vampire_layer
        w = entry.witch_layer

        print("\n" + "=" * 70)
        print("[TYRO INGESTION COMPLETE]")
        print("=" * 70)
        print(f"Node ID:          {entry.node_id}")
        print(f"Timestamp:        {entry.timestamp}")
        print(f"Intensity:        {v.intensity_coefficient} / 10.0")
        print(f"Trigger:          {v.primary_trigger}")
        print(f"Primary Affect:   {w.primary_affect}")
        print(f"Cognitive Loop:   {w.cognitive_loop}")
        print(f"Underlying Need:  {w.unfiltered_need}")
        print(f"Latent Tension:   {w.latent_tension}")
        if v.structural_facts:
            print(f"Structural Facts: {v.structural_facts}")
        if v.related_edges:
            print(f"Related Edges:    {', '.join(v.related_edges)}")
        print("=" * 70 + "\n")

    def print_vault_status(self) -> None:
        """Print vault statistics."""
        stats = self.vault_bridge.read_vault_stats()

        print("\n" + "=" * 70)
        print("[VAULT STATUS]")
        print("=" * 70)
        print(f"Total Nodes:      {stats['total_nodes']}")
        print(f"Latest Entry:     {stats['latest_timestamp'] or 'None'}")
        print(f"Intensity Range:  {stats['intensity_min']} — {stats['intensity_max']}")
        print(f"Intensity Avg:    {stats['intensity_avg']}")
        print("=" * 70 + "\n")

    def interactive_session(self) -> None:
        """Main REPL loop for user interaction."""
        print("\n" + "=" * 70)
        print("[TYRO ENGINE — PHASE 1: INGESTION & VECTOR BEDROCK]")
        print("=" * 70)
        print("\nCommands:")
        print("  /log     — Ingest a new memory node (multiline format)")
        print("  /status  — Show vault statistics")
        print("  /exit    — Close session")
        print("\n" + "=" * 70)

        while True:
            try:
                user_input = input("\n[You] > ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                    print("\n[Tyro] Session closed. Vault intact.\n")
                    break

                if user_input.lower() == "/status":
                    self.print_vault_status()
                    continue

                if user_input.lower() == "/log":
                    print("[Tyro] Enter your log entry (multiline). End with a blank line:")
                    log_lines = []
                    while True:
                        line = input()
                        if not line.strip():
                            break
                        log_lines.append(line)

                    raw_log = "\n".join(log_lines)
                    if not raw_log.strip():
                        print("[Tyro] Empty log rejected. Please provide structured input.\n")
                        continue

                    try:
                        entry = self.ingest_log(raw_log)
                        self.print_ingestion_result(entry)
                    except ValueError as exc:
                        print(f"[Tyro] Ingestion failed: {exc}\n")

                else:
                    print("[Tyro] Unknown command. Use /log, /status, or /exit.\n")

            except KeyboardInterrupt:
                print("\n\n[Tyro] Interrupted. Session closed.\n")
                break


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    engine = TyroEngine(vault_dir="tyro_vault")
    engine.interactive_session()