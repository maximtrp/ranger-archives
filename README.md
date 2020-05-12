# ranger-archives

This is a plugin for [ranger](https://ranger.github.io) file manager that makes it much easier to compress and extract archives. It depends on [atool](https://www.nongnu.org/atool/).

## Installation

### Method 1

Copy `compress.py` and `extract.py` files to `~/.config/ranger/plugins` folder and restart ranger.

### Method 2

Run the following commands in console:

```bash
git clone https://github.com/maximtrp/ranger-archives.git
cd ranger-archives
make install
```

## Usage

The following commands are available:

* `:extract [DIRECTORY]`: extracting files to current or specified directory (optional).
* `:extract_to_dirs`: extracting each archive to a separate directory. E.g.: `1.zip` to dir `1`, `2.zip` to dir `2`, etc.
* `:compress [FILENAME.EXT]`: compressing selected/marked files/directories to an archive. If an archive filename is not specified, it will be named after a parent dir.

## Shortcuts

You can also add these lines to `~/.config/ranger/rc.conf` to use these keyboard shortcuts (`ec`, `ex`):

```
map ex extract
map ec compress
```
