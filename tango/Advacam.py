############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2025
# European Synchrotron Radiation Facility
# CS40220 38043 Grenoble Cedex 9
# FRANCE
#
# Contact: lima@esrf.fr
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
############################################################################

# =============================================================================
#
# file :        Advacam.py
#
# description : Python source for the Advacam and its commands.
#                The class is derived from Device. It represents the
#                CORBA servant object which will be accessed from the
#                network. All commands which can be executed on the
#                Advacam are implemented in this file.
#
# project :     TANGO Device Server
#
# copyleft :    European Synchrotron Radiation Facility
#               BP 220, Grenoble 38043
#               FRANCE
#
# =============================================================================
#         (c) - BCU - ESRF
# =============================================================================
#
import PyTango
from Lima import Core
from Advacam.Interface import Interface
from Advacam.acquisition import Camera

from Lima.Server import AttrHelper


class Advacam(PyTango.LatestDeviceImpl):
    Core.DEB_CLASS(Core.DebModApplication, "LimaCCDs")

    # ------------------------------------------------------------------
    #    Device constructor
    # ------------------------------------------------------------------
    def __init__(self, *args):
        PyTango.LatestDeviceImpl.__init__(self, *args)

        self.__Attribute2FunctionBase = {
            #    'temperature_sp': 'TemperatureSP',
        }

        self.init_device()

    # ------------------------------------------------------------------
    #    Device destructor
    # ------------------------------------------------------------------
    def delete_device(self):
        _AdvacamCamera.quit()

    # ------------------------------------------------------------------
    #    Device initialization
    # ------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def init_device(self):
        self.set_state(PyTango.DevState.ON)
        self.get_device_properties(self.get_device_class())

        self.__OperationMode = {}
        for mode in _AdvacamCamera.OPERATION_MODES:
            self.__OperationMode[_AdvacamCamera.OPERATION_MODES[mode]] = mode
        print(self.__OperationMode)

        if self.energy_threshold:
            _AdvacamCamera.setEnergyThreshold(self.energy_threshold)

    # ------------------------------------------------------------------
    #    getAttrStringValueList command:
    #
    #    Description: return a list of authorized values if any
    #    argout: DevVarStringArray
    # ------------------------------------------------------------------
    @Core.DEB_MEMBER_FUNCT
    def getAttrStringValueList(self, attr_name):
        # use AttrHelper
        return AttrHelper.get_attr_string_value_list(self, attr_name)

    # ==================================================================
    #
    #    Advacam read/write attribute methods
    #
    # ==================================================================
    def __getattr__(self, name):
        # use AttrHelper
        return AttrHelper.get_attr_4u(self, name, _AdvacamCamera)


# ==================================================================
#
#    AdvacamClass class definition
#
# ==================================================================
class AdvacamClass(PyTango.DeviceClass):
    class_property_list = {}

    device_property_list = {
        # define one and only one of the following 4 properties:
        "config_path": [PyTango.DevString, "Camera config path", []],
        "energy_threshold": [PyTango.DevDouble, "energy_threshold", []],
    }

    cmd_list = {
        "getAttrStringValueList": [
            [PyTango.DevString, "Attribute name"],
            [PyTango.DevVarStringArray, "Authorized String value list"],
        ],
    }

    attr_list = {
        "bias_voltage": [
            [PyTango.DevDouble, PyTango.SCALAR, PyTango.READ_WRITE],
            {
                "unit": "V",
                "format": "%1f",
                "description": "Bias high voltage in Volt",
            },
        ],
        "energy_threshold": [
            [PyTango.DevDouble, PyTango.SCALAR, PyTango.READ_WRITE],
            {
                "unit": "keV",
                "format": "%1f",
                "description": "energy threshold in keV",
            },
        ],
        "operation_mode": [
            [PyTango.DevString, PyTango.SCALAR, PyTango.READ_WRITE],
            {
                "unit": "str",
                "description": "timepix3 operation mode",
            },
        ],
        "sensed_bias_voltage": [
            [PyTango.DevDouble, PyTango.SCALAR, PyTango.READ],
            {
                "unit": "V",
                "format": "%1f",
                "description": "Bias voltage sense",
            },
        ],
        "sensed_bias_current": [
            [PyTango.DevDouble, PyTango.SCALAR, PyTango.READ],
            {
                "unit": "uA",
                "format": "%1f",
                "description": "Bias current sense",
            },
        ],
        "temperature": [
            [PyTango.DevDouble, PyTango.SCALAR, PyTango.READ],
            {
                "unit": "C",
                "format": "%1f",
                "description": "temperature",
            },
        ],
    }

    def __init__(self, name):
        PyTango.DeviceClass.__init__(self, name)
        self.set_type(name)


# ----------------------------------------------------------------------------
# Plugins
# ----------------------------------------------------------------------------
_AdvacamCamera = None
_AdvacamInterface = None


def get_control(config_path=None, **keys):
    global _AdvacamCamera
    global _AdvacamInterface

    if config_path is None:
        print("Advacam will use factory configuration in '/opt/pixet/factory'")
    else:
        print("Advacam config path: ", config_path)

    if _AdvacamInterface is None:
        _AdvacamInterface = Interface(config_path)
        _AdvacamCamera = _AdvacamInterface.camera
    return Core.CtControl(_AdvacamInterface)


def get_tango_specific_class_n_device():
    return AdvacamClass, Advacam
