import datetime
import json
import os
from contextlib import contextmanager
from itertools import groupby
from multiprocessing import cpu_count
from multiprocessing.pool import Pool
from operator import attrgetter
from pathlib import Path
from time import time, sleep
from types import SimpleNamespace as Namespace
from typing import List

import psutil

from session_filter import SessionFilter
from settings.constants import Locations
from settings.xsession_config import XSessionConfig, XSessionConfigObject
from utils import wmctl_wrapper, subprocess_utils, retry, gio_utils, wnck_utils


class XSessionManager:

    _moving_windows_pool: Pool

    session_filters: List[SessionFilter]
    base_location_of_sessions: str
    base_location_of_backup_sessions: str

    def __init__(self, session_filters: List[SessionFilter]=None,
                 base_location_of_sessions: str=Locations.BASE_LOCATION_OF_SESSIONS,
                 base_location_of_backup_sessions: str=Locations.BASE_LOCATION_OF_BACKUP_SESSIONS):
        self.session_filters = session_filters
        self.base_location_of_sessions = base_location_of_sessions
        self.base_location_of_backup_sessions = base_location_of_backup_sessions

        self._moved_windowids_cache = []

    def save_session(self, session_name: str, session_filter: SessionFilter=None):
        x_session_config = self.get_session_details(remove_duplicates_by_pid=False,
                                                    session_filters=[session_filter])
        x_session_config.session_name = session_name

        session_path = Path(self.base_location_of_sessions, session_name)
        print('Saving the session to: ' + str(session_path))

        if not session_path.parent.exists():
            session_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Backup the old session
            if session_path.exists():
                self.backup_session(session_path)

        # Save a new session
        x_session_config.session_create_time = datetime.datetime.fromtimestamp(time()).strftime("%Y-%m-%d %H:%M:%S.%f")
        save_session_details_json = json.dumps(x_session_config, default=lambda o: o.__dict__)
        print('Saving the new json format x session [%s] ' % save_session_details_json)
        self.write_session(session_path, save_session_details_json)
        print('Done!')

    def get_session_details(self, remove_duplicates_by_pid=True,
                            session_filters: List[SessionFilter]=None) -> XSessionConfig:

        """
        Get the current running session details, including app name, process id,
        window position, command line etc of each app. See XSessionConfigObject for more information.

        :return: the current running session details
        """

        running_windows: list = wmctl_wrapper.get_running_windows()
        x_session_config: XSessionConfig = XSessionConfigObject.convert_wmctl_result_2_list(running_windows,
                                                                                            remove_duplicates_by_pid)
        print('Got the process list according to wmctl: %s' % json.dumps(x_session_config, default=lambda o: o.__dict__))
        x_session_config_objects: List[XSessionConfigObject] = x_session_config.x_session_config_objects
        for idx, sd in enumerate(x_session_config_objects):
            try:
                process = psutil.Process(sd.pid)
                sd.app_name = process.name()
                sd.cmd = process.cmdline()
                sd.process_create_time = datetime.datetime.fromtimestamp(process.create_time()).strftime("%Y-%m-%d %H:%M:%S")
            except psutil.NoSuchProcess as e:
                print('Failed to get process [%s] info using psutil due to: %s' % (sd, str(e)))
                sd.app_name = ''
                sd.cmd = []
                sd.process_create_time = None

        if session_filters is not None:
            for session_filter in session_filters:
                if session_filter is None:
                    continue
                x_session_config.x_session_config_objects[:] = \
                    session_filter(x_session_config.x_session_config_objects)

        print('Complete the process list according to psutil: %s' %
              json.dumps(x_session_config, default=lambda o: o.__dict__))
        return x_session_config

    def backup_session(self, original_session_path):
        backup_time = datetime.datetime.fromtimestamp(time())
        with open(original_session_path, 'r') as file:
            print('Backing up session located [%s] ' % original_session_path)
            namespace_objs: XSessionConfig = json.load(file, object_hook=lambda d: Namespace(**d))
        current_time_str_as_backup_id = backup_time.strftime("%Y%m%d%H%M%S%f")
        backup_session_path = Path(self.base_location_of_backup_sessions,
                                   os.path.basename(original_session_path) + '.backup-' + current_time_str_as_backup_id)
        if not backup_session_path.parent.exists():
            backup_session_path.parent.mkdir(parents=True, exist_ok=True)
        print('Backup the old session file [%s] to [%s]' % (original_session_path, backup_session_path))
        backup_time_str = backup_time.strftime("%Y-%m-%d %H:%M:%S.%f")
        namespace_objs.backup_time = backup_time_str
        backup_session_details_json = json.dumps(namespace_objs, default=lambda o: o.__dict__)
        self.write_session(backup_session_path, backup_session_details_json)

    def write_session(self, session_path, session_details_json):
        with open(session_path, 'w') as file:
            file.write(
                json.dumps(
                    json.loads(session_details_json),
                    indent=4,
                    sort_keys=True))

    def restore_session(self, session_name, restoring_interval=2):
        session_path = Path(self.base_location_of_sessions, session_name)
        if not session_path.exists():
            raise FileNotFoundError('Session file [%s] was not found.' % session_path)

        with open(session_path, 'r') as file:
            print('Restoring session located [%s] ' % session_path)
            namespace_objs: XSessionConfig = json.load(file, object_hook=lambda d: Namespace(**d))
            # Note: os.fork() does not support the Windows
            pid = os.fork()
            # Run command lines in the child process
            # TODO 1. I'm not sure if this method works well and is the best practice
            # TODO 2. Must run in the child process or receive this error:
            # Gdk-Message: 23:23:24.613: main.py: Fatal IO error 11 (Resource temporarily unavailable) on X server :1
            # Not know the root cause
            if pid == 0:
                x_session_config_objects: List[XSessionConfigObject] = namespace_objs.x_session_config_objects
                # Remove duplicates according to pid
                session_details_dict = {x_session_config.pid: x_session_config
                                        for x_session_config in x_session_config_objects}
                x_session_config_objects = list(session_details_dict.values())
                if self.session_filters is not None:
                    for session_filter in self.session_filters:
                        if session_filter is None:
                            continue
                        x_session_config_objects[:] = session_filter(x_session_config_objects)

                if len(x_session_config_objects) == 0:
                    print('No application to restore.')
                    print('Done!')
                    return

                def restore_sessions():
                    self._moving_windows_pool = Pool(processes=cpu_count())
                    for namespace_obj in x_session_config_objects:
                        cmd: list = namespace_obj.cmd
                        app_name: str = namespace_obj.app_name
                        print('Restoring application:              [%s]' % app_name)
                        if len(cmd) == 0:
                            print('Failure to restore application: [%s] due to empty commandline [%s]' % (app_name, str(cmd)))
                            continue

                        process = subprocess_utils.run_cmd(cmd)
                        # print('Success to restore application:     [%s]' % app_name)

                        self._move_window_async(namespace_obj, process.pid)

                        # Wait some time, in case of freezing the entire system
                        sleep(restoring_interval)

                max_desktop_number = self._get_max_desktop_number(x_session_config_objects)
                with self.create_enough_workspaces(max_desktop_number):
                    restore_sessions()
                print('Done!')

    @contextmanager
    def create_enough_workspaces(self, max_desktop_number: int):
        # Create enough workspaces
        if wnck_utils.is_gnome():
            workspace_count = wnck_utils.get_workspace_count()
            if workspace_count >= max_desktop_number:
                yield
                return

            gsettings = gio_utils.GSettings(access_dynamic_workspaces=True, access_num_workspaces=True)
            if gsettings.is_dynamic_workspaces():
                gsettings.disable_dynamic_workspaces()
                try:
                    gsettings.set_workspaces_number(max_desktop_number)
                    try:
                        yield
                    finally:
                        gsettings.enable_dynamic_workspaces()
                except Exception as e:
                    import traceback
                    print(traceback.format_exc())
            else:
                workspaces_number = gsettings.get_workspaces_number()
                if max_desktop_number > workspaces_number:
                    gsettings.set_workspaces_number(max_desktop_number)
                yield
        else:
            yield

    def close_windows(self):
        sessions: List[XSessionConfigObject] = \
            self.get_session_details(remove_duplicates_by_pid=False,
                                     session_filters=self.session_filters).x_session_config_objects

        if len(sessions) == 0:
            print('No application to close.')
            return

        sessions.sort(key=attrgetter('pid'))
        for pid, group_by_pid in groupby(sessions, key=attrgetter('pid')):
            a_process_with_many_windows: List[XSessionConfigObject] = list(group_by_pid)
            if len(a_process_with_many_windows) > 1:
                a_process_with_many_windows.sort(key=attrgetter('window_id'), reverse=True)
                # Close one application's windows one by one from the last one
                for session in a_process_with_many_windows:
                    print('Closing %s(%s %s).' % (session.app_name, session.window_id, session.pid))
                    # No need to catch the CalledProcessError for now, I think.
                    # In one case, if failed to close one window via 'wmctrl -ic window_id', the '$?' will be 0.
                    # In this case, this application may not be closed successfully.
                    wnck_utils.close_window_gracefully_async(session.window_id_the_int_type)
            else:
                session = a_process_with_many_windows[0]
                print('Closing %s(%s %s).' % (session.app_name, session.window_id, session.pid))
                wnck_utils.close_window_gracefully_async(session.window_id_the_int_type)

            # Wait some time, in case of freezing the entire system
            sleep(0.25)

    def move_window(self, session_name):
        session_path = Path(self.base_location_of_sessions, session_name)
        if not session_path.exists():
            raise FileNotFoundError('Session file [%s] was not found.' % session_path)

        with open(session_path, 'r') as file:
            namespace_objs: XSessionConfig = json.load(file, object_hook=lambda d: Namespace(**d))

        x_session_config_objects: List[XSessionConfigObject] = namespace_objs.x_session_config_objects
        x_session_config_objects.sort(key=attrgetter('desktop_number'))

        if self.session_filters is not None:
            for session_filter in self.session_filters:
                if session_filter is None:
                    continue
                x_session_config_objects[:] = session_filter(x_session_config_objects)

        self._moving_windows_pool = Pool(processes=cpu_count())
        max_desktop_number = self._get_max_desktop_number(x_session_config_objects)
        with self.create_enough_workspaces(max_desktop_number):
            for namespace_obj in x_session_config_objects:
                self._move_window(namespace_obj, need_retry=False)

    def _get_max_desktop_number(self, x_session_config_objects):
        # TODO No need to use int() because the type of 'desktop_number' should be int, something is wrong
        return int(max([x_session_config_object.desktop_number
                        for x_session_config_object in x_session_config_objects])) + 1

    def __getstate__(self):
        self_dict = self.__dict__.copy()
        del self_dict['_moving_windows_pool']
        return self_dict

    def __setstate__(self, state):
        self.__dict__.update(state)

    def _move_window_async(self, namespace_obj: XSessionConfigObject, pid: int = None):
        self._moving_windows_pool.apply_async(
            retry.Retry(6, 1).do_retry(self._move_window, (namespace_obj, pid)))

    def _move_window(self, namespace_obj: XSessionConfigObject, pid: int = None, need_retry=True):
        try:
            desktop_number = namespace_obj.desktop_number

            pids = []
            if pid:
                pids = [str(c.pid) for c in psutil.Process(pid).children()]
                pid_str = str(pid)
                pids.append(pid_str)

            # Get process info according to command line
            if len(pids) == 0:
                cmd = namespace_obj.cmd
                if len(cmd) <= 0:
                    return

                for p in psutil.process_iter(attrs=['pid', 'cmdline']):
                    if len(p.cmdline()) <= 0:
                        continue

                    if p.cmdline() == cmd:
                        pids.append(p.pid)
                        break

            no_need_to_move = True
            moving_windows = []
            running_windows = wmctl_wrapper.get_running_windows()
            x_session_config: XSessionConfig = XSessionConfigObject.convert_wmctl_result_2_list(running_windows, False)
            x_session_config_objects: List[XSessionConfigObject] = x_session_config.x_session_config_objects
            x_session_config_objects.sort(key=attrgetter('desktop_number'))
            for running_window in x_session_config_objects:
                if running_window.pid in pids:
                    if running_window.window_title == namespace_obj.window_title \
                            and running_window.desktop_number != desktop_number:
                        moving_windows.append(running_window)
                        no_need_to_move = False
                        # break
                else:
                    no_need_to_move = False

            if need_retry and len(moving_windows) == 0:
                raise retry.NeedRetryException(namespace_obj)
            elif no_need_to_move:
                return

            for running_window in moving_windows:
                running_window_id = running_window.window_id
                if running_window_id in self._moved_windowids_cache:
                    continue
                print('Moving window to desktop:           [%s : %s]' % (running_window.window_title, desktop_number))
                wmctl_wrapper.move_window_to(running_window_id, desktop_number)
                self._moved_windowids_cache.append(running_window_id)
                # Wait some time to prevent 'X Error of failed request:  BadWindow (invalid Window parameter)'
                sleep(0.25)
        except retry.NeedRetryException as ne:
            raise ne
        except Exception as e:
            import traceback
            print(traceback.format_exc())
