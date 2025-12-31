from datetime import datetime
import pytz

BERLIN_TZ = pytz.timezone('Europe/Berlin')

def to_berlin(dt: datetime) -> datetime:
    """Convert a naive or UTC datetime to Berlin timezone-aware datetime.
    If naive, assume it's already Berlin local time.
    """
    if dt.tzinfo is None:
        # Treat naive datetime as Berlin local time
        return BERLIN_TZ.localize(dt)
    return dt.astimezone(BERLIN_TZ)


def now_berlin() -> datetime:
    """Get current time in Berlin timezone."""
    return datetime.now(pytz.UTC).astimezone(BERLIN_TZ)
