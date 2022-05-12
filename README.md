# Open NVMe Qualification Tool

This tool runs a series of tests to do qualification of NVMe drives. While many drives claim support
for various capabilities, this tool validates many of those assumptions and stresses the drives in
complex manners. These tests include:

- Basic Performance Tests (Sequential/Random I/O)
- NVMe namespace testing
- Driving heavy I/O while driving controller commands
- OPAL testing
- I/O testing across many namespaces concurrently

## Device Pre-requisites

The tests generally assume the following capabilities on the drive:

- TCG Opal or Ruby support - This can be turned off by commenting out the opal tests.
- Multiple Namespaces - This is baked into most tests at the moment. Can not easily be turned off
- Secure Erase - Drive wide and namespace specific secure erase. Can be tuned by turning off tests.

## Test Configuration

This tool is to be copied to a system with the NVMe drive, and then executed directly on the system.

The host operating environment should be either:

- RHEL 8
- Ubuntu 18.04 or 22.04

Prior to running, you should know the following:

- The drive identifier in the system (ex. nvme0)
- The PSID for the drive (if running the OPAL tests)
- Have an updated firmware file on the system, to run the firmware update tests

## Usage

Usage is essentially three different steps.

1. Installation - performed once. See next section.
2. Configuration - update the config file to inform the tool expected results. Some default
   configurations are provided.
3. Execute - run the tests

The test can be started with the following:

```
python3 main.py -c ~/path_to_config.yaml -o ~/path_to_report.txt
```

The `-c` parameter references the configuration file. The `-o` is the location to store the result.

Execution duration will depend highly on the configuration passed in. Tests may take several hours
or a few minutes. It is recommended that if you're runing the tests over SSH, you use a tool like
`screen` or run the test as a background process. This will allow the test to continue in the event
you lose connectivity.

## Installation

This tool is set up to run a variety of tests, and those tests have a series of dependencies. The
following steps must be run ahead of test execution

### RHEL 8

```shell
# Change to root
su

# Install some tools
yum -y install fio nvme-cli python3 python3-pip

# The requirements.txt is from this source folder
pip3 install requirements.txt

# Get the sedutil-cli
wget -c https://github.com/Drive-Trust-Alliance/exec/blob/master/sedutil_LINUX.tgz?raw=true \
    -O sedutil_LINUX.tgz
tar -xvf sedutil_LINUX.tgz
chown root:root sedutil/Release_x86_64/sedutil-cli
mv sedutil/Release_x86_64/sedutil-cli /usr/local/bin
rm -rf ./sedutil*
```

### Ubuntu 18.04

```shell
# Change to root
sudo su

# Install some tools
apt-get install -y fio python3-pip python3

# The requirements.txt is from this source folder
pip3 install requirements.txt

# Needs an updated nvme-cli, that supports json output
wget http://launchpadlibrarian.net/496810028/nvme-cli_1.9-1ubuntu0.1_amd64.deb
dpkg --install nvme-cli_1.9-1ubuntu0.1_amd64.deb
rm nvme-cli_1.9-1ubuntu0.1_amd64.deb

# Get the sedutil-cli
wget -c https://github.com/Drive-Trust-Alliance/exec/blob/master/sedutil_LINUX.tgz?raw=true \
    -O sedutil_LINUX.tgz
tar -xvf sedutil_LINUX.tgz
chown root:root sedutil/Release_x86_64/sedutil-cli
mv sedutil/Release_x86_64/sedutil-cli /usr/local/bin
rm -rf ./sedutil*
```

### Ubuntu 22.04

```shell
# Change to root
sudo su

# Install some tools
apt-get install -y fio nvme-cli python3 python3-pip

# The requirements.txt is from this source folder
pip3 install requirements.txt

# Get the sedutil-cli
wget -c https://github.com/Drive-Trust-Alliance/exec/blob/master/sedutil_LINUX.tgz?raw=true \
    -O sedutil_LINUX.tgz
tar -xvf sedutil_LINUX.tgz
chown root:root sedutil/Release_x86_64/sedutil-cli
mv sedutil/Release_x86_64/sedutil-cli /usr/local/bin
rm -rf ./sedutil*
```
