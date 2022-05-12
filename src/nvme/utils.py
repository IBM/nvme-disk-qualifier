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

import logging
import json
import subprocess
import time


CMD_LS = '/bin/ls'
CMD_NVME = '/usr/sbin/nvme'
CMD_PARTED = '/sbin/parted'
CMD_CAT = '/bin/cat'

logger = logging.getLogger(__name__)


def run_background_cmd(command, shell=False):
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=shell,
                               universal_newlines=True)


def run_cmd(command, shell=False, expected_rc=0, fail_on_err=True,
            warn_on_err=True):
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, shell=shell,
                               universal_newlines=True)
    stdout, stderr = process.communicate()
    stdout = stdout.strip()
    stderr = stderr.strip()

    if process.returncode != expected_rc:
        error_string = f'Command "{command}" failed with error "{stderr}"'
        if fail_on_err:
            raise OSError(error_string)
        elif warn_on_err:
            logger.debug(error_string)
    return process.returncode, stdout, stderr


def get_partitions_for_namespace(device_path):
    prefix = f'{device_path}p'
    rc, out, err = run_cmd(f'{CMD_LS} {prefix}*',
                           shell=True,
                           fail_on_err=False,
                           warn_on_err=False)
    if rc != 0:
        return []
    partitions = []
    start = len(prefix)
    for partition_device in out.splitlines():
        partitions.append(partition_device[start:])
    return partitions


def __get_controller_property(device, attribute, fail_on_err=True):
    rc, out, err = run_cmd([CMD_NVME, 'id-ctrl', f'/dev/{device}'],
                           fail_on_err=fail_on_err)
    if rc != 0:
        # fail_on_err must be False to get here
        # will have already printed an error, so no need to do so again
        return -1

    for line in out.splitlines():
        if len(line.split(':')) != 2:
            continue

        key, val = line.split(':')
        if key.strip() == attribute:
            return val.strip()

    return -1


def get_controller(device, fail_on_err=True):
    logger.debug(f'Determining Controller for device {device}')
    return __get_controller_property(device, 'cntlid', fail_on_err=fail_on_err)


def get_max_namespaces(device, fail_on_err=True):
    logger.debug(f'Determining max number of namespaces for device {device}')
    return int(__get_controller_property(device, 'nn',
                                         fail_on_err=fail_on_err))


def create_namespace(device, size_in_bytes, block_size=4096, controller=None,
                     fail_on_err=True):
    block_count = int(size_in_bytes / block_size)

    logger.debug(f'Creating Namespace on device {device} with {size_in_bytes} '
                 f'bytes and block size {block_size}')
    rc, out, err = run_cmd([CMD_NVME, 'create-ns',
                            f'/dev/{device}', '-s', str(block_count), '-c',
                            str(block_count), '-b', str(block_size)],
                           fail_on_err=fail_on_err)
    logger.debug(f'Create namespace completed, rc={rc}: {out}')
    pos = out.rfind(':') + 1
    namespace = out[pos:]
    time.sleep(2)

    namespace_rescan(device, fail_on_err=fail_on_err)
    time.sleep(2)

    attach_namespace(device, namespace, controller=controller,
                     fail_on_err=fail_on_err)
    time.sleep(2)

    namespace_rescan(device, fail_on_err=fail_on_err)
    time.sleep(2)


def bulk_create_namespace(device, size, block_size, quantity,
                          fail_on_err=True):
    # accelerate by determining controller once
    controller = get_controller(device, fail_on_err=fail_on_err)
    for x in range(0, quantity):
        create_namespace(device, size, block_size, controller=controller,
                         fail_on_err=fail_on_err)


def namespace_rescan(device, fail_on_err=True):
    logger.debug(f'Re-scanning namespaces on device {device}')
    rc, out, err = run_cmd([CMD_NVME, 'ns-rescan',
                            '/dev/' + device],
                           fail_on_err=fail_on_err)
    logger.debug(f'Rescan completed, rc={rc}: {out}')
    return rc


def attach_namespace(device, namespace, controller=None, fail_on_err=True):
    if not controller:
        controller = get_controller(device, fail_on_err=fail_on_err)

    logger.debug(f'Attaching Namespace {namespace} on device {device}'
                 f' from controller {controller}')
    rc, out, err = run_cmd([CMD_NVME, 'attach-ns', '/dev/' + device,
                            '-n', str(namespace), '-c', str(controller)],
                           fail_on_err=fail_on_err)
    logger.debug(f'Attach namespace completed, rc={rc}: {out}')
    return rc


def format_namespace(device, namespace, ses=2, test=False):
    # SECURITY WARNING: Do not set test=True for production environments
    # This option is only provided to assist with drive qualification/testing
    logger.debug(f'Formatting Namespace {namespace} on device {device} '
                 f'with secure erase setting {ses}')
    rc, out, err = run_cmd([CMD_NVME, 'format',
                            '/dev/' + device,
                            '-n', str(namespace),
                            '-s', str(ses)],
                           fail_on_err=(not test))
    logger.debug(f'Format completed, rc={rc}: {out}')
    return rc, out, err


def secure_erase_drive(device):
    rc, out, err = run_cmd([CMD_NVME, 'format',
                            '/dev/' + device,
                            '-n', '0xffffffff',
                            '-s', '1',
                            '-l', '0'],
                           fail_on_err=False)
    logger.debug(f'Format completed, rc={rc}: {out}')
    return rc, out, err


def detach_namespace(device, namespace, controller=-1, fail_on_err=True):
    if controller < 0:
        controller = get_controller(device, fail_on_err=fail_on_err)
        if not controller:
            logger.warning(f'Cannot detach namespace {namespace} on '
                           f'device {device} without knowing controller')
            return -1

    logger.debug(f'Detaching Namespace {namespace} on device {device}'
                 f' from controller {controller}')
    rc, out, err = run_cmd([CMD_NVME, 'detach-ns',
                            '/dev/' + device,
                            '-n', str(namespace),
                            '-c', str(controller)],
                           fail_on_err=fail_on_err)
    logger.debug(f'Detach namespace completed, rc={rc}: {out}')
    return rc


def delete_namespace(device, namespace, timeout=120000, fail_on_err=True):
    format_namespace(device, namespace, 2)
    time.sleep(1)

    detach_namespace(device, namespace, fail_on_err=fail_on_err)
    time.sleep(1)

    namespace_rescan(device, fail_on_err=fail_on_err)
    time.sleep(1)

    rc, out, err = run_cmd([CMD_NVME, 'delete-ns',
                            '/dev/' + device,
                            '-n', str(namespace),
                            '-t', str(timeout)],
                           fail_on_err=fail_on_err)
    return rc


def reset_drive(controller, fail_on_err=True):
    # controller is the drive from the nvme_resource_tree
    device = controller.get("name")

    # TODO: handle detached namespaces. One possibility is to:
    #   1. delete all attached namespaces
    #   2. compare total capacity to available capacity to determine whether
    #      there's anything left
    #   3. if they don't match, delete all possible namespace ids, create a
    #      namespace for the full disk, format it, and delete it
    namespaces = controller.get('namespaces', [])
    for ns in namespaces:
        ns_device_path = ns.get("DevicePath")
        namespace_id = ns.get("NameSpace")

        partitions = get_partitions_for_namespace(ns_device_path)
        for partition in partitions:
            delete_partition(ns_device_path, partition,
                             fail_on_err=fail_on_err)
        delete_namespace(device, namespace_id, fail_on_err=fail_on_err)
    return True


def create_partition(device, namespace, start, end, fail_on_err=True):
    logger.debug(f'Creating partition on device {device} namespace {namespace} '
                 f'from {start} to {end}')
    rc, out, err = run_cmd([CMD_PARTED, f'/dev/{device}n{namespace}',
                            '--script', 'mkpart', 'primary', start, end],
                           fail_on_err=fail_on_err)
    logger.debug(f'Create partition completed, rc={rc}: {out}')


def bulk_create_partition(device, namespace, partition_size, quantity,
                          fail_on_err=True):
    logger.debug(
        f'Creating disk label on device {device} namespace {namespace}')
    rc, out, err = run_cmd([CMD_PARTED, f'/dev/{device}n{namespace}',
                            '--script', 'mklabel', 'gpt'],
                           fail_on_err=fail_on_err)
    logger.debug(f'Create disk label completed, rc={rc}: {out}')
    for x in range(0, quantity):
        start = f'{x * partition_size}GB'
        end = f'{(x+1) * partition_size}GB'
        create_partition(device, namespace, start,
                         end, fail_on_err=fail_on_err)


def delete_partition(ns_device_path, partition, fail_on_err=True):
    logger.debug(f'Deleting partition {ns_device_path}p{partition}')
    rc, out, err = run_cmd([CMD_PARTED,
                            '-s', f'{ns_device_path}',
                            'rm', partition],
                           fail_on_err=fail_on_err)
    logger.debug(f'Delete partition completed, rc={rc}: {out}')
    return rc


def get_max_disk_size(device, fail_on_err=True):
    logger.debug(f'Determining max number disk bytes for device {device}')
    return int(__get_controller_property(device, 'tnvmcap',
                                         fail_on_err=fail_on_err))


def get_unused_disk_size(device, fail_on_err=True):
    logger.debug(f'Determining max number disk bytes for device {device}')
    return int(__get_controller_property(device, 'unvmcap',
                                         fail_on_err=fail_on_err))


def factory_reset(disk_sn):
    # Reset the NVMe drives on the system.
    nvme_resource_tree = generate_resource_tree()

    device = None

    for controller in nvme_resource_tree.values():
        device_sn = controller.get('sn')
        if disk_sn.strip() == device_sn.strip():
            device = controller
            break

    if device is None:
        logger.error(f"Unable to factory reset drive {disk_sn}.  No disk found "
                     "with that serial number.")
        return False

    logger.debug("Removing all of the namespaces on the drive")
    if not reset_drive(device):
        logger.error("Failed to remove namespaces off drive.")
        return False
    logger.debug(f"Successfully removed all namespaces on drive {disk_sn}.")

    logger.debug("Creating a single namespace")
    max_size = get_unused_disk_size(controller.get('name'))
    create_namespace(controller.get('name'), max_size)
    logger.debug(f"Created single name space with size {max_size}")


def list_nvme_namespaces(fail_on_err=True):
    rc, stdout, stderr = run_cmd(
        [CMD_NVME, 'list', '--o', 'json'], fail_on_err=True)
    if stdout == "":
        return {}
    return json.loads(stdout).get("Devices")


def get_controller_data(controller, fail_on_err=True):
    rc, stdout, stderr = run_cmd(
        [CMD_NVME, 'id-ctrl', f'/dev/{controller}', '--o', 'json'],
        fail_on_err=True)
    return json.loads(stdout)


def get_controller_data_human_format(controller, fail_on_err=True):
    rc, stdout, stderr = run_cmd(
        [CMD_NVME, 'id-ctrl', '-H', f'/dev/{controller}'],
        fail_on_err=True)
    return stdout


def list_nvme_controllers(fail_on_err=True):
    path = '/sys/class/nvme'
    rc, out, err = run_cmd([f'{CMD_LS} {path}'],
                           shell=True,
                           fail_on_err=False,
                           warn_on_err=False)
    if rc != 0:
        return []
    return out.splitlines()


def get_controller_serial_number(controller, fail_on_err=True):
    path = f'/sys/class/nvme/{controller}/serial'
    return run_cmd([CMD_CAT, path], fail_on_err=fail_on_err)[1]


def get_controller_firmware(controller, fail_on_err=True):
    path = f'/sys/class/nvme/{controller}/firmware_rev'
    return run_cmd([CMD_CAT, path], fail_on_err=fail_on_err)[1]


def get_controller_model(controller, fail_on_err=True):
    path = f'/sys/class/nvme/{controller}/model'
    return run_cmd([CMD_CAT, path], fail_on_err=fail_on_err)[1]


def __find_namespaces_for_serial(namespaces, serial):
    resp = []
    for namespace in namespaces:
        if namespace.get("SerialNumber") == serial:
            resp.append(namespace)
    return resp


def get_smart_data(device, fail_on_err=True):
    rc, out, err = run_cmd([f'{CMD_NVME} smart-log /dev/{device} -o json'],
                           shell=True, fail_on_err=fail_on_err)
    return json.loads(out)


def generate_resource_tree(fail_on_err=True):
    controllers = list_nvme_controllers(fail_on_err=fail_on_err)

    for controller in controllers:
        namespace_rescan(controller)

    all_namespaces = list_nvme_namespaces(fail_on_err=fail_on_err)
    resp = {}

    for controller in controllers:
        serial = get_controller_serial_number(controller,
                                              fail_on_err=fail_on_err)
        namespaces = __find_namespaces_for_serial(all_namespaces, serial)
        __add_namespaces_to_controller(resp, controller, namespaces,
                                       fail_on_err=fail_on_err)
        resp[controller]['smart'] = get_smart_data(
            controller, fail_on_err=fail_on_err)

    return resp


def __add_namespaces_to_controller(controllers, controller, namespaces,
                                   fail_on_err=True):
    if controllers.get(controller) is None:
        controllers[controller] = get_controller_data(
            controller, fail_on_err=fail_on_err)
        controllers[controller]['name'] = controller
        controllers[controller]['namespaces'] = []

    if namespaces:
        controllers[controller]['namespaces'].extend(namespaces)


def convert_TiB_to_bytes(tb):
    return int(tb * 1024 * 1024 * 1024 * 1024)


def convert_bytes_to_GB(byte_count):
    value = float(byte_count) / (1000.0 * 1000.0 * 1000.0)
    return "{:.2f}".format(value)
