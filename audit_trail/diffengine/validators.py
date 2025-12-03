from __future__ import annotations

from typing import Any, Dict


class DiffValidationError(ValueError):
    pass


def _is_list_of_dicts(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, dict) for item in value)


def validate_diff(diff: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(diff, dict):
        raise DiffValidationError("diff must be a dict")
    for field, change in diff.items():
        if not isinstance(change, dict):
            raise DiffValidationError(f"Invalid diff entry for {field}")
        relation = change.get("relation", "field")
        if relation == "many_to_many":
            added = change.get("added", [])
            removed = change.get("removed", [])
            if not _is_list_of_dicts(added) or not _is_list_of_dicts(removed):
                raise DiffValidationError(
                    f"Invalid many-to-many diff entry for {field}"
                )
        else:
            if "before" not in change or "after" not in change:
                raise DiffValidationError(f"Missing before/after for {field}")
    return diff
