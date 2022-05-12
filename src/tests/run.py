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

from io import StringIO
import logging


class Run:

    def __init__(self):
        # Success:
        #  - None: Ignored
        #  - False: Failed test
        #  - True: Successfully passed
        self.success = None

        # setup common logging handler
        self._stream = StringIO()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        handler = logging.StreamHandler(self._stream)
        handler.setFormatter(formatter)

        self.logger = logging.getLogger(f"{__name__}.{self.name()}")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def name(self) -> str:
        """Returns the name of the test"""
        pass

    def decription(self) -> str:
        """Returns the description of the test"""
        pass

    def execute(self) -> None:
        """Executes the test"""
        pass

    def result(self) -> bool:
        """Returns if the test was a success or not."""
        return self.success

    def report(self) -> str:
        """Returns a string containing the detailed data for the run."""
        return self._stream.getvalue()
