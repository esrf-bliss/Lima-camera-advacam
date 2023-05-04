############################################################################
# This file is part of LImA, a Library for Image Acquisition
#
# Copyright (C) : 2009-2011
# European Synchrotron Radiation Facility
# BP 220, Grenoble 38043
# FRANCE
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


class SyncCtrlObj(Core.HwSyncCtrlObj):
    # Core.Debug.DEB_CLASS(Core.DebModCamera, "SyncCtrlObj")
    def __init__(self, camera, det_info):
        Core.HwSyncCtrlObj.__init__(self)
        self.__camera = weakref.ref(camera)
        self.__det_info = weakref.ref(det_info)

        # Variables
        self.__exposure = camera.acq_expo_time
        self.__latency = det_info.get_min_latency()
        self.__nb_frames = 1
        self.__limaTrig2CamTrig = {
            Core.IntTrig: camera.INTERNAL_TRIG,
            Core.IntTrigMult: camera.INTERNAL_TRIG_MULTI,
        }
        self.__CamTrig2limaTrig = dict(
            [(y, x) for x, y in self.__limaTrig2CamTrig.items()]
        )

    # @Core.Debug.DEB_MEMBER_FUNCT
    def checkTrigMode(self, trig_mode):
        tMode = self.__limaTrig2CamTrig.get(trig_mode, None)
        return tMode is not None

    # @Core.Debug.DEB_MEMBER_FUNCT
    def setTrigMode(self, trig_mode):
        cam = self.__camera()
        if self.checkTrigMode(trig_mode):
            tMode = self.__limaTrig2CamTrig.get(trig_mode)
            cam.trigger_mode = tMode
        else:
            raise Core.Exceptions(Core.Hardware, Core.NotSupported)

    # @Core.Debug.DEB_MEMBER_FUNCT
    def getTrigMode(self):
        cvt_trigger_mode = None
        cam = self.__camera()
        trig_mode = cam.trigger_mode
        return self.__CamTrig2limaTrig.get(trig_mode, None)

    # @Core.Debug.DEB_MEMBER_FUNCT
    def setExpTime(self, exp_time):
        self.__exposure = exp_time
        cam = self.__camera()
        cam.acq_expo_time = exp_time

    # @Core.Debug.DEB_MEMBER_FUNCT
    def getExpTime(self):
        if self.__exposure is None:
            cam = self.__camera()
            self.__exposure = cam.acq_expo_time
        return self.__exposure

    # @Core.Debug.DEB_MEMBER_FUNCT
    def setLatTime(self, lat_time):
        self.__latency = lat_time

    # @Core.Debug.DEB_MEMBER_FUNCT
    def getLatTime(self):
        return self.__latency

    # @Core.Debug.DEB_MEMBER_FUNCT
    def setNbFrames(self, nb_frames):
        self.__nb_frames = nb_frames

    # @Core.Debug.DEB_MEMBER_FUNCT
    def getNbFrames(self):
        return self.__nb_frames

    # @Core.Debug.DEB_MEMBER_FUNCT
    def setNbHwFrames(self, nb_frames):
        self.setNbFrames(nb_frames)

    # @Core.Debug.DEB_MEMBER_FUNCT
    def getNbHwFrames(self):
        return self.getNbHwFrames()

    # @Core.Debug.DEB_MEMBER_FUNCT
    def getValidRanges(self):
        det_info = self.__det_info()
        return Core.HwSyncCtrlObj.ValidRangesType(
            det_info.get_min_exposition_time(),
            det_info.get_max_exposition_time(),
            det_info.get_min_latency(),
            det_info.get_max_latency(),
        )

    def prepareAcq(self):
        cam = self.__camera()
        exposure = self.__exposure
        exposure_period = exposure + self.__latency
        # don't know how to set a period
        cam.acq_nb_frames = self.__nb_frames
