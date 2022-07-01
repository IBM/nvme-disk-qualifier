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


class SecureEraseWithMultiNamespaces(run.Run):

    def __init__(self, config, drive):
        super(SecureEraseWithMultiNamespaces, self).__init__()

        self.drive = drive['name']
        self.ns_qty = config['test_config']['secure_erase_multi_namespace']['ns']
        self.ns_size = (
            config['test_config']['secure_erase_multi_namespace']['ns_size'] *
            1024*1024*1024)

    def name(self):
        return "secure_erase_multi_namespace"

    def description(self):
        return ("Verifies that a secure erase occurs on a disk with multiple "
                "namespaces.  Will erase first, but not second.")

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        self.logger.info(f"  Resetting drive {self.drive}")
        tree = n_utils.generate_resource_tree()
        n_utils.reset_drive(tree[self.drive])

        # Make sure the drive supports at least the number of NS's expected
        drive_namespaces = n_utils.get_max_namespaces(self.drive)
        if drive_namespaces < self.ns_qty:
            self.logger.error(f"Drive {self.drive} supports {drive_namespaces} namespaces. "
                              f"At least {self.ns_qty} required.")
            return

        # Create the namespaces
        for i in range(0, self.ns_qty):
            n_utils.create_namespace(self.drive, self.ns_size)

        # Fill the drive namespaces
        disk_list = ':'.join(
            [f'/dev/{self.drive}n{x}' for x in range(1, self.ns_qty + 1)])
        cmd = (f'fio --name=diskfill --rw=write --bs=256k --iodepth=8 '
               f'--group_reporting --numjobs={self.ns_qty} --direct=1 --size=100% '
               f'--filename={disk_list} --output-format=json')
        self.logger.info(f"Command: {cmd}")
        rc, std_out, std_err = n_utils.run_cmd(cmd, shell=True)

        # Capture the hexdump from the original runs
        initial_responses = []
        for i in range(1, self.ns_qty + 1):
            cmd = (f'hexdump /dev/{self.drive}n{i} -n 100 -s 1000000')
            rc, std_out, std_err = n_utils.run_cmd(cmd, shell=True)
            initial_responses.append(std_out)

        # Try the test.
        rc, out, err = n_utils.format_namespace(self.drive, '1')
        if rc != 0:
            self.logger.error(f"Format of individual namespace failed: {err}")
            return

        # Validate the response hexdumps
        post_responses = []
        for i in range(1, self.ns_qty + 1):
            cmd = (f'hexdump /dev/{self.drive}n{i} -n 100 -s 1000000')
            rc, std_out, std_err = n_utils.run_cmd(cmd, shell=True)
            post_responses.append(std_out)

        # The first namespace shouldn't match, but subsequent ones should
        if initial_responses[0] == post_responses[0]:
            self.logger.error(
                "The initial namespace does not appear to format correctly.")
            return

        for i in range(1, self.ns_qty):
            if initial_responses[i] != post_responses[i]:
                self.logger.error(f"Namespace {i} appears to have been affected by the format.  "
                                  "This must not happen.")
                return

        self.logger.info(
            "Erase of individual namespace completed successfully.")
        self.success = True


class SecureEraseDrive(run.Run):

    def __init__(self, config, drive):
        super(SecureEraseDrive, self).__init__()

        self.drive = drive['name']
        self.ns_qty = config['test_config']['secure_erase_drive']['ns']
        self.ns_size = (
            config['test_config']['secure_erase_drive']['ns_size'] *
            1024*1024*1024)

    def name(self):
        return "secure_erase_drive"

    def description(self):
        return ("Verifies that a secure erase occurs drive wide")

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        self.logger.info(f"  Resetting drive {self.drive}")
        tree = n_utils.generate_resource_tree()
        n_utils.reset_drive(tree[self.drive])

        # Make sure the drive supports at least the number of NS's expected
        drive_namespaces = n_utils.get_max_namespaces(self.drive)
        if drive_namespaces < self.ns_qty:
            self.logger.error(f"Drive {self.drive} supports {drive_namespaces} namespaces. "
                              f"At least {self.ns_qty} required.")
            return

        # Create the namespaces
        for i in range(0, self.ns_qty):
            n_utils.create_namespace(self.drive, self.ns_size)

        # Fill the drive namespaces
        disk_list = ':'.join(
            [f'/dev/{self.drive}n{x}' for x in range(1, self.ns_qty + 1)])
        cmd = (f'fio --name=diskfill --rw=write --bs=256k --iodepth=8 '
               f'--group_reporting --numjobs={self.ns_qty} --direct=1 --size=100% '
               f'--filename={disk_list} --output-format=json')
        self.logger.info(f"Command: {cmd}")
        rc, std_out, std_err = n_utils.run_cmd(cmd, shell=True)

        # Capture the hexdump from the original runs
        initial_responses = []
        for i in range(1, self.ns_qty + 1):
            cmd = (f'hexdump /dev/{self.drive}n{i} -n 100 -s 1000000')
            rc, std_out, std_err = n_utils.run_cmd(cmd, shell=True)
            initial_responses.append(std_out)

        # Try the test.
        rc, out, err = n_utils.secure_erase_drive(self.drive)
        if rc != 0:
            self.logger.error(f"Format of individual namespace failed: {err}")
            return

        # Validate the response hexdumps
        post_responses = []
        for i in range(1, self.ns_qty + 1):
            cmd = (f'hexdump /dev/{self.drive}n{i} -n 100 -s 1000000')
            rc, std_out, std_err = n_utils.run_cmd(cmd, shell=True)
            post_responses.append(std_out)

        for i in range(0, self.ns_qty):
            if initial_responses[i] == post_responses[i]:
                self.logger.error(
                    f"Namespace {i} does not appear to be wiped cleanly.")
                return

        self.logger.info("Secure erase successfully completed")
        self.success = True
