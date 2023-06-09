import re, math, unicodedata

from datetime import datetime, timezone

def truncate_duration(duration):
    sec_split = re.findall(r"\d+(?:\.\d+)?S", duration)
    if sec_split:
        seconds_str = sec_split[0]
        seconds = float(seconds_str.replace('S', ''))

        if not seconds.is_integer():
            ### xAPI 2.0: Truncation required for comparison, not rounding etc.
            # sec_trunc = round(sec_as_num, 2)
            seconds_truncated = math.floor(seconds * 100) / 100
        else:
            seconds_truncated = int(seconds)

        return unicodedata.normalize("NFKD", duration.replace(seconds_str, str(seconds_truncated) + 'S'))
    else:
        return duration

def last_modified_from_statements(statements: list) -> datetime:

    latest_stored = datetime.min.replace(tzinfo=timezone.utc)
    for stmt in statements:
        stored = datetime.fromisoformat(stmt['stored'])
        if stored.astimezone(timezone.utc) > latest_stored.astimezone(timezone.utc):
            latest_stored = stored

    return latest_stored