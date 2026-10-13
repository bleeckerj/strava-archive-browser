"""Compile the archive adapter against the existing FIT Preview decoder."""
from pathlib import Path
import platform
import subprocess
from settings import PROJECT, FIT_PREVIEW, NATIVE_READER


def build():
    if platform.system() != 'Darwin':
        raise SystemExit('The FIT Preview fallback requires macOS. Standard FIT, GPX and TCX imports use portable readers.')
    products = FIT_PREVIEW / '.build/DerivedData/Build/Products/Debug'
    core = FIT_PREVIEW / 'Sources/Core'
    names = ['RouteModel.swift', 'RouteGeometry.swift', 'FITTimestampExpander.swift', 'FITRouteDecoder.swift']
    inputs = [core / name for name in names]
    objects = [products / (name + '.o') for name in ['FITSwiftSDK', 'OrderedCollections', 'InternalCollectionsUtilities']]
    missing = [str(path) for path in inputs + objects if not path.is_file()]
    if missing:
        raise SystemExit('Build the FIT Preview repository first; required build inputs are missing:\n' + '\n'.join(missing))
    NATIVE_READER.parent.mkdir(exist_ok=True)
    command = ['swiftc', '-target', platform.machine() + '-apple-macos15.0',
               '-module-cache-path', str(NATIVE_READER.parent / 'swift-module-cache'),
               '-I', str(products)]
    command += [str(path) for path in inputs]
    command += [str(PROJECT / 'scripts/ArchiveFITReader.swift')]
    command += [str(path) for path in objects] + ['-o', str(NATIVE_READER)]
    print('Compiling FIT Preview archive adapter...', flush=True)
    subprocess.run(command, check=True)
    print('Native FIT reader ready.', flush=True)


if __name__ == '__main__':
    build()
