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

import weakref

from Lima import Core

from .DetInfoCtrlObj import DetInfoCtrlObj
from .SyncCtrlObj import SyncCtrlObj

from .acquisition import Camera


class Interface(Core.HwInterface):
    Core.DEB_CLASS(Core.DebModCamera, "Interface")

    def __init__(self, config_file="/opt/pixet/factory/MiniPIX-J06-W0105.xml"):
        Core.HwInterface.__init__(self)
        self.__config_file = config_file

        self.__buffer = Core.SoftBufferCtrlObj()
        self.__camera = Camera(config_file, self.__buffer)
        self.__detInfo = DetInfoCtrlObj(self.__camera)
        self.__syncObj = SyncCtrlObj(self.__camera, self.__detInfo)
        self.__acquisition_start_flag = False

    def __del__(self):
        self.__camera.quit()

    def quit(self):
        self.__camera.quit()

    @Core.DEB_MEMBER_FUNCT
    def getCapList(self):
        return [Core.HwCap(x) for x in [self.__detInfo, self.__syncObj, self.__buffer]]

    @Core.DEB_MEMBER_FUNCT
    def reset(self, reset_level):
        if reset_level == self.HardReset:
            self.__camera.hard_reset()

    @Core.DEB_MEMBER_FUNCT
    def prepareAcq(self):
        self.__camera.prepareAcq()
        self.__syncObj.prepareAcq()
        self.__image_number = 0

    @Core.DEB_MEMBER_FUNCT
    def startAcq(self):
        self.__acquisition_start_flag = True
        self.__camera.startAcq()
        self.__image_number += 1

    @Core.DEB_MEMBER_FUNCT
    def stopAcq(self):
        self.__camera.stopAcq()
        self.__acquisition_start_flag = False

    @Core.DEB_MEMBER_FUNCT
    def getStatus(self):
        camserverStatus = self.__camera.getStatus()
        status = Core.HwInterface.StatusType()

        if camserverStatus == self.__camera.ERROR:
            status.det = Core.DetFault
            status.acq = Core.AcqFault
            deb.Error("Detector is in Fault stat")
        else:
            if camserverStatus == self.__camera.RUNNING:
                status.det = Core.DetExposure
                status.acq = Core.AcqRunning
            else:
                status.det = Core.DetIdle
                lastAcquiredFrame = self.__camera.acquiredFrames - 1
                requestNbFrame = self.__syncObj.getNbFrames()
                if not self.__acquisition_start_flag or (
                    lastAcquiredFrame >= 0 and lastAcquiredFrame == (requestNbFrame - 1)
                ):
                    status.acq = Core.AcqReady
                else:
                    status.acq = Core.AcqRunning

        status.det_mask = Core.DetExposure | Core.DetFault
        return status

    @Core.DEB_MEMBER_FUNCT
    def getNbAcquiredFrames(self):
        return self.__camera.acquiredFrames

    @Core.DEB_MEMBER_FUNCT
    def getNbHwAcquiredFrames(self):
        return self.getNbAcquiredFrames()

    @property
    def camera(self):
        return self.__camera


def main():
    hwint = Interface()
    ct = Core.CtControl(hwint)

    return ct


if __name__ == "__main__":
    sys.exit(main())
