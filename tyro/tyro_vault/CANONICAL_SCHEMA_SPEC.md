# Tyro Canonical Schema Specification

## Phase 1 Scope

Phase 1 accepts structured, user-provided log input, validates it without LLM inference, and persists one Markdown memory node with YAML frontmatter.

## Input Contract

### Required fields

| Field | Type | Rules |
| --- | --- | --- |
| `intensity` | float | Must be between `1.0` and `10.0`, inclusive |
| `trigger` | string | Must not be empty |
| `affect` | string | Must not be empty |

### Optional fields

| Field | Type | Empty or omitted value |
| --- | --- | --- |
| `loop` | string | Stored as `??` |
| `need` | string | Stored as `??` |
| `tension` | string | Stored as `??` |
| `facts` | semicolon-separated key/value pairs | Stored as `{}` |
| `edges` | comma-separated strings | Stored as `[]` |
| `summary` | string | Stored as an empty string |

Example input:

```text
intensity: 7
trigger: parsing_logic_flaw
affect: trapped
loop: validation_spiral
need: clarity
tension: defensive_code vs readable_validation
facts: code_smell=defensive_pattern; context=stressed
edges: parser, validation
summary: The validation boundary needs to remain explicit.
```

## Persisted Node Contract

Each ingested node is written as a Markdown file with YAML frontmatter containing:

```yaml
node_id: string
timestamp: string
intensity: float
trigger: string
primary_affect: string
cognitive_loop: string
underlying_need: string
latent_tension: string
facts: object
edges: list
```

## Input-to-Storage Names

The parser accepts concise input names and the writer uses descriptive storage names:

| Input | Stored frontmatter |
| --- | --- |
| `affect` | `primary_affect` |
| `need` | `underlying_need` |
| `tension` | `latent_tension` |

## Validation Guarantees

- Invalid intensity values raise `ValueError`.
- Missing required fields raise `ValueError`.
- Lines without a `key: value` separator raise `ValueError`.
- Optional string fields receive `??` when omitted or blank.
- Facts are stored as a string-to-string object.
- Edges are stored as a de-duplicated list of strings.
- Phase 1 performs no embeddings, vector search, or LLM inference.