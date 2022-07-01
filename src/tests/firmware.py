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

import os
import time


class ApplyNew(run.Run):

    def __init__(self, config, drive):
        super(ApplyNew, self).__init__()

        self.drive = drive['name']
        self.fw_path = config['test_config']['fw_update_simple']['fw_file']
        self.expected_version = config['test_config']['fw_update_simple']['expected_version']

    def name(self):
        return "fw_update_simple"

    def description(self):
        return ("Applies new firmware on a disk.  Does with a single namespace.")

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        self.logger.info(f"  Resetting drive {self.drive}")
        tree = n_utils.generate_resource_tree()
        n_utils.reset_drive(tree[self.drive])

        # Create a single namespace
        n_utils.factory_reset(tree[self.drive]['sn'].strip())

        if not os.path.exists(self.fw_path):
            self.logger.error(f'Firmware not available at path {self.fw_path}')
            return

        # Step 1: Download the firmware
        cmd = f'nvme fw-download /dev/{self.drive} --fw={self.fw_path}'
        self.logger.info(f"Firmware download command: {cmd}")
        rc, std_out, std_err = n_utils.run_cmd(
            cmd, shell=True, fail_on_err=False)
        if rc != 0:
            self.logger.error(
                f"Unable to load firmware on drive {self.drive}.  Failing test.  Error is: {std_err}")
            return
        else:
            self.logger.info(f"Firmware download completed successfully.  Response: \n{std_out}")


        # # Step 2: dry-run activate the firmware
        # cmd = f'nvme fw-activate /dev/{self.drive} -a 0 -s 1'
        # self.logger.info(f"Firmware activate command: {cmd}")
        # rc, std_out, std_err = n_utils.run_cmd(
        #     cmd, shell=True, fail_on_err=False)
        # if rc != 0:
        #     self.logger.error(
        #         f"Unable to activate firmware on drive {self.drive}.  Failing test.  Error is: {std_err}")
        #     return
        # else:
        #     self.logger.info(f"Firmware activate completed successfully.  Response: \n{std_out}")

        # Step 3: activate the firmware
        cmd = f'nvme fw-activate /dev/{self.drive} -a 1 -s 1'
        self.logger.info(f"Firmware activate command: {cmd}")
        rc, std_out, std_err = n_utils.run_cmd(
            cmd, shell=True, fail_on_err=False)
        if rc != 0:
            self.logger.error(
                f"Unable to activate firmware on drive {self.drive}.  Failing test.  Error is: {std_err}")
            return
        else:
            self.logger.info(f"Firmware activate completed successfully.  Response: \n{std_out}")

        # Step 4: Reset the the drive
        cmd = f'nvme reset /dev/{self.drive}'
        self.logger.info(f"Resetting drive: {cmd}")
        rc, std_out, std_err = n_utils.run_cmd(
            cmd, shell=True, fail_on_err=False)
        if rc != 0:
            self.logger.error(
                f"Unable to reset drive {self.drive}.  Failing test.  Error is: {std_err}")
            return
        else:
            self.logger.info(f"Drive reset completed successfully.  Response: \n{std_out}")

        # Loop for up to 60 seconds, until the device is back.
        for i in range(0, 60):
            if self.success:
                break

            devices = n_utils.list_nvme_namespaces(fail_on_err=False)
            for device in devices:
                if device.get('DevicePath') == f'/dev/{self.drive}n1':
                    dev_fw = device.get('Firmware')
                    if dev_fw != str(self.expected_version):
                        self.logger.error(f"Firmware found was {dev_fw}.  The expected fw is {self.expected_version}.  Test failed.")
                        return
                    else:
                        self.logger.info("Firmware applied correctly")
                        self.success = True
                        break
                else:
                    time.sleep(1)
        
        if not self.success:
            self.logger.error("Device not found after >60 seconds after FW update.  Failed test.")
            return
