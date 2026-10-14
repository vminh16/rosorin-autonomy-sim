"""Show the demo console log in the terminal window; exit on the __END__ line."""
import sys
import time
path = sys.argv[1]
sys.stdout.write('\033]0;demo console\007\033[2J\033[H'); sys.stdout.flush()
pos = 0
while True:
    try:
        with open(path) as f:
            f.seek(pos); chunk = f.read(); pos = f.tell()
    except FileNotFoundError:
        chunk = ''
    if '__END__' in chunk:
        sys.stdout.write(chunk.split('__END__')[0]); sys.stdout.flush(); time.sleep(1); break
    if chunk:
        sys.stdout.write(chunk); sys.stdout.flush()
    time.sleep(0.03)
