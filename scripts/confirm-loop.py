#!/usr/bin/env python3
"""Run a command under a PTY and auto-confirm Claude Code's startup prompts.

`claude --dangerously-load-development-channels …` does two things that block an
unattended, headless launch:

  1. It requires a TTY. With stdout redirected to a file (a log), Claude falls
     back to `--print` mode and exits with "Input must be provided…". This
     wrapper gives the child a real pseudo-terminal so Claude runs interactively
     even when its output is captured to a file.
  2. It shows up to two confirmation prompts — the development-channel warning
     and, on first run, a "New MCP server found … Enter to confirm" trust
     dialog. This wrapper sends Enter to each.

Claude's TUI positions words with cursor-move escapes instead of literal spaces,
so a raw substring match on "Enter to confirm" fails. We strip ANSI escapes and
whitespace before matching "entertoconfirm" / "esctocancel", and fire on the
prompt's absent→present edge so any number of prompts are answered in order. A
periodic fallback covers prompts the markers miss.

Usage:  python3 confirm-loop.py <command> [args...]
"""
import os, sys, pty, tty, termios, select, signal, struct, fcntl, time, re

# Markers searched in the normalized (ANSI-stripped, whitespace-stripped, lower)
# stream. Both prompts render "Enter to confirm · Esc to cancel".
MARKERS_NORM = (b"entertoconfirm", b"esctocancel")
MIN_INTERVAL = 1.2     # min seconds between sends, to avoid double-firing on a redraw
FALLBACK_SECS = 25     # if output stalls while still armed, send Enter once as a safety
MAX_SENDS = 8          # hard cap on total sends, in case a marker appears in normal output
BUF_LIMIT = 8192       # bytes of recent output kept for marker matching

_ANSI = re.compile(rb"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][0-9A-B]|\x1b[=>]")
_WS = re.compile(rb"\s+")


def normalize(buf):
    return _WS.sub(b"", _ANSI.sub(b"", buf)).lower()


def has_marker(norm):
    return any(m in norm for m in MARKERS_NORM)


def get_winsize(fd):
    try:
        return struct.unpack("HHHH", fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\x00" * 8))[:2]
    except OSError:
        return (40, 120)


def set_winsize(fd, rows, cols):
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def main():
    argv = sys.argv[1:]
    if not argv:
        sys.stderr.write("usage: confirm-loop.py <command> [args...]\n")
        return 2

    pid, master = pty.fork()
    if pid == 0:                       # child: become the real command
        os.execvp(argv[0], argv)
        os._exit(127)

    out = sys.stdout.fileno()
    set_winsize(master, *(get_winsize(out) if os.isatty(out) else (40, 120)))

    stdin_fd = sys.stdin.fileno()
    saved = termios.tcgetattr(stdin_fd) if os.isatty(stdin_fd) else None
    if saved is not None:
        tty.setraw(stdin_fd)

    signal.signal(signal.SIGWINCH, lambda *_: os.isatty(out) and set_winsize(master, *get_winsize(out)))

    watch = [master, stdin_fd]
    buf = b""
    armed = True                       # True while no prompt is on screen; arm→send→disarm
    last_send = 0.0
    last_output = time.monotonic()
    sends = 0

    def send_enter(now):
        nonlocal armed, last_send, sends, buf
        os.write(master, b"\r")
        armed, last_send, sends, buf = False, now, sends + 1, b""

    try:
        while True:
            try:
                rlist, _, _ = select.select(watch, [], [], 1)
            except (OSError, select.error):
                continue
            now = time.monotonic()

            if master in rlist:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    data = b""
                if not data:           # child exited → EOF
                    break
                os.write(out, data)
                last_output = now
                buf = (buf + data)[-BUF_LIMIT:]
                if has_marker(normalize(buf)):
                    if armed and sends < MAX_SENDS and now - last_send >= MIN_INTERVAL:
                        send_enter(now)
                else:
                    armed = True        # prompt cleared → re-arm for the next one

            if stdin_fd in rlist:
                try:
                    data = os.read(stdin_fd, 65536)
                except OSError:
                    data = b""
                if not data:           # stdin closed → stop watching it (avoid busy loop)
                    watch.remove(stdin_fd)
                else:
                    os.write(master, data)

            # Safety: if output stalls while still armed, send Enter once.
            if armed and sends < MAX_SENDS and now - last_output >= FALLBACK_SECS and now - last_send >= FALLBACK_SECS:
                send_enter(now)
    finally:
        if saved is not None:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, saved)

    _, status = os.waitpid(pid, 0)
    if hasattr(os, "waitstatus_to_exitcode"):
        return os.waitstatus_to_exitcode(status)
    return (status >> 8) if os.WIFEXITED(status) else 1


if __name__ == "__main__":
    sys.exit(main())
