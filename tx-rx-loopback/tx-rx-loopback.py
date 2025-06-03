#!/usr/bin/env python3
#
# Copyright 2025 Ettus Research, a National Instruments Brand
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""Example for Tx/Rx loopback using Python/RFNoC UHD API.

This example shows how to set up a basic Tx/Rx loopback and stream using
RF Network-on-chip (RFNoC). It uses the UHD RFNoC API for Python to configure
the USRP device and stream data between the Rx and Tx paths. 

It demonstrates the use of LabVIEW Python Nodes to call into UHD Python API and
to utilize RFNoC capabilities to create graphs connecting multiple RFNoC blocks
and stream data from the host to an USRP and receive back. The LabVIEW example
VI shipped with this package is used to create a Python Object reference in
LabVIEW which holds the Python ExampleSession class object. This ExampleSession
object is then used as input/output to the LabVIEW example. The Python example
is designed with simple modular functions to allow for easy integration into
LabVIEW example. The functions in the Python example can used in 2 ways:

1. Python only: This example can be executed as it is. The main function
setups the Tx/Rx loopback chain, loads the waveform from a Python NumPy Array
file from disk, starts transmitting the waveform samples and receives it.

2. LabVIEW + Python: In this case, the main function from the example is not
executed. Instead the LabVIEW VI is used to call into the defined Python sub
functions using the LabVIEW Python Node. In this case, the LabVIEW VI also
generates the waveform (sine wave) for transmission and uses the Python sub
functions to perform the initial USRP/RFNoC setup and the Tx/Rx streaming. The
VI only passes Tx samples to Python and reads back Rx samples from Python to
display the respective waveform on the VI's front panel. 

Refer to the below documentation for more details on
- UHD Python API user manual: https://files.ettus.com/manual/page_python.html
- UHD Python API Knowledge base: https://kb.ettus.com/UHD_Python_API
- UHD RFNoC user manual: https://files.ettus.com/manual/page_properties.html
- UHD RFNoC API: https://files.ettus.com/manual/group__rfnoc__blocks.html
- UHD RFNoC Knowledge base: https://kb.ettus.com/Getting_Started_with_RFNoC_in_UHD_4.0
- LabVIEW Python Node user manual: https://www.ni.com/en/support/documentation/supplemental/18/installing-python-for-calling-python-code.html
"""
import collections
import os
import threading
import numpy as np
import uhd

# Named tuple to hold block and port information.
BlockInfo = collections.namedtuple(
    "BlockInfo", ["block", "port"])

# Tuple to hold required RFNoC graph settings.
GraphSettings = ("rx_radio", "rx_chan", "tx_radio", "tx_chan")

# Tuple to hold required RF settings.
RfSettings = ("frequency", "gain", "antenna", "rate")

# Maps the otw_format to the corresponding sample size in bytes.
OTW_SIZE_MAPPING = {"sc8": 2, "sc16": 4}

class ExampleSession:
    """ExampleSession class to hold USRP device and graph information."""
    
    def __init__(self, args):
        """Initialize the ExampleSession with the given arguments."""
        self.args = args
        self.graph = uhd.rfnoc.RfnocGraph(args)
        self.tx_md = None
    
    def __del__(self):
        """Destructor to clean up the ExampleSession."""
        self.graph = None
        
    def setup_graph(self, graph_settings):
        """Create Tx/Rx streamers and connect them to given Radio channels.
        
        This method sets up both Rx and Tx streamers and connects them to the appropriate
        radio channels as specified in the `graph_settings` parameter. It performs the following steps:
        - Retrieves the Rx and Tx radio blocks and initializes their control objects.
        - Creates Rx and Tx streamers with the specified stream arguments.
        - Finds the block chains for both Rx and Tx paths using the UHD RFNoC graph.
        - Connects the streamers through the discovered block chains, handling DDC (for Rx) and DUC (for Tx) blocks if present.
        - Raises a RuntimeError if no valid chain is found for the requested radio and channel.
        - Commits the graph after all connections are established.
        """
        # setup rx streamer and connect it to the Rx radio channel
        # and the last block in the Rx chain
        radio_block = self.graph.get_block(f"Radio#{graph_settings.rx_radio}")
        self.rx_radio = uhd.rfnoc.RadioControl(radio_block)
        self.rx_chan = graph_settings.rx_chan
        self.rx_streamer = self.graph.create_rx_streamer(1, uhd.usrp.StreamArgs("fc32", "sc16"))
        
        edges = uhd.rfnoc.get_block_chain(self.graph, self.rx_radio.get_unique_id(), self.rx_chan, True)
        if not edges:
            raise RuntimeError(f"No chain found for {self.self.rx_radio.get_unique_id()} ({self.rx_chan})")

        last_block_in_chain = edges[-1].src_blockid
        last_port_in_chain = edges[-1].src_port

        if "DDC" in last_block_in_chain:
            print("found DDC block")
            self.ddc = BlockInfo(uhd.rfnoc.DdcBlockControl(self.graph.get_block(last_block_in_chain)), last_port_in_chain)
        else:
            self.dcc = None

        uhd.rfnoc.connect_through_blocks(
            self.graph, self.rx_radio.get_unique_id(), self.rx_chan, last_block_in_chain, last_port_in_chain)
        self.graph.connect(last_block_in_chain, last_port_in_chain,
                      self.rx_streamer, 0)

        # setup tx streamer and connect it to the Tx radio channel
        # and the last block in the Tx chain
        radio_block = self.graph.get_block(f"Radio#{graph_settings.tx_radio}")
        self.tx_radio = uhd.rfnoc.RadioControl(radio_block)
        self.tx_chan = graph_settings.tx_chan
        self.tx_streamer = self.graph.create_tx_streamer(1, uhd.usrp.StreamArgs("fc32", "sc16"))
        
        edges = uhd.rfnoc.get_block_chain(self.graph, self.tx_radio.get_unique_id(), self.tx_chan, False)
        if not edges:
            raise RuntimeError(f"No chain found for {self.self.tx_radio.get_unique_id()} ({self.tx_chan})")

        last_block_out_chain = edges[-1].dst_blockid
        last_port_out_chain = edges[-1].dst_port

        if "DUC" in last_block_out_chain:
            print("found DUC block")
            self.duc = BlockInfo(uhd.rfnoc.DucBlockControl(self.graph.get_block(last_block_out_chain)), last_port_out_chain)
        else:
            self.duc = None

        uhd.rfnoc.connect_through_blocks(
            self.graph, last_block_out_chain, last_port_out_chain, self.tx_radio.get_unique_id(), self.tx_chan)
        
        self.graph.connect(self.tx_streamer, 0, last_block_out_chain, last_port_out_chain)
                           
        self.graph.commit()

def check_session(session: any) -> None:
    """Check if session is a valid ExampleSession object."""
    if not isinstance(session, ExampleSession):
        raise RuntimeError(f"session is not an ExampleSession")
        
def check_settings(settings: any) -> None:
    """Check if settings is a valid RF settings object. 
    
    It should have all members --> [frequency, gain, antenna, rate].
    Raises a RuntimeError if a member is missing.
    """
    if not settings:
        raise RuntimeError("settings is empty!")
    settings_members = dir(settings)
    for member in RfSettings:
        if not member in settings_members:
            raise RuntimeError(f"settings is missing {member}-member")

def check_graph_settings(graph_settings: any) -> None:
    """Check if graph_settings is a valid RFNoC graph settings object. 
    
    It should have all members --> [rx_radio, rx_chan, tx_radio, tx_chan].
    Raises a RuntimeError if any member is missing.
    """
    if not graph_settings:
        raise RuntimeError("graph_settings is empty!")
    graph_settings_members = dir(graph_settings)
    for member in GraphSettings:
        if not member in graph_settings_members:
            raise RuntimeError(f"graph_settings is missing {member}-member")
    
def open_session(args: str, graph_settings: any) -> ExampleSession:
    """Open a session with the USRP device and setup the graph.
    
    args: specifies the USRP device arguments, which holds multiple key
    value pairs separated by commas (e.g., addr=192.168.40.2,type=x410).
    graph_settings: The settings for the RFNoC graph containing Rx and Tx
    radios and channels.
    """
    session = ExampleSession(args)
    if not session:
        raise RuntimeError("Failed to open Example session")
    else:
        print("ExampleSession opened")
        check_graph_settings(graph_settings)
        session.setup_graph(graph_settings)
        print("RFNoC blocks connected - Graph setup done")
        return session
    
def configure_rx(session: ExampleSession, rx_settings: any) -> None:
    """Configure the Rx radio with the given settings."""
    
    print("Configuring Rx radio settings.")
    check_session(session)
    check_settings(rx_settings)
    session.rx_radio.set_rx_frequency(rx_settings.frequency, session.rx_chan)
    session.rx_radio.set_rx_gain(rx_settings.gain, session.rx_chan)
    session.rx_radio.set_rx_antenna(rx_settings.antenna, session.rx_chan)
    if session.ddc:
        print(f"Reading DDC block output rate: {session.ddc.block.get_output_rate(session.ddc.port)}")
        print(f"Attempting to set DDC block output rate to: {rx_settings.rate}")
        session.ddc.block.set_output_rate(rx_settings.rate, session.ddc.port)
        print(f"Reading DDC block output rate: {session.ddc.block.get_output_rate(session.ddc.port)}")
    else:
        print("No DDC block found")
        print(f"Reading radio output rate: {session.rx_radio.get_rate()}")
        print(f"Attempting to set radio output rate to: {rx_settings.rate}")
        session.rx_radio.set_rate(rx_settings.rate)
        print(f"Reading radio output rate: {session.rx_radio.get_rate()}")

def configure_tx(session: ExampleSession, tx_settings: any) -> None:
    """Configure the Tx radio with the given settings."""
    
    print("Configuring Tx radio settings.")
    check_session(session)
    check_settings(tx_settings)
    session.tx_radio.set_tx_frequency(tx_settings.frequency, session.tx_chan)
    session.tx_radio.set_tx_gain(tx_settings.gain, session.tx_chan)
    session.tx_radio.set_tx_antenna(tx_settings.antenna, session.tx_chan)
    if session.duc:
        print(f"Reading DUC block input rate: {session.duc.block.get_input_rate(session.duc.port)}")
        print(f"Attempting to set DUC block input rate to: {tx_settings.rate}")
        session.duc.block.set_input_rate(tx_settings.rate, session.duc.port)
        print(f"Reading DUC block input rate: {session.duc.block.get_input_rate(session.duc.port)}")
    else:
        print("No DUC block found")
        print(f"Reading radio input rate: {session.tx_radio.get_rate()}")
        print(f"Attempting to set radio input rate to: {tx_settings.rate}")
        session.tx_radio.set_rate(tx_settings.rate)
        print(f"Reading radio input rate: {session.tx_radio.get_rate()}")
        
def start_rx_stream(session: ExampleSession) -> None:
    """Starts Rx streaming."""
    
    print("Starting to receive...")
    stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
    stream_cmd.stream_now = False
    time_now = session.graph.get_mb_controller().get_timekeeper(0).get_time_now()
    stream_cmd.time_spec = time_now + uhd.types.TimeSpec(0.1)
    session.rx_streamer.issue_stream_cmd(stream_cmd)

def send_data(session: ExampleSession, buffer: np.ndarray) -> int:
    """Send data to the USRP.
    
    This function sends data from the given buffer to the USRP using the
    tx_streamer. It returns the number of samples sent. In the very first call
    (else tree) the start of the Tx data burst will be defined using TXMetadata
    and including a start time in the future.
    """
    if session.tx_md:
        session.tx_md.start_of_burst = False;
        session.tx_md.has_time_spec  = False;
    else:
        session.tx_md = uhd.types.TXMetadata()
        session.tx_md.start_of_burst = True;
        session.tx_md.end_of_burst   = False;
        session.tx_md.has_time_spec  = True;
        time_now = session.graph.get_mb_controller().get_timekeeper(0).get_time_now()
        session.tx_md.time_spec = time_now + uhd.types.TimeSpec(0.1)
    send = session.tx_streamer.send(buffer, session.tx_md)
    return send
 
def receive_data(session: ExampleSession, buffer: np.ndarray, buffer_size: int) -> tuple:
    """Receive data from the USRP.
    
    This function receives data from Rx streamer and passes it to the given
    arg buffer. It returns error codes and number of samples received.
    """
    # Supporting single channel for now
    num_channels = 1
    # Setting OTW_format
    otw_format = OTW_SIZE_MAPPING["sc16"]
    if session.ddc:
        data_rate = session.ddc.block.get_output_rate(session.ddc.port) * num_channels * otw_format
    else:
        data_rate = session.rx_radio.get_rate() * num_channels * otw_format
    rx_md = uhd.types.RXMetadata()
    # calculate the Rx timeout depending on the buffer size. 
    # the buffer should be filled in (buffer_size / data_rate) + some processing delay.
    # factor 2 should give us enough headroom, to receive all samples.
    timeout = 2 * buffer_size / data_rate
    # receive the data
    received = session.rx_streamer.recv(
        buffer, rx_md, timeout)
    return rx_md.error_code, rx_md.out_of_sequence, received
  
def receive_tx_async(session: ExampleSession) -> int:
    """Receive Tx async messages.
    
    This function receives asynchronous messages from the Tx path and returns
    event codes for error checks.
    """
    async_metadata = uhd.types.TXAsyncMetadata()
    if session.tx_streamer.recv_async_msg(async_metadata, 0.000001):
        if async_metadata.event_code != uhd.types.TXMetadataEventCode.burst_ack:
            return async_metadata.event_code
    return 0
           
def send_done(session: ExampleSession) -> None:
    """Send end of burst cmd to the USRP."""
    if session.tx_md:
        print("Sending end of burst cmd")
        session.tx_md.end_of_burst = True
        session.tx_streamer.send(np.zeros((1, 1), dtype=np.complex64), session.tx_md)
        session.tx_md = None

def stop_rx_stream(session: ExampleSession) -> None:
    """Stops Rx streaming."""
    print("Stop Rx streaming")
    stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
    session.rx_streamer.issue_stream_cmd(stream_cmd)

def close_session(session: ExampleSession) -> None:
    """Close the session and release resources."""
    print("Closing Example session")
    session = None

def send_file(session: ExampleSession) -> None:
    """Loads a waveform file from disk, sends it to the USRP device."""
    data = np.load(os.path.join(os.path.dirname(__file__), "waveform.npy"))
    buffer_len = len(data[0])
    sent = 0
    print(f"send file with {buffer_len} samples")
    for i in range(1000):
        sent += send_data(session, data, buffer_len)
        
    send_done(session)
    print(f"done send file, sent {sent}")
        
if __name__ == "__main__":
    """Main function to test the example.
    
    This main function is only used for testing the loopback example from
    within Python. It is not intended to be used from the LabVIEW example VI.
    """
    print(__file__)
    Object = lambda **kwargs: type("Object", (), kwargs)
    
    # Initializing graph settings and RF settings
    graph_settings = Object(rx_radio = 0, rx_chan = 0, tx_radio = 0, tx_chan = 0)
    rx_settings = Object(frequency = 2e9, gain = 0, antenna = "RX2", rate = 1e6)
    tx_settings = Object(frequency = 2e9, gain = 0, antenna = "TX/RX0", rate = 1e6)
    # Open session
    session = open_session("addr=192.168.10.88", graph_settings)
    # Configure Tx and Rx settings
    configure_tx(session, tx_settings)
    configure_rx(session, rx_settings)
    # Start Tx thread --> read waveform from file and send it
    # The example waveform.npy file is a NumPy array containing int64 samples
    # and have properties listed below:
    # Waveform = Sine, Freq tone = 10kHz, Amplitude = 0.707, Size = 10000 samples
    tx_thread = threading.Thread(target=send_file, args=(session,))
    tx_thread.start()
    # Create buffer for Rx
    buffer_size = 10000
    buffer = np.zeros((1, buffer_size), dtype=np.int64)
    # Start Rx streaming
    overall = 0
    start_rx_stream(session)
    i = 1000;
    while i > 0:
        # Receive data
        (error_code, out_of_sequence, recv) = receive_data(session, buffer, buffer_size)
        overall += recv
        if error_code != uhd.types.RXMetadataErrorCode.none:
            if error_code == uhd.types.RXMetadataErrorCode.timeout:
                print("Rx timeout")
                continue
            print(f"break at {i} with {error_code} received {recv}")
            break
        i-=1
    # Stop Rx streaming
    stop_rx_stream(session)
    print(f"Done! Rx received {overall} samples")
    # Wait for Tx thread to finish    
    tx_thread.join()
    # Close session
    close_session(session)

    
