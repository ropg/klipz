"""
Running klipz from the command line will present a character-based clipboard
manager using curses. The user can scroll through past clips and save some
to a special "Saved Clippings" screen. Lots of other features, and great
configurability through a config file that can have python functions in it.

Install with "pip install klipz", see https://github.com/ropg/klipz for the
documentation and issue tracker.
"""
import argparse
import ast
import curses
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import pkg_resources
import pyperclip

# consts
SAVED_HEADER = "Saved Clippings"
SAVED_FILENAME = "saved_clips"
BUFFER_FILENAME = "buffer"
DEFAULT_CONFIG_DIR = "~/.klipz"
CONFIG_FILENAME = "config.py"
ALWAYS = 1000

# global vars
screen = False
width = 0
compare = None
buffer = None
saved_clips = None
displayed = None
selected = 0
bottom = 0
has_upped = False
offset_in_clip = 0
registered_keys = {}
SIGWINCH_works = False
quitting = False


def command_line_arguments():
    """
    This has to be in a separate function for the argparse plugin for the
    sphinx automatic documentation to work.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", "-v", help="Print version number and exit.",
                    action="store_true")
    ap.add_argument("--configdir", "-c", help="By default, .klipz expects its "
                    "config.py in ~/.klipz, but this can be set with this "
                    "option. This is also where the saved_clips file is "
                    "stored.", default=DEFAULT_CONFIG_DIR)
    ap.add_argument("--leavecrlf", "-l", help="By default, klipz removes "
                    "beginning and ending carriage returns and line feeds "
                    "from the all clips. Use this option if you do not want "
                    "that.", action="store_true")
    ap.add_argument("--buffersize", "-b",
                    help="Number of clips in scrollback buffer. By default, "
                    "klipz will show up to 100 clippings.", type=int,
                    default=100)
    return ap


def main():
    """
    Primary klipz entry point
    """
    global cmdline, saved_clips, buffer, displayed, compare
    ap = command_line_arguments()
    cmdline = ap.parse_args()
    if cmdline.version:
        print(pkg_resources.get_distribution("klipz").version)
        sys.exit(0)
    register_default_keys()
    read_config_file()
    saved_clips = from_disk(SAVED_FILENAME)
    buffer = from_disk(BUFFER_FILENAME)
    displayed = buffer
    compare = buffer[0]
    curses.wrapper(worker)


def register_default_keys():
    """
    Register map of keys to functions.
    """
    register_key("e", call_editor)
    register_key("s", toggle_saved)
    register_key("u", move_up)
    register_key("d", move_down)
    register_key("c", delete_clip)
    register_key(curses.KEY_UP, up)
    register_key(curses.KEY_DOWN, down)
    register_key(curses.KEY_LEFT, scroll_left)
    register_key(curses.KEY_RIGHT, scroll_right)


def read_config_file():
    """
    Read klipz configuration file.
    """
    fn = os.path.expanduser(cmdline.configdir + "/" + CONFIG_FILENAME)
    try:
        exec(open(fn).read(), globals())
    except FileNotFoundError:
        pass


def to_disk(tofile, cliplist):
    """
    Write klipz saved clips to disk.
    """
    fn = os.path.expanduser(cmdline.configdir) + "/" + tofile
    try:
        os.mkdir(os.path.expanduser(cmdline.configdir))
    except FileExistsError:
        pass
    try:
        with open(fn, "wb") as f:
            f.write(repr(cliplist).encode("utf-8"))
    except OSError:
        pass


def from_disk(fromfile):
    """
    Load saved klipz clips from disk.
    """
    fn = os.path.expanduser(cmdline.configdir) + "/" + fromfile
    try:
        with open(fn, "rb") as f:
            return ast.literal_eval(f.read().decode("utf-8"))
    except OSError:
        return [""]


def worker(scr):
    """
    Primary klipz worker loop.
    """
    global screen
    screen = scr
    curses.use_default_colors()
    screen.timeout(0)
    redraw()
    signal.signal(signal.SIGWINCH, handle_resize)
    signal.signal(signal.SIGTERM, _quit)
    while not quitting:
        try:
            poll_keys()
            poll_clipboard()
            time.sleep(0.1)
        except KeyboardInterrupt:
            _quit()


def poll_keys():
    """
    Will handle keys until there are no more in the curses buffer. It will
    look up the key in registered keys and call *execute_function*.
    The .get will return None if the key is not in the dictionary, and
    execute_function will just return if it gets that, so this needs not care
    if the key exists or not.
    """
    global compare, offset_in_clip
    key = 0
    while key != -1:
        key = screen.getch()
        if key == curses.KEY_RESIZE and not SIGWINCH_works:
            handle_resize()
        clip = displayed[selected]
        clip = execute_function(key, clip)
        if clip:
            displayed[selected] = clip
            copy_to_clipboard(clip)
            offset_in_clip = 0
        redraw()


def poll_clipboard():
    """
    Will get the paste buffer, clip off and cr's and lf's if needed and
    compare it to the global *compare* variable to see if we've seen it.
    If not, store it in *buffer*, first switching back to the clipboard view
    if we were in "Saved Clippings" view. Also manages maximum buffer size.
    It also executes the function associated with special key ``ALWAYS``, which
    can be tied to a function that always executes for a new clipping.
    """
    global selected, compare, offset_in_clip
    p = pyperclip.paste()
    if not p or p == compare:
        return
    p = cutcrlf(p)
    ret = execute_function(ALWAYS, p)
    if ret:
        p = ret
    if p != pyperclip.paste():
        pyperclip.copy(p)
    if saved_clips is displayed:
        toggle_saved()
    if buffer[0] == "":
        buffer[0] = p
    else:
        buffer.insert(0, p)
    if len(buffer) >= cmdline.buffersize:
        buffer.pop(-1)
    selected = 0
    compare = p
    buffer[0] = p
    offset_in_clip = 0
    redraw()


def _quit(signum=None, frame=None):
    """
    *_quit* is called by signal handlers as well as other callers who want to
    exit. It causes the main loop in *worker* to end, which returns to main and
    resets the terminal properly for non-curses use.
    """
    global quitting
    quitting = True
    if saved_clips is displayed:
        to_disk(SAVED_FILENAME, saved_clips)


def register_key(key, func=None, args=None):
    """
    *register_key* registers a key and ties it to a function to execute. The
    key is either a one-letter string or a key constant from the curses
    library.
    If no args are provided, it means it will call a function with only the
    clipboard contents as an argument and replacing the clipboard with the
    return value from the function (see *execute_function*). If None is passed
    as *args*, the function is merely executed without any arguments and
    nothing else happens.
    *register_key* with only a key as an argument will unregister that key.
    """
    global registered_keys
    if isinstance(key, str):
        key = ord(key)
    if not func and registered_keys.get(key):
        del registered_keys[key]
        return
    if not args:
        args = []
    registered_keys[key] = (func, args)


def execute_function(key, clip):
    """
    *execute_function* gets the current clip and a key value and then sees if
    there is a function registered for that key. If there is it executes. If
    the function returns a string this string is returned, otherwise None.
    """
    lookup = registered_keys.get(key)
    if not lookup:
        return
    (func, args) = lookup
    args = args[:]      # decouple from the list kept in registered_keys
    if type(args) == str:
        args = [args]
    args.insert(0, clip)
    returned = func(*args)
    if type(returned) == str:
        return cutcrlf(returned)


def handle_resize(signum=None, frame=None):
    """
    *handle_resize* handles a terminal resize event. Linux and Mac have a
    signal for that (SIGWINCH), on windows one has to wait for *KEY_RESIZE*
    in a curses *getch* loop. I couldn't get these to come unless I was writing
    to the screen continuously, so this prefers the signal if it's available
    and sets SIGWINCH_works to make sure we don't also parse the KEY_RESIZE.
    """
    global SIGWINCH_works, screen, bottom, offset_in_clip
    if signum or frame:
        SIGWINCH_works = True
    curses.endwin()
    screen = curses.initscr()
    screen.clear()
    curses.resizeterm(*screen.getmaxyx())
    bottom = max(0, selected - curses.LINES + 1)
    offset_in_clip = 0
    redraw()


def redraw():
    """
    *redraw* redraws the displayed clippings and the cursor. It checks whether
    the *displayed* variable point to *saved_clips* to see if it needs to draw
    the 'Saved Clippings' header at the top line.
    """
    global width
    screen.clear()
    width = curses.COLS
    index = curses.LINES + bottom
    if saved_clips is displayed:
        screen.addstr(0, 0, " " * width, curses.A_REVERSE)
        screen.addstr(0, int((width / 2) - (len(SAVED_HEADER) / 2)),
                      SAVED_HEADER, curses.A_REVERSE)
        index -= 1
    while index > bottom:
        index -= 1
        if index >= len(displayed):
            continue
        disp = displayed[index].replace("\n", "↵").replace("\t", "⇥")
        current_line = curses.LINES - 1 - index + bottom
        cursor_state = curses.A_NORMAL
        if index == selected:
            disp = disp[offset_in_clip:]
            cursor_state = curses.A_REVERSE
#            screen.addnstr(current_line, 0, " " * width, width, cursor_state)
        try:
            # May throw exception and even wrap ugly on non-fixed-width chars
            # (e.g. emoticons).  Since we do not control terminal or font there
            # is simply nothing we can do about it.
            disp += " " * width
            screen.addnstr(current_line, 0, disp, width, cursor_state)
        except:
            pass
    screen.move(curses.LINES - 1 - selected + bottom, 0)
    screen.refresh()


def up(clip=None):
    """
    *up* moves the cursor up in the list of clips, scrolling if necessary.
    """
    global selected, bottom, offset_in_clip
    if selected < len(displayed) - 1:
        selected += 1
        top = bottom + curses.LINES
        if saved_clips is displayed:
            top -= 1
        if selected >= top:
            bottom += 1
        copy_to_clipboard(displayed[selected])
        offset_in_clip = 0
        redraw()


def down(clip=None):
    """
    *down* moves the cursor down in the list of clips, scrolling if necessary.
    """
    global selected, bottom, offset_in_clip
    if selected > 0:
        selected -= 1
        if selected < bottom:
            bottom = selected
        copy_to_clipboard(displayed[selected])
        offset_in_clip = 0
        redraw()


def scroll_left(clip=None):
    """
    *scroll_left* scrolls left in the text for the selected item.
    """
    global offset_in_clip
    offset_in_clip -= width
    offset_in_clip = max(0, offset_in_clip)
    redraw()


def scroll_right(clip=None):
    """
    *scroll_right* scrolls right in the text for the selected item.
    """
    global offset_in_clip
    offset_in_clip += width
    offset_in_clip = min(len(displayed[selected]) - width, offset_in_clip)
    offset_in_clip = max(0, offset_in_clip)
    redraw()


def move_down(clip=None):
    """
    *move_down* moves an item down the list by swapping it with the item below
    and making that the current item.
    """
    global selected
    if buffer is displayed:
        return
    if selected > 0:
        saved_clips[selected - 1], saved_clips[selected] = \
            saved_clips[selected], saved_clips[selected - 1]
        selected -= 1
        redraw()


def move_up(clip=None):
    """
    *move_up* moves an item up the list by swapping it with the item below
    and making that the current item.
    """
    global has_upped, selected
    if buffer is displayed:
        return
    if selected == 0 and not has_upped:
        has_upped = True
        saved_clips.insert(0, "")
        selected = 1
        redraw()
    elif selected < len(saved_clips) - 1:
        saved_clips[selected + 1], saved_clips[selected] = \
            saved_clips[selected], saved_clips[selected + 1]
        selected += 1
        redraw()


def delete_clip(clip=None):
    """
    *delete_clip* does what it says on the label, it deletes the current clip
    in the current view.
    """
    global selected
    if (saved_clips is displayed and selected == 0) or len(displayed) == 1:
        displayed[0] = ""
    else:
        del displayed[selected]
        if selected >= len(displayed):
            selected -= 1
            selected = max(0, selected)
    redraw()


def toggle_saved(clip=None):
    """
    *toggle_saved* switches between the clipboard and the saved clips screens.
    """
    global selected, bottom, has_upped, offset_in_clip, displayed
    if saved_clips is displayed:
        to_disk(SAVED_FILENAME, saved_clips)
        displayed = buffer
    else:
        displayed = saved_clips
        has_upped = False
        saved_clips[0] = buffer[selected]
    selected = 0
    offset_in_clip = 0
    bottom = 0
    redraw()


def copy_to_clipboard(s):
    """
    *copy_to_clipboard* copies to the clipboard. By setting the *compare*
    global variable, it makes sure klipz doesn't capture it again.
    """
    global compare
    pyperclip.copy(s)
    compare = s


def pass_as_tempfile(clip, command_and_args):
    """
    *pass_as_tempfile* will put the clipboard contents in a tempfile, the name
    of which is added as last argument to the provided command and arguments.
    It will then execute the command and put the contents of the tempfile
    back on the clipboard afterwards.
    """
    global screen
    curses.endwin()
    with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as tf_out:
        command_and_args.append(tf_out.name)
        tf_out.write(clip.encode("utf-8"))
    subprocess.call(command_and_args)
    with open(tf_out.name, "r") as tf_in:
        clip = tf_in.read()
    os.remove(tf_out.name)
    screen = curses.initscr()
    return cutcrlf(clip)


def pipe_through(clip, command_and_args):
    """
    *pipe_through* pipes *clip* through *command_and_args*, which can be a
    string that is passed to the shell. If it is a list, any arguments after
    the first one are arguments to the shell, not to the command.
    """
    if isinstance(command_and_args, str):
        command_and_args = [command_and_args]
    p = subprocess.Popen(command_and_args, stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE, shell=True)
    s = p.communicate(input=clip.encode("utf-8"))[0].decode("utf-8")
    return cutcrlf(s)


def call_editor(clip):
    """
    *call_editor* uses $EDITOR to edit the clip list.
    """
    editor = os.environ.get("EDITOR", None)
    if editor:
        clip = pass_as_tempfile(clip, [editor])
    return clip


def cutcrlf(clip):
    """
    *cutcrlf* edits *clip* to remove CR or LF characters from the beginning and
    end of the clip, but only if the --leavecrlf command line option was not
    specified.
    """
    if not cmdline.leavecrlf:
        clip = re.sub("^[\r\n]+", "", clip)
        clip = re.sub("[\r\n]+$", "", clip)
    return clip


if __name__ == "__main__":
    main()
