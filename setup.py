import sys

from cx_Freeze import setup, Executable

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

options = {
    'build_exe': {
        'includes': 'atexit'
    }
}

executables = [
    Executable('main.py', base=base)
]

setup(name='main',
      version='0.1',
      description='Sample cx_Freeze PyQt4 script',
      options=options,
      executables=executables
      )