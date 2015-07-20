# -*- coding: utf-8 -*-

from argparse import ArgumentParser, FileType
from contextlib import closing
from json import dumps
from math import ceil
from os.path import basename, dirname, exists, join
from struct import unpack
from subprocess import Popen
from tempfile import NamedTemporaryFile

from jinja2 import FileSystemLoader, Template
from jinja2.environment import  Environment


DEFAULT_TEMPLATE = join(dirname(__file__), 'templates', 'static.jinja2')


# http://blog.taz.net.au/2012/04/09/getting-the-terminal-size-in-python/
def probeDimensions(fd=1):
    """
    Returns height and width of current terminal. First tries to get
    size via termios.TIOCGWINSZ, then from environment. Defaults to 25
    lines x 80 columns if both methods fail.

    :param fd: file descriptor (default: 1=stdout)
    """
    try:
        import fcntl, termios, struct
        hw = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
    except:
        try:
            hw = (os.environ['LINES'], os.environ['COLUMNS'])
        except:  
            hw = (24, 80)

    return hw

def escapeString(string):
    string = string.encode('unicode_escape').decode('utf-8')
    string = string.replace("'", "\\'")
    string = '\'' + string + '\''
    return string

def runTtyrec(command=None):
    scriptfname = None
    CMD = ['ttyrec']

    with NamedTemporaryFile(delete=False) as scriptf:
        scriptfname = scriptf.name

    if command:
        CMD.append('-e')
        CMD.append(command)

    CMD.append(scriptfname)

    proc = Popen(CMD)
    proc.wait()
    return open(scriptfname, 'rb')

def parseTtyrec(scriptf):
    pos = 0
    offset = 0
    oldtime = 0
    ret = []

    with closing(scriptf):
        data = scriptf.read()
        while pos < len(data):
            secs, usecs, amount = unpack('iii', data[pos:pos+12])
            pos += 12
            timing = int(ceil(secs * 1000 + float(usecs) / 1000))
            if oldtime:
                offset += timing - oldtime
            oldtime = timing
            ret.append((escapeString(data[pos:pos+amount].decode(
                        encoding='utf-8', errors='replace')), offset))
            pos += amount
    return dumps(ret)

def renderTemplate(json, dimensions, templatename):
    fsl = FileSystemLoader(dirname(templatename), 'utf-8')
    e = Environment()
    e.loader = fsl

    templatename = basename(templatename)
    return e.get_template(templatename).render(json=json, dimensions=dimensions)


if __name__ == '__main__':
    argparser   =   ArgumentParser(description=
                                        'Stores terminal sessions into HTML.')

    argparser.add_argument('-c', '--command', type=str,
                           help='ttyrec -e command. Invoke command when ttyrec starts', required=False)
    argparser.add_argument('-d', '--dimensions', type=int,
                           metavar=('h','w'), nargs=2,
                           help='dimensions of terminal', required=False)
    argparser.add_argument('-o', '--output-file', type=FileType('w'),
                           help='file to output HTML to', required=False)
    argparser.add_argument('-s', '--script-file', type=str,
                           help='script file to parse', required=False)

    ns = argparser.parse_args()

    command     =   ns.command
    dimensions  =   ns.dimensions
    scriptf     =   ns.script_file
    outf        =   ns.output_file

    if not dimensions:
        dimensions = probeDimensions() if not scriptf else (24,80)

    if not scriptf:
        scriptf = runTtyrec(command)
    else:
        scriptf = open(scriptf, 'rb')

    json = parseTtyrec(scriptf)

    tmpname = DEFAULT_TEMPLATE

    rendered = renderTemplate(json, dimensions, tmpname)

    if outf:
        with closing(outf):
            outf.write(rendered)
    else:
        print rendered
