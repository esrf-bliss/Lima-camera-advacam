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

import pypixet
import time, os, glob
import threading
import numpy
import weakref
import enum
import glob
try:
    from Lima import Core
except:
    pass


class acqThread(threading.Thread):
    Core.DEB_CLASS(Core.DebModCamera, "Advacam.Camera.acqThread")

    @Core.DEB_MEMBER_FUNCT
    def __init__(self, advacam):
        threading.Thread.__init__(self)
        self.advacam = advacam

    @Core.DEB_MEMBER_FUNCT
    def run(self):
        deb.Trace("Starting acqThread")
        if self.advacam.buffer_ctrl:
            buffer_mgr = self.advacam.buffer_ctrl.getBuffer()
            buffer_mgr.setStartTimestamp(Core.Timestamp.now())

        rc = self.advacam.detector.doAdvancedAcquisition(
            self.advacam.acq_nb_frames,
            self.advacam.acq_expo_time,
            pypixet.pixet.PX_ACQTYPE_FRAMES,
            self.advacam.trigger_mode,
            pypixet.pixet.PX_FTYPE_AUTODETECT,
            0,
            "",
        )
        deb.Trace(f"acq thread #{rc}: stop the Acq.")

        self.advacam._stopAcq()

        deb.Trace(f"Acq thread #{rc} finished")

#Enum
MODEL_TYPE = enum.Enum('MODEL_TYPE', ['UNKNOWN','MPX3','TPX3'])

class Camera:
    Core.DEB_CLASS(Core.DebModCamera, "Advacam.Camera")
    # Detector states
    ERROR, READY, RUNNING = range(3)

    # Detector settings
    SET_BIAS_VOLTAGE = 200
    ENERGY_THRESHOLD = 3.6

    # More flags
    px = pypixet.pixet

    PX_THLFLG_ENERGY = px.PX_THLFLG_ENERGY

    PX_TPX3_OPM_TOATOT = px.PX_TPX3_OPM_TOATOT
    PX_TPX3_OPM_TOA = px.PX_TPX3_OPM_TOA
    PX_TPX3_OPM_EVENT_ITOT = px.PX_TPX3_OPM_EVENT_ITOT
    PX_TPX3_OPM_TOT_NOTOA = px.PX_TPX3_OPM_TOT_NOTOA

    TPX3_OPERATION_MODES = {
        PX_TPX3_OPM_TOATOT: "ToA+ToT",
        PX_TPX3_OPM_TOA: "ToA",
        PX_TPX3_OPM_EVENT_ITOT: "Event+iToT",
        PX_TPX3_OPM_TOT_NOTOA: "ToT",
    }
    PX_MPX3_OPM_SPM_1CH = px.PX_MPX3_OPM_SPM_1CH
    PX_MPX3_OPM_SPM_2CH = px.PX_MPX3_OPM_SPM_2CH
    PX_MPX3_OPM_CSM = px.PX_MPX3_OPM_CSM

    MPX3_OPERATION_MODES = {
        PX_MPX3_OPM_SPM_1CH: "SPM_1ch",
        PX_MPX3_OPM_SPM_2CH: "SPM_2ch",
        PX_MPX3_OPM_CSM: "CSM",
    }

    PX_MPX3_GAIN_SUPER_NARROW = px.PX_MPX3_GAIN_SUPER_NARROW
    PX_MPX3_GAIN_NARROW = px.PX_MPX3_GAIN_NARROW
    PX_MPX3_GAIN_BROAD = px.PX_MPX3_GAIN_BROAD

    MPX3_GAIN_MODES = {
        PX_MPX3_GAIN_SUPER_NARROW: "Super_Narrow",
        PX_MPX3_GAIN_NARROW: "Narrow",
        PX_MPX3_GAIN_BROAD: "Broad",
    }

    MPX3_COUNTER_DEPTH_MODES = {
        2: 12,
        3: 24,
    }

    INTERNAL_TRIG = px.PX_ACQMODE_NORMAL
    INTERNAL_TRIG_MULTI = px.PX_ACQMODE_TRG_SWSTART

    # frame data types
    (
        DT_CHAR,
        DT_BYTE,
        DT_I16,
        DT_U16,
        DT_I32,
        DT_U32,
        DT_I64,
        DT_U64,
        DT_FLOAT,
        DT_DOUBLE,
        DT_BOOL,
        DT_STRING,
    ) = range(12)


    MODEL_NAME_2_MODEL_TYPE = {'minipix' : MODEL_TYPE.TPX3,
                               'widepix' : MODEL_TYPE.MPX3,
                               'advapix' : MODEL_TYPE.TPX3,
                               }
                      
    @Core.DEB_MEMBER_FUNCT
    def __init__(
        self, config_file=None, buffer_ctrl=None
    ):
        if config_file is None: # take the factory configuration
            xml_file_path = glob.glob('/opt/pixet/factory/*.xml')
            nb_config_file = len(xml_file_path)
            if nb_config_file == 1:
                config_file = xml_file_path[0]
            else:
                raise RuntimeError("You should define a configuration file") 
        pypixet.start()
        # below example code copied from pixetacq_server.py provided by ID20
        # (https://confluence.esrf.fr/pages/viewpage.action?spaceKey=ID20WK&title=MiniPIX)

        alldevices = pypixet.pixet.devices()  # get all devices (including motors, ...)
        self.detector = alldevices[0]  # get first connected detector
        px_type = self.detector.deviceType()
        px_model_str = self.detector.fullName().split()[0].lower()
        px_model = self.MODEL_NAME_2_MODEL_TYPE.get(px_model_str,MODEL_TYPE.UNKNOWN)
        if px_model is MODEL_TYPE.UNKNOWN:
            raise ValueError(
                f"Model name is {px_model_str}; not manage yet"
                f" Only support {list(self.MODEL_NAME_2_MODEL_TYPE.items())}"
            )

        # minipix is a single chip detector
        # widepix family supports 1x5, 2x5, 1x10, 2x10, 1x15, 2x15 chips detectors
        self.model = px_model
        self.nb_chips = self.detector.chipCount()

        self.detector.loadConfigFromFile(config_file)

        if self.model is MODEL_TYPE.TPX3:
            self.detector.setOperationMode(self.PX_TPX3_OPM_EVENT_ITOT)
            self.OPERATION_MODES = self.TPX3_OPERATION_MODES
        elif self.model is MODEL_TYPE.MPX3:
            self.detector.setOperationMode(self.PX_MPX3_OPM_SPM_1CH)
            self.OPERATION_MODES = self.MPX3_OPERATION_MODES

        detector = self.detector
        print("DETECTOR INFO")
        print("  Model:               ", px_model_str)
        print("  Name:                ", detector.fullName())
        print("  Width x Height:      ", detector.width(), "X", detector.height())
        print("  Pixel count:         ", detector.pixelCount())
        print("  Chip count:          ", detector.chipCount())
        print(
            "  Chip IDs:            ", detector.chipIDs()
        )  # list of detector chip IDs
        print("")
        if self.model is MODEL_TYPE.TPX3:
            print("Energy threshlod:       ", self.energy_threshold0, " keV")
        if self.model is MODEL_TYPE.MPX3:
            print(
                "Energy threshlods:      ",
                "THL0 = ",
                self.energy_threshold0,
                " keV ",
                "THL1 = ",
                self.energy_threshold1,
                " keV",
            )
        # gets the threshold of chip 0 in energy
        print(
            "  Set bias voltage:    ", self.bias_voltage, " V"
        )  # return device bias voltage (set value)
        print(
            "  Sensed bias:         ",
            self.sensed_bias_voltage,
            " V /",
            self.sensed_bias_current,
            " uA",
        )
        refsup = True if detector.isSensorRefreshSupported() == 1 else False
        print("  Refresh support:     ", refsup)
        if self.model is MODEL_TYPE.TPX3:
            print(
                "  Mode:                ",
                self.TPX3_OPERATION_MODES[detector.operationMode()],
            )
        else:
            print(
                "  Mode:                ",
                self.MPX3_OPERATION_MODES[detector.operationMode()],
            )

        print("  Temperature:         ", self.temperature, " degC")
        print("")

        self.__prepared = False

        self.__nb_frames = 1
        self.__expo_time = 1.0
        self.__acquired_frames = 0
        self.__status = self.READY
        self.acqthread = None

        self.__trigger_mode = self.INTERNAL_TRIG
        self.__supported_trigger_mode = [self.INTERNAL_TRIG, self.INTERNAL_TRIG_MULTI]

        if self.model is MODEL_TYPE.TPX3:
            self._supported_operation_mode = [
                self.PX_TPX3_OPM_TOATOT,
                self.PX_TPX3_OPM_TOA,
                self.PX_TPX3_OPM_EVENT_ITOT,
                self.PX_TPX3_OPM_TOT_NOTOA,
            ]
        elif self.model is MODEL_TYPE.MPX3:
            self._supported_operation_mode = [
                self.PX_MPX3_OPM_SPM_1CH,
                self.PX_MPX3_OPM_SPM_2CH,
                self.PX_MPX3_OPM_CSM,
            ]

        # Humm, Lima part if Camera is created from Interface object ctor
        if buffer_ctrl:
            self.__buffer_ctrl = weakref.ref(buffer_ctrl)
        else:
            self.__buffer_ctrl = None

    def hard_reset(self):
        pass

    def __del__(self):
        pypixet.exit()

    @Core.DEB_MEMBER_FUNCT
    def quit(self):
        pypixet.exit()

    @Core.DEB_MEMBER_FUNCT
    def callback(self, value):
        deb.Trace("Callback " + str(value))
        frame = self.detector.lastAcqFrameRefInc()

        # data is a python list
        if self.__buffer_mgr:
            frame_dim = self.__buffer_mgr.getFrameDim()
            frame_size = frame_dim.getMemSize()
            frame_id = self.__acquired_frames

            # for the time being only event+itot mode supported and
            # event subframe is #1 with type int16 (signed)
            if self.model is MODEL_TYPE.TPX3:
                r_data = frame.subFrames()[1].data()
                name = frame.subFrames()[0].frameName()
                ftype = frame.subFrames()[0].frameType()
                deb.Trace(f"subframe 0 name {name} and type {ftype}")
                name = frame.subFrames()[1].frameName()
                ftype = frame.subFrames()[1].frameType()
                deb.Trace(f"subFrame 1 name {name} and type {ftype}")
            else:               # MPX3
                r_data = frame.data()
            # reshape data
            data = numpy.array(r_data, dtype=numpy.int16)
            data = data.reshape(self.width, self.height)

            self.__buffer_mgr.copy_data(frame_id, data)

            frame_info = Core.HwFrameInfoType()
            frame_info.acq_frame_nb = frame_id
            frame_info.frame_timestamp = Core.Timestamp.now()

            # raise the new frame !
            self.__buffer_mgr.newFrameReady(frame_info)

        frame.destroy()

        if self.__acquired_frames != value:
            self.__acquired_frames = value

        if self.trigger_mode == self.INTERNAL_TRIG_MULTI:
            self.__status = self.READY

    @Core.DEB_MEMBER_FUNCT
    def prepareAcq(self):
        if not self.__prepared:
            self.detector.registerEvent(
                pypixet.pixet.PX_EVENT_ACQ_FINISHED, self.callback, self.callback
            )
            if self.buffer_ctrl:
                # get the buffer mgr here, to be filled in the callback funct
                self.__buffer_mgr = self.buffer_ctrl.getBuffer()
            else:
                self.__buffer_mgr = None

            self.__prepared = True
            self.__acquired_frames = 0

    @Core.DEB_MEMBER_FUNCT
    def getStatus(self):
        # if self.detector.isReadyForSoftwareTrigger(0):
        return self.__status

    @Core.DEB_MEMBER_FUNCT
    def startAcq(self):
        if self.__acquired_frames == 0:
            self.acqthread = acqThread(self)
            self.acqthread.start()
            time.sleep(0.03)

        self.__status = self.RUNNING

        rc = self.detector.doSoftwareTrigger(0)
        deb.Trace(f"startAcq(): Trigger {self.acquiredFrames+1}")

    @Core.DEB_MEMBER_FUNCT
    def stopAcq(self):
        self._stopAcq(abort=True)

    @Core.DEB_MEMBER_FUNCT
    def _stopAcq(self, abort=False):
        self.detector.unregisterEvent(
            pypixet.pixet.PX_EVENT_ACQ_FINISHED, self.callback, self.callback
        )
        if abort:
            self.detector.abortOperation()
            if self.acqthread:
                self.acqthread.join()
                self.acqthread = None
        self.__prepared = False
        self.__status = self.READY

    @property
    def acq_nb_frames(self):
        return self.__nb_frames

    @acq_nb_frames.setter
    def acq_nb_frames(self, frames):
        self.__nb_frames = frames

    @property
    def acq_expo_time(self):
        return self.__expo_time

    @acq_expo_time.setter
    def acq_expo_time(self, time):
        self.__expo_time = time

    @property
    def acquiredFrames(self):
        return self.__acquired_frames

    @property
    def fullName(self):
        return self.detector.fullName()

    @property
    def width(self):
        return self.detector.width()

    @property
    def height(self):
        return self.detector.height()

    @property
    def bpp(self):
        if self.model is MODEL_TYPE.TPX3:
            # According to the doc "AdvaPIX\ TPX3\ &\ MiniPIX\ TPX3\ -\ User\ Manual.pdf", page 7:
            # ToT & ToA: Tot 14bit, ToA 10bit, Fast ToA 4bit@640MHz
            # Only ToA:  ToA 14bit Only Fast ToA 4bit@640 MHz
            # Event Count & Integral ToT: Integral ToT 14bit, Hit Counter: 10bit
            return 16
        elif self.model is MODEL_TYPE.MPX3:
            return self.MPX3_COUNTER_DEPTH_MODES[self.detector.counterDepth()]

    @property
    def buffer_ctrl(self):
        return self.__buffer_ctrl()

    @property
    def trigger_mode(self):
        return self.__trigger_mode

    @trigger_mode.setter
    def trigger_mode(self, mode):
        if mode not in self.__supported_trigger_mode:
            raise ValueError
        else:
            self.__trigger_mode = mode

    ###############################
    # Detector specific properties
    ###############################
    @property
    def chip_id(self):
        # supposing we only have 1 chip (#0)
        return self.detector.chipIDs()[0]

    @property
    def energy_threshold0(self):
        if self.model is MODEL_TYPE.TPX3:
            return self.detector.threshold(0, self.PX_THLFLG_ENERGY)
        else:                   # MPX3
            return self.detector.threshold(0, 0, self.PX_THLFLG_ENERGY)

    @energy_threshold0.setter
    def energy_threshold0(self, value):
        # do not know the valid range !! suppose up to 120 keV
        if value < 0 or value > 120:
            raise ValueError("Invalid energy threshold, range = [0,120] keV")
        if self.model is MODEL_TYPE.TPX3:
            for ch in range(self.nb_chips):
                self.detector.setThreshold(ch, value, self.PX_THLFLG_ENERGY)
        else:                   # MPX3
            for ch in range(self.nb_chips):
                self.detector.setThreshold(ch, 0, value, self.PX_THLFLG_ENERGY)

    @property
    def energy_threshold1(self):
        if self.model is MODEL_TYPE.TPX3:
            return None
        else:                   # MPX3
            # suppose that all the chips have been set with the same thl
            return self.detector.threshold(0, 1, self.PX_THLFLG_ENERGY)

    @energy_threshold1.setter
    def energy_threshold1(self, value):
        if self.model is MODEL_TYPE.TPX3:
            raise ValueError("Advacam model only supports 1 threshold")

        # do not know the valid range !! suppose up to 120 keV
        if value < 0 or value > 120:
            raise ValueError("Invalid energy threshold, range = [0,120] keV")
        for ch in self.nb_chips:
            self.detector.setThreshold(ch, 1, value, self.PX_THLFLAG_ENERGY)

    @property
    def bias_voltage(self):
        return self.detector.bias()

    @bias_voltage.setter
    def bias_voltage(self, value):
        self.detector.setBias(value)

    @property
    def sensed_bias_voltage(self):
        return self.detector.biasVoltageSense()

    @property
    def sensed_bias_current(self):
        return self.detector.biasCurrentSense()

    @property
    def temperature(self):
        return self.detector.parameters().get("Temperature").getDouble()

    @property
    def operation_mode(self):
        return self.OPERATION_MODES[self.detector.operationMode()]

    @operation_mode.setter
    def operation_mode(self, value):
        if value not in self.OPERATION_MODES.values():
            raise ValueError("Invalid operation mode")
        d = self.OPERATION_MODES
        mode = list(d.keys())[list(d.values()).index(value)]
        self.detector.setOperationMode(mode)

    # for pytango automatic wrapping

    def setEnergyThreshold(self, value):
        self.energy_threshold0 = value

    def getEnergyThreshold(self):
        return self.energy_threshold0

    def setEnergyThreshold0(self, value):
        self.energy_threshold0 = value

    def getEnergyThreshold0(self):
        return self.energy_threshold0

    def setEnergyThreshold1(self, value):
        self.energy_threshold0 = value

    def getEnergyThreshold1(self):
        return self.energy_threshold0

    def setBiasVoltage(self, value):
        self.bias_voltage = value

    def getBiasVoltage(self):
        return self.bias_voltage

    def getSensedBiasVoltage(self):
        return self.sensed_bias_voltage

    def getSensedBiasCurrent(self):
        return self.sensed_bias_current

    def getTemperature(self):
        return self.temperature

    def getOperationMode(self):
        return self.detector.operationMode()

    def setOperationMode(self, value):
        self.operation_mode = value


def main():
    advacam = Camera()

    advacam.acqNbFrames = 10
    advacam.acqExpoTime = 0.4

    advacam.prepareAcq()
    advacam.startAcq()

    nb_frames = 1
    while advacam.getStatus() != "Ready":
        if advacam.acquiredFrames == nb_frames:
            advacam.startAcq()
            nb_frames += 1


if __name__ == "__main__":
    sys.exit(main())
