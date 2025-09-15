# ranger-archives

A cross-platform plugin for [ranger](https://ranger.github.io) file manager that provides seamless archive compression and extraction. The plugin automatically detects and uses available archiver programs such as `tar`, `zip`, `7z`, and prioritizes parallelized versions like `pbzip2`, `pigz`, `pixz` for better performance.

## Key Features

- **Cross-platform compatibility** with intelligent tool detection and validation
- **Extensive format support**: 20+ formats including tar.gz, tar.bz2, tar.xz, tar.lz4, tar.zst, zip, 7z, rar, lzh, zpaq
- **Smart tool selection**: Prioritizes parallel compression tools (pigz, pbzip2, pixz) for better performance
- **Automatic fallback**: Uses alternative tools when preferred ones are unavailable
- **Safe operations**: Validates tool compatibility and handles encoding issues gracefully
- **Multiple extraction modes**: Extract to current directory, custom directory, or individual subdirectories
- **Custom flag support**: Pass specific flags to underlying compression/decompression tools
- **Auto-completion**: Tab completion for common archive formats in ranger
- **Standalone CLI**: Command-line interface for testing and automation outside ranger
- **Comprehensive testing**: Real-world test suite with file integrity verification

[![asciicast](https://asciinema.org/a/ii764wsN8rWZfMCwVlnJAWcPM.svg)](https://asciinema.org/a/ii764wsN8rWZfMCwVlnJAWcPM)

## Donate

If you find this plugin useful, please consider donating any amount of money. This will help me spend more time on supporting open-source software.

<a href="https://www.buymeacoffee.com/maximtrp" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

## Installation

Clone this repo into ranger plugins folder. In Linux, it is typically located here: `~/.config/ranger/plugins`.

```bash
cd ~/.config/ranger/plugins
git clone https://github.com/maximtrp/ranger-archives.git
```

## Usage

### Ranger Commands

* `:extract [DIRECTORY]` - Extract archives to current or specified directory
* `:extract_raw [FLAGS]` - Extract archives using custom flags (e.g., `-U` for Unicode handling)
* `:extract_to_dirs [FLAGS]` - Extract each archive to its own subdirectory based on filename
* `:compress [FLAGS] [FILENAME.EXT]` - Compress selected files/directories to archive with auto-naming

The compress command supports tab completion for common formats (.zip, .tar.gz, .tar.bz2, .tar.xz, .7z) and automatically names archives after the current directory if no filename is provided.

### Command Line Interface

The plugin includes a standalone CLI tool for testing and automation:

```bash
# Compress files
python3 archive_cli.py compress test.zip file1.txt file2.txt
python3 archive_cli.py compress test.tar.gz folder/ --flags="-v"

# Extract archives
python3 archive_cli.py decompress test.zip
python3 archive_cli.py decompress test.tar.gz --output=extract/
```

## Examples

### Extraction

#### Basic

Select an archive and type:

```
:extract some_dir
```

Or even just:

```
:extract
```

#### Using flags

This is an example of extracting a zip archive to a directory `dirname` and escaping all non-ASCII Unicode chars:

```
:extract_raw -U -d dirname
```

### Compression

#### Basic

Select a file or a folder (or multiple files and folder) in *ranger* and enter:

```
:compress files.zip
```

or (use quotation marks with filenames containing spaces)

```
:compress "my important files.zip"
```

#### Using flags 

`zip` archiver provides a flag for better compression ratio `-9` (just like `gzip` and many others).
We can just add it before an archive filename:

```
:compress -9 file.zip
```

The other flags can be used likewise.

## Shortcuts

Add these lines to `~/.config/ranger/rc.conf` for keyboard shortcuts:

```
map ex extract
map ec compress
```

## Testing

Run the comprehensive test suite to verify format support:

```bash
python3 test_real_world.py
```

This creates test data with various file types and validates compression/decompression for all available formats on your system. The test suite:

- Creates diverse test files (text, binary, Unicode, nested directories)
- Tests compression and decompression cycles
- Verifies file integrity using SHA256 checksums
- Measures performance and compression ratios
- Generates detailed reports with format compatibility

## Supported Formats

The plugin automatically detects and supports these formats based on available tools:

### Archive Formats
- **ZIP**: .zip (via zip/unzip or 7z)
- **7-Zip**: .7z (via 7z/7za)
- **RAR**: .rar (via rar/unrar or 7z)
- **TAR**: .tar (via tar or 7z)

### Compressed Archives
- **Gzip**: .tar.gz, .tgz (via tar + gzip/pigz)
- **Bzip2**: .tar.bz2, .tbz2 (via tar + bzip2/pbzip2/lbzip2)
- **XZ**: .tar.xz, .txz (via tar + xz/pixz)
- **LZ4**: .tar.lz4 (via tar + lz4)
- **Zstandard**: .tar.zst (via tar + zstd)
- **LZIP**: .tar.lz (via tar + lzip/plzip)
- **LRZIP**: .tar.lrz (via tar + lrzip)
- **LZOP**: .tar.lzop, .tzo (via tar + lzop)

### Single-file Compression
- **.gz**: via gzip/pigz
- **.bz2**: via bzip2/pbzip2/lbzip2
- **.xz**: via xz/pixz
- **.lz4**: via lz4
- **.lz**: via lzip/plzip
- **.lrz**: via lrzip
- **.lzop**: via lzop

### Legacy Formats
- **LHA/LZH**: .lha, .lzh (via lha)
- **ZPAQ**: .zpaq (via zpaq)
- **DEB**: .deb (via ar - extraction only)
