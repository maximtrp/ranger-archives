import unittest
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import archives_utils
from archives_utils import ArchiveCompressor, ArchiveDecompressor


class CommandBuilderTests(unittest.TestCase):
    def setUp(self):
        available = {"7zz", "ar", "bzip3", "gzip", "tar", "unzip", "xz", "zip"}
        self.which = patch.object(
            archives_utils,
            "which",
            side_effect=lambda command: (
                f"/tools/{command}" if command in available else None
            ),
        )
        self.which.start()

    def tearDown(self):
        self.which.stop()

    def test_arguments_are_parsed_without_literal_shell_quotes(self):
        self.assertEqual(
            archives_utils.parse_escape_args('-9 "value with spaces"'),
            ["-9", "value with spaces"],
        )

    def test_single_file_compression_uses_safe_worker_redirection(self):
        command = ArchiveCompressor.get_command("output.gz", [], ["file's name.txt"])
        self.assertEqual(command[2:5], ["--stdout", "output.gz", "--"])
        self.assertEqual(command[-3:], ["/tools/gzip", "-c", "file's name.txt"])
        self.assertNotIn("sh", command)

    def test_option_like_single_filename_is_protected(self):
        command = ArchiveCompressor.get_command("output.gz", [], ["-input"])
        self.assertEqual(command[-1], "./-input")

    def test_option_like_zip_filename_is_protected(self):
        command = ArchiveCompressor.get_command("output.zip", [], ["-input"])
        self.assertEqual(command[-1], "./-input")

    def test_option_like_tar_filename_is_protected(self):
        command = ArchiveCompressor.get_command("output.tar.gz", [], ["-input"])
        self.assertEqual(command[-2:], ["--", "./-input"])

    def test_option_like_tar_archive_name_is_protected(self):
        command = ArchiveCompressor.get_command("-output.tar.gz", [], ["input"])
        self.assertIn("./-output.tar.gz", command)

    def test_option_like_archive_is_protected_during_extraction(self):
        command = ArchiveDecompressor.get_command("-archive.zip", [], None)
        self.assertIn("./-archive.zip", command)
        self.assertNotIn("-archive.zip", command)

    def test_option_like_compressed_tar_is_protected_during_extraction(self):
        command = ArchiveDecompressor.get_command("-archive.tar.gz", [], None)
        self.assertIn("./-archive.tar.gz", command)
        self.assertNotIn("-archive.tar.gz", command)

    def test_single_file_extraction_honors_output_directory(self):
        command = ArchiveDecompressor.get_command(
            "/archives/file.gz", [], "/output directory"
        )
        self.assertEqual(command[2:5], ["--stdout", "/output directory/file", "--"])
        self.assertEqual(command[-3:], ["/tools/gzip", "-dc", "/archives/file.gz"])

    def test_tar_lzma_is_recognized_as_tar_archive(self):
        format_name, _ = archives_utils.find_archive_format("archive.tar.lzma")
        self.assertEqual(format_name, "tar_xz")

    def test_multiple_lzma_inputs_use_tar_lzma_name_once(self):
        command = ArchiveCompressor.get_command("archive.lzma", [], ["one", "two"])
        self.assertIn("archive.tar.lzma", command)
        self.assertNotIn("archive.tar.tar.lzma", command)

    def test_unknown_format_does_not_silently_become_zip(self):
        self.assertEqual(
            ArchiveCompressor.get_command("archive.unknown", [], ["file"]), []
        )

    def test_7zz_is_supported(self):
        command = ArchiveCompressor.get_command("archive.7z", [], ["file"])
        self.assertEqual(command[0], "/tools/7zz")

    def test_missing_extraction_tools_returns_no_command(self):
        with patch.object(archives_utils, "which", return_value=None):
            self.assertEqual(
                ArchiveDecompressor.get_command("archive.zip", [], None), []
            )

    def test_missing_compression_tools_returns_no_command(self):
        with patch.object(archives_utils, "which", return_value=None):
            self.assertEqual(
                ArchiveCompressor.get_command("archive.zip", [], ["file"]), []
            )

    def test_deb_destination_runs_ar_in_requested_directory(self):
        command = ArchiveDecompressor.get_command(
            "/archives/package.deb", [], "/output"
        )
        self.assertEqual(command[2:5], ["--cwd", "/output", "--"])
        self.assertEqual(command[-3:], ["/tools/ar", "-x", "/archives/package.deb"])

    def test_zip_destination_is_created_by_worker_not_builder(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "new directory"
            command = ArchiveDecompressor.get_command(
                "/archives/archive.zip", [], str(destination)
            )
            self.assertFalse(destination.exists())
            self.assertEqual(command[2:5], ["--mkdir", str(destination), "--"])

    def test_pipe_extraction_preserves_user_flags(self):
        command = ArchiveDecompressor.get_command(
            "/archives/archive.tar.bz3", ["--warning=no-unknown-keyword"], "/output"
        )
        self.assertIn("--warning=no-unknown-keyword", command)


class WorkerTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("gzip"), "gzip is not installed")
    def test_single_file_round_trip_with_apostrophe_and_destination(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "file's name.txt"
            archive = root / "output.gz"
            destination = root / "extracted"
            source.write_text("archive contents", encoding="utf-8")

            compression = ArchiveCompressor.get_command(str(archive), [], [source.name])
            self.assertEqual(subprocess.run(compression, cwd=root).returncode, 0)

            extraction = ArchiveDecompressor.get_command(
                str(archive), [], str(destination)
            )
            self.assertEqual(subprocess.run(extraction, cwd=root).returncode, 0)
            self.assertEqual(
                (destination / "output").read_text(encoding="utf-8"),
                "archive contents",
            )

    def test_mkdir_mode_executes_the_wrapped_command(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "created"
            marker = Path(temporary_directory) / "marker"
            worker = Path(archives_utils.__file__).with_name("archive_worker.py")
            result = subprocess.run(
                [
                    sys.executable,
                    str(worker),
                    "--mkdir",
                    str(destination),
                    "--",
                    sys.executable,
                    "-c",
                    f"from pathlib import Path; Path({str(marker)!r}).touch()",
                ]
            )
            self.assertEqual(result.returncode, 0)
            self.assertTrue(destination.is_dir())
            self.assertTrue(marker.is_file())

    def test_failed_redirection_removes_partial_archive(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "partial.gz"
            worker = Path(archives_utils.__file__).with_name("archive_worker.py")
            result = subprocess.run(
                [
                    sys.executable,
                    str(worker),
                    "--stdout",
                    str(output),
                    "--",
                    sys.executable,
                    "-c",
                    "import sys; print('partial'); sys.exit(7)",
                ]
            )
            self.assertEqual(result.returncode, 7)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
