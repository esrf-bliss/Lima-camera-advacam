.. _lima-tango-advacam:

Advacam Tango device
=====================

This is the reference documentation of the Advacam Tango device.

you can also find some useful information about the camera models/prerequisite/installation/configuration/compilation in the :ref:`Advacam camera plugin <camera-advacam>` section.

Properties
----------

======================== =============== ================================= =====================================
Property name	         Mandatory	 Default value	                   Description
======================== =============== ================================= =====================================
config_path              Yes             N/A                               the detector XML configuration file
energy_threshold         No              3.6                               the energy threshold in keV 
======================== =============== ================================= =====================================


Attributes
----------
============================== ======= ======================= ============================================================
Attribute name		       RW      Type                    Description
============================== ======= ======================= ============================================================
bias_voltage                   rw      DevDouble               Bias high voltage in Volt
energy_threshold               rw      DevDouble               energy threshold in keV
operation_mode                 rw      DevString               operation modes supported, ToA+ToT,ToA,Event+iToT and ToT
sensed_bias_voltage            ro      DevDouble               Bias voltage sense in Volt
sensed_bias_current            ro      DevDouble               Bias current in A
temperature                    ro      DevDouble               Temperature of the camera core
============================== ======= ======================= ============================================================


Commands
--------

=======================	=============== =======================	===========================================
Command name		Arg. in		Arg. out		Description
=======================	=============== =======================	===========================================
Init			DevVoid 	DevVoid			Do not use
State			DevVoid		DevLong			Return the device state
Status			DevVoid		DevString		Return the device state as a string
getAttrStringValueList	DevString:	DevVarStringArray:	Return the authorized string value list for
			Attribute name	String value list	a given attribute name
=======================	=============== =======================	===========================================


