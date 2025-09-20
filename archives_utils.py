from shlex import split, quote
from shutil import which
from re import search
from typing import Union, Tuple, List, Optional, Dict, Any
from pathlib import Path


# Unified format configurations matching main.lua FORMATS table
FORMATS = {
    # TAR-based compressed formats
    "tar_bz2": {
        "patterns": [r"\.tar\.bz2$", r"\.tbz2?$"],
        "compression": [{"tools": ["pbzip2", "lbzip2", "bzip2"], "flags": ["-cf"]}],
        "extraction": [{"tools": ["tar"], "flags": ["-xf"]}],
    },
    "tar_bz3": {
        "patterns": [r"\.tar\.bz3$", r"\.tbz3$"],
        "special_extraction": "pipe",
        "compression": [{"tools": ["bzip3"], "flags": ["-cf"]}],
        "extraction": [{"tools": ["tar"], "flags": ["-xf"]}],
    },
    "tar_gz": {
        "patterns": [r"\.tar\.gz$", r"\.tgz$", r"\.taz$"],
        "compression": [{"tools": ["pigz", "gzip"], "flags": ["-cf"]}],
        "extraction": [{"tools": ["tar"], "flags": ["-xf"]}],
    },
    "tar_xz": {
        "patterns": [r"\.tar\.xz$", r"\.txz$", r"\.tlz$"],
        "compression": [{"tools": ["pixz", "xz"], "flags": ["-cf"]}],
        "extraction": [{"tools": ["tar"], "flags": ["-xf"]}],
    },
    "tar_lz4": {
        "patterns": [r"\.tar\.lz4$"],
        "compression": [{"tools": ["lz4"], "flags": ["-cf"]}],
        "extraction": [{"tools": ["tar"], "flags": ["-xf"]}],
    },
    "tar_lrz": {
        "patterns": [r"\.tar\.lrz$"],
        "compression": [{"tools": ["lrzip"], "flags": ["-cf"]}],
        "extraction": [{"tools": ["tar"], "flags": ["-xf"]}],
    },
    "tar_lzip": {
        "patterns": [r"\.tar\.lz$"],
        "compression": [{"tools": ["plzip", "lzip"], "flags": ["-cf"]}],
        "extraction": [{"tools": ["tar"], "flags": ["-xf"]}],
    },
    "tar_lzop": {
        "patterns": [r"\.tar\.lzop$", r"\.tzo$"],
        "compression": [{"tools": ["lzop"], "flags": ["-cf"]}],
        "extraction": [{"tools": ["tar"], "flags": ["-xf"]}],
    },
    "tar_zst": {
        "patterns": [r"\.tar\.zst$"],
        "compression": [{"tools": ["zstd"], "flags": ["-cf"]}],
        "extraction": [{"tools": ["tar"], "flags": ["-xf"]}],
    },
    "tar": {
        "patterns": [r"\.tar$"],
        "compression": [
            {"tools": ["tar"], "flags": ["-cf"]},
            {"tools": ["7z"], "flags": ["a"]},
        ],
        "extraction": [{"tools": ["tar"], "flags": ["-xf"]}],
    },
    # Single-file compression formats
    "bz2": {
        "patterns": [r"\.bz2$"],
        "single_file": True,
        "check_tar": True,
        "compression": [{"tools": ["pbzip2", "lbzip2", "bzip2"], "flags": ["-c"]}],
        "extraction": [{"tools": ["pbzip2", "lbzip2", "bzip2"], "flags": ["-dk"]}],
    },
    "bz3": {
        "patterns": [r"\.bz3$"],
        "single_file": True,
        "check_tar": True,
        "compression": [{"tools": ["bzip3"], "flags": ["-c"]}],
        "extraction": [{"tools": ["bzip3"], "flags": ["-dk"]}],
    },
    "gz": {
        "patterns": [r"\.gz$"],
        "single_file": True,
        "check_tar": True,
        "compression": [{"tools": ["pigz", "gzip"], "flags": ["-c"]}],
        "extraction": [{"tools": ["pigz", "gzip"], "flags": ["-dk"]}],
    },
    "xz": {
        "patterns": [r"\.xz$", r"\.lzma$"],
        "single_file": True,
        "check_tar": True,
        "compression": [{"tools": ["pixz", "xz"], "flags": ["-c"]}],
        "extraction": [{"tools": ["pixz", "xz"], "flags": ["-dk"]}],
    },
    "lzip": {
        "patterns": [r"\.lz$"],
        "single_file": True,
        "check_tar": True,
        "compression": [{"tools": ["plzip", "lzip"], "flags": ["-c"]}],
        "extraction": [{"tools": ["plzip", "lzip"], "flags": ["-dk"]}],
    },
    "lz4": {
        "patterns": [r"\.lz4$"],
        "single_file": True,
        "check_tar": True,
        "compression": [{"tools": ["lz4"], "flags": ["-c"]}],
        "extraction": [{"tools": ["lz4"], "flags": ["-dk"]}],
    },
    "lzop": {
        "patterns": [r"\.lzop$"],
        "single_file": True,
        "check_tar": True,
        "compression": [{"tools": ["lzop"], "flags": ["-c"]}],
        "extraction": [{"tools": ["lzop"], "flags": ["-dk"]}],
    },
    "lrzip": {
        "patterns": [r"\.lrz$"],
        "single_file": True,
        "check_tar": True,
        "compression": [{"tools": ["lrzip"], "flags": ["-o", "-"]}],
        "extraction": [{"tools": ["lrzip"], "flags": ["-d"]}],
    },
    # Standard archive formats
    "seven_zip": {
        "patterns": [r"\.7z$"],
        "compression": [{"tools": ["7z"], "flags": ["a"]}],
        "extraction": [{"tools": ["7z"], "flags": ["x"], "output_flag": "-o"}],
    },
    "rar": {
        "patterns": [r"\.rar$"],
        "compression": [{"tools": ["rar"], "flags": ["a", "-r"]}],
        "extraction": [
            {"tools": ["unrar", "rar"], "flags": ["x"], "output_flag": "-op"},
            {"tools": ["7z"], "flags": ["x"], "output_flag": "-o"},
        ],
    },
    "zip": {
        "patterns": [r"\.zip$"],
        "compression": [
            {"tools": ["zip"], "flags": ["-r"]},
            {"tools": ["7z"], "flags": ["a", "-tzip"]},
        ],
        "extraction": [
            {"tools": ["unzip"], "flags": [], "output_flag": "-d"},
            {"tools": ["7z"], "flags": ["x"], "output_flag": "-o"},
        ],
    },
    "zpaq": {
        "patterns": [r"\.zpaq$"],
        "compression": [{"tools": ["zpaq"], "flags": ["a"]}],
        "extraction": [{"tools": ["zpaq"], "flags": ["x"], "output_flag": "-to"}],
    },
    "deb": {
        "patterns": [r"\.deb$"],
        "extraction": [{"tools": ["ar"], "flags": ["-x"]}],
    },
}


def is_command_available(cmd: str) -> bool:
    """Check if a command is available in PATH"""
    if not cmd or cmd == "":
        return False
    return which(cmd) is not None


def find_available_tool(tools: List[str]) -> Optional[str]:
    """Find the first available tool from a list of tools"""
    if not tools:
        return None

    for tool in tools:
        if is_command_available(tool):
            return tool
    return None


def find_available_tool_group(
    tool_groups: List[Dict[str, Any]],
) -> Tuple[Optional[str], Optional[List[str]], Optional[str]]:
    """Find the first available tool group and return tool, flags, and output_flag"""
    if not tool_groups:
        return None, None, None

    for group in tool_groups:
        tool = find_available_tool(group["tools"])
        if tool:
            return tool, group["flags"], group.get("output_flag")
    return None, None, None


def is_tar_format(format_name: str) -> bool:
    """Check if a format is tar-based"""
    return format_name and (format_name.startswith("tar_") or format_name == "tar")


def match_format_patterns(filename: str, patterns: List[str]) -> bool:
    """Check if filename matches any of the patterns"""
    filename_lower = filename.lower()
    for pattern in patterns:
        if search(pattern, filename_lower):
            return True
    return False


def find_archive_format(
    filename: str,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Find the archive format for a given filename"""
    for format_name, config in FORMATS.items():
        if match_format_patterns(filename, config["patterns"]):
            return format_name, config
    return None, None


def is_compressed_tar_archive(file_path: str) -> bool:
    """Check if a file is a compressed tar archive based on filename"""
    return ".tar." in Path(file_path).name.lower()


class ArchiveCompressor:
    """Handles archive compression operations"""

    @staticmethod
    def get_command(
        archive_name: str, user_flags: List[str], files: List[str]
    ) -> List[str]:
        """Get compression command for the given archive format"""
        format_name, format_config = find_archive_format(archive_name)
        if not format_config:
            return ArchiveCompressor._get_fallback_compression_command(
                archive_name, user_flags, files
            )

        # Try to find available compression tools
        tool, tool_flags, _ = find_available_tool_group(format_config["compression"])
        if not tool:
            # Try fallback format if available
            if format_config.get("fallback") and format_config["fallback"] in FORMATS:
                fallback_config = FORMATS[format_config["fallback"]]
                fallback_tool, fallback_flags, _ = find_available_tool_group(
                    fallback_config["compression"]
                )
                if fallback_tool:
                    return ArchiveCompressor._build_standard_command(
                        fallback_tool, fallback_flags, user_flags, archive_name, files
                    )
            return ArchiveCompressor._get_fallback_compression_command(
                archive_name, user_flags, files
            )

        # Single-file compression
        if format_config.get("single_file"):
            return ArchiveCompressor._handle_single_file_compression(
                tool, tool_flags, user_flags, archive_name, files
            )

        # TAR-based compression
        if is_tar_format(format_name):
            if format_name == "tar":
                # Plain tar format - no compression program needed
                return ArchiveCompressor._build_standard_command(
                    tool, tool_flags, user_flags, archive_name, files
                )
            else:
                # Compressed tar format - use compression program
                return ArchiveCompressor._build_tar_command_with_compression(
                    tool, tool_flags, user_flags, archive_name, files
                )

        # Standard archive formats
        return ArchiveCompressor._build_standard_command(
            tool, tool_flags, user_flags, archive_name, files
        )

    @staticmethod
    def _build_tar_command_with_compression(
        tool: str,
        tool_flags: List[str],
        user_flags: List[str],
        archive_name: str,
        files: List[str],
    ) -> List[str]:
        """Build tar command with compression program"""
        if not is_command_available("tar"):
            return []

        return [
            which("tar"),
            *tool_flags,
            *user_flags,
            archive_name,
            "--use-compress-program",
            which(tool),
            *files,
        ]

    @staticmethod
    def _handle_single_file_compression(
        tool: str,
        tool_flags: List[str],
        user_flags: List[str],
        archive_name: str,
        files: List[str],
    ) -> List[str]:
        """Handle single-file compression"""
        if len(files) == 1:
            flags_str = " ".join(tool_flags + user_flags)
            return [
                "sh",
                "-c",
                f"{which(tool)} {flags_str} '{files[0]}' > '{archive_name}'",
            ]

        return ArchiveCompressor._convert_to_tar_format(
            tool, tool_flags, user_flags, archive_name, files
        )

    @staticmethod
    def _convert_to_tar_format(
        tool: str,
        tool_flags: List[str],
        user_flags: List[str],
        archive_name: str,
        files: List[str],
    ) -> List[str]:
        """Convert single-file compression to tar format for multiple files"""
        for format_name, format_config in FORMATS.items():
            if format_config.get("single_file"):
                for pattern in format_config["patterns"]:
                    if search(pattern, archive_name.lower()):
                        clean_pattern = pattern.replace(r"\.", ".").replace("$", "")
                        tar_name = archive_name.replace(
                            clean_pattern, f".tar{clean_pattern}"
                        )

                        tar_format_name, tar_format_config = find_archive_format(
                            tar_name
                        )
                        if tar_format_config and is_tar_format(tar_format_name):
                            tar_tool, tar_flags, _ = find_available_tool_group(
                                tar_format_config["compression"]
                            )
                            if tar_flags:
                                return ArchiveCompressor._build_tar_command_with_compression(
                                    tar_tool, tar_flags, user_flags, tar_name, files
                                )

                        return ArchiveCompressor._build_tar_command_with_compression(
                            tool, ["-cf"], user_flags, tar_name, files
                        )

        return ArchiveCompressor._build_tar_command_with_compression(
            tool, ["-cf"], user_flags, f"{archive_name}.tar", files
        )

    @staticmethod
    def _build_standard_command(
        tool: str,
        tool_flags: List[str],
        user_flags: List[str],
        archive_name: str,
        files: List[str],
    ) -> List[str]:
        """Build standard archive command"""
        return [which(tool), *tool_flags, *user_flags, archive_name, *files]

    @staticmethod
    def _get_fallback_compression_command(
        archive_name: str, user_flags: List[str], files: List[str]
    ) -> List[str]:
        """Get fallback compression command using zip"""
        zip_config = FORMATS.get("zip")
        tool, tool_flags, _ = find_available_tool_group(zip_config["compression"])
        if tool:
            return ArchiveCompressor._build_standard_command(
                tool, tool_flags, user_flags, f"{archive_name}.zip", files
            )
        return []


class ArchiveDecompressor:
    """Handles archive decompression operations"""

    @staticmethod
    def get_command(
        archive_name: str, user_flags: List[str], to_dir: str = None
    ) -> List[str]:
        """Get decompression command for the given archive format"""
        if to_dir:
            Path(to_dir).mkdir(parents=True, exist_ok=True)

        format_name, format_config = find_archive_format(archive_name)

        # Special handling for formats that need piped extraction
        if format_config and format_config.get("special_extraction") == "pipe":
            return ArchiveDecompressor._build_pipe_extraction_command(
                archive_name, format_config, to_dir
            )

        if not format_config:
            return ArchiveDecompressor._get_fallback_extraction_command(
                archive_name, user_flags, to_dir
            )

        # Handle ambiguous compressed files
        if format_config.get("check_tar"):
            if is_compressed_tar_archive(archive_name):
                # It's a compressed tar archive
                if is_command_available("tar"):
                    return (
                        [which("tar"), "-xf", archive_name]
                        + (["-C", to_dir] if to_dir else [])
                        + user_flags
                    )
            else:
                # It's a true single-file compression
                return ArchiveDecompressor._build_single_file_extraction_command(
                    archive_name, format_config, user_flags
                )

        # Standard extraction
        tool, tool_flags, output_flag = find_available_tool_group(
            format_config["extraction"]
        )

        # Try fallback format if primary tool not available
        if (
            not tool
            and format_config.get("fallback")
            and format_config["fallback"] in FORMATS
        ):
            fallback_config = FORMATS[format_config["fallback"]]
            tool, tool_flags, output_flag = find_available_tool_group(
                fallback_config["extraction"]
            )

        if not tool:
            return ArchiveDecompressor._get_fallback_extraction_command(
                archive_name, user_flags, to_dir
            )

        return ArchiveDecompressor._build_extraction_command(
            tool, tool_flags, user_flags, output_flag, archive_name, to_dir
        )

    @staticmethod
    def _build_pipe_extraction_command(
        archive_name: str, format_config: Dict[str, Any], to_dir: Optional[str]
    ) -> List[str]:
        """Build piped extraction command for special formats"""
        compression_tool, compression_flags, _ = find_available_tool_group(
            format_config["compression"]
        )
        if compression_tool and is_command_available("tar"):
            pipe_cmd = (
                f"{which(compression_tool)} -dc '{archive_name}' | {which('tar')} -xf -"
            )
            if to_dir:
                pipe_cmd += f" -C '{to_dir}'"
            return ["sh", "-c", pipe_cmd]
        return []

    @staticmethod
    def _build_single_file_extraction_command(
        archive_name: str, format_config: Dict[str, Any], user_flags: List[str]
    ) -> List[str]:
        """Build single-file extraction command"""
        tool, tool_flags, _ = find_available_tool_group(format_config["extraction"])
        if tool:
            return [which(tool), *tool_flags, *user_flags, archive_name]
        return []

    @staticmethod
    def _build_extraction_command(
        tool: str,
        tool_flags: List[str],
        user_flags: List[str],
        output_flag: Optional[str],
        archive_name: str,
        to_dir: Optional[str],
    ) -> List[str]:
        """Build standard extraction command"""
        cmd = [which(tool), *tool_flags, *user_flags, archive_name]

        # Handle output directory - match Lua logic
        if to_dir and output_flag:
            if output_flag in ["-o", "-op", "--output="]:
                cmd.append(f"{output_flag}{to_dir}")
            elif output_flag in ["-d", "-to"]:
                cmd.extend([output_flag, to_dir])
            elif output_flag == "":
                cmd.append(to_dir)
            else:
                cmd += [output_flag, to_dir]
        elif to_dir and tool == "tar":
            cmd += ["-C", to_dir]

        return cmd

    @staticmethod
    def _get_fallback_extraction_command(
        archive_name: str, user_flags: List[str], to_dir: Optional[str]
    ) -> List[str]:
        """Get fallback extraction command"""
        # Try 7z first, then unzip
        for tool in ["7z", "unzip"]:
            if is_command_available(tool):
                if tool == "7z":
                    return [which(tool), "x", *user_flags, archive_name] + (
                        [f"-o{to_dir}"] if to_dir else []
                    )
                elif tool == "unzip":
                    return [which(tool), *user_flags, archive_name] + (
                        ["-d", to_dir] if to_dir else []
                    )

        # Final fallback - assume 7z is available
        return ["7z", "x", *user_flags, archive_name] + (
            [f"-o{to_dir}"] if to_dir else []
        )


def parse_escape_args(args: str = "") -> List[str]:
    """Parses and escapes arguments"""
    return list(map(quote, split(args)))


# Backwards compatibility functions
def get_compression_command(
    archive_name: str, flags: List[str], files: List[str]
) -> List[str]:
    """Get compression command - backwards compatibility wrapper"""
    return ArchiveCompressor.get_command(archive_name, flags, files)


def get_decompression_command(
    archive_name: str, flags: List[str], to_dir: str = None
) -> List[str]:
    """Get decompression command - backwards compatibility wrapper"""
    return ArchiveDecompressor.get_command(archive_name, flags, to_dir)


def _find_binaries(binaries: List[str]) -> Union[Tuple[str, str], Tuple[None, None]]:
    """Finds archivers binaries in PATH - backwards compatibility"""
    res = list(filter(lambda x: x[1] is not None, zip(binaries, map(which, binaries))))
    return res[0] if res else (None, None)
