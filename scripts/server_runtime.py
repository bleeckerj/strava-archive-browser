"""Track server instances and provide operator status and shutdown commands."""
from datetime import datetime
from pathlib import Path
import json
import os
import signal
import sys
import time

from server_processes import InspectionError, inspect_process, listening_processes, project_servers


def record_path(project, pid):
    return project / '.runtime' / 'servers' / f'{pid}.json'


def register_server(project, port):
    record = {
        'pid': os.getpid(),
        'port': port,
        'url': f'http://127.0.0.1:{port}/',
        'project': str(project),
        'command': [sys.executable, str(Path(sys.argv[0]).resolve()), *sys.argv[1:]],
        'started_at': datetime.now().astimezone().isoformat(timespec='seconds'),
    }
    path = record_path(project, record['pid'])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, indent=2) + '\n')
    temporary.replace(path)
    return path


def print_process(process):
    print(f'  PID:      {process.listener.pid}')
    print(f'  Listening: {", ".join(process.listener.addresses)}')
    print(f'  Folder:   {process.directory or "Unavailable"}')
    print(f'  Command:  {process.command}')
    print(f'  Started:  {process.started} (local time; running {process.elapsed})')


def show_status(project, port=None):
    servers = project_servers(project, port)
    if not servers:
        print(f'No Strava archive browser servers running for {project}.')
        if port is not None:
            return show_conflict(project, port)
        return 0
    for process in servers:
        print('Strava archive browser is running:')
        print_process(process)
        path = record_path(project, process.listener.pid)
        print(f'  Record:   {path if path.exists() else "Legacy instance; discovered from its live process"}')
        for actual_port in sorted(process.listener.ports):
            print(f'  Open:     http://127.0.0.1:{actual_port}/')
            print(f'  Stop:     python3 scripts/serve.py stop --port {actual_port}')
    return 0


def show_conflict(project, port):
    listeners = listening_processes(port)
    if not listeners:
        print(f'Port {port} has no visible TCP listener. Try again or inspect it with lsof -nP -iTCP:{port}.')
        return 0
    print(f'Port {port} is already in use:', flush=True)
    for listener in listeners:
        try:
            process = inspect_process(listener)
        except InspectionError as error:
            print(f'  PID {listener.pid}: {listener.name}; {error}')
            continue
        print_process(process)
        if process.belongs_to(project):
            print(f'  Open:     http://127.0.0.1:{port}/')
            print(f'  Stop:     python3 scripts/serve.py stop --port {port}')
        else:
            print('  This listener belongs to another program and will be left running.')
    print('Inspect this project: npm run status')
    print('Choose another port: python3 scripts/serve.py --port PORT')
    return 0


def stop_servers(project, port=None):
    servers = project_servers(project, port)
    if not servers:
        print(f'No Strava archive browser servers running for {project}.')
        if port is not None:
            show_conflict(project, port)
        return 0
    result = 0
    for process in servers:
        pid = process.listener.pid
        current = inspect_process(process.listener)
        if not current.belongs_to(project) or current.started != process.started:
            raise InspectionError(f'PID {pid} changed identity; no signal sent.')
        print(f'Stopping Strava archive browser PID {pid} on port(s) {", ".join(map(str, sorted(process.listener.ports)))}...', flush=True)
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 5
        while any(listener.pid == pid for listener in listening_processes()):
            if time.monotonic() >= deadline:
                print(f'PID {pid} still has a listener after 5 seconds. Run npm run status to inspect it.', flush=True)
                result = 1
                break
            time.sleep(0.1)
        else:
            record_path(project, pid).unlink(missing_ok=True)
            print(f'Stopped PID {pid}; its listening socket is closed.', flush=True)
    return result
