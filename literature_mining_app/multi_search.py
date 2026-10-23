"""Sequential search runner; credentials and partial failed batches are excluded."""

from collections.abc import Callable

import pandas as pd

import providers
from schema import COLUMNS

EXPORT_COLUMNS = COLUMNS + ["standard_query", "executed_query"]


def run_searches(
    queries: dict[str, str],
    standard_query: str,
    credentials: dict[str, dict],
    max_results: int | None,
    on_event: Callable[[dict], None] | None = None,
) -> tuple[pd.DataFrame, list[dict]]:
    if not queries:
        raise ValueError("Select at least one database.")
    if any(database not in providers.MULTI_DATABASES for database in queries):
        raise ValueError("A selected database does not support standard Boolean mode.")
    if max_results is not None and max_results < 1:
        raise ValueError("The article limit must be at least 1.")
    selected = [database for database in providers.MULTI_DATABASES if database in queries]
    for database in selected:
        if not queries[database].strip():
            raise ValueError(f"The translated query for {database} is empty.")
        providers.validate_credentials(database, credentials.get(database, {}))

    frames, summaries = [], []
    for index, database in enumerate(selected):
        def emit(status, fetched=0, total=0, message="", completed=index):
            event = {
                "database": database, "status": status, "fetched": fetched,
                "total": total, "message": message, "completed": completed,
            }
            if on_event:
                on_event(event)
            return event

        emit("Running")
        try:
            frame, total = providers.search(
                database, queries[database], credentials.get(database, {}), max_results,
                lambda fetched, total: emit("Running", fetched, total),
            )
            frame = frame.reindex(columns=COLUMNS).copy()
            frame["source_database"] = database
            frame["standard_query"] = standard_query
            frame["executed_query"] = queries[database]
            frames.append(frame)
            limited = max_results is not None and len(frame) >= max_results and len(frame) < total
            status = "Limited" if limited else "Completed"
            message = "Article limit reached." if limited else ""
            if not limited and len(frame) < total:
                message = "Reported count may be estimated or may have changed during retrieval."
            summaries.append(emit(status, len(frame), total, message, index + 1))
        except Exception as exc:
            # Isolate each source, including unexpected response parsing errors.
            summaries.append(emit("Failed", message=providers.error_message(database, exc), completed=index + 1))
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=EXPORT_COLUMNS)
    return combined.reindex(columns=EXPORT_COLUMNS), summaries
