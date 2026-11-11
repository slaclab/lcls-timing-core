import os

from setuptools import setup
from setuptools.command.build_py import build_py
from git import Repo

repo = Repo()

# Get version before adding version file
ver = repo.git.describe('--tags')
ver = ver.replace('-', '+', 1) # https://github.com/pypa/setuptools/issues/3772

class BuildPyWithVersion(build_py):
    """Append the version constant to the built package, never to the tracked source."""
    def run(self):
        super().run()
        init = os.path.join(self.build_lib, 'LclsTimingCore', '__init__.py')
        with open(init) as vf:
            lines = [l for l in vf.read().splitlines() if not l.startswith('__version__=')]
        with open(init, 'w') as vf:
            vf.write('\n'.join(lines) + f'\n\n__version__="{ver}"\n')

setup (
   name='lcls_timing_core',
   version=ver,
   packages=['LclsTimingCore', ],
   package_dir={'':'python'},
   cmdclass={'build_py': BuildPyWithVersion},
)
