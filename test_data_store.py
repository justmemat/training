"""Tests for the feature-based JSON storage layer."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import data_store


class DataStoreTests(unittest.TestCase):
    def test_initializes_separate_files_and_round_trips_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(data_store, "DATA_DIRECTORY", Path(directory)):
                data_store.initialize_data_files()

                self.assertEqual(
                    {path.name for path in Path(directory).iterdir()},
                    set(data_store.DATA_FILES.values()),
                )
                records = [{"name": "Example Team Member"}]
                data_store.save_records("team_members", records)
                self.assertEqual(data_store.load_records("team_members"), records)

    def test_unknown_feature_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown data feature"):
            data_store.load_records("unknown")


if __name__ == "__main__":
    unittest.main()
