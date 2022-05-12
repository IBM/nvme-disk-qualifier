# ======================================================================
# Copyright IBM Corp. 2022
# The source code for this program is not published or otherwise
# divested of its trade secrets, irrespective of what has been deposited
# with the U.S. Copyright Office.
# ======================================================================

import argparse
import logging
import time
import yaml

from datetime import datetime

from nvme import utils as n_utils

from tests import erase
from tests import firmware
from tests import namespaces
from tests import opal
from tests import perf

# setup common logging handler
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)

# setup logger for utils
logger = logging.getLogger("")
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Qualifies a NVMe disk.  Ensures it passes a robust set of tests.\n"
                     "WARNING: All data on drive will be erased."),
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("-c", "--config", required=True,
                        help=("The path to the config file"))

    parser.add_argument("-r", "--report", required=True,
                        help=("The path for the output report to be put into.  Will be standard text."))

    return parser


def write_report(tests, drive, output_path):
    r = open(output_path, "w+")

    r.write("NVMe Disk Tester\n")

    date = datetime. now(). strftime("%Y_%m_%d-%I:%M:%S_%p")
    r.write(f"Date Run: {date}\n")
    r.write(f"Drive Path: /dev/{drive}\n")
    r.write(f"Model: {n_utils.get_controller_model(drive)}\n")
    r.write(f"Serial Num: {n_utils.get_controller_serial_number(drive)}\n")
    r.write(f"Firmware Level: {n_utils.get_controller_firmware(drive)}\n\n")

    r.write(f"Tests Executed: {len(tests)}\n")
    r.write(f"Tests Passed: {len([t for t in tests if t.result()])}\n")
    r.write(f"Tests Failed: {len([t for t in tests if t.result() is False and t.result() is not None])}\n")
    r.write(f"Tests Ignored: {len([t for t in tests if t.result() is None])}\n\n")

    for test in tests:
        r.write(
            '--------------------------------------------------------------------------------\n')
        r.write(
            '--------------------------------------------------------------------------------\n')
        r.write(f'Test: {test.name()}\n')
        r.write(f'Description: {test.description()}\n')

        # This might be ignored
        if test.result() is None:
            r.write("Test Skipped\n")
            continue

        # Not ignored, finish results
        r.write(f'Test Passed: {test.result()}\n')
        r.write(
            '--------------------------------------------------------------------------------\n')
        r.write('Test Logs:\n')
        r.write(f'{test.report()}')
        r.write(
            '--------------------------------------------------------------------------------\n')

    r.close()


def main():
    parser = init_argparse()
    args = parser.parse_args()

    with open(args.config, 'r') as config_file:
        config = yaml.safe_load(config_file)

    tests = [opal.OpalCapable(config),
             opal.OpalLockTest(config),
             namespaces.NSLayout(config),
             namespaces.ParallelIO(config),
             perf.SeqRead(config),
             perf.SeqWrite(config),
             perf.SeqMixed(config),
             perf.RandRead(config),
             perf.RandWrite(config),
             namespaces.MultiNSPerf(config),
             erase.SecureEraseDrive(config),
             erase.SecureEraseWithMultiNamespaces(config),
             firmware.ApplyNew(config)
             ]

    for test in tests:
        if test.name() in config.get('execute', []) or config.get('execute') is None:
            logger.info(f"Starting test: {test.name()}")
            logger.info(f"  Description: {test.description()}")
            test.execute()
            logger.info(f"  Test finished.  Result: {test.result()}")
            time.sleep(1)
        else:
            logger.info(f"Ignoring test: {test.name()}")

    logger.info("All tests complete.  Compiling report.")
    write_report(tests, config['drive']['name'], args.report)
    logger.info("Test finished.")


if __name__ == '__main__':
    main()
