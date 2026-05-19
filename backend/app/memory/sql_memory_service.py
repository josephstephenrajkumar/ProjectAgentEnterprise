"""
SQL Memory Service — manages SqlQueryMemory and QueryFeedback tables.

Implements the learning layer from SQL_LEARNING_LAYER.md:
- Lookup: find high-confidence SQL templates before dynamic generation.
- Record: store query success/failure for reinforcement learning.
"""
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from app.config.settings import get_settings

settings = get_settings()


def lookup_template(query: str) -> Optional[dict]:
    """Search SqlQueryMemory for a reusable SQL template matching the query intent.

    Returns dict with keys: sql_template, confidence_score, intent_name
    or None if no match found.
    """
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()

        # Check QueryFeedback (legacy reinforcement cache)
        cursor.execute(
            "SELECT user_query, generated_sql FROM QueryFeedback "
            "WHERE feedback_score > 0 ORDER BY feedback_score DESC"
        )
        rows = cursor.fetchall()

        words = set(query.lower().split())
        for q_text, sql_text in rows:
            past_words = set(q_text.lower().split())
            intersection = words.intersection(past_words)
            if len(intersection) / max(len(words), 1) > 0.7:
                conn.close()
                return {
                    "sql_template": sql_text,
                    "confidence_score": len(intersection) / len(words),
                    "intent_name": "query_feedback_match",
                    "past_query": q_text,
                }

        # Check SqlQueryMemory (new structured memory)
        cursor.execute(
            "SELECT intent_name, sql_template, confidence_score "
            "FROM SqlQueryMemory WHERE confidence_score > 0.5 "
            "ORDER BY confidence_score DESC"
        )
        for intent_name, sql_template, confidence in cursor.fetchall():
            # Simple keyword overlap check for now
            template_words = set(intent_name.lower().split())
            overlap = words.intersection(template_words)
            if len(overlap) / max(len(words), 1) > 0.5:
                conn.close()
                return {
                    "sql_template": sql_template,
                    "confidence_score": confidence,
                    "intent_name": intent_name,
                }

        conn.close()
    except Exception:
        pass
    return None


def record_result(
    user_query: str,
    generated_sql: str,
    score: int,
    intent_name: str = "auto",
) -> None:
    """Record a query success/failure in QueryFeedback for reinforcement learning."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM QueryFeedback WHERE generated_sql = ?",
            (generated_sql,),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                "UPDATE QueryFeedback SET feedback_score = feedback_score + ?, last_used = ? WHERE id = ?",
                (score, datetime.utcnow().isoformat(), existing[0]),
            )
        else:
            cursor.execute(
                "INSERT INTO QueryFeedback (id, user_query, generated_sql, feedback_score, last_used) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    user_query,
                    generated_sql,
                    score,
                    datetime.utcnow().isoformat(),
                ),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Failed to record SQL feedback: {e}")


def get_semantic_glossary() -> str:
    """Fetch user-enhanced semantic mappings to guide the LLM."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT keyword, entity, attribute, filter_logic FROM SemanticMap"
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return ""

        glossary = "\nSEMANTIC GLOSSARY (Mapping user terms to DB schema):\n"
        for kw, ent, attr, filt in rows:
            logic = f" (Logic: {filt})" if filt else ""
            glossary += f"- '{kw}' -> Entity: {ent}, Attribute: {attr}{logic}\n"
        return glossary
    except Exception:
        return ""
