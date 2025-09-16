from pathlib import Path
from ranger.api.commands import Command
from ranger.core.loader import CommandLoader
from shlex import quote
from .archives_utils import parse_escape_args, ArchiveDecompressor


class extract(Command):
    def execute(self):
        """Extract files to current directory or specified directory"""
        files = self.fm.thisdir.get_selection()
        if not files:
            return

        def refresh(_):
            self.fm.get_directory(self.fm.thisdir.path).load_content()

        dirname_raw = " ".join(self.line.strip().split()[1:])
        self._clear_buffers()

        for file in files:
            self._extract_file(file, dirname_raw, refresh)

    def _clear_buffers(self):
        """Clear ranger buffers"""
        self.fm.copy_buffer.clear()
        self.fm.cut_buffer = False

    def _extract_file(self, file, dirname_raw, refresh_callback):
        """Extract a single file"""
        descr = f"Extracting: {Path(file.path).name}"
        command = ArchiveDecompressor.get_command(file.path, [], dirname_raw if dirname_raw else None)
        obj = CommandLoader(args=command, descr=descr, read=True)
        obj.signal_bind('after', refresh_callback)
        self.fm.loader.add(obj)


class extract_raw(Command):
    def execute(self):
        """Extract files with custom flags"""
        files = self.fm.thisdir.get_selection()
        if not files:
            return

        def refresh(_):
            self.fm.get_directory(self.fm.thisdir.path).load_content()

        flags = parse_escape_args(self.line.strip())[1:]
        self._clear_buffers()

        for file in files:
            self._extract_file_with_flags(file, flags, refresh)

    def _clear_buffers(self):
        """Clear ranger buffers"""
        self.fm.copy_buffer.clear()
        self.fm.cut_buffer = False

    def _extract_file_with_flags(self, file, flags, refresh_callback):
        """Extract a single file with flags"""
        descr = f"Extracting: {Path(file.path).name}"
        command = ArchiveDecompressor.get_command(file.path, flags.copy())
        obj = CommandLoader(args=command, descr=descr, read=True)
        obj.signal_bind('after', refresh_callback)
        self.fm.loader.add(obj)


class extract_to_dirs(Command):
    def execute(self):
        """Extract files to subdirectories"""
        files = self.fm.thisdir.get_selection()
        if not files:
            return

        def refresh(_):
            self.fm.get_directory(self.fm.thisdir.path).load_content()

        flags = parse_escape_args(self.line.strip())[1:]
        self._clear_buffers()

        for file in files:
            dirname = Path(file.path).stem
            self._extract_file_to_dir(file, flags, dirname, refresh)

    def _clear_buffers(self):
        """Clear ranger buffers"""
        self.fm.copy_buffer.clear()
        self.fm.cut_buffer = False

    def _extract_file_to_dir(self, file, flags, dirname, refresh_callback):
        """Extract a single file to directory"""
        descr = f"Extracting: {Path(file.path).name}"
        command = ArchiveDecompressor.get_command(file.path, flags.copy(), dirname)
        obj = CommandLoader(args=command, descr=descr, read=True)
        obj.signal_bind('after', refresh_callback)
        self.fm.loader.add(obj)
