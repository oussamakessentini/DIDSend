#  CanApi4.py: Definition of the CAN-API
#
#  Version 4.3.4
#
#  Principle:
#  ~~~~~~~~~~
#  The driver supports multiple clients (= Windows applications that
#  communicate with CAN buses), and multiple CAN hardware implemented
#  with SJA1000 CAN controllers.
#  A cardinal point is the idea of the "net": it describes a CAN bus that
#  is extended virtually into the PC. Multiple clients can be connected
#  to one net, which itself can have an interface to a physical CAN bus
#  via an appropriate CAN adapter.
#  A net definition determines, aside from the Bit rate, an amount
#  of CAN messages to process.
#
#  Clients that are specialized on some kind of CAN bus (e.g. stepper
#  motor control, car radio panel, etc.), should not offer any hardware
#  selection, but directly address a fixed net (e.g. 'Lab-Net').
#  The connection net - hardware can then be accomplished by a separate
#  configuration tool (the settings depend on the respective PC and its
#  CAN hardware).
#
#  If necessary, CAN nodes connected to an external CAN bus can 
#  be simulated by clients on the same net. In this case there is no
#  CAN hardware required, the complete bus can be simulated within the
#  PC. The net can then be defined as an 'Internal Net'.
#
#  Samples for possible net configurations:
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  (can all be realized at the same time):
#                                                   external
#                                    ,------------< CAN bus 'A'
#  ,--------. ,--------.       ,-----+----.
#  |Client A| |Client B|       |Hardware 1|
#  `---+----' `----+---'       `-----+----'
#      `-----------+-----------------'
#               N e t  I                           external
#                                    ,------------< CAN bus 'B'
#  ,--------. ,--------.       ,-----+----.
#  |Client C| |Client D|       |Hardware 2|
#  `---+--+-' `----+---'       `-----+----'
#      |  `--------+-----------------'              external
#      |        N e t  II            ,------------< CAN bus 'C'
#      |      ,--------.       ,-----+----.
#      |      |Client E|       |Hardware 3|
#      |      `----+---'       `-----+----'
#      `-----------+-----------------'             'Gateway'
#               N e t  III
#   ,--------. ,--------. ,--------.
#   |Client F| |Client G| |Client H|
#   `---+----' `---+----' `---+----'               'Internal net'
#       `----------+----------'
#               N e t  IV
#
#  Features:
#  ~~~~~~~~~
#   - 1 client can be connected to multiple nets
#   - 1 net supplies multiple clients
#   - 1 hardware can be used by 1 net at the same time
#   - each net can be assigned to 1 hardware or no hardware at all
#   - if a client sends a message on the net, the message will be routed
#     to all other clients and over a connected hardware to the physical
#     bus
#   - if a message is received from a hardware, it will be routed to all
#     clients which are connected to the hardware via a net. Each client
#     only receives the messages which pass its acceptance filter
#   - CAN hardware can be configured via a Windows Control Panel application,
#     nets can be configured with a separate tool.
#     Multiple nets can be defined for each hardware, but only one can be
#     active at the same time.
#   - clients connect to a net via the name of the net
#   - each hardware has its own transmit queue to buffer outgoing messages
#   - each client has a receive queue to buffer received messages
#   - each client has a transmit queue, which holds outgoing messages until
#     their scheduled real send time. Is the send time reached they will
#     be written into the transmit queue of the hardware.
#   - client: 'client handle'. This number is used by the driver to
#             identify and manage a client
#   - hw:     'hardware handle'. This number is used by the driver to
#             identify and manage a hardware
#   - net:    'net handle'. This number is used by the driver to
#             identify and manage a net
#   - all handles are 1-based. 0 = illegal handle
#   - used hardware and nets are defined in the Registry.
#     When a PCAN driver is loaded, it reads the configuration and
#     initializes all hardware and nets.
#
#  Registry Keys:
#  10/8.1/7:
#      HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\Pcan_usb
#      HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\Pcan_pci
#      HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\Pcan_pccard
#      HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\Pcan_virtual
#      HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\Pcan_lan
#
#  Values (as strings):
#      Net<NetHandle>=<Name>,<HwHandle>,<BTR0BTR1>
#
#  Example:
#      Hardware1=1,0x300,15
#      Net7=TestNet,1,0x001C
#
#   - the API functions are divided into 3 groups:
#     1) Control-API: control of the driver through configuration tools
#     2) Client-API: reading and writing of messages through applications
#     3) Info-API: helper functions


# Module Imports
#
from ctypes import *
from string import *
import platform

##############################
# Type definitions
##############################

HCANHW              = c_uint8   # type 'hardware handle'
HCANNET             = c_uint8   # type 'net handle'
HCANCLIENT          = c_uint8   # type 'client handle'
HCANOBJECT          = c_uint8   # any handle type
can_status_t        = int       # status value/return code


##############################
# Constants definitions
##############################

# Maximum values for CAN identifiers
CAN_MAX_STANDARD_ID = c_uint32(0x7FF)
CAN_MAX_EXTENDED_ID = c_uint32(0x1FFFFFFF)

# Bit rate codes = BTR0/BTR1 register values for non-CAN-FD hardware
CAN_BITRATE_1M    = c_uint(0x0014)    #     1 Mbit/s
CAN_BITRATE_800K  = c_uint(0x0016)    #   800 kbit/s
CAN_BITRATE_500K  = c_uint(0x001C)    #   500 kbit/s
CAN_BITRATE_250K  = c_uint(0x011C)    #   250 kbit/s
CAN_BITRATE_125K  = c_uint(0x031C)    #   125 kbit/s
CAN_BITRATE_100K  = c_uint(0x432F)    #   100 kbit/s
CAN_BITRATE_95K   = c_uint(0xC34E)    # 95.23 kbit/s
CAN_BITRATE_83K   = c_uint(0x852B)    # 83.33 kbit/s
CAN_BITRATE_50K   = c_uint(0x472F)    #    50 kbit/s
CAN_BITRATE_47K   = c_uint(0x1414)    #  47.6 kbit/s
CAN_BITRATE_33K   = c_uint(0x8B2F)    # 33.33 kbit/s
CAN_BITRATE_20K   = c_uint(0x532F)    #    20 kbit/s
CAN_BITRATE_10K   = c_uint(0x672F)    #    10 kbit/s
CAN_BITRATE_5K    = c_uint(0x7F7F)    #     5 kbit/s

# Error Codes
CAN_ERR_OK                  = can_status_t(0x0000)     # No error
CAN_ERR_XMTFULL             = can_status_t(0x0001)     # Transmit buffer in CAN controller is full
CAN_ERR_OVERRUN             = can_status_t(0x0002)     # CAN controller was read too late
CAN_ERR_BUSWARNING          = can_status_t(0x0008)     # Bus error: an error counter reached the 'warning' limit  
CAN_ERR_BUSPASSIVE          = can_status_t(0x40000)    # Bus error: CAN controller is in Error Passive state
CAN_ERR_BUSOFF              = can_status_t(0x0010)     # Bus error: CAN controller is in Bus-off state
CAN_ERR_QRCVEMPTY           = can_status_t(0x0020)     # Receive queue is empty
CAN_ERR_QOVERRUN            = can_status_t(0x0040)     # Receive queue was read too late
CAN_ERR_QXMTFULL            = can_status_t(0x0080)     # Transmit queue ist full
CAN_ERR_REGTEST             = can_status_t(0x0100)     # Test of the CAN controller hardware registers failed (no hardware found)
CAN_ERR_NODRIVER            = can_status_t(0x0200)     # Driver not loaded
CAN_ERRMASK_ILLHANDLE       = can_status_t(0x1C00)     # Mask for all handle errors
CAN_ERR_HWINUSE             = can_status_t(0x0400)     # Hardware already in use by a net
CAN_ERR_NETINUSE            = can_status_t(0x0800)     # A client is already connected to the net
CAN_ERR_ILLHW               = can_status_t(0x1400)     # Hardware is invalid
CAN_ERR_ILLNET              = can_status_t(0x1800)     # Net is invalid (handle/name)
CAN_ERR_ILLCLIENT           = can_status_t(0x1C00)     # Client is invalid
CAN_ERR_RESOURCE            = can_status_t(0x2000)     # Resource (queue, client, timer) cannot be created
CAN_ERR_ILLPARAMTYPE        = can_status_t(0x4000)     # Invalid parameter
CAN_ERR_ILLPARAMVAL         = can_status_t(0x8000)     # Invalid parameter value
CAN_ERR_UNKNOWN             = can_status_t(0x10000)    # Unknown error
CAN_ERR_ILLFUNCTION         = can_status_t(0x20000)    # CAN-API function not supported
CAN_ERR_ILLMODE             = can_status_t(0x80000)    # Object in wrong state for attempted operation
CAN_ERR_SYSTEMERROR_MASK    = can_status_t(0x80000000) # Mask for Windows system error codes

CAN_ERR_ANYBUSERR           = can_status_t(CAN_ERR_BUSWARNING | CAN_ERR_BUSPASSIVE | CAN_ERR_BUSOFF)


# Parameter codes for SetParam|GetParam

# Hardware: index number of the driver-internal hardware sub-type (PCAN-USB, PCAN-USB Pro, ...) (uint32)
CAN_PARAM_HWDRIVERNR  = c_uint16(2) # 0x02

# Name of the driver/hardware/net/client (string255)
CAN_PARAM_NAME  = c_uint16(3) # 0x03

# Hardware: I/O address of the hardware (uint32)
CAN_PARAM_HWPORT = c_uint16(4) # 0x04

# Hardware interrupt (uint32)
CAN_PARAM_HWINT = c_uint16(5) # 0x05

# Hardware: the net that is connected to the hardware (uint32)
CAN_PARAM_HWNET = c_uint16(6) # 0x06

# Hardware/net: Bit rate, as BTR0/BTR1 code (uint32)
CAN_PARAM_BITRATE = c_uint16(7) # 0x07

# Hardware: CAN controller operation mode (uint32)
# 0 = controller is in Reset mode, 1 = Operation mode 
CAN_PARAM_ACTIVE = c_uint16(10) # 0x0a

# Hardware/client: unsent messages in transmit queue (uint32)
CAN_PARAM_XMTQUEUEFILL = c_uint16(11) # 0x0b

# Hardware/client: unread messages in receive queue (uint32)
CAN_PARAM_RCVQUEUEFILL = c_uint16(12) # 0x0c

# Net: hardware handle associated with net (uint32)
CAN_PARAM_NETHW        = c_uint16(19) # Deprecated, use CAN_PARAM_NETHW_ACTIVE
CAN_PARAM_NETHW_ACTIVE = c_uint16(19) # 0x13

# Net: Flag: clients[i] <> 0: client 'i' belongs to net (string255)
CAN_PARAM_NETCLIENTS = c_uint16(20) # 0x14

# Client: window handle of client (uint32)
CAN_PARAM_HWND = c_uint16(21) # 0x15

# Client: Flag: nets[i] <> 0: net 'i' belongs to client (string255)
CAN_PARAM_CLNETS = c_uint16(22) # 0x16

# Driver/hardware/client: transmit queue size (uint32)
# Parameter is read-only for hardware and client
CAN_PARAM_XMTQUEUESIZE = c_uint16(23) # 0x17

# Driver/hardware/client: receive queue size (uint32)
# Parameter is read-only for hardware and client
CAN_PARAM_RCVQUEUESIZE = c_uint16(24) # 0x18

# Client: handle of Receive Event (uint32)
CAN_PARAM_ONRCV_EVENT_HANDLE = c_uint16(26) # Deprecated, use CAN_PARAM_EVENT_ONRCV

# Client: trigger mode of Receive Events (uint32)
# 0 = set (default), 1 = pulse
CAN_PARAM_ONRCV_EVENT_PULSE = c_uint16(27) # Deprecated, use CAN_PARAM_EVENT_ONRCV

# Client: enables/disables self-receive (uint32)
# 0 = self-receive disabled (default)
# 1 = client receives all of its own transmitted messages
CAN_PARAM_SELF_RECEIVE = c_uint16(28) # 0x1c

# Net: Delayed Message Distribution (uint32)
# 0 = transmits the messages to the other clients while writing into the
#     hardware queue (default)
# 1 = transmits the messages to the other clients only when hardware has
#     successfully transmitted the message on the bus
CAN_PARAM_DELAYED_MESSAGE_DISTRIBUTION = c_uint16(29) # 0x1d

# Hardware (ExpressCard/ExpressCard 34): Unique reseller/distributor
# code for OEM hardware (uint32)
CAN_PARAM_HW_OEM_ID = c_uint16(30) # 0x1e

# Hardware: location info text that describes the "position" of the
# hardware used (string255)
# Example: "I/O addr 0x378", "PCI bus 0, slot 7, controller 1"
# Can be specified in the registry or will be created automatically
CAN_PARAM_LOCATION_INFO = c_uint16(31) # 0x1f

# Hardware: PCI bus to which the hardware is connected (uint32)
CAN_PARAM_HWBUS = c_uint16(32) # 0x20

# Hardware: PCI slot to which the hardware is connected (uint32)
CAN_PARAM_HWDEVICE = c_uint16(33) # 0x21

# Hardware: PCI function of card (uint32)
CAN_PARAM_HWFUNCTION = c_uint16(34) # 0x22

# Hardware/net: 0-based index of the CAN controller (uint32)
CAN_PARAM_HWCONTROLLER = c_uint16(35) # 0x23

# Hardware: measured bus load values of PCAN-USB Pro and FD-compatible PCAN hardware (uint32)
CAN_PARAM_BUSLOAD = c_uint16(38) # 0x26

# Hardware/net: enable/disable Listen-only mode (uint32)
# 0 = Listen-only mode disabled (default), 1 = Listen-only mode enabled
CAN_PARAM_LISTEN_ONLY = c_uint16(49) # 0x31

# Hardware/net: Device ID (uint32)
CAN_PARAM_HW_DEVICENR = c_uint16(50) # 0x32

# Hardware: PEAK serial number (uint32)
CAN_PARAM_HW_SERNR = c_uint16(51) # 0x33

# Client/net/hardware: enable/disable Error Frames (uint32)
# 0 = Error Frames disabled (default)
# 1 = Error Frames enabled, client receives Error Frames in can_errorframe_t records
# Parameter is read-only for hardware and net
CAN_PARAM_RCVERRFRAMES = c_uint16(53) # 0x35

# Client: exact 11-bit filtering (uint32)
# 0 = client filters by code/mask (default)
# 1 = client filters exact message ranges
CAN_PARAM_EXACT_11BIT_FILTER = c_uint16(56) # 0x38

# Hardware: location info that the user can set (string255)
# Actual data length is shorter than string length (249 characters + \0).
CAN_PARAM_USER_LOCATION_INFO = c_uint16(57) # 0x39

# Hardware: controls the "Select" LED of PCAN hardware (uint32)
# PCAN-USB (firmware version < 8):
#   0/1: causes an LED status change (LED blinks once)
# All other USB devices:
#   0 = LED off, 1 = LED on, 2 = LED blinks slow, 3 = LED blinks fast,
#   0xFFFFFFFF = revert to default state
CAN_PARAM_SELECT_LED = c_uint16(58) # 0x3a

# Net: client handle of net master (uint32)
# 0 = no master defined (default)
CAN_PARAM_NET_MASTER = c_uint16(66) # 0x42

# Hardware: enables 5V output on CAN connector (PCAN-PC Card/ExpressCard only) (uint32)
# 0 = 5V output disabled (default), 1 = 5V output enabled
CAN_PARAM_BUSPOWER = c_uint16(79) # 0x4f

# Hardware: Error Warning Limit in SJA1000 (uint32)
CAN_PARAM_ERROR_WARNING_LIMIT = c_uint16(83) # 0x53

# Hardware/client: Dual Filter Mode: use 1 or 2 acceptance filters (uint32)
CAN_PARAM_ACCFILTER_COUNT = c_uint16(84) # 0x54

# Hardware: patch for PCAN-USB, sets the Reset/Bus-On mode of SJA1000 (uint32)
CAN_PARAM_BUSON = c_uint16(90) # 0x5a

# Driver: load "hardware" keys from Registry (uint32)
# 0 = disabled, 1 = enabled (default)
CAN_PARAM_REGISTRYHARDWARELOADING = c_uint16(92) # 0x5c

# Driver: automatic Bus-On (uint32)
# 0 = automatic Bus-On disabled, 1 = automatic Bus-On after Bus-Off
CAN_PARAM_AUTOBUSON = c_uint16(96) # 0x60

# Hardware: enable/disable bus load measurement in hardware (PCAN-USB Pro and FD-compatible
# PCAN hardware) (uint32)
# 0 = bus load measurement disabled (default), 1 = bus load measurement enabled
CAN_PARAM_BUSLOAD_ENABLE = c_uint16(106) # 0x6a

# Hardware: creation of bus errors (PCAN-USB Pro and FD-compatible PCAN hardware)
# (can_param_buserrorgeneration_t)
CAN_PARAM_BUSERRORGENERATION = c_uint16(110) # 0x6e

# Client: accumulated ERR_QXMTFULL errors of a hardware, which occurred while the client was
# sending from its transmit queue (read-only) (uint32)
CAN_PARAM_XMTQUEUE_ERR_QXMTFULL_COUNT = c_uint16(113) # 0x71

# Client: enable/disable RTR frames (uint32)
# 0 = RTR frames disabled
# 1 = RTR frames enabled (default), client receives RTR frames in can_msg_rtr_t records
CAN_PARAM_RCVRTRFRAMES = c_uint16(119) # 0x77

# Client: enable/disable status frames (uint32)
# 0 = Status frames disabled
# 1 = Status frames enabled (default), client receives Status frames in can_hwstatus_t records
CAN_PARAM_RCVSTATUSFRAMES = c_uint16(120) # 0x78

# Hardware/net: indicates whether a hardware is FD-compatible or whether a net is a CAN FD net
# (read-only) (uint32)
# Hardware: 0 = Hardware is not FD-compatible, 1 = hardware is FD-compatible
# Net: 0 = Net is a CAN 2.0B net, 1 = net is a CAN FD net
CAN_PARAM_IS_FD = c_uint16(127)  # 0x7f

# Hardware: IP address of PCAN_LAN device (string255)
CAN_PARAM_IPADDRESS = c_uint16(128)  # 0x80

# Hardware: number of CAN controllers per hardware (uint32)
CAN_PARAM_HWCONTROLLER_COUNT = c_uint16(129) # 0x81

# Hardware: PEAK part number (string255)
CAN_PARAM_PARTNO = c_uint16(130) # 0x82

# Hardware (PCAN_LAN): number of receive/transmit routes (uint32)
CAN_PARAM_LAN_RCVROUTE_COUNT = c_uint16(131) # 0x83
CAN_PARAM_LAN_XMTROUTE_COUNT = c_uint16(132) # 0x84

# Client: limits the number of records returned by CAN_Read() (uint32)
# Default = 0 = no limit
CAN_PARAM_READ_MAX_RECORDCOUNT = c_uint16(133) # 0x85

# Client/net: enables/disables bus load frames (uint32)
# 0 = bus load frames disabled (default)
# 1 = bus load frames enabled, client receives bus load data in can_busload_t records
# Bus load measurement must be enabled separately for the hardware (CAN_PARAM_BUSLOAD_ENABLE) 
# to receive bus load data
# Parameter is read-only for net
CAN_PARAM_RCVBUSLOADFRAMES = c_uint16(134) # 0x86

# Client: enables/disables Events (uint32)
# 0 = events disabled (default)
# 1 = events enabled, client receives events in can_event_..._t records
CAN_PARAM_RCVEVENTS = c_uint16(135) # 0x87

# Hardware/net: CAN FD ISO/non-ISO mode for FD-compatible PCAN hardware (uint32)
# 0 = old Bosch standard, no Stuff Bit counter
# 1 = new ISO mode with Stuff Bit counter (default for hardware)
# 0xFFFFFFFF (net only) = ISO mode is determined by hardware configuration (default for net)
CAN_PARAM_CANFD_ISOMODE = c_uint16(136) # Deprecated, use CAN_PARAM_FD_ISOMODE
CAN_PARAM_FD_ISOMODE = c_uint16(136) # 0x88

# Hardware (USB hardware): OEM code of hardware (uint64)
# Valid OEM code is needed for driver for password access.
# Write through to device only possible with PEAK tools.
CAN_PARAM_OEM_CODE = c_uint16(137) # 0x89

# Hardware (FD-compatible USB hardware): password protection for 
# CAN_PARAM_USERDATA_SECURE device field (string255)
# Write: unlock device by sending a password, OEM code must have been set before.
# Read: one of the strings "OEM_CODE_VIRGIN", "PW_VIRGIN", "PW_FAIL", "PW_OK"
# Actual password length is shorter than string length (31 characters + \0).
CAN_PARAM_PASSWORD = c_uint16(138) # 0x8a

# Hardware (FD-compatible USB hardware): arbitrary user string, secured for
# OEM versions (string255)
# Write only possible for non-OEM version.
# Actual data length is shorter than string length (119 characters + \0).
CAN_PARAM_USERDATA_SECURE = c_uint16(139) # 0x8b

# Hardware (FD-compatible USB hardware): arbitrary user string (string255)
# Actual data length is shorter than string length (119 characters + \0).
CAN_PARAM_USERDATA = c_uint16(140) # 0x8c

# Hardware: hardware ID for the device as used in Windows (string255)
# String exactly as used in .INF file, in registry, and in device manager.
CAN_PARAM_HARDWARE_ID = c_uint16(141) # 0x8d

# Client: process ID of client == calling process of CAN_RegisterClient() (uint32)
CAN_PARAM_PROCESS_ID = c_uint16(142) # 0x8e

# Driver: upper limit of hardware handle range (1..MAX_HCANHW) (uint32)
CAN_PARAM_MAX_HCANHW = c_uint16(143) # 0x8f

# Driver: upper limit of net handle range (1..MAX_HCANNET) (uint32)
CAN_PARAM_MAX_HCANNET = c_uint16(144) # 0x90

# Driver: upper limit of client handle range (1..MAX_HCANCLIENT) (uint32)
CAN_PARAM_MAX_HCANCLIENT = c_uint16(145) # 0x91

# Driver: hardware handle enumeration method (uint32)
# 0 = Legacy hardware enumeration: 16..1, 17..MAX_HCANHW (default)
# 1 = Linear hardware enumeration: 1..MAX_HCANHW
CAN_PARAM_HW_ENUMERATION_LINEAR = c_uint16(146) # 0x92

# Pause between two transmit messages in microseconds (uint32)
# Client: current pause value for client
# Hardware: supported value range (read-only)
CAN_PARAM_XMT_INTERFRAME_DURATION = c_uint16(147) # 0x93

# Hardware handle of a net, as set in net registration. Valid even if associated hardware is
# not plugged in. See also CAN_PARAM_NETHW_ACTIVE (uint32)
CAN_PARAM_NETHW_PRESET = c_uint16(148) # 0x94

# API: Debug Log level (uint32)
# 0 = disabled
# 1 = calls only (w/o GetSystemTime)
# 2 = calls (w/o GetSystemTime), parameters, entry/exit, return values
# 3 = calls (including GetSystemTime), parameters, entry/exit, return values
CAN_PARAM_DEBUGLOG_LEVEL = c_uint16(149) # 0x95

# API: Path of Debug Log file, without file name (string255, UTF-8)
# Empty string switches off Log file generation, only OutputDebugString output
CAN_PARAM_DEBUGLOG_PATH = c_uint16(150) # 0x96

# Hardware/net: Timestamp Start-of-Frame (uint32)
# 0 = The timestamp of a CAN message is determined at End-of-Frame (default)
# 1 = The timestamp of a CAN message is determined at Start-of-Frame instead of End-of-Frame
CAN_PARAM_TIMESTAMP_SOF = c_uint16(151) # 0x97

# Hardware/net: Send ACK as sender (uint32)
# * The CAN controller sends an ACK slot on CAN also as sender.
# * No other CAN node must be present on the bus to ACK the CAN frame.
# * No external devices needed for ACK.
# 0 = Self-ACK disabled (default)
# 1 = Self-ACK enabled
CAN_PARAM_TX_SELF_ACK = c_uint16(152) # 0x98

# Hardware/net: Ignore BRS frames as receiver (uint32)
# * When a CAN FD frame with BRS is received the CAN controller will change to 'wait for bus idle' and
#   the frame is ignored, no Error Frame is sent.
# * Used to enable minimal CAN communication even when fast bitrate is unknown.
# 0 = BRS-ignore disabled (default)
# 1 = BRS-ignore enabled
CAN_PARAM_BRS_IGNORE = c_uint16(153) # 0x99

# Hardware: List of protocols supported with current settings (uint32)
# Bitwise OR of CAN_CONST_PROTOCOL_* constants
CAN_PARAM_PROTOCOLS = c_uint16(154) # 0x9a


# Parameters that set/return structured data

# Driver/API: PCAN driver or API DLL version (can_param_version_t)
CAN_PARAM_VERSION = c_uint16(200) # 0xc8

# Hardware: version of device firmware (can_param_version_t)
CAN_PARAM_FIRMWARE_VERSION = c_uint16(201) # 0xc9

# Hardware: version of device bootloader firmware (can_param_version_t)
CAN_PARAM_BOOTLOADER_VERSION = c_uint16(202) # 0xca

# Hardware: version of CPLD firmware (PCAN-USB Pro only) (can_param_version_t)
CAN_PARAM_CPLD_VERSION = c_uint16(203) # 0xcb

# Hardware: revision level of hardware device (can_param_version_t)
CAN_PARAM_HARDWARE_VERSION = c_uint16(204) # 0xcc

# Hardware/net: CAN non-FD bit rates in terms of CiA specifications (can_param_bitrate_nom_t)
CAN_PARAM_BITRATE_NOM = c_uint16(205) # 0xcd

# Hardware/net: CAN FD bit rates in terms of CiA specifications (can_param_bitrate_fd_t)
CAN_PARAM_BITRATE_FD = c_uint16(206) # 0xce 

# Hardware/net/client: Acceptance Filter, works on message ID, with binary code and mask patterns
# (read-only) (can_param_acceptance_filter_t)
CAN_PARAM_ACCEPTANCE_FILTER = c_uint16(207) # 0xcf

# Hardware/net/client: statistics for received and transmitted messages (can_param_traffic_t)
CAN_PARAM_TRAFFIC = c_uint16(208) # 0xd0

# Driver: version and copyright information of a device driver (string255)
CAN_PARAM_VERSIONINFO = c_uint16(209) # 0xd1

# Hardware (FD-compatible USB/PCI hardware): IRQ delay and timeout for buffered designs
# (IRQ throttle) (can_param_irq_timing_t)
# For good throughput, set count_limit and time_limit high:
# -> buffers are better filled, less IRQs occur and system load is lower.
# For good response timing, set count_limit and time_limit low:
# -> more IRQs occur, delay shrinks, buffers get less filled and system load is higher.
CAN_PARAM_IRQ_TIMING = c_uint16(211) # 0xd3

# Hardware (PCAN-Chip USB): Operation mode of 32 digital I/O pins (can_param_io_t)
# Bit mask with pin configuration: 0 = input, 1 = output
CAN_PARAM_IO_DIGITAL_CONFIG = c_uint16(213) # 0xd5

# Hardware (PCAN-Chip USB): Value assigned to 32 digital I/O pins (can_param_io_t)
# Bit mask with input/output level: 0 = low level voltage, 1 = high level
CAN_PARAM_IO_DIGITAL_VALUE = c_uint16(214) # 0xd6

# Hardware (PCAN-Chip USB): Sets multiple digital I/O pins to high level (can_param_io_t)
# Bit mask: 0 = no effect on pin, 1 = set to high level (write-only)
CAN_PARAM_IO_DIGITAL_SET = c_uint16(215) # 0xd7

# Hardware (PCAN-Chip USB): Clears multiple digital I/O pins to low level (can_param_io_t)
# Bit mask: 0 = no effect on pin, 1 = set to low level (write-only)
CAN_PARAM_IO_DIGITAL_CLEAR = c_uint16(216) # 0xd8

# Hardware (PCAN-Chip USB): Value of a single analog input pin (read-only) (can_param_io_t)
CAN_PARAM_IO_ANALOG_VALUE = c_uint16(217) # 0xd9

# Client: Win32 event for message reception notification (can_param_event_t)
# Replaces CAN_PARAM_ONRCV_EVENT_HANDLE and CAN_PARAM_ONRCV_EVENT_PULSE
CAN_PARAM_EVENT_ONRCV = c_uint16(218) # 0xda

# Client: Win32 event signaled on Client DELAY XMT BUFFER EMPTY (can_param_event_t)
CAN_PARAM_EVENT_ONDELAYXMTEMPTY = c_uint16(219) # 0xdb


# Other constants

MAX_HCANHW      = int(64)  # only hardware 1 .. MAX_HCANHW permitted
MAX_HCANNET     = int(64)  # only nets 1 .. MAX_HCANNET permitted
MIN_HCANNET_FD  = int(33)  # CAN FD nets permitted from handle 33 .. MAX_HCANNET
MAX_HCANCLIENT  = int(64)  # only clients 1 .. MAX_HCANCLIENT permitted

CAN_PARAM_OBJCLASS_DRIVER     = int(0x1)    # = 1. field objclass: driver parameter
CAN_PARAM_OBJCLASS_HARDWARE   = int(0x2)    # = 2. field objclass: hardware parameter
CAN_PARAM_OBJCLASS_NET        = int(0x3)    # = 3. field objclass: net parameter
CAN_PARAM_OBJCLASS_CLIENT     = int(0x4)    # = 4. field objclass: client parameter
CAN_PARAM_OBJCLASS_API        = int(0x5)    # = 5. field objclass: API parameter

CAN_PARAM_MAX_HARDWARENAMELEN = int(33)     # length of a hardware name: 32 characters + terminator
CAN_PARAM_MAX_NETNAMELEN      = int(21)     # length of a net name: 20 characters + terminator
CAN_PARAM_MAX_CLIENTNAMELEN   = int(21)     # length of a client name: 20 characters + terminator
CAN_PARAM_CONST_MAX_STRINGLEN = int(256)    # size of info fields: 255 bytes + terminator

CAN_CONST_CAN_DATA_COUNT      = int(8)      # number of data bytes in a CAN message frame
CAN_CONST_CANFD_DATA_COUNT    = int(64)     # deprecated, use CAN_CONST_FD_DATA_COUNT
CAN_CONST_FD_DATA_COUNT       = int(64)     # number of data bytes in a CAN FD message frame
CAN_CONST_MAX_INFOLEN         = int(256)    # length of an info string: 255 characters + terminator

# Protocol types for CAN_PARAM_PROTOCOLS
CAN_CONST_PROTOCOL_CAN20A     = int(0x1)    # = 1. CAN 2.0A, 11-bit ID
CAN_CONST_PROTOCOL_CAN20B     = int(0x2)    # = 2. CAN 2.0B, 29-bit ID
CAN_CONST_PROTOCOL_CAN20AB    = int(CAN_CONST_PROTOCOL_CAN20A | CAN_CONST_PROTOCOL_CAN20B)
                                            # = 3. CAN 2.0, 11- & 29-bit ID (mask for CAN 2.0 capabilities)
CAN_CONST_PROTOCOL_FD_BOSCH   = int(0x4)    # = 4. CAN FD, first Bosch definition
CAN_CONST_PROTOCOL_FD_ISO     = int(0x8)    # = 8. CAN FD, later ISO definition
CAN_CONST_PROTOCOL_FD_ANY     = int(CAN_CONST_PROTOCOL_FD_BOSCH | CAN_CONST_PROTOCOL_FD_ISO)
                                            # = 12. CAN FD, either ISO or Bosch (mask for CAN FD capabilites)

# Record types

CAN_INVALID_RECORDTYPE                  = c_uint16(0x0)      # Guaranteed not to be a valid record type
CAN_RECORDTYPE_basedata                 = c_uint16(0x1000)   # Abstract base class.
                                                             # Identical header for all data records ("msg..." and "event_..."),
                                                             # so all records can be cast to this
CAN_RECORDTYPE_basemsg                  = c_uint16(0x1001)   # Abstract base class.
                                                             # Identical header for records "msg", "msg_rtr", "msg_fd"
                                                             # so all message records can be cast to this
CAN_RECORDTYPE_msg                      = c_uint16(0x1002)   # CAN message 11/29-bit ID; non-FD, 8 data bytes
CAN_RECORDTYPE_msg_rtr                  = c_uint16(0x1003)   # CAN RTR message 11/29-bit ID
CAN_RECORDTYPE_msg_fd                   = c_uint16(0x1004)   # Represents a CAN bus message with FDF bit set.
                                                             # ID = 11/29-bit ID; max. 64 data bytes
                                                             # identical with standard CAN message up to the ID field
CAN_RECORDTYPE_interframespace_pause    = c_uint16(0x1006)   # Forces an interframe space when sent. Hardware inhibits sending for x microseconds.
                                                             # Flows through driver like a message, but not supported by all hardware.
CAN_RECORDTYPE_hwstatus                 = c_uint16(0x1101)   # Message related errors (as OVERRUN, BUSWARNING, BUSPASSIVE, BUSOFF).
                                                             # Also used as error feedback for CAN_Write()
CAN_RECORDTYPE_errorframe               = c_uint16(0x1102)   # Error frame from CAN core, mapped to SJA1000 ECC error code capture
CAN_RECORDTYPE_errorcounter_decrement   = c_uint16(0x1103)   # Some error counter decremented
CAN_RECORDTYPE_busload                  = c_uint16(0x1104)   # CAN bus load in percent
CAN_RECORDTYPE_event_pnp                = c_uint16(0x1301)   # Plug&Play event from driver (hardware connect/disconnect detected)
CAN_RECORDTYPE_event_fd_error           = c_uint16(0x1302)   # Incompatibility between FD net and non-FD hardware
CAN_RECORDTYPE_event_param              = c_uint16(0x1303)   # A hardware or net parameter was changed, all clients get notified

# Types of parameter records

CAN_RECORDTYPE_param_base               = c_uint16(0xFFF)    # Common to all parameter set/get records
CAN_RECORDTYPE_param_uint32             = c_uint16(0xFFD)    # 32-bit unsigned integer
CAN_RECORDTYPE_param_uint64             = c_uint16(0xFFB)    # 64-bit unsigned integer
CAN_RECORDTYPE_param_string255          = c_uint16(0xFF9)    # string with 255 byte characters + terminating null character
# Record types for parameters that set/return structured data
CAN_RECORDTYPE_param_version            = c_uint16(0xFF8)    # Generic record to hold all version informations
CAN_RECORDTYPE_param_bitrate_btr0btr1   = c_uint16(0x7)      # See also CAN_PARAM_BITRATE
CAN_RECORDTYPE_param_bitrate_nom        = c_uint16(0xCD)     # See also CAN_PARAM_BITRATE_NOM
CAN_RECORDTYPE_param_bitrate_fd         = c_uint16(0xCE)     # See also CAN_PARAM_BITRATE_FD
CAN_RECORDTYPE_param_acceptance_filter  = c_uint16(0xCF)     # See also CAN_PARAM_ACCEPTANCE_FILTER
CAN_RECORDTYPE_param_buserrorgeneration = c_uint16(0x6E)     # See also CAN_PARAM_BUSERRORGENERATION
CAN_RECORDTYPE_param_traffic            = c_uint16(0xD0)     # See also CAN_PARAM_TRAFFIC
CAN_RECORDTYPE_param_irq_timing         = c_uint16(0xD3)     # See also CAN_PARAM_IRQ_TIMING
CAN_RECORDTYPE_param_io                 = c_uint16(0xFF7)    # Generic access to digital and analog I/O pins
CAN_RECORDTYPE_param_io_digital_config  = c_uint16(0xD5)     # See also CAN_PARAM_IO_DIGITAL_CONFIG
CAN_RECORDTYPE_param_io_digital_value   = c_uint16(0xD6)     # See also CAN_PARAM_IO_DIGITAL_VALUE
CAN_RECORDTYPE_param_io_digital_set     = c_uint16(0xD7)     # See also CAN_PARAM_IO_DIGITAL_SET
CAN_RECORDTYPE_param_io_digital_clear   = c_uint16(0xD8)     # See also CAN_PARAM_IO_DIGITAL_CLEAR
CAN_RECORDTYPE_param_io_analog_value    = c_uint16(0xD9)     # See also CAN_PARAM_IO_ANALOG_VALUE
CAN_RECORDTYPE_param_event              = c_uint16(0xFF6)    # Generic register/unregister Win32 event 
CAN_RECORDTYPE_param_event_onrcv        = c_uint16(0xDA)     # See also CAN_PARAM_EVENT_ONRCV
CAN_RECORDTYPE_param_event_ondelayxmtempty = c_uint16(0xDB)  # See also CAN_PARAM_EVENT_ONDELAYXMTEMPTY


# Message types

CAN_MSGTYPE_STANDARD       = int(0x0000)    # standard data frame (CAN 2.0A, 11-bit ID)
CAN_MSGTYPE_EXTENDED       = int(0x0001)    # 1, if extended data frame (CAN 2.0B, 29-bit ID)
CAN_MSGTYPE_SELFRECEIVE    = int(0x0002)    # 1, if message shall be/has been self-received by the client
CAN_MSGTYPE_HW_SELFRECEIVE = int(0x0004)    # 1, if self-receive was performed by hardware. 0, if hardware is incapable of self-receive
CAN_MSGTYPE_SINGLESHOT     = int(0x0008)    # 1, if no re-transmission shall be performed for the message (self-ACK)
CAN_MSGTYPE_BRS            = int(0x0010)    # Bit Rate Switch: 1, if CAN FD frame data was sent with higher bit rate
CAN_MSGTYPE_ESI            = int(0x0020)    # Error State Indicator: 1, if CAN FD transmitter was error active


# PCAN device types

pcan_unknown    = c_int(0x0)
pcan_isa        = c_int(0x1)
pcan_pci        = c_int(0x2) 
pcan_usb        = c_int(0x3)
pcan_pccard     = c_int(0x4)
pcan_virtual    = c_int(0x5) 
pcan_lan        = c_int(0x6)
pcan_dng        = c_int(0x7)
dci_can         = c_int(0x8)


##############################
# Structure definitions
##############################

# Represents the data bytes of a CAN message
#
class can_data_union(Union):
    """
    Represents the data bytes of a CAN message
    """
    _pack_ = 1
    _fields_ = [ ("data",       c_uint8  * CAN_CONST_CAN_DATA_COUNT),
                 ("data_x2",    c_uint16 * 4),
                 ("data_x4",    c_uint32 * 2),
                 ("data_x8",    c_uint64 * 1)]


# Represents the data bytes of a CAN FD message 
#
class can_data_fd_union(Union):
    """
    Represents the data bytes of a CAN FD message 
    """
    _pack_   = 1       
    _fields_ = [ ("data",       c_uint8 * CAN_CONST_FD_DATA_COUNT), 
                 ("data_x2",    c_uint16 * 32), 
                 ("data_x4",    c_uint32 * 16), 
                 ("data_x8",    c_uint64 * 8) ]


# Common record header
#
class can_recordheader_t(Structure):
    """
    Common record header
    """
    _pack_   = 1       
    _fields_ = [ ("size",       c_uint16),       # #0 +0x00  absolute length of record in bytes
                 ("type",       c_uint16) ]      # #1 +0x02  type code of the record (only LSBs with mask 0x3fff)


# Record "basedata"
#      type = CAN_RECORDTYPE_basedata = 0x1000
# hierarchy = Is a base record for these other records:
#                 "basemsg", "hwstatus", "errorframe", "errorcounter_decrement", "busload",
#                 "event_pnp", "event_fd_error", "event_param".
#      size = 22 = 0x16 bytes, aligned to 1 bytes
#      info = Abstract base class
#             Identical header for all data records ("msg..." and "event_..."),
#             so all records can be cast to this
#
class can_basedata_t(can_recordheader_t):
    """
    Record "basedata"
    """
    _pack_   = 1       
    _fields_ = [ ("timestamp",   c_uint64),      # #2 +0x04  record timestamp in microseconds system time, 64-bit
                 ("tag",         c_uint64),      # #3 +0x0C  space for application-specific data(object pointer)
                 ("client",      HCANCLIENT),    # #4 +0x14  PCAN client handle (sender, if message is received)
                 ("net",         HCANNET) ]      # #5 +0x15  PCAN net handle


# Record "basemsg"
#      type = CAN_RECORDTYPE_basemsg = 0x1001
# hierarchy = Inherits fields from base record "basedata".
#             Is a base record for these other records: 
#                 "msg", "msg_rtr", "msg_fd".
#      size = 29 = 0x1d bytes, aligned to 1 bytes
#      info = Abstract base class.
#             Identical header for records "msg", "msg_rtr", "msg_fd"
#             so all message records can be cast to this
#
class can_basemsg_t(can_basedata_t):
    """
    Record "basemsg"
    """
    _pack_   = 1       
    _fields_ = [ ("msgtype",     c_uint16),      # #6 +0x16  message flags. See CAN_MSGTYPE_... constants
                 ("id",          c_uint32),      # #7 +0x18  11/29-bit CAN identifier
                 ("dlc",         c_uint8) ]      # #8 +0x1C  physical Data Length Code, encodes count of bytes


# Record "msg"   
#      type = CAN_RECORDTYPE_msg = 0x1002
# hierarchy = Inherits fields from base record "basemsg".
#      size = 37 = 0x25 bytes, aligned to 1 bytes
#      info = CAN message 11/29-bit ID; non-FD, 8 data bytes
#
class can_msg_t(can_basemsg_t):
    """
    Record "msg"
    """
    _pack_   = 1       
    _fields_ = [ ("data",        can_data_union) ]       # #9 +0x1D  data bytes (8)
    

# Record "msg_rtr"
#      type = CAN_RECORDTYPE_msg_rtr = 0x1003
# hierarchy = Inherits fields from base record "basemsg".
#      size = 29 = 0x1d bytes, aligned to 1 bytes
#      info = CAN RTR frame 11/29-bit ID
#
class can_msg_rtr_t(can_basemsg_t):
    """
    Record "msg_rtr"
    """
    _pack_   = 1


# Record "msg_fd"
#      type = CAN_RECORDTYPE_msg_fd = 0x1004
# hierarchy = Inherits fields from base record "basemsg".
#      size = 93 = 0x5d bytes, aligned to 1 bytes
#      info = Represents a CAN bus message with FDF bit set.
#             ID = 11/29-bit; max. 64 data bytes
#
class can_msg_fd_t(can_basemsg_t):
    """
    Record "msg_fd"
    """
    _pack_   = 1       
    _fields_ = [ ("data",        can_data_fd_union) ]    # #9 +0x1D  data bytes (64)


# Record "interframespace_pause"
#      type = CAN_RECORDTYPE_interframespace_pause = 0x1006
# hierarchy = Inherits fields from base record "basedata".
#      size = 26 = 0x1a bytes, aligned to 1 bytes
#      info = Forces an interframe space when sent. Hardware inhibits sending for x microseconds.
#             Flows through driver like a message, but not supported by all hardware.
#
class can_interframespace_pause_t(can_basedata_t):
    """
    Record "interframespace_pause"
    """
    _pack_   = 1       
    _fields_ = [ ("delay",       c_uint32) ]    # #6 +0x16  delay in microseconds. Current maximum is 1023.


# Record "hwstatus"
#      type = CAN_RECORDTYPE_hwstatus = 0x1101
# hierarchy = Inherits fields from base record "basedata".
#      size = 26 = 0x1a bytes, aligned to 1 bytes
#      info = Message related errors (as OVERRUN, BUSWARNING, BUSPASSIVE, BUSOFF)
#             Also used as error feedback for CAN_Write()
#
class can_hwstatus_t(can_basedata_t):
    """
    Record "hwstatus"
    """
    _pack_   = 1       
    _fields_ = [ ("status",      c_uint32) ]     # #6 +0x16  CAN status code (can_status_t)


# Record "errorframe"
#      type = CAN_RECORDTYPE_errorframe = 0x1102
# hierarchy = Inherits fields from base record "basedata".
#      size = 28 = 0x1c bytes, aligned to 1 bytes
#      info = Error frame from the CAN core, mapped to SJA1000 ECC error code capture 
#
class can_errorframe_t(can_basedata_t):
    """
    Record "errorframe"
    """
    _pack_   = 1       
    _fields_ = [ ("errortype",   c_uint8),       # #6 +0x16  0x01 = bit error, 0x02 = form error, 0x04 = stuff error, 0x08 = other
                 ("direction",   c_uint8),       # #7 +0x17  1, if error occurred on RCV, 0 for XMT
                 ("ecc",         c_uint8),       # #8 +0x18  Error Code Capture, error position in bit stream. Defined as 'SAJ1000.ECC & 0x1f'
                 ("rxErrCount",  c_uint8),       # #9 +0x19  Receive error counter value, caused by standard messages
                 ("txErrCount",  c_uint8),       # #10 +0x1A Transmit error counter value, caused by standard messages
                 ("errorsource", c_uint8) ]      # #11 +0x1B 0 = CAN bus, 1 = error generator


# Record "errorcounter_decrement"
#      type = CAN_RECORDTYPE_errorcounter_decrement = 0x1103
# hierarchy = Inherits fields from base record "basedata".
#      size = 24 = 0x18 bytes, aligned to 1 bytes
#      info = Some error counter was decremented
#
class can_errorcounter_decrement_t(can_basedata_t):
    """
    Record "errorcounter_decrement"
    """
    _pack_   = 1       
    _fields_ = [ ("rxErrCount",  c_uint8),       # #6 +0x16  Receive error counter value, caused by standard messages
                 ("txErrCount",  c_uint8) ]      # #7 +0x17  Transmit error counter value, caused by standard messages


# Record "busload"
#      type = CAN_RECORDTYPE_busload = 0x1104
# hierarchy = Inherits fields from base record "basedata".
#      size = 24 = 0x18 bytes, aligned to 1 bytes
#      info = CAN bus load in percent
#
class can_busload_t(can_basedata_t):
    """
    Record "busload"
    """    
    _pack_   = 1       
    _fields_ = [ ("busload",     c_uint16) ]     # #6 +0x16  bus load in percent


# Class definiton for the additional info text in event records
#
class info_text(Array):    
    
    _pack_   = 1       
    _type_ = c_char
    _length_ = CAN_CONST_MAX_INFOLEN + 1


# Record "event_pnp"
#      type = CAN_RECORDTYPE_event_pnp = 0x1301
# hierarchy = Inherits fields from base record "basedata".
#      size = 285 = 0x11d bytes, aligned to 1 bytes
#      info = Plug&Play event from driver
#             Hardware connect/disconnect detected
#
class can_event_pnp_t(can_basedata_t):
    """
    Record "event_pnp"
    """
    _pack_   = 1       
    _fields_ = [ ("hw",          HCANHW),        # #6 +0x16  handle of hardware
                 ("plug_type",   c_uint32),      # #7 +0x17  0 = plug-out, 1 = plug-in
                 ("hw-net",      HCANNET),       # #8 +0x1b  hardware is connected to this net
                 ("info",        info_text) ]    # #9 +0x1c  additional info text


# Record "event_fd_error" ***
#      type = CAN_RECORDTYPE_event_fd_error = 0x1302
# hierarchy = Inherits fields from base record "basedata".
#      size = 281 = 0x119 bytes, aligned to 1 bytes
#      info = Incompatibility between FD net and non-FD hardware
#
class can_event_fd_error_t(can_basedata_t):
    """
    Record "event_fd_error"
    """
    _pack_   = 1       
    _fields_ = [ ("hw",          HCANHW),        # #6 +0x16  handle of hardware
                 ("hw-net",      HCANNET),       # #7 +0x17  hardware was supposed to connect to this net
                 ("info",        info_text) ]    # #8 +0x18  additional info text


# Record "event_param" ***
#      type = CAN_RECORDTYPE_event_param = 0x1303
# hierarchy = Inherits fields from base record "basedata".
#      size = 291 = 0x123 bytes, aligned to 1 bytes
#      info = A hardware or net parameter was changed, all clients get notified.
#             (field 'net' not used)
#
class can_event_param_t(can_basedata_t):
    """
    Record "event_param"
    """
    _pack_   = 1       
    _fields_ = [ ("objclass",    c_uint32),      # #6 +0x16  class of the object that changed a parameter (see CAN_PARAM_OBJCLASS_... constants)
                 ("objhandle",   c_uint32),      # #7 +0x1A  handle of the object that changed a parameter (0 for driver)
                 ("parameter",   c_uint32),      # #8 +0x1E  code/recordtype of changed parameter
                                                 #           parameter belongs to class <objclass> and handle <objhandle>
                 ("info",        info_text) ]    # #9 +0x22  additional info text


# can_any_record: Union for all types of records
#
class can_any_record(Union):
    """
    Union for all types of records
    """
    _pack_   = 1       
    _fields_ = [ ("header",      can_recordheader_t),  # identical for all records
                 ("basedata",    can_basedata_t),
                 ("basemsg",     can_basemsg_t),
                 ("msg",         can_msg_t),
                 ("msg_rtr",     can_msg_rtr_t),
                 ("msg_fd",      can_msg_fd_t),
                 ("interframespace_pause", can_interframespace_pause_t),
                 ("hwstatus",    can_hwstatus_t),
                 ("errorframe",  can_errorframe_t),
                 ("errorcounter_decrement", can_errorcounter_decrement_t),
                 ("busload",     can_busload_t),
                 ("event_pnp",   can_event_pnp_t),
                 ("event_fd_error", can_event_fd_error_t),
                 ("event_param", can_event_param_t) ]


# Other records

# Record "available_hardware"
# hierarchy = Not inherited from any other record.
#      size = 50 = 0x32 bytes, aligned to 1 bytes
#      info = Data of available hardware. Returned from CAN_GetAvailableHardware.
#
class can_available_hardware_t(Structure):
    """
    Record "available_hardware"
    """
    _pack_   = 1       
    _fields_ = [ ("device",      c_int32),       # #0 +0x00  device
                 ("hw",          HCANHW),        # #1 +0x04  hardware handle
                 ("name",        c_char * CAN_PARAM_MAX_HARDWARENAMELEN),
                                                 # #2 +0x05  hardware name
                 ("type",        c_uint32),      # #3 +0x26  hardware type, see also CAN_PARAM_HWDRIVERNR
                 ("channel",     c_uint32),      # #4 +0x2A  channel number (1-based index)
                 ("reserved",    c_uint32) ]     # #5 +0x2E  reserved for future use


# Parameters

# Record "param_base"
#      type = CAN_RECORDTYPE_param_base = 0xfff
# hierarchy = Is the base record for all other can_param_... records
#      size = 12 = 0xc bytes, aligned to 1 bytes
#      info = Common to all parameter set/get records
#
class can_param_base_t(can_recordheader_t):
    """
    Record "param_base"
    """
    _pack_   = 1       
    _fields_ = [ ("objclass",    c_uint32),      # #2 +0x04  class of the object this parameter belongs to (see CAN_PARAM_OBJCLASS_... constants)
                 ("objhandle",   c_uint32) ]     # #3 +0x08  handle of the object this parameter belongs to (0 for driver)


# Record "param_uint32"
#      type = CAN_RECORDTYPE_param_uint32 = 0xffd
# hierarchy = Inherits fields from base record "param_base".
#      size = 16 = 0x10 bytes, aligned to 1 bytes
#
class can_param_uint32_t(can_param_base_t):
    """
    Record "param_uint32"
    """
    _pack_   = 1       
    _fields_ = [ ("value",       c_uint32) ]     # #4 +0x0C  an unsigned 32-bit numeric value


# Record "param_uint64"
#      type = CAN_RECORDTYPE_param_uint64 = 0xffb
# hierarchy = Inherits fields from base record "param_base".
#      size = 20 = 0x14 bytes, aligned to 1 bytes
#
class can_param_uint64_t(can_param_base_t):
    """
    Record "param_uint64"
    """
    _pack_   = 1       
    _fields_ = [ ("value",       c_uint64) ]     # #4 +0x0C  an unsigned 64-bit numeric value


# Record "param_string255"
#      type = CAN_RECORDTYPE_param_string255 = 0xff9
# hierarchy = Inherits fields from base record "param_base".
#      size = 268 = 0x10c bytes, aligned to 1 bytes
#
class can_param_string255_t(can_param_base_t):
    """
    Record "param_string255"
    """
    _pack_   = 1       
    _fields_ = [ ("value",       c_char * CAN_PARAM_CONST_MAX_STRINGLEN) ]
                                                 # #4 +0x0C  (string data type logic) a 255 char string, used for info fields


# Record "param_version"
#      type = CAN_RECORDTYPE_param_version = 0xff8
# hierarchy = Inherits fields from base record "param_base".
#      size = 32 = 0x20 bytes, aligned to 1 bytes
#      info = Generic record to hold all version informations
#             Version info is hold as <major>.<minor>.<revision>-<build> <debug/release>
#             Was CAN_PARAM_VERSION_*, CAN_PARAM_HARDWARE_*, CAN_PARAM_CPLD_*,
#             CAN_PARAM_FIRMWARE_*, CAN_PARAM_BOOTLOADER_*
#
class can_param_version_t(can_param_base_t):
    """
    Record "param_version"
    """
    _pack_   = 1       
    _fields_ = [ ("major",       c_uint32),      # #4 +0x0C  significant changes, new product; change means compatibility issue
                 ("minor",       c_uint32),      # #5 +0x10  functional changes; change means downward compatibility
                 ("revision",    c_uint32),      # #6 +0x14  patch level, bug fixes; change should not raise a compatibility issue
                 ("build",       c_uint32),      # #7 +0x18  sequential compile count, unique ID for each binary
                 ("debug",       c_uint32) ]     # #8 +0x1C  0=release, 1=debug build


# Record "param_bitrate_btr0btr1"
#      type = CAN_RECORDTYPE_param_bitrate_btr0btr1 = 0x7
# hierarchy = Inherits fields from base record "param_uint32".
#      size = 16 = 0x10 bytes, aligned to 1 bytes
#      info = CAN_PARAM_BITRATE
#             Defines bit rates in terms SJA1000 timing register BTR0BTR1 values
#
class can_param_bitrate_btr0btr1_t(can_param_base_t):
    """
    Record "param_bitrate_btr0btr1"
    """
    _pack_   = 1       
    _fields_ = [ ("value",       c_uint32) ]     # #4 +0x0C  an unsigned numeric value


# Record "param_bitrate_nom"
#      type = CAN_RECORDTYPE_param_bitrate_nom = 0xcd
# hierarchy = Inherits fields from base record "param_base".
#      size = 33 = 0x21 bytes, aligned to 1 bytes
#      info = Defines CAN non-FD bit rates in terms of CiA specifications
#             Same as driver-internal representation
#
class can_param_bitrate_nom_t(can_param_base_t):
    """
    Record "param_bitrate_nom"
    """
    _pack_   = 1         
    _fields_ = [ ("f_core",      c_uint32),      # #4 +0x0C  clock of CAN state machine. time_quantum = brp / f_core
                 ("brp",         c_uint32),      # #5 +0x10  clock prescaler for nominal time quantum
                 ("tseg1",       c_uint32),      # #6 +0x14  tseg1 segment for nominal bit rate in time quanta. tseg1 = prop_seg + phase1_seg
                 ("tseg2",       c_uint32),      # #7 +0x18  tseg2 segment for nominal bit rate in time quanta
                 ("sjw",         c_uint32),      # #8 +0x1C  Synchronization Jump Width for nominal bit rate in time quanta
                 ("sam",         c_uint8) ]      # #9 +0x20  1 = SJA1000 could set 3x sampling, 0 = 1x sampling. Not used in FPGA-based hardware


# Record "param_bitrate_fd"
#      type = CAN_RECORDTYPE_param_bitrate_fd = 0xce
# hierarchy = Inherits fields from base record "param_base".
#      size = 53 = 0x35 bytes, aligned to 1 bytes
#      info = Defines CAN FD bit rates in terms of CiA specifications
#             Same as driver-internal representation
#
class can_param_bitrate_fd_t(can_param_base_t):
    """
    Record "param_bitrate_fd"
    """
    _pack_   = 1       
    _fields_ = [ ("f_core",      c_uint32),      # #4  +0x0C  clock of CAN state machine. time_quantum = brp / f_core
                 ("nom_brp",     c_uint32),      # #5  +0x10  clock prescaler for nominal time quantum
                 ("nom_tseg1",   c_uint32),      # #6  +0x14  tseg1 segment for nominal bit rate in time quanta. tseg1 = prop_seg + phase1_seg
                 ("nom_tseg2",   c_uint32),      # #7  +0x18  tseg2 segment for nominal bit rate in time quanta
                 ("nom_sjw",     c_uint32),      # #8  +0x1C  Synchronization Jump Width for nominal bit rate in time quanta
                 ("nom_sam",     c_uint8),       # #9  +0x20  1 = SJA1000 could set 3x sampling, 0 = 1x sampling. Not used in FPGA-based hardware
                 ("data_brp",    c_uint32),      # #10 +0x21  clock prescaler for high-speed data bit rate time quantum. time_quantum = brp / f_core
                 ("data_tseg1",  c_uint32),      # #11 +0x25  tseg1 segment for fast data bit rate bit rate in time quanta. tseg1 = prop_seg + phase1_seg
                 ("data_tseg2",  c_uint32),      # #12 +0x29  tseg2 segment for fast data bit rate bit rate in time quanta
                 ("data_sjw",    c_uint32),      # #13 +0x2D  Synchronization Jump Width for nominal bit rate in time quanta
                 ("data_sam",    c_uint32) ]     # #14 +0x31  secondary sample point delay for high-speed data bit rate in f_cancore cycles. Not used in FPGA-based hardware


# Record "param_acceptance_filter"
#      type = CAN_RECORDTYPE_param_acceptance_filter = 0xcf
# hierarchy = Inherits fields from base record "param_base".
#      size = 22 = 0x16 bytes, aligned to 1 bytes
#      info = Defines a single acceptance filter.
#             Filter works on message ID, with binary code and mask patterns.
#
class can_param_acceptance_filter_t(can_param_base_t):
    """
    Record "param_acceptance_filter"
    """
    _pack_   = 1       
    _fields_ = [ ("index",       c_uint8),       # #4 +0x0C  number of filter, 0 .. CAN_PARAM_ACCFILTER_COUNT-1
                 ("extended",    c_uint8),       # #5 +0x0D  0 = 11-bit filter, 1 = 29-bit
                 ("code",        c_uint32),      # #6 +0x0E  message ID must match 'code' bit positions where 'mask' = 1
                 ("mask",        c_uint32) ]     # #7 +0x12  message ID must match 'code' bit positions where 'mask' = 1


# Record "param_buserrorgeneration"
#      type = CAN_RECORDTYPE_param_buserrorgeneration = 0x6e
# hierarchy = Inherits fields from base record "param_base".
#      size = 24 = 0x18 bytes, aligned to 1 bytes
#      info = CAN_PARAM_BUSERRORGENERATION
#             Create errors on bus (PCAN-USB Pro and FD-compatible PCAN hardware)
#
class can_param_buserrorgeneration_t(can_param_base_t):
    """
    Record "param_buserrorgeneration"
    """
    _pack_   = 1         
    _fields_ = [ ("mode",          c_uint16),    # #4 +0x0C  0 = off, 1 = repeated, 2 = single
                 ("bit_pos",       c_uint16),    # #5 +0x0E  bit position
                 ("id",            c_uint32),    # #6 +0x10  in repeat mode: CAN ID (11-bit and 29-bit)
                 ("ok_counter",    c_uint16),    # #7 +0x14  in repeat mode: number of successive CAN messages to leave untouched
                 ("error_counter", c_uint16) ]   # #8 +0x16  in repeat mode: number of successive CAN messages to disrupt


# Record "param_traffic"
#      type = CAN_RECORDTYPE_param_traffic = 0xd0
# hierarchy = Inherits fields from base record "param_base".
#      size = 36 = 0x24 bytes, aligned to 1 bytes
#      info = Statistics for received and transmitted messages
#
class can_param_traffic_t(can_param_base_t):
    """
    Record "param_traffic"
    """
    _pack_   = 1       
    _fields_ = [ ("rcvmsgcnt",   c_uint32),      # #4 +0x0C  total number of received messages
                 ("rcvbitcnt",   c_uint32),      # #5 +0x10  total number of received bits
                 ("xmtmsgcnt",   c_uint32),      # #6 +0x14  total number of transmitted messages
                 ("xmtbitcnt",   c_uint32),      # #7 +0x18  total number of transmitted bits
                 ("msgcnt",      c_uint32),      # #8 +0x1C  total number of received and transmitted messages
                 ("bitcnt",      c_uint32) ]     # #9 +0x20  total number of received and transmitted bits


# Record "param_irq_timing"
#      type = CAN_RECORDTYPE_param_irq_timing = 0xd3
# hierarchy = Inherits fields from base record "param_base".
#      size = 20 = 0x14 bytes, aligned to 1 bytes
#      info = IRQ delay and timeout for buffered designs (IRQ throttle).
#             For good throughput, set count_limit and time_limit high:
#             -> buffers are better filled, less IRQs occur and system load is lower.
#             For good response timing, set count_limit and time_limit low:
#             -> more IRQs occur, delay shrinks, buffers get less filled and system load is higher.
#
class can_param_irq_timing_t(can_param_base_t):
    """
    Record "param_irq_timing"
    """
    _pack_   = 1       
    _fields_ = [ ("count_limit", c_uint32),      # #4 +0x0C  trigger IRQ at least every <count_limit> records
                 ("time_limit",  c_uint32) ]     # #5 +0x10  trigger IRQ at least every <time_limit> microseconds


# Record "param_io"
#      type = CAN_RECORDTYPE_param_io = 0xff7
# hierarchy = Inherits fields from base record "param_base".
#      size = 20 = 0x14 bytes, aligned to 1 bytes
#      info = Generic access to digital and analog I/O pins.
#             Used for configuration, set, and get, with parameters 
#             CAN_PARAM_IO_DIGITAL_CONFIG, CAN_PARAM_IO_DIGITAL_VALUE, CAN_PARAM_IO_DIGITAL_SET,
#             CAN_PARAM_IO_DIGITAL_CLEAR, CAN_PARAM_IO_ANALOG_VALUE
#
class can_param_io_t(can_param_base_t):
    """
    Record "param_io"
    """
    _pack_   = 1       
    _fields_ = [ ("index",       c_uint32),      # #4 +0x0C  index of 32-bit bank to modify; must be 0, reserved for future use
                 ("value",       c_uint32) ]     # #5 +0x10  generic field: bit mask for 32 digital pins, or single analog value


# Record "param_event"
#      type = CAN_RECORDTYPE_param_event = 0xff6
# hierarchy = Inherits fields from (and can be casted to) base record "param_base".
#      size = 20 = 0x14 bytes, aligned to 1 bytes
#      info = Generic register/unregister Win32 event
#             Used for configuration, set, and get, with parameters
#             CAN_PARAM_EVENT_ONRCV, CAN_PARAM_EVENT_ONDELAYXMTEMPTY
#
class can_param_event_t(can_param_base_t):
    """
    Record "param_event"
    """
    _pack_   = 1       
    _fields_ = [ ("handle",      c_uint32),      # #4 +0x0C  Event handle created with Win32 CreateEvent()
                                                 #           32-bit despite beeing PVOID. Only 32 LSBs valid on Win64
                                                 #           https://docs.microsoft.com/de-de/windows/win32/winprog64/interprocess-communication?redirectedfrom=MSDN
                 ("pulse",       c_uint32) ]     # #5 +0x10  Triggermode of event (1 = Pulse, 0 = Set)


# can_any_param_t: Union for all types of parameter records
class can_any_param_t(Union):
    """
    Union for all types of parameter records
    """
    _pack_   = 1       
    _fields_ = [ ("header",              can_recordheader_t),  # identical for all records
                 ("base",                can_param_base_t),
                 ("uint32",              can_param_uint32_t),
                 ("uint64",              can_param_uint64_t),
                 ("string255",           can_param_string255_t),
                 ("version",             can_param_version_t),
                 ("bitrate_btr0btr1",    can_param_bitrate_btr0btr1_t),
                 ("bitrate_nom",         can_param_bitrate_nom_t),
                 ("bitrate_fd",          can_param_bitrate_fd_t),
                 ("acceptance_filter",   can_param_acceptance_filter_t),
                 ("buserrorgeneration",  can_param_buserrorgeneration_t),
                 ("traffic",             can_param_traffic_t),
                 ("irq_timing",          can_param_irq_timing_t),
                 ("io",                  can_param_io_t),
                 ("event",               can_param_event_t) ]


# can_any_bitrate_t: Union for all types of bit rate records
class can_any_bitrate_t(Union):
    """
    Union for all types of bit rate records
    """
    _pack_   = 1       
    _fields_ = [ ("header",              can_recordheader_t),  # identical for all records
                 ("base",                can_param_base_t),
                 ("bitrate_btr0btr1",    can_param_bitrate_btr0btr1_t),
                 ("bitrate_nom",         can_param_bitrate_nom_t),
                 ("bitrate_fd",          can_param_bitrate_fd_t) ]


# CAN-API 4 class implementation
#
class CanApi4:
    """
    CanApi4 class implementation
    """

    def __init__ (self):
        # Loads the CanApi4.dll
        #
        self.__m_dllCanApi4 = None
        try:
            self.__m_dllCanApi4 = windll.LoadLibrary("CanApi4")
        except:
            self.__m_dllCanApi4 = None
        if self.__m_dllCanApi4 == None:
            print("Exception: CanApi4.dll could not be loaded!")


    # Indicates whether the DLL has been loaded successfully
    #
    def isLoaded(self):
        """
        Indicates whether the DLL has been loaded successfully

        Returns:
          True if the DLL has been loaded successfully, False otherwise
        """
        return self.__m_dllCanApi4 != None


    def RegisterNet(
        self,
        device,
        net,
        name,
        hw,
        bitrate):
        """
        Adds a net to the driver's net list.

        Parameters:
          device:   PCAN device to be used.
          net:      Requested handle of the PCAN net. If 0, the net handle is
                    determined automatically.
          name:     Name of the PCAN net to be registered.
          hw:       Related CAN hardware handle. If an internal net shall be defined
                    and no hardware shall be connected, this value must be 0.
          bitrate:  Bit rate record.

        Returns:
          Error code. Possible errors: NODRIVER, ILLNET, ILLHW, ILLPARAMVAL.
        """
        try:
            res = self.__m_dllCanApi4.CAN_RegisterNet(device, net, name, hw, byref(bitrate))        
            return can_status_t(res)
        except:
            print("Exception on CanApi4.RegisterNet")
            raise


    def RemoveNet(
        self,
        device,
        net):
        """
        Deletes a net definition from the driver's net list.

        Parameters:
          device: PCAN device to be used.
          net:    Handle of the net to be removed.

        Returns:
          Error code. Possible errors: NODRIVER, ILLNET, NETINUSE.
        """
        try:
            res = self.__m_dllCanApi4.CAN_RemoveNet(device, net)
            return can_status_t(res);

        except:
            print("Exception on CanApi4.RemoveNet")
            raise


    def RegisterClient(
        self,
        device,
        name,
        wnd):
        """        
        Registers a client at the device driver. Creates a client handle and
        allocates the receive queue (only one per client). The wnd parameter
        can be 0 for Console Applications. The client does not receive any
        messages until either RegisterMessages() or SetClientFilter() is called.

        Parameters:
          device: PCAN device to be used.
          name:   Name of the client.
          wnd:    Window handle of the client (only for information purposes).
        
        Returns:
           A tuple with 2 elements:
           [0] Error code. Possible errors: NODRIVER, RESOURCE.
           [1] The handle that was assigned to the client.
        """
        try:
            client = HCANCLIENT()
            res = self.__m_dllCanApi4.CAN_RegisterClient(device, name, wnd, byref(client))
            return can_status_t(res), client.value
        except:            
            print("Exception on CanApi4.RegisterClient")
            raise


    def RemoveClient(
        self,
        device,
        client):
        """
        Removes a client from the client list in the device driver. Free all
        resources (receive/transmit queues etc.)
        Each call of this function can change the filter of the connected
        hardware, so that the CAN controller must be reset.

        Parameters:
          device: PCAN device to be used.
          client: Handle of the client.
        
        Returns:
          Error code. Possible errors: NODRIVER, ILLCLIENT.
        """
        try:
            res = self.__m_dllCanApi4.CAN_RemoveClient(device, client)
            return can_status_t(res)
        except:
            print("Exception on CanApi4.RemoveClient")
            raise


    def ConnectToNet(
        self,
        device,
        client,
        netName):
        """        
        Connects a client to a net.
        The net is assigned by its name. The hardware is initialized with the
        Bit rate if it is the first client which connects to the net.
        If the hardware is already in use by another net, the connection fails and
        the error ERR_HWINUSE will be returned.

        Parameters:
          device:  PCAN device to be used.
          client:  Handle of the client to be connected to the net.
          netName: Name of the net with which the client shall be connected.

        Returns:
          A tuple with 2 elements:
          [0] Error code.
              Possible errors: NODRIVER, ILLCLIENT, ILLNET, ILLHW, ILLPARAMVAL, HWINUSE, REGTEST.
          [1] The handle of the net, with which the client has been connected.
        """
        try:
            net = HCANNET()
            res = self.__m_dllCanApi4.CAN_ConnectToNet(device, client, netName, byref(net))
            return can_status_t(res), net.value
        except:
            print("Exception on CanApi4.ConnectToNet")
            raise


    def DisconnectFromNet(
        self,
        device,
        client,
        net):
        """
        Disconnects a client from a net. This means: no more messages will be
        received by this client. Each call of this function can change the
        filter of the connected hardware, so that the CAN controller must be
        reset.

        Parameters:
          device: PCAN device to be used.
          client: Handle of the client to be disconnected from a net.
          net:    Handle of the net, from which the client shall be disconnected.

        Returns:
          Error code. Possible errors: NODRIVER, ILLCLIENT, ILLNET, REGTEST.
        """
        try:
            res = self.__m_dllCanApi4.CAN_DisconnectFromNet(device, client, net)
            return can_status_t(res)
        except :
            print("Exception on CanApi4.DisconnectFromNet")
            raise


    def ConnectToHardware(
        self,
        device,
        client,
        params):
        """
        Connects a client to a hardware.

        Parameters:
          device: PCAN device to be used.
          client: Handle of the client to be connected to the hardware.
          params: Parameter string.

        Returns:
          A tuple with 2 elements:
          [0] Error code.
              Possible errors: NODRIVER, ILLCLIENT, ILLNET, ILLHW, ILLPARAMVAL, HWINUSE, REGTEST.
          [1] The handle of the net with which the client has been connected.
        """
        try:
            net = HCANNET()
            res = self.__m_dllCanApi4.CAN_ConnectToHardware(device, client, params, byref(net))
            return can_status_t(res), net
        except :
            print("Exception on CanApi4.ConnectToHardware")
            raise


    def GetSystemTime(
        self,
        device):
        """        
        Gets the internal device driver timer value of the Virtual Machine
        Manager.

        Parameters:
          device: PCAN device to be used.

        Returns:
          A tuple with 2 elements:
          [0] Error code. Possible errors: NODRIVER.
          [1] The timestamp in microseconds.
        """
        try:
            time = c_uint64()
            res = self.__m_dllCanApi4.CAN_GetSystemTime(device, byref(time))
            return can_status_t(res), time.value
        except:
            print("Exception on CanApi4.GetSystemTime")
            raise


    def GetHardwareStatus(
        self,
        device,
        hw):
        """
        Gets the current state of a hardware (e.g. ERR_BUSOFF, ERR_OVERRUN, ...)

        Parameters:
          device: PCAN device to be used.
          hw:     Handle of the hardware.

        Returns:
          Error code.
          Possible errors: NODRIVER, ILLHW, BUSWARNING, BUSPASSIVE, BUSOFF, OVERRUN.
        """
        try:
            res = self.__m_dllCanApi4.CAN_GetHardwareStatus(device, hw)
            return can_status_t(res)
        except:
            print("Exception on CanApi4.GetHardwareStatus")
            raise


    def RegisterMessages(
        self,
        device,
        client,
        net,
        IDfrom,
        IDto,
        extended):
        """
        Announces that the client wants to receive messages from the net.
        The acceptance filter of the client will be expanded so that all
        messages in the specified range will be received.
        There is only ONE filter for Standard and Extended messages.
        The Standard messages will be registered as if the ID was built with
        the bits in positions 28..18.
        Example: registration of Standard ID 0x400 means that the Extended ID
        0x10000000 will be also received.
        If the specified CAN-ID range requires a reconfiguration of the CAN
        controller, the CAN controller performs a hardware reset cycle.
        It is not guaranteed that the client only receives the messages with
        the specified CAN-ID range. The actually received messages depend on
        the used CAN controller (usually SJA1000).

        Parameters:
          device:   PCAN device to be used.
          client:   Handle of the client, for which the reception filter shall be
                    expanded.
          net:      Handle of the connected PCAN net, for which the reception filter
                    shall be expanded.
          IDfrom,
          IDto:     These values specify the message ID range that shall pass the
                    acceptance filter.
          extended: Specifies whether the parameters IDfrom and IDto contain
                    11-bit IDs (extended = 0) or 29-bit IDs (extended = 1).

        Returns:
          Error code. Possible errors: NODRIVER, ILLCLIENT, ILLNET, REGTEST.
        """
        try:
            res = self.__m_dllCanApi4.CAN_RegisterMessages(device, client, net, IDfrom, IDto, extended)
            return can_status_t(res)
        except:
            print("Exception on CanApi4.RegisterMessages")
            raise


    def SetClientFilter(
        self,
        device,
        client,
        net,
        filterIndex,
        filterMode,
        extended,
        accCode,
        accMask):
        """
        Sets the filters of a client, of the connected net, and of the
        connected hardware.

        Parameters:
          device:      PCAN device to be used.
          client:      Handle of the client to be configured.
          net:         Handle of the net, with which the client is connected.
          filterIndex: Specifies which filter shall be set. 0 = first filter,
                       1 = second filter (in Dual-Filter-Mode).
          filterMode:  Not used, must be 0.
          extended:    Specifies whether the accCode/accMask parameters contain
                       11-bit values (extended = 0), or 29-bit values (extended = 1).
          accCode,
          accMask:     The acceptance code and mask are part of the acceptance
                       filter of the SJA1000.

        Rrturns:
          Error code. Possible errors: NODRIVER, ILLCLIENT, ILLNET, ILLPARAMVAL.
        """
        try:
            res = self.__m_dllCanApi4.CAN_SetClientFilter(device, client, net, filterIndex, filterMode, extended, accCode, accMask)
            return can_status_t(res)
        except:
            print("Exception on CanApi4.SetClientFilter")
            raise


    def ResetClientFilter(
        self,
        device,
        client):
        """
        Resets the filter of a client.

        Parameters:
          device: PCAN device to be used.
          client: Handle of the client, for which the filter shall be reset.

        Returns:
          Error code. Possible errors: NODRIVER, ILLCLIENT, ILLNET.
        """
        try:
            res = self.__m_dllCanApi4.CAN_ResetClientFilter(device, client)
            return can_status_t(res)
        except:
            print("Exception on CanApi4.ResetClientFilter")
            raise

    def Read(
        self,
        device,
        client,
        bytesToRead):
        """
        Returns a number of CAN_*-records from the client's receive queue.
        Records are CAN messages, error events, and other information.

        Parameters:
          device:      PCAN device to be used.
          client:      Handle of the client whose receive queue shall be read.
          bytesToRead: Number of bytes that shall be read from the receive buffer.

        Returns:
          A tuple with 3 elements:  
          [0] Error code.
              Possible errors: NODRIVER, ILLCLIENT, QRCVEMPTY, ILLPARAMVAL, RESOURCE.
          [1] Number of bytes actually read from the receive queue.
          [2] Buffer with the data read from the receive queue.
        """
        try:
            bytesRead = c_uint()
            ByteArray = c_byte * bytesToRead
            bytesBuffer = ByteArray()
            res = self.__m_dllCanApi4.CAN_Read(device, client, byref(bytesBuffer), sizeof(bytesBuffer), byref(bytesRead))
            return can_status_t(res), bytesRead.value, bytesBuffer[0:bytesRead.value]        
        except:
            print("Exception on CanApi4.Read")
            raise


    def Write(
        self,
        device,
        buffer):
        """
        Writes a number of CAN messages or other commands into the transmit queue
        of a client.

        Parameters:
          device:       PCAN device to be used.
          buffer:       Buffer that contains the messages to write.

        Returns:
          A tuple with 2 elements:  
          [0] Error code.
              Possible errors: NODRIVER, ILLCLIENT, ILLNET, BUSOFF, QXMTFULL, ILLPARAMVAL.
          [1] Number of bytes actually written.
        """
        try:
            bytesWritten = c_uint()
            res = self.__m_dllCanApi4.CAN_Write(device, byref(buffer), sizeof(buffer), byref(bytesWritten))
            return can_status_t(res), bytesWritten.value
        except:
            print("Exception on CanApi4.Write")
            raise


    def ResetClient(
        self,
        device,
        client):
        """
        Resets the receive and transmit queues of a client.

        Parameters:
          device: PCAN device to be used.
          client: Handle of the client whose queues shall be reset.
        
        Returns:
          Error code. Possible errors: NODRIVER, ILLCLIENT.
        """
        try:
            res = self.__m_dllCanApi4.CAN_ResetClient(device, client)
            return can_status_t(res)
        except:
            print("Exception on CanApi4.ResetClient")
            raise


    def ResetHardware(
        self,
        device,
        hw):
        """
        Resets the hardware (CAN controller) and initializes the controller
        with the last valid Bit rate and filter settings.
        If a net is connected to a hardware:
        Resets the CAN controller, flushes the transmit queue.
        Affects the other clients that are connected to the same hardware via
        a PCAN net.

        Parameters:
          device: PCAN device to be used.
          hw:     Handle of the hardware to reset.
        
        Returns: 
          Error code. Possible errors: NODRIVER, ILLHW, REGTEST.
        """
        try:
            res = self.__m_dllCanApi4.CAN_ResetHardware(device, hw)
            return can_status_t(res)
        except:
            print("Exception on CanApi4.ResetHardware")
            raise


    def GetParam(
        self,
        device,
        param):
        """
        Gets a driver/hardware/net/client/API parameter value.

        Parameters:
          device: PCAN device to be used.
          param:  The parameter to get.
        
        Returns:
          A tuple with 2 elements:
          [0] Error code:
              Possible errors: NODRIVER, ILLCLIENT, ILLNET, ILLHW, ILLPARAMTYPE, ILLPARAMVAL.
          [1] Parameter data.
        """
        try:
            res = self.__m_dllCanApi4.CAN_GetParam(device, byref(param))
            return can_status_t(res), param
        except:
            print("Exception on CanApi4.GetParam")
            raise


    def SetParam(
        self,
        device,
        param):
        """
        Sets a driver/hardware/net/client parameter value.

        Parameters:
          device: PCAN device to be used.
          param:  The parameter to be set.
        
        Returns:
          Error code.
          Possible errors: NODRIVER, ILLCLIENT, ILLNET, ILLHW, ILLPARAMTYPE, ILLPARAMVAL, ILLMODE.
        """
        try:
            res = self.__m_dllCanApi4.CAN_SetParam(device, byref(param))
            return can_status_t(res)
        except:
            print("Exception on CanApi4.SetParam")
            raise


    def GetErrText(
        self,
        error):
        """
        Converts a combination of error flags to text.

        Parameters:
          error:    The error flags to be converted.
        
        Returns:
          A tuple with 2 elements:
          [0] Error code. Possible errors: ILLPARAMVAL.
          [1] Resulting error text.
        """
        try:
            textBuff = create_string_buffer(256)
            res = self.__m_dllCanApi4.CAN_GetErrText(error, byref(textBuff), sizeof(textBuff))
            return can_status_t(res), textBuff.value
        except:
            print("Exception on CanApi4.GetErrText")
            raise


    def BitrateToBitsPerSecond(
        self,
        bitrate):

        """
        Calculates true bits-per-second values from a bit rate parameter record.

        Parameters:
          bitrate: Bit rate parameter record.
        
        Returns:
          A tuple with 3 elements:
          [0] Error code.
              CAN_ERR_OK, if the call succeeded. Possible errors: ILLPARAMVAL.
          [1] Nominal bit rate in bits/s.
          [2] Data bit rate in bits/s.
        """
        try:
            
            nominal_bps = c_uint()
            data_bps = c_uint()
            res = self.__m_dllCanApi4.CAN_BitrateToBitsPerSecond(byref(bitrate), byref(nominal_bps), byref(data_bps))
            return can_status_t(res), nominal_bps.value, data_bps.value
        except:
            print("Exception on CanApi4.BitrateToBitsPerSecond")
            raise


    def GetAvailableHardware(
        self,
        deviceFilter):
        """
        Returns information about the CAN hardware channels currently available on the computer.

        Parameters:
          deviceFilter: Filters the device for which hardware is searched. If pcan_unknown is specified, hardware channels
                        of all installed devices are returned.

        Returns:
           A tuple with 2 elements:
           [0] Error code. Possible errors: NODRIVER, ILLPARAMVAL.
           [1] Array of can_available_hardware_t records.
        """
        try:
            hardwareBuff = (can_available_hardware_t * MAX_HCANHW)()
            hardwareCount = c_uint()
            res = self.__m_dllCanApi4.CAN_GetAvailableHardware(deviceFilter, byref(hardwareBuff), MAX_HCANHW, byref(hardwareCount))
            return can_status_t(res), hardwareBuff[0:hardwareCount.value]
        except:
            print("Exception on CanApi4.GetAvailableHardware")
            raise
        
