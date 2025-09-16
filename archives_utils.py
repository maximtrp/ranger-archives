from shlex import split, quote
from shutil import which
from re import search
from typing import Union, Tuple, List, Optional
from pathlib import Path
import platform


def _find_binaries(binaries: List[str]) -> Union[Tuple[str, str], Tuple[None, None]]:
    """Finds archivers binaries in PATH"""
    res = list(filter(lambda x: x[1] is not None, zip(binaries, map(which, binaries))))
    return res[0] if res else (None, None)


class ArchiveCompressor:
    """Handles archive compression operations"""

    @staticmethod
    def get_command(archive_name: str, flags: List[str], files: List[str]) -> List[str]:
        """Get compression command for the given archive format"""
        # Tar-based formats
        tar_formats = [
            (r"\.(tar\.|t)bz[2]*$", ["pbzip2", "lbzip2", "bzip2"]),
            (r"\.(tar\.(gz|z)|t(g|a)z)$", ["pigz", "gzip"]),
            (r"\.(tar\.(xz|lzma)|t(xz|lz))$", ["pixz", "xz"]),
            (r"\.tar\.lz4$", ["lz4"]),
            (r"\.tar\.lrz$", ["lrzip"]),
            (r"\.tar\.lz$", ["plzip", "lzip"]),
            (r"\.(tar\.lzop|tzo)$", ["lzop"]),
            (r"\.tar\.zst$", ["zstd"]),
        ]

        for pattern, bins in tar_formats:
            if search(pattern, archive_name):
                binary, binary_path = _find_binaries(bins)
                if binary:
                    return ArchiveCompressor._get_tar_command(
                        archive_name, flags, files, binary_path
                    )

        # Single-file compression that creates tar archives
        single_formats = [
            (r"\.bz[2]*$", ["pbzip2", "lbzip2", "bzip2"]),
            (r"\.g*z$", ["pigz", "gzip"]),
            (r"\.(xz|lzma)$", ["pixz", "xz"]),
            (r"\.lz$", ["plzip", "lzip"]),
        ]

        for pattern, bins in single_formats:
            if search(pattern, archive_name):
                binary, binary_path = _find_binaries(bins)
                if binary:
                    return ArchiveCompressor._handle_single_file(
                        archive_name, flags, files, binary, binary_path
                    )

        if search(r"\.lzop$", archive_name):
            tar_name = archive_name.replace(".lzop", ".tar.lzop")
            binary, binary_path = _find_binaries(["lzop"])
            if binary:
                return ArchiveCompressor._get_tar_command(
                    tar_name, flags, files, binary_path
                )

        # Archive formats
        if search(r"\.7z$", archive_name):
            binary, binary_path = _find_binaries(["7z", "7za"])
            if binary:
                return [binary_path, "a", *[*flags, "-bd"], archive_name, *files]

        if search(r"\.rar$", archive_name):
            binary, binary_path = _find_binaries(["rar"])
            if binary:
                return [binary_path, "a", "-r", *flags, archive_name, *files]

        if search(r"\.zip$", archive_name):
            binary, binary_path = _find_binaries(["zip", "7z", "7za"])
            if binary == "zip":
                return [binary_path, *(flags + ["-r"]), archive_name, *files]
            elif binary in ["7z", "7za"]:
                return [binary_path, "a", *flags, archive_name, *files]

        if search(r"\.zpaq$", archive_name):
            binary, binary_path = _find_binaries(["zpaq"])
            if binary:
                return [binary_path, "a", archive_name, *files, *flags]

        if search(r"\.tar$", archive_name):
            binary, binary_path = _find_binaries(["tar", "7z", "7za"])
            if binary == "tar":
                return [binary_path, "-cf", archive_name, *flags, *files]
            elif binary in ["7z", "7za"]:
                return [binary_path, "a", *flags, archive_name, *files]

        # Fallback
        binary, binary_path = _find_binaries(["zip", "7z", "7za"])
        if binary == "zip":
            return [binary_path, *(flags + ["-r"]), f"{archive_name}.zip", *files]
        elif binary in ["7z", "7za"]:
            return [binary_path, "a", *flags, f"{archive_name}.zip", *files]
        return ["zip", "-r", f"{archive_name}.zip", *files]

    @staticmethod
    def _get_tar_command(
        archive_name: str, flags: List[str], files: List[str], compression_program: str
    ) -> List[str]:
        """Generate tar command with compression support"""
        tar_binary, tar_path = _find_binaries(["tar"])
        if not tar_binary:
            return []
        return [
            tar_path,
            "-cf",
            archive_name,
            "--use-compress-program",
            compression_program,
            *flags,
            *files,
        ]

    @staticmethod
    def _handle_single_file(
        archive_name: str,
        flags: List[str],
        files: List[str],
        binary: str,
        binary_path: str,
    ) -> List[str]:
        """Handle single-file compression"""

        # If only one file, use true single-file compression
        if len(files) == 1:
            return [binary_path, "-c", *flags, files[0]]

        # Multiple files: create tar version since single-file compression can't handle multiple files
        tar_name = (
            archive_name.replace(".gz", ".tar.gz")
            .replace(".bz2", ".tar.bz2")
            .replace(".xz", ".tar.xz")
            .replace(".lzma", ".tar.lzma")
            .replace(".lz4", ".tar.lz4")
            .replace(".lz", ".tar.lz")
            .replace(".lzop", ".tar.lzop")
        )

        # If no replacement happened, add .tar
        if tar_name == archive_name:
            tar_name = archive_name + ".tar"

        return ArchiveCompressor._get_tar_command(tar_name, flags, files, binary_path)


class ArchiveDecompressor:
    """Handles archive decompression operations"""

    @staticmethod
    def _is_compressed_tar(archive_path: str) -> bool:
        """Simple heuristic to check if a file is a tar archive"""
        # If filename contains .tar., it's definitely a tar archive
        return ".tar." in Path(archive_path).name.lower()

    @staticmethod
    def get_command(
        archive_name: str, flags: List[str], to_dir: str = None
    ) -> List[str]:
        """Get decompression command for the given archive format"""
        if to_dir:
            Path(to_dir).mkdir(parents=True, exist_ok=True)

        # Tar-based formats (always tar)
        if search(
            r"\.tar\.(bz2*|g*z|lz(4|ma)|lr*z|lzop|xz|zst)$|\.t(a|b|g|l|x)z2*$",
            archive_name,
        ):
            binary, binary_path = _find_binaries(["tar"])
            if binary:
                safe_flags = flags + (["-C", to_dir] if to_dir else [])
                return [binary_path, "-xf", archive_name, *safe_flags]

        # Ambiguous single-file compression formats - check if they're actually tar
        if search(r"\.gz$|\.bz2$|\.xz$|\.lz$|\.lzop$", archive_name):
            if ArchiveDecompressor._is_compressed_tar(archive_name):
                # It's a compressed tar archive
                binary, binary_path = _find_binaries(["tar"])
                if binary:
                    safe_flags = flags + (["-C", to_dir] if to_dir else [])
                    return [binary_path, "-xf", archive_name, *safe_flags]
            else:
                # It's a true single-file archive
                return ArchiveDecompressor._get_single_file_decompress_command(
                    archive_name, flags, to_dir
                )

        # Archive formats
        if search(r"\.7z$", archive_name):
            binary, binary_path = _find_binaries(["7z", "7za"])
            if binary:
                safe_flags = flags + ([f"-o{Path(to_dir)}"] if to_dir else [])
                return [binary_path, "x", *safe_flags, archive_name]

        if search(r"\.rar$", archive_name):
            binary, binary_path = _find_binaries(["rar", "unrar", "7z", "7za"])
            if binary in ["rar", "unrar"]:
                command = [binary_path, "x", *flags, archive_name]
                if to_dir:
                    command += [str(Path(to_dir))]
                return command
            elif binary in ["7z", "7za"]:
                safe_flags = flags + ([f"-o{Path(to_dir)}"] if to_dir else [])
                return [binary_path, "x", *safe_flags, archive_name]

        if search(r"\.zip$", archive_name):
            binary, binary_path = _find_binaries(["7z", "7za", "unzip"])
            if binary == "unzip":
                command = [binary_path, *flags, archive_name]
                if to_dir:
                    command += ["-d", str(Path(to_dir))]
                return command
            elif binary in ["7z", "7za"]:
                safe_flags = flags + ([f"-o{Path(to_dir)}"] if to_dir else [])
                return [binary_path, "x", *safe_flags, archive_name]

        if search(r"\.zpaq$", archive_name):
            binary, binary_path = _find_binaries(["zpaq"])
            if binary:
                command = [binary_path, "x", archive_name, *flags]
                if to_dir:
                    command.extend(["-to", str(Path(to_dir))])
                return command

        if search(r"\.tar$", archive_name):
            binary, binary_path = _find_binaries(["tar", "7z", "7za"])
            if binary == "tar":
                safe_flags = flags + (["-C", str(Path(to_dir))] if to_dir else [])
                return [binary_path, "-xf", archive_name, *safe_flags]
            elif binary in ["7z", "7za"]:
                safe_flags = flags + ([f"-o{Path(to_dir)}"] if to_dir else [])
                return [binary_path, "x", *safe_flags, archive_name]

        if search(r"\.deb$", archive_name):
            binary, binary_path = _find_binaries(["ar"])
            if binary:
                safe_flags = flags + ([f"--output={Path(to_dir)}"] if to_dir else [])
                return [binary_path, "xv", *safe_flags, archive_name]

        # Fallback
        binary, binary_path = _find_binaries(["7z", "7za", "unzip"])
        if binary in ["7z", "7za"]:
            fallback_command = [binary_path, "x", archive_name]
            if to_dir:
                fallback_command += [f"-o{Path(to_dir)}"]
        elif binary == "unzip":
            fallback_command = [binary_path, archive_name]
            if to_dir:
                fallback_command += ["-d", str(Path(to_dir))]
        else:
            fallback_command = ["7z", "x", archive_name]
            if to_dir:
                fallback_command += [f"-o{Path(to_dir)}"]

        return fallback_command

    @staticmethod
    def _get_single_file_decompress_command(
        archive_name: str, flags: List[str], to_dir: str = None
    ) -> List[str]:
        """Generate single-file decompression command"""
        # Map extensions to their binary preferences
        format_binaries = {
            ".gz": ["gzip", "pigz"],
            ".bz2": ["bzip2", "pbzip2", "lbzip2"],
            ".xz": ["xz", "pixz"],
            ".lz": ["lzip", "plzip"],
            ".lzop": ["lzop"],
        }

        for ext, binaries in format_binaries.items():
            if archive_name.endswith(ext):
                binary, binary_path = _find_binaries(binaries)
                if binary:
                    return [binary_path, "-dc", *flags, archive_name]

        return []


def parse_escape_args(args: str = "") -> List[str]:
    """Parses and escapes arguments"""
    return list(map(quote, split(args)))
