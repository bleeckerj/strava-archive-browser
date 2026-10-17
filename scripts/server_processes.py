"""Identify local listeners and verify ownership before stopping a server."""
from dataclasses import dataclass
from pathlib import Path
import re
import shlex
import subprocess


class InspectionError(RuntimeError):
    pass


def run_inspection(arguments):
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise InspectionError(f'Cannot run {arguments[0]}: {error}') from error
    if result.returncode and (result.stderr.strip() or result.returncode != 1):
        raise InspectionError(result.stderr.strip() or f'{arguments[0]} failed')
    return result.stdout


@dataclass
class Listener:
    pid: int
    name: str
    addresses: list

    @property
    def ports(self):
        return {int(address.rsplit(':', 1)[1]) for address in self.addresses}


@dataclass
class ServerProcess:
    listener: Listener
    command: str
    directory: str
    started: str
    elapsed: str

    def belongs_to(self, project):
        try:
            arguments = shlex.split(self.command)
            interpreter, script = arguments[:2]
            return (
                re.fullmatch(r'python(?:\d+(?:\.\d+)*)?', Path(interpreter).name.lower()) is not None
                and bool(self.directory or Path(script).is_absolute())
                and (Path(self.directory) / script).resolve() == project.resolve() / 'scripts' / 'serve.py'
            )
        except (ValueError, OSError):
            return False


def listening_processes(port=None):
    selector = f'-iTCP:{port}' if port is not None else '-iTCP'
    output = run_inspection(['lsof', '-nP', selector, '-sTCP:LISTEN', '-Fpcn'])
    listeners = []
    current = None
    for line in output.splitlines():
        if line.startswith('p'):
            current = Listener(int(line[1:]), '', [])
            listeners.append(current)
        elif current is not None and line.startswith('c'):
            current.name = line[1:]
        elif current is not None and line.startswith('n'):
            current.addresses.append(line[1:])
    return listeners


def inspect_process(listener):
    output = run_inspection(['ps', '-p', str(listener.pid), '-o', 'lstart=,etime=,command='])
    fields = output.strip().split(None, 6)
    if len(fields) != 7:
        raise InspectionError(f'PID {listener.pid} exited or its command is unavailable.')
    cwd_output = run_inspection(['lsof', '-a', '-p', str(listener.pid), '-d', 'cwd', '-Fn'])
    directory = next((line[1:] for line in cwd_output.splitlines() if line.startswith('n')), '')
    return ServerProcess(listener, fields[6], directory, ' '.join(fields[:5]), fields[5])


def project_servers(project, port=None):
    servers = []
    for listener in listening_processes(port):
        if not listener.name.lower().startswith('python'):
            continue
        process = inspect_process(listener)
        if process.belongs_to(project):
            servers.append(process)
    return servers
