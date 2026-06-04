import os, sys, subprocess

os.chdir(r'D:\work\research\agents-nexus\packages\server')
src_dir = os.path.join(os.getcwd(), 'src')

env = os.environ.copy()
env['PYTHONPATH'] = src_dir

# Run server.py directly instead of through uvicorn module import
proc = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'server:app', '--host', '0.0.0.0', '--port', '8097'],
    env=env,
    cwd=src_dir  # Run from src directory so 'server' resolves correctly
)
proc.wait()
