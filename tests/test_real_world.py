#!/usr/bin/env python3
"""
Real-world test scenarios for ranger-archives cross-platform compatibility
Tests actual compression and decompression with file integrity verification
"""

import sys
import os
import shutil
import tempfile
import hashlib
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict
import time

# Add parent directory to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from archives_utils import (
    ArchiveCompressor,
    ArchiveDecompressor,
)


class ArchiveTestRunner:
    def __init__(self):
        self.test_results = []
        self.temp_dirs = []
        self.results_dir = Path("test_results")
        self.results_dir.mkdir(exist_ok=True)

    def cleanup(self):
        """Clean up temporary directories"""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_directory_hashes(self, directory: Path) -> Dict[str, str]:
        """Get hashes of all files in a directory"""
        hashes = {}
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(directory)
                hashes[str(rel_path)] = self.get_file_hash(file_path)
        return hashes

    def run_command(
        self, command: List[str], cwd: Path = None
    ) -> Tuple[bool, str, str]:
        """Run a command and return success, stdout, stderr"""
        try:
            result = subprocess.run(command, cwd=cwd, capture_output=True, timeout=300)

            # Handle encoding with fallback chain
            for encoding in ["utf-8", "latin-1"]:
                try:
                    stdout = result.stdout.decode(encoding)
                    stderr = result.stderr.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                stdout = result.stdout.decode("utf-8", errors="ignore")
                stderr = result.stderr.decode("utf-8", errors="ignore")

            return result.returncode == 0, stdout, stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    def test_archive_format(
        self, archive_name: str, test_data_dir: Path, flags: List[str] = None
    ) -> Dict:
        """Test a specific archive format with compression and decompression"""
        if flags is None:
            flags = []

        test_result = {
            "archive_format": archive_name,
            "flags": flags,
            "success": False,
            "compression_time": 0,
            "decompression_time": 0,
            "original_size": 0,
            "compressed_size": 0,
            "compression_ratio": 0,
            "files_match": False,
            "error": None,
        }

        try:
            # Create temporary directories
            work_dir = Path(tempfile.mkdtemp(prefix="archive_test_"))
            extract_dir = work_dir / "extract"
            extract_dir.mkdir()
            self.temp_dirs.append(work_dir)

            # Copy test data to work directory
            test_copy = work_dir / "test_data"
            shutil.copytree(test_data_dir, test_copy)

            # Get original directory size and hashes
            original_hashes = self.get_directory_hashes(test_copy)
            original_size = sum(
                f.stat().st_size for f in test_copy.rglob("*") if f.is_file()
            )
            test_result["original_size"] = original_size

            # Get list of files to compress (relative paths)
            files_to_compress = [
                str(f.relative_to(test_copy))
                for f in test_copy.rglob("*")
                if f.is_file()
            ]

            # Test compression
            archive_path = work_dir / archive_name
            compression_command = ArchiveCompressor.get_command(
                str(archive_path), flags, files_to_compress
            )

            if not compression_command:
                test_result["error"] = (
                    f"No compression command generated for {archive_name}"
                )
                return test_result

            print(f"  Compressing with command: {' '.join(compression_command)}")

            start_time = time.time()
            success, stdout, stderr = self.run_command(
                compression_command, cwd=test_copy
            )
            compression_time = time.time() - start_time
            test_result["compression_time"] = compression_time

            if not success:
                test_result["error"] = f"Compression failed: {stderr}"
                return test_result

            # Handle cases where single-file compression creates different filename
            if not archive_path.exists():
                # Check for tar variants when expecting single-file compression
                potential_files = []
                if archive_name.endswith(".gz"):
                    potential_files.append(work_dir / archive_name.replace(".gz", ".tar.gz"))
                elif archive_name.endswith(".bz2"):
                    potential_files.append(work_dir / archive_name.replace(".bz2", ".tar.bz2"))
                elif archive_name.endswith(".xz"):
                    potential_files.append(work_dir / archive_name.replace(".xz", ".tar.xz"))
                elif archive_name.endswith(".lz4"):
                    potential_files.append(work_dir / archive_name.replace(".lz4", ".tar.lz4"))
                elif archive_name.endswith(".lrz"):
                    potential_files.append(work_dir / archive_name.replace(".lrz", ".tar.lrz"))
                elif archive_name.endswith(".lzop"):
                    potential_files.append(work_dir / archive_name.replace(".lzop", ".tar.lzop"))

                # Try to find and rename the created file
                for potential_file in potential_files:
                    if potential_file.exists():
                        potential_file.rename(archive_path)
                        break

                # Final check
                if not archive_path.exists():
                    test_result["error"] = f"Archive file not created: {archive_path}"
                    return test_result

            # Get compressed size
            compressed_size = archive_path.stat().st_size
            test_result["compressed_size"] = compressed_size
            test_result["compression_ratio"] = (
                (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            )

            # Test decompression
            decompression_command = ArchiveDecompressor.get_command(
                str(archive_path), [], str(extract_dir)
            )

            if not decompression_command:
                test_result["error"] = (
                    f"No decompression command generated for {archive_name}"
                )
                return test_result

            print(f"  Decompressing with command: {' '.join(decompression_command)}")

            start_time = time.time()
            success, stdout, stderr = self.run_command(decompression_command)
            decompression_time = time.time() - start_time
            test_result["decompression_time"] = decompression_time

            if not success:
                test_result["error"] = f"Decompression failed: {stderr}"
                return test_result

            # Verify file integrity
            extracted_hashes = self.get_directory_hashes(extract_dir)

            # Compare hashes
            files_match = True
            for file_path, original_hash in original_hashes.items():
                if file_path not in extracted_hashes:
                    files_match = False
                    test_result["error"] = f"Missing file after extraction: {file_path}"
                    break
                elif extracted_hashes[file_path] != original_hash:
                    files_match = False
                    test_result["error"] = f"Hash mismatch for {file_path}"
                    break

            test_result["files_match"] = files_match
            test_result["success"] = files_match

        except Exception as e:
            test_result["error"] = str(e)

        return test_result

    def create_test_data(self):
        """Create test data for archive testing"""
        print("📁 Creating test data...")

        test_data_dir = Path("test_data")
        if test_data_dir.exists():
            shutil.rmtree(test_data_dir)

        # Create directory structure
        directories = ["small", "medium", "large", "nested/deep/structure"]
        for dir_path in directories:
            (test_data_dir / dir_path).mkdir(parents=True)

        # Create test files
        self._create_small_files(test_data_dir)
        self._create_medium_files(test_data_dir)
        self._create_large_files(test_data_dir)
        self._create_nested_files(test_data_dir)
        self._create_special_files(test_data_dir)
        self._create_variety_files(test_data_dir)

        print(f"✅ Test data created in: {test_data_dir.absolute()}")

        # Show summary
        total_files = len(list(test_data_dir.rglob("*")))
        total_size = sum(
            f.stat().st_size for f in test_data_dir.rglob("*") if f.is_file()
        )
        print(f"   📊 Created {total_files} items, total size: {total_size:,} bytes")

        return test_data_dir

    def _create_small_files(self, base_dir: Path):
        """Create small test files"""
        print("  Creating small files...")
        (base_dir / "small" / "small.txt").write_text("Small test file content")
        (base_dir / "small" / "small2.txt").write_text(
            "Another small file with different content"
        )

    def _create_medium_files(self, base_dir: Path):
        """Create medium test files"""
        print("  Creating medium files...")
        # Medium text file
        medium_text = "\n".join(
            f"Line {i}: This is a medium-sized text file for testing compression algorithms."
            for i in range(1000)
        )
        (base_dir / "medium" / "medium.txt").write_text(medium_text)

        # Medium binary file
        (base_dir / "medium" / "medium.bin").write_bytes(os.urandom(50000))

    def _create_large_files(self, base_dir: Path):
        """Create large test files"""
        print("  Creating large file...")
        large_data = b"".join(os.urandom(10000) for _ in range(100))  # 1MB total
        (base_dir / "large" / "large.bin").write_bytes(large_data)

    def _create_nested_files(self, base_dir: Path):
        """Create nested structure files"""
        print("  Creating nested structure...")
        files_data = {
            "nested/deep/structure/deep.txt": "Deep nested file content",
            "nested/file1.txt": "Nested file 1 content",
            "nested/file2.txt": "Nested file 2 content",
        }
        for file_path, content in files_data.items():
            (base_dir / file_path).write_text(content)

    def _create_special_files(self, base_dir: Path):
        """Create files with special characters"""
        print("  Creating files with special characters...")
        (base_dir / "file with spaces.txt").write_text("File with spaces in name")
        (base_dir / "unicode.txt").write_text("Unicode content: 测试文件 åäö ñáéíóú")

    def _create_variety_files(self, base_dir: Path):
        """Create variety of file types"""
        variety_files = {
            "empty.txt": "",
            "config.json": '{"test": true, "value": 42, "array": [1, 2, 3]}',
            "script.py": '#!/usr/bin/env python3\nprint("Hello, World!")\n',
            "README.md": "# Test Project\n\nThis is a **test** project with *markdown*.\n",
            "data.csv": "name,age,city\nJohn,30,NYC\nJane,25,LA\nBob,35,Chicago\n",
            "repetitive.txt": "This line repeats many times for compression testing.\n"
            * 500,
        }

        for file_path, content in variety_files.items():
            (base_dir / file_path).write_text(content)

        # Create binary pattern file
        binary_data = bytearray()
        for i in range(256):
            binary_data.extend([i] * 10)
        (base_dir / "patterns.bin").write_bytes(binary_data)

    def run_comprehensive_tests(self):
        """Run comprehensive tests on all supported archive formats"""

        # Create test data
        test_data_dir = self.create_test_data()

        # Get available archive formats
        archive_formats = self._get_available_formats()

        print(f"\n📊 Testing {len(archive_formats)} archive formats")

        print("🧪 Starting comprehensive archive tests...")
        print("=" * 80)

        all_passed = True

        for archive_name, flags in archive_formats:
            print(f"\n📦 Testing {archive_name} {flags}")
            print("-" * 40)

            result = self.test_archive_format(archive_name, test_data_dir, flags)
            self.test_results.append(result)

            if result["success"]:
                print(f"✅ {archive_name}: PASSED")
                print(f"   Compression: {result['compression_time']:.2f}s")
                print(f"   Decompression: {result['decompression_time']:.2f}s")
                print(
                    f"   Size: {result['original_size']} → {result['compressed_size']} bytes"
                )
                print(f"   Ratio: {result['compression_ratio']:.1f}% reduction")
            else:
                print(f"❌ {archive_name}: FAILED")
                print(f"   Error: {result['error']}")
                all_passed = False

        # Generate detailed report
        self.generate_report()

        return all_passed

    def generate_report(self):
        """Generate detailed test report"""
        report_file = self.results_dir / "test_report.md"

        with open(report_file, "w") as f:
            f.write("# Archive Format Test Report\n\n")
            f.write(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Summary
            passed = sum(1 for r in self.test_results if r["success"])
            total = len(self.test_results)
            f.write(f"## Summary\n\n")
            f.write(f"- **Total tests:** {total}\n")
            f.write(f"- **Passed:** {passed}\n")
            f.write(f"- **Failed:** {total - passed}\n")
            f.write(f"- **Success rate:** {(passed / total) * 100:.1f}%\n\n")

            # Detailed results
            f.write("## Detailed Results\n\n")
            f.write(
                "| Format | Status | Comp. Time | Decomp. Time | Original Size | Compressed Size | Ratio | Error |\n"
            )
            f.write(
                "|--------|--------|------------|--------------|---------------|-----------------|-------|---------|\n"
            )

            for result in self.test_results:
                status = "✅ PASS" if result["success"] else "❌ FAIL"
                error = (
                    result["error"][:50] + "..."
                    if result["error"] and len(result["error"]) > 50
                    else (result["error"] or "")
                )

                f.write(
                    f"| {result['archive_format']} | {status} | "
                    f"{result['compression_time']:.2f}s | {result['decompression_time']:.2f}s | "
                    f"{result['original_size']} | {result['compressed_size']} | "
                    f"{result['compression_ratio']:.1f}% | {error} |\n"
                )

                # Performance analysis
            successful_results = [r for r in self.test_results if r["success"]]
            if successful_results:
                f.write("\n## Performance Analysis\n\n")
                self._write_performance_stats(f, successful_results)

        print(f"\n📊 Detailed report saved to: {report_file}")

    def _get_available_formats(self):
        """Get list of available archive formats based on tool availability"""
        # Always available formats
        archive_formats = [("test.zip", []), ("test.tar", [])]

        # Conditional formats based on tool availability
        test_formats = [
            # Compressed tar formats
            ("test.tar.gz", [], ["tar", "gzip"]),
            ("test.tar.bz2", [], ["tar", "bzip2"]),
            ("test.tar.xz", [], ["tar", "xz"]),
            ("test.tar.lz4", [], ["tar", "lz4"]),
            ("test.tar.zst", [], ["tar", "zstd"]),
            ("test.tar.lz", [], ["tar", "lzip"]),
            ("test.tar.lrz", [], ["tar", "lrzip"]),
            ("test.tar.lzop", [], ["tar", "lzop"]),
            # Individual compression formats
            ("test.gz", [], ["gzip"]),
            ("test.bz2", [], ["bzip2"]),
            ("test.xz", [], ["xz"]),
            ("test.lz4", [], ["lz4"]),
            ("test.lz", [], ["lzip"]),
            ("test.lrz", [], ["lrzip"]),
            ("test.lzop", [], ["lzop"]),
            # 7z formats
            ("test.7z", [], ["7z"]),
            ("test_fast.7z", ["-mx1"], ["7z"]),
            ("test_best.7z", ["-mx9"], ["7z"]),
            # Other formats
            ("test.rar", [], ["rar"]),
            ("test.lzh", [], ["jlha"]),
            ("test.zpaq", [], ["zpaq"]),
        ]

        # Check tool availability and add formats
        for format_name, flags, required_tools in test_formats:
            tools_available = all(ArchiveCompressor._find_binaries([tool])[0] for tool in required_tools)

            if tools_available:
                archive_formats.append((format_name, flags))
                print(
                    f"  ✅ {format_name} - Tools available: {', '.join(required_tools)}"
                )
            else:
                print(
                    f"  ⚠️  {format_name} - Missing tools: {', '.join(required_tools)}"
                )

        return archive_formats

    def _write_performance_stats(self, f, successful_results):
        """Write performance statistics to report"""
        performance_metrics = {
            "Best compression ratio": (
                "compression_ratio",
                lambda x: f"{x:.1f}% reduction",
                min,
            ),
            "Fastest compression": ("compression_time", lambda x: f"{x:.2f}s", min),
            "Fastest decompression": ("decompression_time", lambda x: f"{x:.2f}s", min),
        }

        for label, (metric, formatter, selector) in performance_metrics.items():
            best_result = selector(successful_results, key=lambda x: x[metric])
            value = formatter(best_result[metric])
            f.write(f"**{label}:** {best_result['archive_format']} ({value})\n\n")


def main():
    """Main test function"""
    print("🚀 Real-World Archive Testing Suite")
    print("=" * 80)

    test_runner = ArchiveTestRunner()

    try:
        success = test_runner.run_comprehensive_tests()
        print("\n" + "=" * 80)

        result_msg = {
            True: (
                "✅ All archive tests PASSED!",
                "The ranger-archives plugin is working correctly across all supported formats.",
            ),
            False: (
                "❌ Some archive tests FAILED!",
                "Check the detailed report for more information.",
            ),
        }[success]

        print(result_msg[0])
        print(result_msg[1])
        return 0 if success else 1

    except Exception as e:
        print(f"💥 Test suite crashed: {e}")
        import traceback

        traceback.print_exc()
        return 2
    finally:
        test_runner.cleanup()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
