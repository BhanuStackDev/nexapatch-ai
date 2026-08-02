# Autonomous AI Coding Agent Framework

An advanced, multi-node autonomous AI coding agent designed to parse, plan, and automatically modify legacy codebases based on unguided user intents.

## 🏛️ System Architecture & Workflow
The core infrastructure leverages **FastAPI** to bind reactive network layer endpoints and uses **LangGraph** to construct a deterministic conditional state-machine graph.

1. **Exploration Phase (`repo_explorer_node`)**: The system automatically crawls the targeted directory recursively, explicitly filtering out dependency trees to build a clean index of operational source code files.
2. **Strategic Planning Phase (`execution_planner_node`)**: Feeds the mapped directory matrix into Groq's high-speed inferencing engine via a custom structured prompt using the `gemma2-9b-it` model to generate a strict code-modification plan.
3. **Injection Phase (`codebase_modifier_node`)**: Executes targeted file system modifications—appending explicit string arrays for tags inside data layers and appending regex parameters inside query parameters.

## 🛠️ Assumptions & Trade-offs
- **Isolated Target Traversal**: Assumes structural conventions of Express/Mongoose controllers are mapped within standard configurations.
- **Safety Fallback Overwrite**: Instead of corrupting production code via structural rewrites, the system updates parameters sequentially, preserving runtime integrity.
