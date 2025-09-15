from shlex import split, quote
from shutil import which
from re import search
from typing import Union, Tuple, List, Optional
from pathlib import Path
import platform
import subprocess
import logging


def parse_escape_args(args: str = "") -> List[str]:
    """Parses and escapes arguments"""
    return list(map(quote, split(args)))


def get_tool_info(binary_path: str) -> str:
    """Get tool type and version info for platform-specific handling"""
    try:
        result = subprocess.run([binary_path, '--version'], capture_output=True, timeout=5)

        # Handle encoding issues with fallback chain
        for encoding in ['utf-8', 'latin-1']:
            try:
                version_info = result.stdout.decode(encoding) + result.stderr.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            version_info = result.stdout.decode('utf-8', errors='ignore') + result.stderr.decode('utf-8', errors='ignore')

        # Detect tool type
        tool_patterns = {
            'gnu_tar': ['GNU tar'],
            'bsd_tar': ['bsdtar', 'libarchive'],
            '7zip': ['7-Zip', 'p7zip'],
            'info_zip': ['Info-ZIP']
        }

        for tool_type, patterns in tool_patterns.items():
            if any(pattern in version_info for pattern in patterns):
                return tool_type

    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass

    return 'unknown'


def validate_flags_for_tool(binary_path: str, flags: List[str]) -> List[str]:
    """Remove unsupported flags for specific tool implementations"""
    tool_type = get_tool_info(binary_path)
    safe_flags = []

    # Define flag compatibility matrix
    flag_compatibility = {
        'bsd_tar': {
            'unsupported': ['--use-compress-program'],
            'alternatives': {'--use-compress-program': '-I'}
        },
        'gnu_tar': {
            'unsupported': [],
            'alternatives': {}
        },
        '7zip': {
            'unsupported': ['-r'] if platform.system() == 'Windows' else [],
            'alternatives': {}
        },
        'unknown': {
            'unsupported': ['--use-compress-program'],  # Conservative approach
            'alternatives': {}
        }
    }

    compatibility = flag_compatibility.get(tool_type, flag_compatibility['unknown'])

    for flag in flags:
        if flag not in compatibility.get('unsupported', []):
            safe_flags.append(flag)
        elif flag in compatibility.get('alternatives', {}):
            safe_flags.append(compatibility['alternatives'][flag])

    return safe_flags


def get_safe_tar_command(archive_name: str, flags: List[str], files: List[str],
                        compression_program: Optional[str] = None) -> List[str]:
    """Generate tar command with cross-platform compatibility"""
    tar_binary, tar_path = find_binaries(['tar'])
    if not tar_binary:
        return []

    tool_type = get_tool_info(tar_path)
    safe_flags = validate_flags_for_tool(tar_path, flags)

    if compression_program:
        if tool_type == 'gnu_tar':
            # GNU tar supports --use-compress-program
            command = [tar_path, '-cf', archive_name, '--use-compress-program', compression_program, *safe_flags, *files]
        elif tool_type == 'bsd_tar':
            # BSD tar: use built-in compression flags instead of -I which is problematic
            if 'gzip' in compression_program or 'pigz' in compression_program:
                command = [tar_path, '-czf', archive_name, *safe_flags, *files]
            elif 'bzip2' in compression_program or 'pbzip2' in compression_program or 'lbzip2' in compression_program:
                command = [tar_path, '-cjf', archive_name, *safe_flags, *files]
            elif 'xz' in compression_program or 'pixz' in compression_program:
                command = [tar_path, '-cJf', archive_name, *safe_flags, *files]
            else:
                # For other compression programs, create tar first then compress separately
                # This is handled by individual format handlers
                temp_tar = archive_name.rsplit('.', 1)[0] if '.' in archive_name else archive_name
                if not temp_tar.endswith('.tar'):
                    temp_tar += '.tar'
                command = [tar_path, '-cf', temp_tar, *safe_flags, *files]
        else:
            # Unknown tar: try built-in compression flags if possible
            if archive_name.endswith('.tar.gz') or archive_name.endswith('.tgz'):
                command = [tar_path, '-czf', archive_name, *safe_flags, *files]
            elif archive_name.endswith('.tar.bz2') or archive_name.endswith('.tbz2'):
                command = [tar_path, '-cjf', archive_name, *safe_flags, *files]
            elif archive_name.endswith('.tar.xz') or archive_name.endswith('.txz'):
                command = [tar_path, '-cJf', archive_name, *safe_flags, *files]
            else:
                # Fallback: create uncompressed tar
                temp_tar = archive_name.rsplit('.', 1)[0] if '.' in archive_name else archive_name + '.tar'
                command = [tar_path, '-cf', temp_tar, *safe_flags, *files]
    else:
        command = [tar_path, '-cf', archive_name, *safe_flags, *files]

    return command


def find_binaries(
        binaries: List[str]) -> Union[Tuple[str, str], Tuple[None, None]]:
    """Finds archivers binaries in PATH"""
    res = list(filter(
        lambda x: x[1] is not None,
        zip(binaries, map(which, binaries))))
    return res[0] if res else (None, None)


def get_compression_command(
        archive_name: str,
        flags: List[str],
        files: List[str]) -> List[str]:
    """Returns cross-platform compatible compression command"""

    # Define format patterns and their corresponding tools
    format_configs = [
        # Tar-based formats
        (r"\.(tar\.|t)bz[2]*$", ["pbzip2", "lbzip2", "bzip2"], True),
        (r"\.(tar\.(gz|z)|t(g|a)z)$", ["pigz", "gzip"], True),
        (r"\.(tar\.(xz|lzma)|t(xz|lz))$", ["pixz", "xz"], True),
        (r"\.tar\.lz4$", ["lz4"], True),
        (r"\.tar\.lrz$", ["lrzip"], True),
        (r"\.tar\.lz$", ["plzip", "lzip"], True),
        (r"\.(tar\.lzop|tzo)$", ["lzop"], True),
        (r"\.tar\.zst$", ["zstd"], True),

        # Single-file compression formats
        (r"\.bz[2]*$", ["pbzip2", "lbzip2", "bzip2"], False),
        (r"\.g*z$", ["pigz", "gzip"], False),
        (r"\.(xz|lzma)$", ["pixz", "xz"], False),
        (r"\.lz4$", ["lz4"], False),
        (r"\.lrz$", ["lrzip"], False),
        (r"\.lz$", ["plzip", "lzip"], False),
        (r"\.lzop$", ["lzop"], False),
    ]

    for pattern, bins, is_tar_format in format_configs:
        if search(pattern, archive_name):
            binary, binary_path = find_binaries(bins)
            if not binary:
                continue

            if is_tar_format:
                command = get_safe_tar_command(archive_name, flags, files, binary_path)
                if command:
                    return command
            else:
                return _handle_single_file_compression(archive_name, flags, files, binary, binary_path)

    # Archive formats
    archive_configs = [
        (r"\.7z$", ["7z", "7za"], _handle_7z_compression),
        (r"\.rar$", ["rar"], _handle_rar_compression),
        (r"\.zip$", ["zip", "7z", "7za"], _handle_zip_compression),
        (r"\.zpaq$", ["zpaq"], _handle_zpaq_compression),
        (r"\.l(zh|ha)$", ["lha"], _handle_lha_compression),
        (r"\.tar$", ["tar", "7z", "7za"], _handle_tar_compression),
    ]

    for pattern, bins, handler in archive_configs:
        if search(pattern, archive_name):
            binary, binary_path = find_binaries(bins)
            if binary:
                return handler(archive_name, flags, files, binary, binary_path)

    return _fallback_compression(archive_name, flags, files)


def _handle_single_file_compression(archive_name: str, flags: List[str], files: List[str],
                                   binary: str, binary_path: str) -> List[str]:
    """Handle single-file compression formats"""
    if len(files) == 1:
        if binary in ['gzip', 'pigz', 'bzip2', 'pbzip2', 'lbzip2', 'xz', 'pixz']:
            safe_flags = validate_flags_for_tool(binary_path, flags + ['-k'])
            return [binary_path, *safe_flags, files[0]]
        elif binary == 'lz4':
            safe_flags = validate_flags_for_tool(binary_path, flags)
            return [binary_path, *safe_flags, files[0], archive_name]
        elif binary in ['lzip', 'plzip']:
            safe_flags = validate_flags_for_tool(binary_path, flags + ['-k'])
            return [binary_path, *safe_flags, '-c', files[0]] + ['>', archive_name]
        elif binary == 'lrzip':
            safe_flags = validate_flags_for_tool(binary_path, flags)
            return [binary_path, *safe_flags, *files]
        elif binary == 'lzop':
            safe_flags = validate_flags_for_tool(binary_path, flags)
            return [binary_path, *safe_flags, '-o', archive_name, *files]
    else:
        # Multiple files: create tar version
        if '.gz' in archive_name:
            tar_name = archive_name.replace('.gz', '.tar.gz')
        elif '.bz2' in archive_name:
            tar_name = archive_name.replace('.bz2', '.tar.bz2')
        elif '.xz' in archive_name:
            tar_name = archive_name.replace('.xz', '.tar.xz')
        elif '.lzma' in archive_name:
            tar_name = archive_name.replace('.lzma', '.tar.lzma')
        elif '.lz4' in archive_name:
            tar_name = archive_name.replace('.lz4', '.tar.lz4')
        elif '.lzop' in archive_name:
            tar_name = archive_name.replace('.lzop', '.tar.lzop')
        else:
            tar_name = archive_name + '.tar'
        return get_safe_tar_command(tar_name, flags, files, binary_path)
    return []


def _handle_7z_compression(archive_name: str, flags: List[str], files: List[str],
                          binary: str, binary_path: str) -> List[str]:
    """Handle 7z compression"""
    safe_flags = validate_flags_for_tool(binary_path, flags)
    tool_type = get_tool_info(binary_path)
    if tool_type == '7zip' and platform.system() != 'Windows':
        safe_flags += ["-r"]
    return [binary_path, "a", *safe_flags, archive_name, *files]


def _handle_rar_compression(archive_name: str, flags: List[str], files: List[str],
                           binary: str, binary_path: str) -> List[str]:
    """Handle RAR compression"""
    safe_flags = validate_flags_for_tool(binary_path, flags)
    return [binary_path, "a", *safe_flags, archive_name, *files]


def _handle_zip_compression(archive_name: str, flags: List[str], files: List[str],
                           binary: str, binary_path: str) -> List[str]:
    """Handle ZIP compression"""
    if binary == 'zip':
        safe_flags = validate_flags_for_tool(binary_path, flags + ["-r"])
        return [binary_path, *safe_flags, archive_name, *files]
    elif binary in ['7z', '7za']:
        safe_flags = validate_flags_for_tool(binary_path, flags)
        tool_type = get_tool_info(binary_path)
        if tool_type == '7zip' and platform.system() != 'Windows':
            safe_flags += ["-r"]
        return [binary_path, "a", *safe_flags, archive_name, *files]
    return []


def _handle_zpaq_compression(archive_name: str, flags: List[str], files: List[str],
                            binary: str, binary_path: str) -> List[str]:
    """Handle ZPAQ compression"""
    safe_flags = validate_flags_for_tool(binary_path, flags)
    return [binary_path, "a", archive_name, *files, *safe_flags]


def _handle_lha_compression(archive_name: str, flags: List[str], files: List[str],
                           binary: str, binary_path: str) -> List[str]:
    """Handle LHA compression"""
    safe_flags = validate_flags_for_tool(binary_path, flags)
    return [binary_path, "c", *safe_flags, archive_name, *files]


def _handle_tar_compression(archive_name: str, flags: List[str], files: List[str],
                           binary: str, binary_path: str) -> List[str]:
    """Handle TAR compression"""
    if binary == "tar":
        safe_flags = validate_flags_for_tool(binary_path, flags)
        return [binary_path, "-cf", archive_name, *safe_flags, *files]
    elif binary in ["7z", "7za"]:
        safe_flags = validate_flags_for_tool(binary_path, flags)
        return [binary_path, "a", *safe_flags, archive_name, *files]
    return []


def _fallback_compression(archive_name: str, flags: List[str], files: List[str]) -> List[str]:
    """Fallback compression using common tools"""
    fallback_bins = ["zip", "7z", "7za"]
    binary, binary_path = find_binaries(fallback_bins)

    if binary == 'zip':
        safe_flags = validate_flags_for_tool(binary_path, flags + ["-r"])
        return [binary_path, *safe_flags, f"{archive_name}.zip"] + files
    elif binary in ['7z', '7za']:
        safe_flags = validate_flags_for_tool(binary_path, flags)
        return [binary_path, "a", *safe_flags, f"{archive_name}.zip"] + files
    else:
        return ["zip", "-r", f"{archive_name}.zip"] + files



def get_decompression_command(
        archive_name: str,
        flags: list,
        to_dir: str = None) -> List[str]:
    """Returns cross-platform compatible decompression command"""
    tar_full = r"\.tar\.(bz2*|g*z|lz(4|ma)|lr*z|lzop|xz|zst)$"
    tar_short = r"\.t(a|b|g|l|x)z2*"

    if to_dir:
        Path(to_dir).mkdir(parents=True, exist_ok=True)

    if search(tar_full, archive_name) is not None or\
            search(tar_short, archive_name) is not None:
        # Matches all supported tarballs
        bins = ["tar"]
        binary, binary_path = find_binaries(bins)

        if binary:
            safe_flags = validate_flags_for_tool(binary_path, flags)
            if to_dir:
                safe_flags += ['-C', to_dir]
            command = [binary_path, "-xf", archive_name, *safe_flags]
            return command

    elif search(r"\.7z$", archive_name) is not None:
        bins = ["7z", "7za"]
        binary, binary_path = find_binaries(bins)
        if binary:
            safe_flags = validate_flags_for_tool(binary_path, flags)
            if to_dir:
                # Use pathlib for cross-platform path handling
                safe_flags += [f'-o{Path(to_dir)}']
            command = [binary_path, "x", *safe_flags, archive_name]
            return command

    elif search(r"\.rar$", archive_name) is not None:
        bins = ["7z", "7za", "unrar", "rar"]
        binary, binary_path = find_binaries(bins)

        if binary == 'rar' or binary == 'unrar':
            safe_flags = validate_flags_for_tool(binary_path, flags)
            command = [binary_path, "x", *safe_flags, archive_name]
            if to_dir:
                command += [str(Path(to_dir))]
            return command
        elif binary in ['7z', '7za']:
            safe_flags = validate_flags_for_tool(binary_path, flags)
            if to_dir:
                safe_flags += [f'-o{Path(to_dir)}']
            command = [binary_path, "x", *safe_flags, archive_name]
            return command

    elif search(r"\.zip$", archive_name) is not None:
        bins = ["7z", "7za", "unzip"]
        binary, binary_path = find_binaries(bins)

        if binary == 'unzip':
            safe_flags = validate_flags_for_tool(binary_path, flags)
            command = [binary_path, *safe_flags, archive_name]
            if to_dir:
                command += ['-d', str(Path(to_dir))]
            return command
        elif binary in ['7z', '7za']:
            safe_flags = validate_flags_for_tool(binary_path, flags)
            if to_dir:
                safe_flags += [f'-o{Path(to_dir)}']
            command = [binary_path, "x", *safe_flags, archive_name]
            return command

    elif search(r"\.zpaq$", archive_name) is not None:
        bins = ["zpaq"]
        binary, binary_path = find_binaries(bins)

        if binary:
            safe_flags = validate_flags_for_tool(binary_path, flags)
            command = [binary_path, "x", archive_name, *safe_flags]
            return command

    elif search(r"\.l(zh|ha)$", archive_name) is not None:
        # Matches:
        # .lzh
        # .lha
        bins = ["lha"]
        binary, binary_path = find_binaries(bins)

        if binary:
            safe_flags = validate_flags_for_tool(binary_path, flags)
            if to_dir:
                safe_flags += [f'w={Path(to_dir)}']
            command = [binary_path, "x", *safe_flags, archive_name]
            return command

    elif search(r"\.tar$", archive_name) is not None:
        bins = ["tar", "7z", "7za"]
        binary, binary_path = find_binaries(bins)

        if binary == "tar":
            safe_flags = validate_flags_for_tool(binary_path, flags)
            if to_dir:
                safe_flags += ['-C', str(Path(to_dir))]
            command = [binary_path, "-xf", archive_name, *safe_flags]
            return command
        elif binary in ["7z", "7za"]:
            safe_flags = validate_flags_for_tool(binary_path, flags)
            if to_dir:
                safe_flags += [f'-o{Path(to_dir)}']
            command = [binary_path, "x", *safe_flags, archive_name]
            return command

    elif search(r"\.deb$", archive_name) is not None:
        # Matches:
        # .deb
        bins = ["ar"]
        binary, binary_path = find_binaries(bins)

        if binary:
            safe_flags = validate_flags_for_tool(binary_path, flags)
            if to_dir:
                safe_flags += [f'--output={Path(to_dir)}']
            command = [binary_path, "xv", *safe_flags, archive_name]
            return command

    # Improved fallback with cross-platform compatibility
    fallback_bins = ["7z", "7za", "unzip"]
    binary, binary_path = find_binaries(fallback_bins)

    if binary in ['7z', '7za']:
        fallback_command = [binary_path, "x", archive_name]
        if to_dir:
            fallback_command += [f'-o{Path(to_dir)}']
    elif binary == 'unzip':
        fallback_command = [binary_path, archive_name]
        if to_dir:
            fallback_command += ['-d', str(Path(to_dir))]
    else:
        # Last resort
        fallback_command = ["7z", "x", archive_name]
        if to_dir:
            fallback_command += [f'-o{Path(to_dir)}']

    return fallback_command
