import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from homeassistant.util import dt as dt_util
import logging

_LOGGER = logging.getLogger(__name__)

def slugify(value: str) -> str:
    """Simplified slugify function for entity_id creation."""
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[\s\-]+", "_", value)  # Substitui espaços e traços por underscore único
    return value

def _safe_parse_dt(value: Any, *, assume_tz: timezone = timezone.utc) -> Optional[datetime]:
    """Safely parse a datetime from storage.
    Accepts None, str (ISO8601), or datetime. Returns tz-aware datetime or None.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=assume_tz)
        return value

    if isinstance(value, str) and value.strip():
        try:
            dt = dt_util.parse_datetime(value)
            if dt is None:
                dt = datetime.fromisoformat(value)
            if dt and dt.tzinfo is None:
                dt = dt.replace(tzinfo=assume_tz)
            return dt
        except Exception as err:
            _LOGGER.debug("Failed to parse datetime from '%s': %s", value, err)

    return None