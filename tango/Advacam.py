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
import tango
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property

from lima import core
from Advacam.Interface import Interface
from Advacam.acquisition import Camera
from lima.server import AttrHelper


def _make_dynamic_enum_fget_fset(attr_name, dict_attr_name):
    """Like AttrHelper.make_fget_fset, but the enum dict isn't a fixed
    class-level constant: operation_mode's valid values depend on which
    chip model is connected (TPX3/MPX3/TPX_MPX), so they're only known
    once the camera is queried, at init_device time.
    """
    camel = AttrHelper._title_case(attr_name)
    get_name, set_name = "get" + camel, "set" + camel

    def fget(self):
        value = getattr(self._AdvacamCamera, get_name)()
        return AttrHelper.getDictKey(getattr(self, dict_attr_name), value)

    def fset(self, value):
        d = getattr(self, dict_attr_name)
        resolved = AttrHelper.getDictValue(d, value.upper())
        if resolved is None:
            tango.Except.throw_exception(
                "WrongData",
                "Wrong value %s: %s" % (attr_name, value.upper()),
                "LimaCCDs Class",
            )
        getattr(self._AdvacamCamera, set_name)(resolved)

    return fget, fset


class Advacam(Device):

    core.DEB_CLASS(core.DebModule.DebModApplication, "LimaCCDs")

    # ------------------------------------------------------------------
    #    Static properties
    # ------------------------------------------------------------------
    _AdvacamCamera = None
    """Reference to Lima advacam camera binding"""
    _AdvacamInterface = None
    """Reference to Lima advacam interface binding"""

    # ------------------------------------------------------------------
    #    Device properties
    # ------------------------------------------------------------------
    config_path = device_property(dtype=str, doc="Camera config path")
    device_id = device_property(
        dtype=str,
        doc="Device identifier (serial) mandatory if several cameras are connected",
    )
    energy_threshold = device_property(dtype=float, doc="Energy threshold in keV")

    # ------------------------------------------------------------------
    #    Device initialization
    # ------------------------------------------------------------------
    @core.DEB_MEMBER_FUNCT
    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.ON)

        self._OperationMode = {}
        for mode in self._AdvacamCamera.OPERATION_MODES:
            self._OperationMode[self._AdvacamCamera.OPERATION_MODES[mode]] = mode
        # Legacy dict used by AttrHelper.get_attr_string_value_list
        self.__OperationMode = self._OperationMode

        if self.energy_threshold:
            self._AdvacamCamera.setEnergyThreshold(self.energy_threshold)

    # ------------------------------------------------------------------
    #    Device destructor
    # ------------------------------------------------------------------
    def delete_device(self):
        self._AdvacamCamera.quit()

    # ------------------------------------------------------------------
    #    Commands
    # ------------------------------------------------------------------
    @command(
        dtype_in=str,
        doc_in="Attribute name",
        dtype_out=(str,),
        doc_out="Authorized String value list",
    )
    @core.DEB_MEMBER_FUNCT
    def getAttrStringValueList(self, attr_name):
        return AttrHelper.get_attr_string_value_list(self, attr_name)

    # ------------------------------------------------------------------
    #    Attributes fully dispatched by naming convention
    # ------------------------------------------------------------------
    _bias_voltage_fget, _bias_voltage_fset = AttrHelper.make_fget_fset(
        "bias_voltage", lambda self: self._AdvacamCamera
    )
    bias_voltage = attribute(
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        unit="V",
        format="%1f",
        doc="Bias high voltage in Volt",
        fget=_bias_voltage_fget,
        fset=_bias_voltage_fset,
    )

    _energy_threshold0_fget, _energy_threshold0_fset = AttrHelper.make_fget_fset(
        "energy_threshold0", lambda self: self._AdvacamCamera
    )
    energy_threshold0 = attribute(
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        unit="keV",
        format="%1f",
        doc="energy threshold 0 in keV",
        fget=_energy_threshold0_fget,
        fset=_energy_threshold0_fset,
    )

    _energy_threshold1_fget, _energy_threshold1_fset = AttrHelper.make_fget_fset(
        "energy_threshold1", lambda self: self._AdvacamCamera
    )
    energy_threshold1 = attribute(
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        unit="keV",
        format="%1f",
        doc="energy threshold 1 in keV",
        fget=_energy_threshold1_fget,
        fset=_energy_threshold1_fset,
    )

    _sensed_bias_voltage_fget, _ = AttrHelper.make_fget_fset(
        "sensed_bias_voltage", lambda self: self._AdvacamCamera
    )
    sensed_bias_voltage = attribute(
        dtype=float,
        access=AttrWriteType.READ,
        unit="V",
        format="%1f",
        doc="Bias voltage sense",
        fget=_sensed_bias_voltage_fget,
    )

    _sensed_bias_current_fget, _ = AttrHelper.make_fget_fset(
        "sensed_bias_current", lambda self: self._AdvacamCamera
    )
    sensed_bias_current = attribute(
        dtype=float,
        access=AttrWriteType.READ,
        unit="uA",
        format="%1f",
        doc="Bias current sense",
        fget=_sensed_bias_current_fget,
    )

    _temperature_fget, _ = AttrHelper.make_fget_fset(
        "temperature", lambda self: self._AdvacamCamera
    )
    temperature = attribute(
        dtype=float,
        access=AttrWriteType.READ,
        unit="C",
        format="%1f",
        doc="temperature",
        fget=_temperature_fget,
    )

    # ------------------------------------------------------------------
    #    Attribute with a per-instance (hardware-dependent) enum dict
    # ------------------------------------------------------------------
    _operation_mode_fget, _operation_mode_fset = _make_dynamic_enum_fget_fset(
        "operation_mode", "_OperationMode"
    )
    operation_mode = attribute(
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        unit="str",
        doc="chip operation mode",
        fget=_operation_mode_fget,
        fset=_operation_mode_fset,
    )


# ----------------------------------------------------------------------------
# Plugins
# ----------------------------------------------------------------------------


def get_control(
    config_path=None, device_id="", _Advacam=Advacam, _Interface=Interface, **keys
):
    camera = _Advacam._AdvacamCamera
    interface = _Advacam._AdvacamInterface

    if config_path is None:
        print("Advacam will use factory configuration in '/opt/pixet/factory'")
    else:
        print(f"Advacam config path: {config_path} (device_id = {device_id})")

    if interface is None:
        interface = _Interface(config_path, device_id)
        camera = interface.camera
        _Advacam._AdvacamCamera = camera
        _Advacam._AdvacamInterface = interface

    return core.CtControl(interface)


def get_tango_specific_class_n_device():
    return Advacam.TangoClassClass, Advacam
