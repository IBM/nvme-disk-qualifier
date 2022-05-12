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
import random
import time


class NSLayout(run.Run):

    def __init__(self, config):
        super(NSLayout, self).__init__()

        self.drive = config['drive']['name']
        self.namespace_size = (config['test_config']['ns_layout']['ns_size'] *
                               1024 * 1024 * 1024)
        self.num_namespaces = config['test_config']['general']['max_ns']

    def name(self):
        return "ns_layout"

    def description(self):
        return ("Executes laying out many namespaces on the drive to ensure proper "
                "namespace ordering.")

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        self.logger.debug(f"  Resetting drive {self.drive}")

        # Make sure the drive supports at least the number of NS's expected
        drive_namespaces = n_utils.get_max_namespaces(self.drive)
        if drive_namespaces < self.num_namespaces:
            self.logger.error(f"Drive {self.drive} supports {drive_namespaces} namespaces. "
                              f"At least {self.num_namespaces} required.")
            return

        tree = n_utils.generate_resource_tree()
        n_utils.reset_drive(tree[self.drive])

        self.logger.debug(f"  Creating {self.num_namespaces} namespaces")
        for i in range(0, self.num_namespaces):
            n_utils.create_namespace(self.drive, self.namespace_size)

        # Make sure that there are exactly 32 namespaces
        tree = n_utils.generate_resource_tree()
        namespaces = sorted([x['NameSpace']
                             for x in tree[self.drive]['namespaces']])
        if len(namespaces) != self.num_namespaces:
            self.logger.error(
                "The number of namespaces is not accurate.  Please investigate.")
            return

        # Now delete a few, and see where the new ones add.
        self.logger.info("Deleting a few namespaces")
        n_utils.delete_namespace(self.drive, 1)
        n_utils.delete_namespace(self.drive, 2)
        n_utils.delete_namespace(self.drive, 3)

        # Create 3
        self.logger.info("Adding namespaces back in")
        n_utils.create_namespace(self.drive, self.namespace_size)
        n_utils.create_namespace(self.drive, self.namespace_size)
        n_utils.create_namespace(self.drive, self.namespace_size)

        tree = n_utils.generate_resource_tree()
        new_namespaces = sorted([x['NameSpace']
                                 for x in tree[self.drive]['namespaces']])

        if new_namespaces != namespaces:
            self.logger.error("The namespace id's were not reused.  When a namespace is deleted, "
                              "the deleted identifier should be re-used on a subsequent create.")
            return

        self.logger.info(
            "Namespaces created in slots of prior deleted.  Success!")
        self.success = True


class MultiNSPerf(run.Run):

    def __init__(self, config):
        super(MultiNSPerf, self).__init__()

        self.drive = config['drive']['name']
        self.ramp = config['test_config']['general']['fio_ramptime']
        self.duration = config['test_config']['general']['fio_runtime']
        self.min_read_bw = config['test_config']['multi_ns_perf']['bw_read']
        self.min_write_bw = config['test_config']['multi_ns_perf']['bw_write']
        self.min_mixed_bw = config['test_config']['multi_ns_perf']['bw_mixed']
        self.namespace_size = config['test_config']['multi_ns_perf']['ns_size'] * \
            1024 * 1024 * 1024
        self.num_namespaces = config['test_config']['general']['max_ns']

    def name(self):
        return "multi_ns_perf"

    def description(self):
        return ("Runs I/O tests across many namespaces and validates "
                "the overall performance.")

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        # Make sure the drive supports at least the number of NS's expected
        drive_namespaces = n_utils.get_max_namespaces(self.drive)
        if drive_namespaces < self.num_namespaces:
            self.logger.error(f"Drive {self.drive} supports {drive_namespaces} namespaces. "
                              f"At least {self.num_namespaces} required.")
            return

        self.logger.info(f"  Resetting drive {self.drive}")

        tree = n_utils.generate_resource_tree()
        n_utils.reset_drive(tree[self.drive])

        # Create all the namespaces
        n_utils.bulk_create_namespace(
            self.drive, self.namespace_size, 4096, self.num_namespaces)

        # We assume the namespaces are n1 - n32 (if 32 namespaces)
        drive_string = ':'.join(
            [f'/dev/{self.drive}n{x}' for x in range(1, self.num_namespaces + 1)])
        rc, std_out, std_err = \
            n_utils.run_cmd(f'fio --name=seqmixed --iodepth=64 --rw=rw --bs=256k --runtime={self.duration} '
                            f'--ramp={self.ramp} --group_reporting --numjobs=32 --sync=1 --direct=1 --size=100% '
                            f'--filename=/dev/{self.drive}n1 --output-format=json', shell=True)

        results = json.loads(std_out)
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

        self.logger.info("Drive met minimum bandwidth.")
        self.success = True


class ParallelIO(run.Run):

    def __init__(self, config):
        super(ParallelIO, self).__init__()

        self.drive = config['drive']['name']
        self.random_ops = config['test_config']['parallel']['random_ops']
        self.fio_ns_size = (config['test_config']['parallel']
                            ['ns_fio_size'] * 1024 * 1024 * 1024)
        self.ns_size = (config['test_config']['parallel']
                        ['ns_size'] * 1024 * 1024 * 1024)
        self.initial_ns = config['test_config']['parallel']['initial_ns']

    def name(self):
        return "parallel"

    def description(self):
        return ("Executes I/O operations in parallel to namespace create/delete.")

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        # Make sure the drive supports at least the number of NS's expected
        drive_namespaces = n_utils.get_max_namespaces(self.drive)
        if drive_namespaces < 16:
            self.logger.error(f"Drive {self.drive} supports {drive_namespaces} namespaces. "
                              f"At least 16 required for this test.")
            return

        self.logger.info("Note, this test takes a while.  Failure is a HANG")
        self.logger.debug(f"  Resetting drive {self.drive}")
        tree = n_utils.generate_resource_tree()
        n_utils.reset_drive(tree[self.drive])

        # Create a baseline 1 TB space for hammering in parallel
        self.logger.debug(f"  Creating baseline namespaces that will be FIO'd")
        n_utils.create_namespace(self.drive, self.fio_ns_size)
        n_utils.create_namespace(self.drive, self.fio_ns_size)
        runtime = self.random_ops * 8
        time.sleep(1)

        # Start running both big sequential and random r/w in parallel
        self.logger.debug(f"  Running FIO test.")
        n_utils.run_background_cmd(
            f'fio --name=seqwrite --iodepth=64 --rw=write --bs=256k --runtime={runtime} '
            f'--group_reporting --numjobs=32 --sync=1 --direct=1 --size=100% '
            f'--filename=/dev/{self.drive}n1', shell=True)
        n_utils.run_background_cmd(
            f'fio --name=4krand5050 --iodepth=1 --rw=randrw --bs=4k --runtime={runtime} '
            f'--group_reporting --numjobs=32 --sync=1 --direct=1 --size=100% '
            f'--filename=/dev/{self.drive}n2', shell=True)

        # Now bulk create!
        self.logger.debug(
            f"  Creating {self.initial_ns} namespaces to start namespace ops")
        n_utils.bulk_create_namespace(
            self.drive, self.ns_size, 4096, self.initial_ns)

        self.logger.debug(
            f"  Running {self.random_ops} create/delete namespaces while FIO runs")
        for i in range(0, self.random_ops):
            opt = random.randint(1, 2)

            tree = n_utils.generate_resource_tree()
            if len(tree[self.drive]['namespaces']) > 15:
                opt = 2
            elif len(tree[self.drive]['namespaces']) < 4:
                opt = 1

            if opt == 1:
                self.logger.debug("  Creating a namespace")
                n_utils.create_namespace(self.drive, self.ns_size)
            else:
                self.logger.debug("  Deleting a namespace")
                tree = n_utils.generate_resource_tree().get(self.drive)
                namespaces = tree.get('namespaces', [])
                if len(namespaces) == 0:
                    continue
                namespace = random.choice(namespaces)
                while namespace.get("NameSpace") in [1, 2]:
                    namespace = random.choice(namespaces)
                n_utils.delete_namespace(
                    self.drive, namespace.get("NameSpace"))
        self.logger.info("Completed Parallel I/O & Namespace Creation test")
        self.success = True
