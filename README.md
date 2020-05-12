# klipz - multi-platform clipboard manager using curses

[![PyPI version](https://img.shields.io/pypi/v/klipz.svg)](https://pypi.python.org/pypi/alphashape/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/klipz.svg)](https://pypi.python.org/pypi/alphashape/)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/ropg/klipz/blob/master/LICENSE)

`klipz` is a simple tool to scroll back in your computer's clipboard. Every time you copy something to the clipboard it appears on the bottom line of the klipz main window, scrolling up the previous clippings. You can scroll back in that window to reload one of your older clippings to the clipboard. There's also a separate screen with saved clippings for things that you want to not scroll away. You can edit your clippings in your favorite editor and there's a config file that lets you configure custom actions.

## Installation

klipz is on [PyPI](https://pypi.org/project/klipz), so installing is easy: 

```
pip install klipz
```

Alternatively, you can clone the github repository and install from there:

```
git clone https://github.com/ropg/klipz
cd klipz
pip install .
```

## Using klipz

### Scrolling back in clipboard

On the command line, enter `klipz`. Your terminal window now goes blank except the bottom line shows the current contents of the clipboard on a line that shows as a bar with foreground and background colors swapped (so white on bloack if your terminal window is black on white). `klipz` uses one line per clipping so it may not show the whole clipboard. Use the left and right arrows to see the rest.

At this point you probably want to shrink the terminal window to something like 10 lines by 60 characters and set the font a little smaller (using Ctrl minus or Cmd minus in many cases). Simply put the window in the bottom corner of your screen and copy a few more text clippings from a webpage or somewhere else. As you can see the past clippings scroll up.

To reload a previous clipping, activate the window by clicking on it and scroll up using the up arrow key. If you go back to another application and paste, you'll see that the contents of the clipboard have been replaced to match the selection in klipz.

### Saved Clippings

By pressing the 's' key, you switch back and forth between the "Saved Clippings" screen and the scrolling clipboard screen you've seen before. The clip you had selected in the clipboard screen will appear on the bottom line of the "Saved Clippings" screen, but is not yet saved. Only the lines above the bottom one are actually saved. You can move your line up by pressing 'u', now the clipping is actually saved. If you keep pressing 'u' it will move further up, swapping with the line above it and pressing 'd' will move a line down the list. Pressing 'c' will clear (delete) a clipping from the list. Deleting clippings also works in the clipboard view mode, just in case you copied something embarrassing.

Saved clippings are saved to disk, so they will reappear when you start klipz again. (By default, this happens in a file called `saved_clippings` in the `.klipz` directory in your home directory that klipz creates.)

### Some things to know

* klipz does not deal with copied pictures or anything that is not text. Emoji work fine as they are unicode "text", but no pictures. You can copy and paste everything else just fine, it will just now show up in klipz.

* klipz will remove any beginning and ending carriage returns and linefeeds from your clippings. Because really, those are just annoying. If you don't want this, start with `klipz --leavecrlf`.

* If you have the `EDITOR` environment variable set to your favorite editor, you can press 'e' on a clipping.