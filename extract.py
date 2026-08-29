from pathlib import Path
from ranger.api.commands import Command
from ranger.core.loader import CommandLoader
from .archives_utils import parse_escape_args, ArchiveDecompressor


class extract(Command):
    def execute(self):
        """Extract files to current directory or specified directory"""
        files = self.fm.thisdir.get_selection()
        if not files:
            return

        cwd_path = Path(self.fm.thisdir.path)

        def refresh(_):
            self.fm.get_directory(str(cwd_path)).load_content()

        arguments = parse_escape_args(self.line.strip())[1:]
        if len(arguments) > 1:
            self.fm.notify("Usage: extract [directory]", bad=True)
            return
        dirname_raw = str(cwd_path / arguments[0]) if arguments else None
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
        command = ArchiveDecompressor.get_command(file.path, [], dirname_raw)
        if not command:
            self.fm.notify(f"No extraction tool available for {file.path}", bad=True)
            return
        obj = CommandLoader(
            args=command,
            descr=descr,
            read=False,
            popenArgs={"cwd": self.fm.thisdir.path},
        )
        obj.signal_bind("after", refresh_callback)
        self.fm.loader.add(obj)


class extract_raw(Command):
    def execute(self):
        """Extract files with custom flags"""
        files = self.fm.thisdir.get_selection()
        if not files:
            return

        cwd_path = self.fm.thisdir.path

        def refresh(_):
            self.fm.get_directory(cwd_path).load_content()

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
        if not command:
            self.fm.notify(f"No extraction tool available for {file.path}", bad=True)
            return
        obj = CommandLoader(
            args=command,
            descr=descr,
            read=False,
            popenArgs={"cwd": self.fm.thisdir.path},
        )
        obj.signal_bind("after", refresh_callback)
        self.fm.loader.add(obj)


class extract_to_dirs(Command):
    def execute(self):
        """Extract files to subdirectories"""
        files = self.fm.thisdir.get_selection()
        if not files:
            return

        cwd_path = Path(self.fm.thisdir.path)

        def refresh(_):
            self.fm.get_directory(str(cwd_path)).load_content()

        flags = parse_escape_args(self.line.strip())[1:]
        self._clear_buffers()

        for file in files:
            dirname = cwd_path / Path(file.path).stem
            self._extract_file_to_dir(file, flags, dirname, refresh)

    def _clear_buffers(self):
        """Clear ranger buffers"""
        self.fm.copy_buffer.clear()
        self.fm.cut_buffer = False

    def _extract_file_to_dir(self, file, flags, dirname, refresh_callback):
        """Extract a single file to directory"""
        descr = f"Extracting: {Path(file.path).name}"
        command = ArchiveDecompressor.get_command(file.path, flags.copy(), dirname)
        if not command:
            self.fm.notify(f"No extraction tool available for {file.path}", bad=True)
            return
        obj = CommandLoader(
            args=command,
            descr=descr,
            read=False,
            popenArgs={"cwd": self.fm.thisdir.path},
        )
        obj.signal_bind("after", refresh_callback)
        self.fm.loader.add(obj)
