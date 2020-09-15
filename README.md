# [xsession-manager](https://github.com/nlpsuge/xsession-manager)

Python-based command line tool to save and restore sessions for X11 desktops like Gnome, 
and other features to maintain sessions. The project is currently in an early stage of development.
## Install


## Usage:

```
usage: main.py [-h] [-s [SAVE]] [-c [CLOSE_ALL [CLOSE_ALL ...]]]
               [-r [RESTORE]] [-ri RESTORING_INTERVAL] [-pr [PR]] [-l]
               [-t DETAIL] [-x EXCLUDE [EXCLUDE ...]]

optional arguments:
  -h, --help            show this help message and exit
  -s [SAVE], --save [SAVE]
                        Save the current session. Save to the default session
                        if not specified a session name.
  -c [CLOSE_ALL [CLOSE_ALL ...]], --close-all [CLOSE_ALL [CLOSE_ALL ...]]
                        Close the windows gracefully. Close all windows if
                        only -c/--close-all is present. You can specify
                        arguments to tell me which windows should be closed,
                        that is <window_id>, <pid>, <app_name> or <title_name>
                        exactly the same as -x.
  -r [RESTORE], --restore [RESTORE]
                        Restore a session gracefully. Restore the default
                        session if not specified a session name.
  -ri RESTORING_INTERVAL, --restoring-interval RESTORING_INTERVAL
                        Specify the interval between restoring applications,
                        in seconds. The default is 2 seconds.
  -pr [PR]              Pop up a dialog to ask user whether to restore a X
                        session.
  -l, --list            List the sessions.
  -t DETAIL, --detail DETAIL
                        Check out the details of a session.
  -x EXCLUDE [EXCLUDE ...], --exclude EXCLUDE [EXCLUDE ...]
                        Exclude apps from the operation according to
                        <window_id>, <pid>, <app_name> or <title_name>.
                        Require at least one value
```

## If you want to restore the previous X session automatically after login
Here is a solution. If you are using Fedora, create a file named ```auto-restore-working-state.desktop``` and the ```Exec``` should be:
```bash
xsession-manager -pr
```
Then put this file into ```~/.config/autostart```.

## Todo:
[TODO](https://github.com/nlpsuge/xsession-manager/blob/master/TODO.md)
