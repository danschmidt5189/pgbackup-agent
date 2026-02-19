"""Tests for pgbackup.storage."""

from unittest.mock import MagicMock, patch

from pgbackup.storage import upload_to_s3


class TestUploadToS3:
    """S3 upload tests with mocked boto3."""

    def test_upload_returns_uri(self, tmp_path):
        dump = tmp_path / "db.dump"
        dump.write_text("data")

        mock_client = MagicMock()
        with patch(
            "pgbackup.storage.boto3.client",
            return_value=mock_client,
        ):
            uri = upload_to_s3(
                str(dump), "mybucket", "path/db.dump"
            )

        assert uri == "s3://mybucket/path/db.dump"
        mock_client.upload_file.assert_called_once_with(
            str(dump), "mybucket", "path/db.dump"
        )

    def test_custom_endpoint(self, tmp_path):
        dump = tmp_path / "db.dump"
        dump.write_text("data")

        mock_client = MagicMock()
        with patch(
            "pgbackup.storage.boto3.client",
            return_value=mock_client,
        ) as mock_boto:
            upload_to_s3(
                str(dump),
                "mybucket",
                "key",
                endpoint_url="http://minio:9000",
            )

        mock_boto.assert_called_once_with(
            "s3", endpoint_url="http://minio:9000"
        )

    def test_no_endpoint(self, tmp_path):
        dump = tmp_path / "db.dump"
        dump.write_text("data")

        mock_client = MagicMock()
        with patch(
            "pgbackup.storage.boto3.client",
            return_value=mock_client,
        ) as mock_boto:
            upload_to_s3(str(dump), "mybucket", "key")

        mock_boto.assert_called_once_with("s3")
