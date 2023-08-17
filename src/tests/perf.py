# Copyright 2022 IBM Corp.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from nvme import utils as n_utils
from tests import run

import json


class RandRead(run.Run):

    def __init__(self, config):
        super(RandRead, self).__init__()

        self.drive = config['drive']['name']
        self.ramp = config['test_config']['general']['fio_ramptime']
        self.duration = config['test_config']['perf_rand_read'].get('runtime', \
            config['test_config']['general']['fio_runtime'])
        self.ioengine = config['test_config']['general'].get('ioengine', 'libaio')
        self.min_iops = config['test_config']['perf_rand_read']['iops']


    def name(self):
        return "perf_rand_read"

    def description(self):
        return ("Executes a random small block (4k) read test")

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        self.logger.info(f"  Resetting drive {self.drive}")
        tree = n_utils.generate_resource_tree()
        n_utils.reset_drive(tree[self.drive])

        # Create a single namespace
        n_utils.factory_reset(tree[self.drive]['sn'].strip())

        cmd = (f'fio --name=4krandread --iodepth=4 --rw=randread --bs=4k --runtime={self.duration} '
               f'--ramp={self.ramp} --group_reporting --numjobs=32 --sync=1 --direct=1 --size=100% '
               f'--ioengine={self.ioengine} --filename=/dev/{self.drive}n1 --output-format=json')
        self.logger.info(f"Command: {cmd}")
        rc, std_out, std_err = n_utils.run_cmd(cmd, shell=True)

        if rc != 0:
            self.logger.error(f"Failed to run test.  Error was:\n {std_err}")
            return
        else:
            self.logger.info("I/O command completed.  Comparing data.")

        results = json.loads(std_out)
        self.logger.info(f"Raw Test Results: {json.dumps(results, indent=2)}")

        test_iops = results['jobs'][0]['read']['iops']
        if test_iops < self.min_iops:
            self.logger.error(
                f"Drive must hit at least {self.min_iops}.  Drive only gets to {test_iops}.  DRIVE FAILED.")
            return

        # TODO latency checks anyone?

        self.logger.info("Drive passed bandwidth requirements.")
        self.success = True


class RandWrite(run.Run):

    def __init__(self, config):
        super(RandWrite, self).__init__()

        self.drive = config['drive']['name']
        self.ramp = config['test_config']['general']['fio_ramptime']
        self.ioengine = config['test_config']['general'].get('ioengine', 'libaio')
        self.duration = config['test_config']['perf_rand_write'].get('runtime', \
            config['test_config']['general']['fio_runtime'])
        self.min_iops = config['test_config']['perf_rand_write']['iops']

    def name(self):
        return "perf_rand_write"

    def description(self):
        return ("Executes a random small block (4k) write test")

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        self.logger.info(f"  Resetting drive {self.drive}")
        tree = n_utils.generate_resource_tree()
        n_utils.reset_drive(tree[self.drive])

        # Create a single namespace
        n_utils.factory_reset(tree[self.drive]['sn'].strip())

        cmd = (f'fio --name=4krandwrite --iodepth=1 --rw=randwrite --bs=4k --runtime={self.duration} '
               f'--ramp={self.ramp} --group_reporting --numjobs=32 --sync=1 --direct=1 --size=100% '
               f'--ioengine={self.ioengine} --filename=/dev/{self.drive}n1 --output-format=json')
        self.logger.info(f"Command: {cmd}")
        rc, std_out, std_err = n_utils.run_cmd(cmd, shell=True)

        if rc != 0:
            self.logger.error(f"Failed to run test.  Error was:\n {std_err}")
            return
        else:
            self.logger.info("I/O command completed.  Comparing data.")

        results = json.loads(std_out)
        self.logger.info(f"Raw Test Results: {json.dumps(results, indent=2)}")

        test_iops = results['jobs'][0]['write']['iops']
        if test_iops < self.min_iops:
            self.logger.error(
                f"Drive must hit at least {self.min_iops}.  Drive only gets to {test_iops}.  DRIVE FAILED.")
            return

        # TODO latency checks anyone?

        self.logger.info("Drive passed bandwidth requirements.")
        self.success = True


class SeqMixed(run.Run):

    def __init__(self, config):
        super(SeqMixed, self).__init__()

        self.drive = config['drive']['name']
        self.ramp = config['test_config']['general']['fio_ramptime']
        self.ioengine = config['test_config']['general'].get('ioengine', 'libaio')
        self.duration = config['test_config']['perf_seq_mixed'].get('runtime', \
            config['test_config']['general']['fio_runtime'])
        self.min_read_bw = config['test_config']['perf_seq_mixed']['bw_read']
        self.min_write_bw = config['test_config']['perf_seq_mixed']['bw_write']
        self.min_mixed_bw = config['test_config']['perf_seq_mixed']['bw_mixed']


    def name(self):
        return "perf_seq_mixed"

    def description(self):
        return "Executes a sequential large block (256k) read/write test"

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        self.logger.info(f"  Resetting drive {self.drive}")
        tree = n_utils.generate_resource_tree()
        n_utils.reset_drive(tree[self.drive])

        # Create a single namespace
        n_utils.factory_reset(tree[self.drive]['sn'].strip())

        cmd = (f'fio --name=seqmixed --iodepth=64 --rw=rw --bs=128k --runtime={self.duration} '
               f'--ramp={self.ramp} --group_reporting --numjobs=32 --sync=1 --direct=1 --size=100% '
               f'--ioengine={self.ioengine} --filename=/dev/{self.drive}n1 --output-format=json')
        self.logger.info(f"Command: {cmd}")
        rc, std_out, std_err = n_utils.run_cmd(cmd, shell=True)

        if rc != 0:
            self.logger.error(f"Failed to run test.  Error was:\n {std_err}")
            return
        else:
            self.logger.info("I/O command completed.  Comparing data.")

        results = json.loads(std_out)
        self.logger.info(f"Raw Test Results: {json.dumps(results, indent=2)}")

        read_bw = results['jobs'][0]['read']['bw']
        write_bw = results['jobs'][0]['write']['bw']
        if read_bw + write_bw < self.min_mixed_bw:
            self.logger.error(
                f"Drive must hit at least {self.min_mixed_bw} mixed BW.  Drive "
                f"only gets to {read_bw + write_bw}.  DRIVE FAILED.")
            return

        if read_bw < self.min_read_bw:
            self.logger.error(
                f"Drive must hit at least {self.min_read_bw} read BW during mixed test.  Drive "
                f"only gets to {read_bw}.  DRIVE FAILED.")
            return

        if write_bw < self.min_write_bw:
            self.logger.error(
                f"Drive must hit at least {self.min_write_bw} read BW during mixed test.  Drive "
                f"only gets to {write_bw}.  DRIVE FAILED.")
            return

        # TODO latency checks anyone?

        self.logger.info("Drive passed bandwidth requirements.")
        self.success = True


class SeqRead(run.Run):

    def __init__(self, config):
        super(SeqRead, self).__init__()

        self.drive = config['drive']['name']
        self.ramp = config['test_config']['general']['fio_ramptime']
        self.ioengine = config['test_config']['general'].get('ioengine', 'libaio')
        self.duration = config['test_config']['perf_seq_read'].get('runtime', \
            config['test_config']['general']['fio_runtime'])
        self.min_bw = config['test_config']['perf_seq_read']['bandwidth']

    def name(self):
        return "perf_seq_read"

    def description(self):
        return "Executes a sequential large block (256k) read only test"

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        self.logger.info(f"  Resetting drive {self.drive}")
        tree = n_utils.generate_resource_tree()
        n_utils.reset_drive(tree[self.drive])

        # Create a single namespace
        n_utils.factory_reset(tree[self.drive]['sn'].strip())

        cmd = (f'fio --name=seqread --iodepth=64 --rw=read --bs=128k --runtime={self.duration} '
               f'--ramp={self.ramp} --group_reporting --numjobs=32 --sync=1 --direct=1 --size=100% '
               f'--ioengine={self.ioengine} --filename=/dev/{self.drive}n1 --output-format=json')
        self.logger.info(f"Command: {cmd}")
        rc, std_out, std_err = n_utils.run_cmd(cmd, shell=True)

        if rc != 0:
            self.logger.error(f"Failed to run test.  Error was:\n {std_err}")
            return
        else:
            self.logger.info("I/O command completed.  Comparing data.")

        results = json.loads(std_out)
        self.logger.info(f"Raw Test Results: {json.dumps(results, indent=2)}")

        test_bw = results['jobs'][0]['read']['bw']
        if test_bw < self.min_bw:
            self.logger.error(
                f"Drive must hit at least {self.min_bw}.  Drive only gets to {test_bw}.  DRIVE FAILED.")
            return

        # TODO latency checks anyone?

        self.logger.info("Drive passed bandwidth requirements.")
        self.success = True


class SeqWrite(run.Run):

    def __init__(self, config):
        super(SeqWrite, self).__init__()

        self.drive = config['drive']['name']
        self.ramp = config['test_config']['general']['fio_ramptime']
        self.ioengine = config['test_config']['general'].get('ioengine', 'libaio')
        self.duration = config['test_config']['perf_seq_write'].get('runtime', \
            config['test_config']['general']['fio_runtime'])
        self.min_bw = config['test_config']['perf_seq_write']['bandwidth']

    def name(self):
        return "perf_seq_write"

    def description(self):
        return "Executes a sequential large block (256k) write only test"

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        self.logger.debug(f"  Resetting drive {self.drive}")
        tree = n_utils.generate_resource_tree()
        n_utils.reset_drive(tree[self.drive])

        # Create a single namespace
        n_utils.factory_reset(tree[self.drive]['sn'].strip())

        cmd = (f'fio --name=seqwrite --iodepth=64 --rw=write --bs=128k --runtime={self.duration} '
               f'--ramp={self.ramp} --group_reporting --numjobs=32 --sync=1 --direct=1 --size=100% '
               f'--ioengine={self.ioengine} --filename=/dev/{self.drive}n1 --output-format=json')
        self.logger.info(f"Command: {cmd}")
        rc, std_out, std_err = n_utils.run_cmd(cmd, shell=True)

        if rc != 0:
            self.logger.error(f"Failed to run test.  Error was:\n {std_err}")
            return
        else:
            self.logger.info("I/O command completed.  Comparing data.")

        results = json.loads(std_out)
        self.logger.info(f"Raw Test Results: {json.dumps(results, indent=2)}")

        test_bw = results['jobs'][0]['write']['bw']
        if test_bw < self.min_bw:
            self.logger.error(
                f"Drive must hit at least {self.min_bw}.  Drive only gets to {test_bw}.  DRIVE FAILED.")
            return

        # TODO latency checks - anyone?

        # Consider a success
        self.logger.info("Drive passed bandwidth requirements.")
        self.success = True
