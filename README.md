Some very useful Shells

# 1.[save_restore_opened_apps](https://github.com/nlpsuge/MyShell/blob/master/save_restore_opened_apps)

Save the current opened GUI applications. And re-open or restore them.

Usage: __
chmod +x save_restore_opened_apps__
#Save the current opened GUI applications__
./save_restore_opened_apps -s__
./save_restore_opened_apps --save__
#Re-open or restore them.__
./save_restore_opened_apps -r__
./save_restore_opened_apps --restore

Todo:
1. Need to handle WINE-based application
2. Need to avoid to save system's applications
