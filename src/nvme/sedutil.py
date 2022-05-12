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

from nvme import utils

import logging
import sys

logger = logging.getLogger(__name__)

TEST_PWD = 'passw0rd'


def check_opal_capability(drive):
    output = query_drive(drive)
    return 'LockingSupported = Y' in output


def is_locked(drive):
    output = query_drive(drive)
    return 'Locked = Y' in output


def initial_setup(drive):
    rc, stdout, stderr = utils.run_cmd(
        f"/usr/local/bin/sedutil-cli --initialSetup {TEST_PWD} /dev/{drive}",
        shell=True, fail_on_err=False)

    # So this usually fails on the MBR bits for enterprise drives.  Make sure
    # it has at least this line, then query for rest.
    if 'LockingRange0 set to RW' not in stdout:
        logger.error(f"Initial setup of OPAL drive failed: {drive}")
        return False

    drive_state = query_drive(drive)
    if not 'LockingEnabled = Y' in drive_state and not 'MediaEncrypt = Y' in drive_state:
        logger.error(f"Locking of drive {drive} not set to enabled")
        return False

    # Enable the locking range.
    rc, stdout, stderr = utils.run_cmd(
        f"/usr/local/bin/sedutil-cli --enablelockingrange 0 {TEST_PWD} /dev/{drive}",
        shell=True, fail_on_err=False)
    if 'LockingRange0 enabled ReadLocking,WriteLocking' not in stdout:
        logger.error(f"Locking range not enabled for {drive}.")
        return False

    return True


def lock_drive(drive):
    # Enable the locking range.
    rc, stdout, stderr = utils.run_cmd(
        f"/usr/local/bin/sedutil-cli --setLockingRange 0 LK {TEST_PWD} /dev/{drive}",
        shell=True, fail_on_err=False)
    if 'LockingRange0 set to LK' not in stdout:
        logger.error(f"Unable to lock drive {drive}.")
        return False
    return True


def unlock_drive(drive):
    # Enable the locking range.
    rc, stdout, stderr = utils.run_cmd(
        f"/usr/local/bin/sedutil-cli --setLockingRange 0 RW {TEST_PWD} /dev/{drive}",
        shell=True, fail_on_err=False)
    if 'LockingRange0 set to RW' not in stdout:
        logger.error(f"Unable to lock drive {drive}.")
        return False
    return True


def reset_via_psid(drive, psid):
    # Make sure it queries ok
    query_drive(drive)

    cmd = (f"/usr/local/bin/sedutil-cli --yesIreallywanttoERASEALLmydatausingthePSID "
           f"{psid} /dev/{drive}")

    rc, stdout, stderr = utils.run_cmd(cmd, shell=True, fail_on_err=False)
    if rc != 0:
        logger.error("Unable to reset drive with PSID - nothing can continue")
        logger.error(stderr)
        sys.exit(1)

    return True


def query_drive(drive):
    rc, stdout, stderr = utils.run_cmd(
        f"/usr/local/bin/sedutil-cli --query /dev/{drive}",
        shell=True, fail_on_err=False)

    if rc != 0:
        logger.error("Failure with sedutil-cli.  Verify install / drive")
        logger.error(stderr)
        sys.exit(1)

    return stdout
