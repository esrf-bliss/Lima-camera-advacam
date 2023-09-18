############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2023
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

try:
    from Lima import Core
except:
    pass


class acqThread(threading.Thread):
    Core.DEB_CLASS(Core.DebModCamera, "Minipix.Camera.acqThread")

    @Core.DEB_MEMBER_FUNCT
    def __init__(self, minipix):
        threading.Thread.__init__(self)
        self.minipix = minipix

    @Core.DEB_MEMBER_FUNCT
    def run(self):
        deb.Trace("Starting acqThread")
        if self.minipix.buffer_ctrl:
            buffer_mgr = self.minipix.buffer_ctrl.getBuffer()
            buffer_mgr.setStartTimestamp(Core.Timestamp.now())

        rc = self.minipix.detector.doAdvancedAcquisition(
            self.minipix.acq_nb_frames,
            self.minipix.acq_expo_time,
            #pypixet.pixet.PX_ACQTYPE_FRAMES,
            pypixet.pixet.PX_ACQTYPE_DATADRIVEN,
            self.minipix.trigger_mode,
            #0,
            pypixet.pixet.PX_FTYPE_AUTODETECT,
            0,
            "",
        )
        deb.Trace(f"acq thread #{rc}: stop the Acq.")

        self.minipix._stopAcq()

        deb.Trace(f"Acq thread #{rc} finished")


class Camera:
    Core.DEB_CLASS(Core.DebModCamera, "Minipix.Camera")
    # Detector states
    ERROR, READY, RUNNING = range(3)

    # Detector states
    ERROR, READY, RUNNING = range(3)

    # Detector settings
    SET_BIAS_VOLTAGE = 200
    ENERGY_THRESHOLD = 3.6
    PX_THLFLAG_ENERGY = 0x2

    # More flags from Pixet GUI -> Python Scripting -> Help -> Function List
    (
        PX_TPX3_OPM_TOATOT,
        PX_TPX3_OPM_TOA,
        PX_TPX3_OPM_EVENT_ITOT,
        PX_TPX3_OPM_TOT_NOTOA,
    ) = range(4)
    OPERATION_MODES = ["ToA+ToT", "ToA", "Event+iToT", "ToT"]

    INTERNAL_TRIG = pypixet.pixet.PX_ACQMODE_NORMAL
    INTERNAL_TRIG_MULTI = pypixet.pixet.PX_ACQMODE_TRG_SWSTART

    @Core.DEB_MEMBER_FUNCT
    def __init__(
        self, config_file="/opt/pixet/factory/MiniPIX-J06-W0105.xml", buffer_ctrl=None
    ):
        pypixet.start()

        time.sleep(1)

        # below example code copied from pixetacq_server.py provided by ID20 (https://confluence.esrf.fr/pages/viewpage.action?spaceKey=ID20WK&title=MiniPIX)

        alldevices = pypixet.pixet.devices()  # get all devices (including motors, ...)
        detectors = pypixet.pixet.devicesByType(3)  # get all connected Timepix3
        self.detector = detectors[0]  # get first connected detector
        self.detector.loadConfigFromFile(config_file)

        # self.bias_voltage = self.SET_BIAS_VOLTAGE
        # time.sleep(1)

        self.energy_threshold = self.ENERGY_THRESHOLD
        time.sleep(1)

        self.detector.setOperationMode(self.PX_TPX3_OPM_EVENT_ITOT)
        time.sleep(1)

        detector = self.detector
        print("DETECTOR INFO")
        print("  Name:                ", detector.fullName())
        print("  Width x Height:      ", detector.width(), "X", detector.height())
        print("  Pixel count:         ", detector.pixelCount())
        print("  Chip count:          ", detector.chipCount())
        print(
            "  Chip IDs:            ", detector.chipIDs()
        )  # list of detector chip IDs
        print("")
        print(
            "  Energy threshold:    ", self.energy_threshold, " keV"
        )  # gets the threshold of chip 0 in energy
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
        print("  Refresh support:     ", detector.isSensorRefreshSupported())
        print("  Mode:                ", self.OPERATION_MODES[detector.operationMode()])
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
        self._supported_operation_mode = [
            self.PX_TPX3_OPM_TOATOT,
            self.PX_TPX3_OPM_TOA,
            self.PX_TPX3_OPM_EVENT_ITOT,
            self.PX_TPX3_OPM_TOT_NOTOA,
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

            # workaround since frame.data seems to be encoded data
            # but we dont have the encoding schema with Event+ToT mode
            # frame.save(f"/tmp/minipix_{value}.dat", 2, 0)
            # data = numpy.loadtxt(f"/tmp/minipix_{value}_Event.dat", dtype=numpy.uint16)

            # r_data = frame.data()
            # reshape data
            # data = numpy.array(r_data,dtype=numpy.int16)
            # data = data.reshape(self.width, self.height)

            # new solution, since Anuj.Rathi@advacam.cz email 
            # the frame.pixels()[0] contains indices of pixels hit by x-rays
            # the bincount result may be too short (some empty bins after the last non-empty one --> need a different function
            # test = np.bincount(frame.pixels()[0])  # is this the same as the "frame"?
            data = numpy.histogram(frame.pixels()[0], self.width*self.height)[0]
            data = test.reshape(self.width*self.height)
            
            self.__buffer_mgr.copy_data(frame_id, data)

            frame_info = Core.HwFrameInfoType()
            frame_info.acq_frame_nb = frame_id
            frame_info.frame_timestamp = Core.Timestamp.now()

            # raise the new frame !
            self.__buffer_mgr.newFrameReady(frame_info)

            del data
            # frame.save() creates 4 files Event.dat, Event.dat.dsc, iToT.dat and iTot.dat.dsc
            for f in glob.glob("/tmp/minipix_*"):
                os.remove(f)

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
        # According to the doc "AdvaPIX\ TPX3\ &\ MiniPIX\ TPX3\ -\ User\ Manual.pdf", page 7:
        # ToT & ToA: Tot 14bit, ToA 10bit, Fast ToA 4bit@640MHz
        # Only ToA:  ToA 14bit Only Fast ToA 4bit@640 MHz
        # Event Count & Integral ToT: Integral ToT 14bit, Hit Counter: 10bit
        return 16

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
    def energy_threshold(self):
        return self.detector.threshold(0, self.PX_THLFLAG_ENERGY)

    @energy_threshold.setter
    def energy_threshold(self, value):
        # do not know the valid range !! suppose up to 120 keV
        if value < 0 or value > 120:
            raise ValueError("Invalid energy threshold, range = [0,120] keV")

        self.detector.setThreshold(0, value, self.PX_THLFLAG_ENERGY)

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
        return self.detector.temperature()

    @property
    def operation_mode(self):
        return self.OPERATION_MODES[self.detector.operationMode()]

    @operation_mode.setter
    def operation_mode(self, value):
        if value not in self.OPERATION_MODES:
            raise ValueError("Invalid operation mode")
        self.detector.setOperationMode(self.OPERATION_MODES.index(value))

    # for pytango automatic wrapping

    def setEnergyThreshold(self, value):
        self.energy_threshold = value

    def getEnergyThreshold(self):
        return self.energy_threshold

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
        return self.operation_mode

    def setOperationMode(self, value):
        self.operation_mode = value


def main():
    minipix = Camera()

    minipix.acqNbFrames = 10
    minipix.acqExpoTime = 0.4

    minipix.prepareAcq()
    minipix.startAcq()

    nb_frames = 1
    while minipix.getStatus() != "Ready":
        if minipix.acquiredFrames == nb_frames:
            minipix.startAcq()
            nb_frames += 1


if __name__ == "__main__":
    sys.exit(main())
