import json
import logging
import os
import unittest

from base import TEST_DATA_DIR, TestDirBase, DEBUG, get_temp_file

from pbsmrtpipe.models import RunnableTask, TaskTypes
import pbsmrtpipe.tools.runner as R

log = logging.getLogger(__name__)


def _to_cmd(msg, output_file):
    return "echo \"{m}\" > {o}".format(o=output_file, m=msg)


def _to_runnable_task(task_id, input_files, output_files, cmds):
    ropts = {}
    nproc = 1
    resources = []
    rt = RunnableTask(task_id, TaskTypes.LOCAL, input_files, output_files, ropts, nproc, resources, cmds, None, {})
    return rt


def _create_runnable_task(task_id, input_names, output_names):
    """Write the necessary files and generate the cmds"""
    input_files = [get_temp_file(suffix=x) for x in input_names]
    output_files = [get_temp_file(suffix=x) for x in output_names]
    msg = "MOCK DATA"
    cmds = [_to_cmd(msg, x) for x in output_files]
    return _to_runnable_task(task_id, input_files, output_files, cmds)


class TestRunnableTask(TestDirBase):
    TASK_ID = "my_task_01"
    INPUT_FILE_NAMES = ['file1.txt', 'file2.txt']
    OUTPUT_FILE_NAMES = ['out1.txt']
    NPROC = 1

    def _to_runnable_task(self):
        return _create_runnable_task(self.TASK_ID, self.INPUT_FILE_NAMES, self.OUTPUT_FILE_NAMES)

    def test_01(self):
        rt = self._to_runnable_task()
        self.assertIsInstance(rt, RunnableTask)

        f = lambda x: os.path.join(self.temp_dir, x)

        stdout = f("stdout")
        stderr = f("stderr")
        rcode, run_time = R.run_task(rt, self.temp_dir, stdout, stderr, DEBUG)
        # Need to generate a manifest on-the-fly otherwise there the paths
        # in the manifest will be wrong.
        self.assertIsInstance(rcode, int)


class TestHelloRunnableTask(TestRunnableTask):
    TASK_ID = "my_task_02"
    INPUT_FILE_NAMES = ['file1.txt', 'file2.txt']
    OUTPUT_FILE_NAMES = ['out1.txt', 'out2.txt', 'out3.txt']
    RESOURCES = []