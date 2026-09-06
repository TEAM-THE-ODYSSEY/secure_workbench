"""
Metadata filter builder for enforcing domain and document attributes criteria during search queries.
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FilterCondition(BaseModel):
    """Encapsulates filter conditions for retrieval queries."""
    department: Optional[str] = None
    plant: Optional[str] = None
    unit: Optional[str] = None
    equipment_id: Optional[str] = None
    document_type: Optional[str] = None
    revision: Optional[str] = None
    status: Optional[str] = "ACTIVE"
    access_level: Optional[str] = None
    extra_filters: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert filter condition into clean dictionary."""
        d = {
            "department": self.department,
            "plant": self.plant,
            "unit": self.unit,
            "equipment_id": self.equipment_id,
            "document_type": self.document_type,
            "revision": self.revision,
            "status": self.status,
            "access_level": self.access_level,
        }
        d.update(self.extra_filters)
        return {k: v for k, v in d.items() if v is not None}


class MetadataFilter:
    """Validator and evaluator for metadata filter constraints."""

    @staticmethod
    def match(metadata: Dict[str, Any], filter_condition: FilterCondition) -> bool:
        """Check if target metadata dictionary satisfies the filter_condition."""
        filters = filter_condition.to_dict()
        if not filters:
            return True

        for k, expected in filters.items():
            actual = metadata.get(k)
            if actual is None:
                continue
            
            if isinstance(expected, str) and isinstance(actual, str):
                if expected.lower() != actual.lower():
                    return False
            elif actual != expected:
                return False

        return True
