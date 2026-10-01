############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2024
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

import weakref

from lima import core

from .DetInfoCtrlObj import DetInfoCtrlObj
from .SyncCtrlObj import SyncCtrlObj

from .acquisition import Camera


def _combine_det_status(*members):
    # The new pybind11-bound DetStatus/AcqStatus enums don't support the
    # bitwise-or the old sip-bound ones did (det_mask is a bitmask of
    # flags) - combine by value and rebuild a DetStatus instance.
    value = 0
    for m in members:
        value |= m.value
    return core.DetStatus(value)


class Interface(core.HwInterface):
    core.DEB_CLASS(core.DebModule.DebModCamera, "Interface")

    def __init__(self, config_file=None, device_id=""):
        core.HwInterface.__init__(self)

        self.__buffer = core.SoftBufferCtrlObj()
        self.__camera = Camera(config_file, device_id, self.__buffer)
        self.__detInfo = DetInfoCtrlObj(self.__camera)
        self.__syncObj = SyncCtrlObj(self.__camera, self.__detInfo)
        self.__acquisition_start_flag = False

    def __del__(self):
        self.__camera.quit()

    def quit(self):
        self.__camera.quit()

    @core.DEB_MEMBER_FUNCT
    def getCapList(self):
        return [core.HwCap(x) for x in [self.__detInfo, self.__syncObj, self.__buffer]]

    @core.DEB_MEMBER_FUNCT
    def reset(self, reset_level):
        if reset_level == self.HardReset:
            self.__camera.hard_reset()

    @core.DEB_MEMBER_FUNCT
    def prepareAcq(self):
        self.__camera.prepareAcq()
        self.__syncObj.prepareAcq()
        self.__image_number = 0

    @core.DEB_MEMBER_FUNCT
    def startAcq(self):
        self.__acquisition_start_flag = True
        self.__camera.startAcq()
        self.__image_number += 1

    @core.DEB_MEMBER_FUNCT
    def stopAcq(self):
        self.__camera.stopAcq()
        self.__acquisition_start_flag = False

    @core.DEB_MEMBER_FUNCT
    def getStatus(self):
        camserverStatus = self.__camera.getStatus()
        status = core.HwInterface.StatusType()

        if camserverStatus == self.__camera.ERROR:
            status.det = core.DetStatus.DetFault
            status.acq = core.AcqStatus.AcqFault
            deb.Error("Detector is in Fault stat")
        else:
            if camserverStatus == self.__camera.RUNNING:
                status.det = core.DetStatus.DetExposure
                status.acq = core.AcqStatus.AcqRunning
            else:
                status.det = core.DetStatus.DetIdle
                lastAcquiredFrame = self.__camera.acquiredFrames - 1
                requestNbFrame = self.__syncObj.getNbFrames()
                if not self.__acquisition_start_flag or (
                    lastAcquiredFrame >= 0 and lastAcquiredFrame == (requestNbFrame - 1)
                ):
                    status.acq = core.AcqStatus.AcqReady
                else:
                    status.acq = core.AcqStatus.AcqRunning

        status.det_mask = _combine_det_status(core.DetStatus.DetExposure,
                                              core.DetStatus.DetFault)
        return status

    @core.DEB_MEMBER_FUNCT
    def getNbAcquiredFrames(self):
        return self.__camera.acquiredFrames

    @core.DEB_MEMBER_FUNCT
    def getNbHwAcquiredFrames(self):
        return self.getNbAcquiredFrames()

    @property
    def camera(self):
        return self.__camera


def main():
    hwint = Interface()
    ct = core.CtControl(hwint)

    return ct


if __name__ == "__main__":
    sys.exit(main())
