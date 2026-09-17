"""
Sibyl-Memory provider adapter for Hermes Agent.

Wraps sibyl_memory_hermes.SibylMemoryProvider to match the MemoryProvider ABC.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.memory_provider import MemoryProvider, RecallStatus

logger = logging.getLogger(__name__)


class SibylMemoryProvider(MemoryProvider):
    """Hermes Agent memory provider backed by Sibyl-Memory (local SQLite, zero deps)."""

    name = "sibyl"

    def __init__(self) -> None:
        self._provider = None
        self._session_id = ""
        self._last_prefetch_result = ""
        self._last_prefetch_count = 0

    def is_available(self) -> bool:
        """Check if sibyl-memory-hermes is installed and DB is accessible."""
        try:
            import sibyl_memory_hermes
            from sibyl_memory_hermes import SibylMemoryProvider as SibylProvider
            provider = SibylProvider()
            self._provider = provider
            return True
        except Exception as e:
            logger.debug(f"Sibyl provider not available: {e}")
            return False

    def unavailable_reason(self) -> str:
        """Return user-facing reason why provider is unavailable."""
        try:
            import sibyl_memory_hermes
        except ImportError:
            return "sibyl-memory-hermes package not installed. Run: uv pip install sibyl-memory-hermes"
        try:
            from sibyl_memory_hermes import SibylMemoryProvider as SibylProvider
            SibylProvider()
            return ""
        except Exception as e:
            return f"Sibyl DB not accessible: {e}"

    def initialize(self, session_id: str, **kwargs) -> None:
        """Initialize the provider for a session."""
        self._session_id = session_id
        if self._provider is None:
            try:
                from sibyl_memory_hermes import SibylMemoryProvider as SibylProvider
                db_path = kwargs.get("db_path")
                if db_path:
                    self._provider = SibylProvider(db_path=db_path)
                else:
                    self._provider = SibylProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize Sibyl provider: {e}")
                self._provider = None

    def system_prompt_block(self) -> str:
        """Static system prompt text for Sibyl memory."""
        return (
            "\n[Sibyl Memory: Active - persistent local memory with FTS5 search across "
            "entities, state docs, references, and journal. Use memory tools to recall, "
            "remember, search, and manage long-term facts.]\n"
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Retrieve relevant memories for the upcoming turn."""
        if not self._provider or not query or query.strip() == "":
            self._last_prefetch_result = ""
            self._last_prefetch_count = 0
            return ""

        try:
            results = self._provider.search(query, limit=10)
            if not results:
                self._last_prefetch_result = ""
                self._last_prefetch_count = 0
                return ""

            parts = ["[Sibyl Recall]"]
            for hit in results:
                tier = hit.get("tier", "unknown")
                key = hit.get("key", "")
                body = hit.get("body", {})
                snippet = hit.get("snippet", "")

                if tier == "entity":
                    category = hit.get("category", "")
                    parts.append(f"  - entity/{category}/{key}: {snippet}")
                elif tier == "state":
                    parts.append(f"  - state/{key}: {snippet}")
                elif tier == "reference":
                    parts.append(f"  - ref/{key}: {snippet}")
                elif tier == "journal":
                    parts.append(f"  - journal/{key}: {snippet}")

            self._last_prefetch_result = "\n".join(parts)
            self._last_prefetch_count = len(results)
            return self._last_prefetch_result

        except Exception as e:
            logger.debug(f"Sibyl prefetch failed: {e}")
            self._last_prefetch_result = ""
            self._last_prefetch_count = 0
            return ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Queue a background recall - no-op for Sibyl (sync prefetch is fast)."""
        pass

    def recall_status(self) -> Optional[RecallStatus]:
        """Return status of last prefetch for the recall indicator."""
        if self._last_prefetch_count > 0:
            return RecallStatus(provider_label="sibyl", count=self._last_prefetch_count)
        return None

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Persist a completed turn to the journal."""
        if not self._provider:
            return
        try:
            self._provider.save_context(
                inputs={"user": user_content},
                outputs={"assistant": assistant_content},
            )
        except Exception as e:
            logger.debug(f"Sibyl sync_turn failed: {e}")

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return OpenAI function schemas for Sibyl memory tools."""
        return [
            {
                "name": "sibyl_remember",
                "description": "Store a fact/entity in long-term memory. Use for preferences, decisions, project details, user info, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Category namespace (e.g., \'persona\', \'user\', \'project\', \'preferences\', \'coding\')"
                        },
                        "name": {
                            "type": "string",
                            "description": "Unique name within category (e.g., \'core\', \'profile\', \'voice\', \'database_choice\')"
                        },
                        "body": {
                            "type": "object",
                            "description": "JSON payload to store (dict or list). Primitive values are wrapped as {\'value\': ...}."
                        },
                        "status": {
                            "type": "string",
                            "description": "Optional status tag (e.g., \'active\', \'archived\', \'deprecated\')",
                            "default": "active"
                        }
                    },
                    "required": ["category", "name", "body"]
                }
            },
            {
                "name": "sibyl_recall",
                "description": "Retrieve a single entity by category and name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Category namespace"},
                        "name": {"type": "string", "description": "Entity name within category"}
                    },
                    "required": ["category", "name"]
                }
            },
            {
                "name": "sibyl_search",
                "description": "Full-text search across all memory tiers (entities, state, references, journal). Returns ranked snippets.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query (FTS5 phrase)"},
                        "limit": {"type": "integer", "description": "Max results", "default": 10},
                        "tiers": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Restrict to tiers: \'entity\', \'state\', \'reference\', \'journal\'"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "sibyl_list",
                "description": "List entities in a category, optionally filtered by status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Category to list (optional: all categories)"},
                        "status": {"type": "string", "description": "Filter by status"},
                        "limit": {"type": "integer", "description": "Max results", "default": 50}
                    }
                }
            },
            {
                "name": "sibyl_forget",
                "description": "Delete an entity. Returns true if deleted, false if not found.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Category namespace"},
                        "name": {"type": "string", "description": "Entity name"}
                    },
                    "required": ["category", "name"]
                }
            },
            {
                "name": "sibyl_set_state",
                "description": "Set a state-tier document (hot, single-current-value per key).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "State key"},
                        "body": {"type": "object", "description": "JSON payload (dict or list)"}
                    },
                    "required": ["key", "body"]
                }
            },
            {
                "name": "sibyl_get_state",
                "description": "Get a state-tier document.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "State key"}
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "sibyl_set_reference",
                "description": "Set a reference-tier document (immortal knowledge: markdown, notes, runbooks).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Reference key"},
                        "body": {"type": "string", "description": "Markdown/text content"},
                        "metadata": {"type": "object", "description": "Optional structured metadata"}
                    },
                    "required": ["key", "body"]
                }
            },
            {
                "name": "sibyl_get_reference",
                "description": "Get a reference-tier document.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Reference key"}
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "sibyl_health",
                "description": "Check Sibyl memory health (DB size, schema version, tenant).",
                "parameters": {"type": "object", "properties": {}}
            }
        ]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """Handle Sibyl memory tool calls."""
        if not self._provider:
            return '{"error": "Sibyl provider not initialized"}'

        import json

        try:
            if tool_name == "sibyl_remember":
                category = args["category"]
                name = args["name"]
                body = args["body"]
                status = args.get("status", "active")
                result = self._provider.remember(category, name, body, status=status)
                return json.dumps({"ok": True, "entity": result})

            elif tool_name == "sibyl_recall":
                category = args["category"]
                name = args["name"]
                result = self._provider.recall(category, name)
                if result:
                    return json.dumps({"ok": True, "entity": result})
                return json.dumps({"ok": False, "error": "Not found"})

            elif tool_name == "sibyl_search":
                query = args["query"]
                limit = args.get("limit", 10)
                tiers = tuple(args["tiers"]) if args.get("tiers") else None
                results = self._provider.search(query, limit=limit, tiers=tiers)
                return json.dumps({"ok": True, "results": list(results), "count": len(results)})

            elif tool_name == "sibyl_list":
                category = args.get("category")
                status = args.get("status")
                limit = args.get("limit", 50)
                results = self._provider.list(category=category, status=status, limit=limit)
                return json.dumps({"ok": True, "entities": results, "count": len(results)})

            elif tool_name == "sibyl_forget":
                category = args["category"]
                name = args["name"]
                deleted = self._provider.forget(category, name)
                return json.dumps({"ok": True, "deleted": deleted})

            elif tool_name == "sibyl_set_state":
                key = args["key"]
                body = args["body"]
                self._provider.set_state(key, body)
                return json.dumps({"ok": True})

            elif tool_name == "sibyl_get_state":
                key = args["key"]
                result = self._provider.get_state(key)
                if result:
                    return json.dumps({"ok": True, "state": result})
                return json.dumps({"ok": False, "error": "Not found"})

            elif tool_name == "sibyl_set_reference":
                key = args["key"]
                body = args["body"]
                metadata = args.get("metadata")
                self._provider.set_reference(key, body, metadata=metadata)
                return json.dumps({"ok": True})

            elif tool_name == "sibyl_get_reference":
                key = args["key"]
                result = self._provider.get_reference(key)
                if result:
                    return json.dumps({"ok": True, "reference": result})
                return json.dumps({"ok": False, "error": "Not found"})

            elif tool_name == "sibyl_health":
                health = self._provider.health()
                return json.dumps({"ok": True, "health": health})

            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})

        except Exception as e:
            logger.exception(f"Sibyl tool {tool_name} failed")
            return json.dumps({"error": str(e)})

    def shutdown(self) -> None:
        """Clean shutdown."""
        self._provider = None

    def get_config_schema(self) -> List[Dict[str, Any]]:
        """Setup fields for `hermes memory setup`."""
        return [
            {
                "key": "db_path",
                "description": "Path to SQLite database (default: ~/.sibyl-memory/memory.db)",
                "type": "text",
                "default": "~/.sibyl-memory/memory.db",
                "required": False
            },
            {
                "key": "tenant_id",
                "description": "Optional tenant override (default: from credentials or DEFAULT_TENANT)",
                "type": "text",
                "required": False
            }
        ]

    def save_config(self, values: Dict[str, Any], MIKASA_HOME: str) -> None:
        """Write config to native sibyl-memory config."""
        import json
        from sibyl_memory_hermes import DEFAULT_DB_PATH, DEFAULT_CRED_PATH

        config = {}
        if "db_path" in values and values["db_path"]:
            config["db_path"] = values["db_path"]
        if "tenant_id" in values and values["tenant_id"]:
            config["tenant_id"] = values["tenant_id"]

        config_dir = Path(DEFAULT_DB_PATH).parent
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

    def backup_paths(self) -> List[str]:
        """Paths to include in `hermes backup`."""
        from sibyl_memory_hermes import DEFAULT_DB_PATH, DEFAULT_CRED_PATH
        paths = []
        if Path(DEFAULT_DB_PATH).exists():
            paths.append(str(DEFAULT_DB_PATH))
        if Path(DEFAULT_CRED_PATH).exists():
            paths.append(str(DEFAULT_CRED_PATH))
        return paths

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """End-of-session hook - could extract facts here."""
        pass

    def on_memory_write(self, action: str, target: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Mirror built-in memory tool writes to Sibyl."""
        if not self._provider:
            return
        try:
            if target == "memory":
                self._provider.remember("memory", f"entry_{action}", {"text": content, "action": action})
            elif target == "user":
                self._provider.remember("user", f"profile_{action}", {"text": content, "action": action})
        except Exception as e:
            logger.debug(f"Sibyl on_memory_write failed: {e}")


def register(ctx) -> None:
    """Plugin entry point: register the Sibyl memory provider."""
    ctx.register_memory_provider(SibylMemoryProvider())
