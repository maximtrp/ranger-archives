import os
from ranger.api.commands import *
from ranger.core.loader import CommandLoader

class compress(Command):
    def execute(self):
        """ Compress marked files to current directory """
        cwd = self.fm.thisdir
        marked_files = cwd.get_selection()

        if not marked_files:
            return

        def refresh(_):
            cwd = self.fm.get_directory(original_path)
            cwd.load_content()

        original_path = cwd.path

        # Parsing arguments line
        parts = self.line.strip().split()
        if len(parts) > 1:
            au_flags = [' '.join(parts[1:])]
        else:
            au_flags = [os.path.basename(self.fm.thisdir.path) + '.zip']

        # Making description line
        files_num = len(marked_files)
        files_num_str = str(files_num) + ' objects' if files_num > 1 else '1 object'
        descr = "Compressing " + files_num_str + " -> " + os.path.basename(au_flags[0])

        # Creating archive
        obj = CommandLoader(args=['apack'] + au_flags + \
                [os.path.relpath(f.path, cwd.path) for f in marked_files], descr=descr, read=True)

        obj.signal_bind('after', refresh)
        self.fm.loader.add(obj)

    def tab(self, tabnum):
        """ Complete with current folder name """

        extension = ['.zip', '.tar.gz', '.rar', '.7z']
        return ['compress ' + os.path.basename(self.fm.thisdir.path) + ext for ext in extension]
