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

from nvme import sedutil
from nvme import utils as n_utils
from tests import run


class OpalCapable(run.Run):

    def __init__(self, config):
        super(OpalCapable, self).__init__()

        self.drive = config['drive']['name']

    def name(self):
        return "opal_capable"

    def description(self):
        return ("Verifies that the drive is capable of Opal")

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        if not sedutil.check_opal_capability(self.drive):
            self.logger.error(f"Drive {self.drive} is not capable of OPAL.")
            return

        self.logger.info(f"Drive {self.drive} appears to be opal capable.")
        self.success = True


class OpalLockTest(run.Run):

    def __init__(self, config):
        super(OpalLockTest, self).__init__()

        self.drive = config['drive']['name']
        self.psid = config['drive']['psid']

    def name(self):
        return "opal_test_locked_write"

    def description(self):
        return ("Locks a drive, tries to write to it.  Should fail the write.  "
                "Will then unlock.")

    def execute(self):
        # Start in a failed state, work to success
        self.success = False

        # Just validate that it's OPAL enabled
        if not sedutil.check_opal_capability(self.drive):
            self.logger.error(f"Drive {self.drive} is not capable of OPAL.")
            return

        # Start with a PSID reset, just in case it's in a weird state
        sedutil.reset_via_psid(self.drive, self.psid)

        # Format it.
        tree = n_utils.generate_resource_tree()
        n_utils.factory_reset(tree[self.drive]['sn'].strip())

        # Set up
        if not sedutil.initial_setup(self.drive):
            self.logger.error(
                f"Drive {self.drive} is not able to set up OPAL.")
            sedutil.reset_via_psid(self.drive, self.psid)
            return

        # Lock
        if not sedutil.lock_drive(self.drive):
            self.logger.error(f"Drive {self.drive} is unable to be locked.")
            sedutil.reset_via_psid(self.drive, self.psid)
            return

        # FIO should fail
        rc, stdout, stderr = n_utils.run_cmd(
            f'fio --name=seqread --iodepth=64 --rw=read --bs=128k --runtime=5 '
            f'--ramp=2 --group_reporting --numjobs=32 --sync=1 --direct=1 --size=100% '
            f'--filename=/dev/{self.drive}n1 --output-format=json', shell=True,
            fail_on_err=False)
        if f'error on file /dev/{self.drive}n1' not in stderr or rc == 0:
            self.logger.error(
                f"Writing to drive seems to pass, even though "
                f"drive {self.drive} is locked")
            sedutil.reset_via_psid(self.drive, self.psid)
            return
        else:
            self.logger.info(
                "Errors expected.  Unlocking and verifying drive now works.")

        # Unlock the drive
        if not sedutil.unlock_drive(self.drive):
            self.logger.error("Unable to unlock drive")
            sedutil.reset_via_psid(self.drive, self.psid)
            return
        else:
            self.logger.info(
                "Drive successfully unlocked.  Attempting I/O tests.")

        # FIO should now pass
        rc, stdout, stderr = n_utils.run_cmd(
            f'fio --name=seqread --iodepth=64 --rw=read --bs=128k --runtime=5 '
            f'--ramp=2 --group_reporting --numjobs=32 --sync=1 --direct=1 --size=100% '
            f'--filename=/dev/{self.drive}n1 --output-format=json', shell=True)

        if rc != 0:
            self.logger.error("I/O failed after drive was unlocked")
            return
        else:
            self.logger.info(
                "Drive I/O passed after unlock.  Reseting via PSID")

        # Now PSID revert again
        sedutil.reset_via_psid(self.drive, self.psid)

        self.logger.info("Test passed!")
        self.success = True
