#!/usr/bin/env python3
#
# Copyright 2025 Ettus Research, a National Instruments Brand
#
# SPDX-License-Identifier: MIT
#
""""Example for verifying the UHD software environment.

This example checks if the UHD Python module is installed and working correctly.
It queries the UHD version and lists any connected USRP devices.
This is useful for ensuring that the UHD software environment is set up correctly.
"""	

def check_sw_env():
    """Check the UHD software environment by reading out the version."""
    try:
        import uhd
        # Query UHD version information
        version = uhd.get_version_string()
        # Query USRP devices infromation
        usrps = uhd.find("")
        usrps_string = ""
        if not usrps:
            usrps_string = "No USRP devices found."
        else:
            for usrp in usrps:
                if usrp:
                    usrps_string += (usrp.to_pp_string())
        return("UHD is installed and working in the Python environment.\n"
               f"Version: {version}\n\n"
               f"Found USRP Devices (multiple occurrences of the same device possible)\n\n{usrps_string}")
    except ModuleNotFoundError as err:
        return ("UHD is not installed or not found in the Python environment. \n"
                f"Error: {err}")
    
if __name__ == "__main__":
    result = check_sw_env()
    print(result)