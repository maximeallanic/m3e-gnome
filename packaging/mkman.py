#!/usr/bin/env python3
"""Write a short man page for one script from its --help text.

usage: mkman.py NAME VERSION SUMMARY < help-text > NAME.1

The help text is shown verbatim in a no-fill block (so it stays correct whatever its width), after a
short NAME/DESCRIPTION header, followed by FILES and SEE ALSO sections. Hyphens and backslashes are escaped
for roff; lines starting with a dot or an apostrophe are protected.
"""
import sys


def roff(line):
    line = line.replace('\\', '\\e').replace('-', '\\-')
    if line.startswith(('.', "'")):
        line = '\\&' + line
    return line


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    name, version, summary = sys.argv[1:]
    text = sys.stdin.read().rstrip('\n')
    out = [
        f'.TH {name.upper()} 1 "" "m3e-gnome {version}" "User Commands"',
        '.SH NAME',
        roff(f'{name} - {summary}'),
        '.SH DESCRIPTION',
        'This is the output of the command with \\fB\\-\\-help\\fR. Inside it the script is called by its name in the',
        'source tree (for example ./install.sh); with the package, use the command name above.',
        '.PP',
        '.nf',
    ]
    out += [roff(l) for l in text.split('\n')]
    out += [
        '.fi',
        '.SH FILES',
        '.TP',
        '.I /usr/share/m3e\\-gnome',
        'The read-only tree the commands run from.',
        '.TP',
        '.I ~/.local/share/m3e\\-gnome',
        'Manifest and backups of what the installer changed.',
        '.SH SEE ALSO',
        '.BR m3e\\-gnome\\-install (1),',
        '.BR m3e\\-gnome\\-uninstall (1),',
        '.BR m3e\\-gnome\\-verify (1),',
        '/usr/share/doc/m3e\\-gnome/README.md',
    ]
    print('\n'.join(out))


main()
