#!/usr/bin/env python3
"""
Command-line interface for ranger-archives
Provides compress and decompress commands for testing
"""

import sys
import argparse
import subprocess
from pathlib import Path
from typing import List

# Add current directory to path to import our modules
sys.path.insert(0, str(Path(__file__).parent))

from archives_utils import get_compression_command, get_decompression_command, parse_escape_args

def run_command(command: List[str], cwd: Path = None) -> bool:
    """Run a command and return success status"""
    try:
        print(f"🔧 Running: {' '.join(command)}")
        if cwd:
            print(f"📁 Working directory: {cwd}")

        result = subprocess.run(command, cwd=cwd)
        success = result.returncode == 0

        status_msg = "✅ Command completed successfully" if success else f"❌ Command failed with exit code {result.returncode}"
        print(status_msg)
        return success

    except Exception as e:
        print(f"💥 Error running command: {e}")
        return False

def compress_files(archive_name: str, files: List[str], flags: str = "", cwd: str = None) -> bool:
    """Compress files into an archive"""
    print(f"📦 Compressing files into: {archive_name}")
    print(f"📄 Files: {', '.join(files)}")

    flag_list = parse_escape_args(flags) if flags else []
    if flag_list:
        print(f"🏁 Flags: {', '.join(flag_list)}")

    command = get_compression_command(archive_name, flag_list, files)
    if not command:
        print(f"❌ No compression method available for: {archive_name}")
        return False

    work_dir = Path(cwd) if cwd else Path.cwd()
    return run_command(command, work_dir)

def decompress_archive(archive_name: str, output_dir: str = None, flags: str = "") -> bool:
    """Decompress an archive"""
    print(f"📦 Decompressing archive: {archive_name}")
    if output_dir:
        print(f"📁 Output directory: {output_dir}")

    flag_list = parse_escape_args(flags) if flags else []
    if flag_list:
        print(f"🏁 Flags: {', '.join(flag_list)}")

    command = get_decompression_command(archive_name, flag_list, output_dir)
    if not command:
        print(f"❌ No decompression method available for: {archive_name}")
        return False

    return run_command(command)

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="ranger-archives CLI - Compress and decompress files using various formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compress files
  %(prog)s compress test.zip file1.txt file2.txt
  %(prog)s compress test.tar.gz folder/ --flags="-v"
  %(prog)s compress test.7z *.txt --flags="-mx9"

  # Decompress archives
  %(prog)s decompress test.zip
  %(prog)s decompress test.tar.gz --output=extract/
  %(prog)s decompress test.7z --output=out/ --flags="-y"

  # Test specific directory
  %(prog)s compress test.tar.bz2 * --cwd=test_data/
        """
    )

    subparsers = parser.add_subparsers(dest='action', help='Action to perform')

    # Compress subcommand
    compress_parser = subparsers.add_parser('compress', help='Compress files into archive')
    compress_parser.add_argument('archive', help='Archive name (format determined by extension)')
    compress_parser.add_argument('files', nargs='+', help='Files/directories to compress')
    compress_parser.add_argument('--flags', default='', help='Additional flags for compression tool')
    compress_parser.add_argument('--cwd', help='Working directory for compression')

    # Decompress subcommand
    decompress_parser = subparsers.add_parser('decompress', help='Decompress archive')
    decompress_parser.add_argument('archive', help='Archive to decompress')
    decompress_parser.add_argument('--output', help='Output directory for extraction')
    decompress_parser.add_argument('--flags', default='', help='Additional flags for decompression tool')

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        return 1

    print("🚀 ranger-archives CLI")
    print("=" * 50)

    success = {
        'compress': lambda: compress_files(args.archive, args.files, args.flags, args.cwd),
        'decompress': lambda: decompress_archive(args.archive, args.output, args.flags)
    }.get(args.action, lambda: False)()

    print("=" * 50)
    status_msg = "✅ Operation completed successfully!" if success else "❌ Operation failed!"
    print(status_msg)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())