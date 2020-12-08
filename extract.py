import os
from ranger.api.commands import *
from ranger.core.loader import CommandLoader

class extract(Command):
    def execute(self):
        """Extract copied files to current directory or directory
        specified in a command line
        """

        cwd = self.fm.thisdir
        copied_files = cwd.get_selection()

        if not copied_files:
            return

        def refresh(_):
            cwd = self.fm.get_directory(original_path)
            cwd.load_content()

        one_file = copied_files[0]
        cwd = self.fm.thisdir
        original_path = cwd.path

        line_args = self.line.split()[1:]
        if line_args:
            extraction_dir = os.path.join(cwd.path, "".join(line_args))
            os.makedirs(extraction_dir, exist_ok=True)
            flags = ['-X', extraction_dir]
            flags += ['-e']
        else:
            flags = ['-X', cwd.path]
            flags += ['-e']

        self.fm.copy_buffer.clear()
        self.fm.cut_buffer = False

        if len(copied_files) == 1:
            descr = "Extracting: " + os.path.basename(one_file.path)
        else:
            descr = "Extracting files from: " + os.path.basename(one_file.dirname)
        obj = CommandLoader(args=['aunpack'] + flags \
            + [f.path for f in copied_files], descr=descr, read=True)

        obj.signal_bind('after', refresh)
        self.fm.loader.add(obj)

class extract_to_dirs(Command):
    def execute(self):
        """ Extract copied files to a subdirectories """

        cwd = self.fm.thisdir
        original_path = cwd.path
        copied_files = cwd.get_selection()

        if not copied_files:
            return

        def refresh(_):
            cwd = self.fm.get_directory(original_path)
            cwd.load_content()

        def make_flags(fn):
            fn_wo_ext = os.path.basename(os.path.splitext(fn)[0])
            flags = ['-X', fn_wo_ext]
            return flags

        one_file = copied_files[0]
        self.fm.copy_buffer.clear()
        self.fm.cut_buffer = False

        # Making description line
        if len(copied_files) == 1:
            descr = "Extracting: " + os.path.basename(one_file.path)
        else:
            descr = "Extracting files from: " + os.path.basename(one_file.dirname)

        # Extracting files
        for f in copied_files:
            obj = CommandLoader(
                args=['aunpack'] + make_flags(f.path) + [f.path],
                descr=descr, read=True
            )
            obj.signal_bind('after', refresh)
            self.fm.loader.add(obj)
