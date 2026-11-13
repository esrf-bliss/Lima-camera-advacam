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

import os, weakref

from lima import core


class DetInfoCtrlObj(core.HwDetInfoCtrlObj):
    # core.Debug.DEB_CLASS(core.DebModule.DebModCamera, "DetInfoCtrlObj")
    def __init__(self, camera):
        core.HwDetInfoCtrlObj.__init__(self)

        self.__camera = weakref.ref(camera)

        # Variables
        self.__name = camera.fullName
        self.__id = camera.chip_id
        self.__width = camera.width
        self.__height = camera.height
        self.__bpp = camera.bpp

    # @core.Debug.DEB_MEMBER_FUNCT
    def getMaxImageSize(self):
        return core.Size(self.__width, self.__height)

    # @core.Debug.DEB_MEMBER_FUNCT
    def getDetectorImageSize(self):
        return self.getMaxImageSize()

    # @core.Debug.DEB_MEMBER_FUNCT
    def getDefImageType(self):
        if self.__bpp == 16:
            return core.ImageType.Bpp16
        elif self.__bpp == 12:
            return core.ImageType.Bpp12
        elif self.__bpp == 24:
            return core.ImageType.Bpp24
        else:
            raise core.Exception("Unsupported bpp: %s" % self.__bpp)

    # @core.Debug.DEB_MEMBER_FUNCT
    def getCurrImageType(self):
        return self.getDefImageType()

    # @core.Debug.DEB_MEMBER_FUNCT
    def setCurrImageType(self):
        raise core.Exception("setCurrImageType not supported")

    # @core.Debug.DEB_MEMBER_FUNCT
    def getPixelSize(self):
        # Timepix3 is 55um x 55 um
        return 55e-6, 55e-6

    # @core.Debug.DEB_MEMBER_FUNCT
    def getDetectorType(self):
        return "Advacam"

    # @core.Debug.DEB_MEMBER_FUNCT
    def getDetectorModel(self):
        return f"{self.__name} - {self.__id}"

    ##@brief image size won't change so no callback
    # @core.Debug.DEB_MEMBER_FUNCT
    def registerMaxImageSizeCallback(self, cb):
        pass

    ##@brief image size won't change so no callback
    # @core.Debug.DEB_MEMBER_FUNCT
    def unregisterMaxImageSizeCallback(self, cb):
        pass

    # @core.Debug.DEB_MEMBER_FUNCT
    def get_min_exposition_time(self):
        return 1e-7

    ##@todo don't know realy what is the maximum exposure time
    # for now set to a high value 1 hour
    # @core.Debug.DEB_MEMBER_FUNCT
    def get_max_exposition_time(self):
        return 1e6

    # @core.Debug.DEB_MEMBER_FUNCT
    def get_min_latency(self):
        return 0

    # @core.Debug.DEB_MEMBER_FUNCT
    def get_max_latency(self):
        return 0
