from datetime import datetime, timezone
import time


class DateHelper:
    """Collection of datetime utility methods."""

    @staticmethod
    def date_to_unix(day: int, month: int, year: int) -> int:
        """Convert a date to a Unix timestamp (UTC)."""
        dt = datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
        return int(dt.timestamp())

    @staticmethod
    def unix_to_date(unix_time: float) -> datetime:
        """Convert a Unix timestamp to a datetime (UTC)."""
        return datetime.fromtimestamp(unix_time, tz=timezone.utc)

    @staticmethod
    def local_to_utc(dt: datetime) -> datetime:
        """Convert local datetime to UTC datetime."""
        return dt.astimezone(timezone.utc)

    @staticmethod
    def utc_to_local(dt: datetime) -> datetime:
        """Convert UTC datetime to local datetime."""
        return dt.astimezone()

    @staticmethod
    def seconds_since_last_contact(last_contact: float) -> int:
        """Return seconds since the given Unix timestamp."""
        return int(time.time() - last_contact)

    @staticmethod
    def age(unix_timestamp: float) -> int:
        """Calculate age in years from a Unix timestamp (UTC)."""
        birthday = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
        today = datetime.now(timezone.utc)
        years = today.year - birthday.year
        if (today.month, today.day) < (birthday.month, birthday.day):
            years -= 1
        return years

    @staticmethod
    def sec_to_ydhms(seconds: int) -> str:
        """Convert seconds to 'y d h m s' format."""
        years, rem = divmod(seconds, 31536000)
        days, rem = divmod(rem, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, rem = divmod(rem, 60)
        seconds = rem
        parts = []
        if years:   parts.append(f"{years}y")
        if days:    parts.append(f"{days}d")
        if hours:   parts.append(f"{hours}h")
        if minutes: parts.append(f"{minutes}m")
        if seconds: parts.append(f"{seconds}s")
        return "".join(parts) or "0s"
