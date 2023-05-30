import unittest

from datetime import datetime, timezone

def last_modified_from_statements(statements: list) -> datetime:

    latest_stored = datetime.min.replace(tzinfo=timezone.utc)
    for stmt in statements:
        stored = datetime.fromisoformat(stmt['stored'])
        if stored.astimezone(timezone.utc) > latest_stored.astimezone(timezone.utc):
            latest_stored = stored

    return latest_stored

class TestUtilityMethods(unittest.TestCase):

    def test_last_modified_helper(self):

        expected_time = datetime.utcnow()
        expected_time_str = expected_time.isoformat()

        statements = [
            { "stored": expected_time_str },
            { "stored": expected_time_str }
        ]

        last_modified = last_modified_from_statements(statements)

        self.assertTrue(expected_time == last_modified)


if __name__=="__main__":
    unittest.main()