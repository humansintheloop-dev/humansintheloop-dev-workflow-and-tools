import pytest

from i2code.idea.metadata import read_metadata, write_metadata


@pytest.mark.unit
class TestReadMetadata:
    def test_reads_valid_metadata_file(self, tmp_path):
        metadata_file = tmp_path / "test-metadata.yaml"
        metadata_file.write_text("state: draft\n")

        result = read_metadata(metadata_file)

        assert result == {"state": "draft"}

    def test_missing_file_raises_file_not_found_error(self, tmp_path):
        missing = tmp_path / "nonexistent-metadata.yaml"

        with pytest.raises(FileNotFoundError):
            read_metadata(missing)


@pytest.mark.unit
class TestWriteMetadata:
    def test_write_then_read_round_trips(self, tmp_path):
        metadata_file = tmp_path / "test-metadata.yaml"
        data = {"state": "ready"}

        write_metadata(metadata_file, data)
        result = read_metadata(metadata_file)

        assert result == {"state": "ready"}

    def test_preserves_unknown_keys_on_write(self, tmp_path):
        metadata_file = tmp_path / "test-metadata.yaml"
        metadata_file.write_text("state: draft\ncustom_field: hello\n")

        data = read_metadata(metadata_file)
        data["state"] = "ready"
        write_metadata(metadata_file, data)

        result = read_metadata(metadata_file)
        assert result["state"] == "ready"
        assert result["custom_field"] == "hello"
