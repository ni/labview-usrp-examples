# Example for Tx/Rx Loopback using Python/RFNoC UHD API
This example shows how to set up a basic Tx/Rx loopback and stream data using
RF Network-on-chip (RFNoC). It uses the UHD RFNoC API for Python to configure
the USRP device and stream data between the Rx and Tx paths.

More detailed information can be found in the in-code documentation of the
example.

## Software Setup
- Make sure that software [dependencies](../README.md#dependencies) are satisfied.
- Install required software as described in the section 
[software-setup](../README.md#software-setup).

## Hardware Setup
The following description refers to the use of a USRP X410 device. Other USRP
devices like the USRP X440 or USRP N3x0 can also be integrated. For device-specific 
settings, please refer to the [USRP Manual](https://files.ettus.com/manual/).

The reference setup for this example consists of the following components:
- PXIe-1095 Chassis
- PXIe-8881 Embedded Controller
- PXIe-8240 Ethernet Interface Module or 
[similar](https://www.ni.com/en-gb/shop/category/gpib-serial-and-ethernet.html?productId=139226) 
supporting 10 Gigabit or more
- USRP X410 with X4_200 FPGA image

Make sure that the USRP device QSFP28 Port 0 is directly connected via a 
QSFP28 cable to the PXIe Ethernet Interface Module. Prepare the USRP to be 
compatible with the UHD version installed before (e.g. 4.8.0) by
- [updating the filesystem](https://files.ettus.com/manual/page_usrp_x4xx.html#x4xx_updating_filesystems)
- [updating the FPGA image](https://files.ettus.com/manual/page_usrp_x4xx.html#x4xx_updating_fpga)

For Tx-Rx loopback operation, connect a Tx port to an Rx port using an
SMA cable and a 30dB attenuator (e.g. TX/RX 0 -> RX1 of RF 0, daughterboard 0).

Example configuration:
![Tx/Rx Loopback Cabling](../assets/tx-rx-loopback-cabling.png)

## Check Connectivity
Make sure that both the PXIe Windows Controller and USRP have IP addresses
in the same subnet. To assign a static IP address to the USRP QSFP28 ports,
refer to these [instructions](https://files.ettus.com/manual/page_usrp_x4xx.html#x4xx_getting_started_network_connectivity).
Remember the IP address of the configured interface e.g. sfp0, QSFP28 0 
(4-lane interface or lane 0).

## Run the Example
- Make sure that you have both the VI and Python file in the same directory.
- Open the VI using LabVIEW and enter the IPv4 address of the configured QSFP28 port of the USRP into the `USRP IP address` field.
- Adjust the `Python Version` to your installation.
- Adjust the `RFNoC Graph Settings` to your SMA cabling (e.g. keep all `0` if you have connected TX/RX 0 -> RX1 of RF 0, daughter board 0).
- Adjust the `Rx Active Antenna`, e.g. to `RX1`, and `Tx Active Antenna`, e.g. to `TX/RX0`.
- Adjust the `Rx Gain` and `Tx Gain` settings to your needs.
- Run the Example.
- The `Tx Waveform Graph` should now be visible under `Received Signal`.

## Example Front Panel
![Tx/Rx Loopback Front Panel](../assets/tx-rx-loopback-front-panel.png)