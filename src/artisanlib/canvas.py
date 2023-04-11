#
# ABOUT
# Artisan Main Canvas

# LICENSE
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 2 of the License, or
# version 3 of the License, or (at your option) any later version. It is
# provided for educational purposes and is distributed in the hope that
# it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
# the GNU General Public License for more details.

# AUTHOR
# Marko Luther, 2023

from artisanlib import __version__
from artisanlib import __revision__
from artisanlib import __build__

from artisanlib import __release_sponsor_domain__
from artisanlib import __release_sponsor_url__

import time as libtime
import os
import sys  # @UnusedImport
import ast
import platform
import math
import warnings
import numpy
import logging
import re
from bisect import bisect_right
import psutil
from psutil._common import bytes2human

from typing import Optional, List, Dict, Callable, Tuple, Union, Any, cast, TYPE_CHECKING  #for Python >= 3.9: can remove 'List' since type hints can now use the generic 'list'
from typing_extensions import Final  # Python <=3.7

if TYPE_CHECKING:
    from artisanlib.types import ProfileData, EnergyMetrics, BTU # pylint: disable=unused-import
    from artisanlib.main import ApplicationWindow # pylint: disable=unused-import
    from plus.stock import Blend # pylint: disable=unused-import
    from plus.blend import CustomBlend # pylint: disable=unused-import
    from matplotlib.lines import Line2D # pylint: disable=unused-import
    from matplotlib.text import Text # pylint: disable=unused-import
    from matplotlib.collections import PolyCollection # pylint: disable=unused-import
    from matplotlib.axes import Axes # pylint: disable=unused-import
    from matplotlib.text import Annotation # pylint: disable=unused-import
    from matplotlib.image import AxesImage # pylint: disable=unused-import
    import numpy.typing as npt # pylint: disable=unused-import

from artisanlib.suppress_errors import suppress_stdout_stderr
from artisanlib.util import (uchr, fill_gaps, deltaLabelPrefix, deltaLabelUTF8, deltaLabelMathPrefix, stringfromseconds,
        fromFtoC, fromCtoF, RoRfromFtoC, RoRfromCtoF, toInt, toString, toFloat, application_name, getResourcePath, getDirectory,
        abbrevString, scaleFloat2String)
from artisanlib import pid
from artisanlib.time import ArtisanTime
from artisanlib.filters import LiveMedian
from artisanlib.dialogs import ArtisanMessageBox

# import artisan.plus module
from plus.util import roastLink
from plus.queue import addRoast

try:
    #pylint: disable-next = E, W, R, C
    from PyQt6.QtWidgets import (QApplication, QWidget, QMessageBox, # @Reimport @UnresolvedImport @UnusedImport # pylint: disable=import-error
                             QGraphicsEffect, # @Reimport @UnresolvedImport @UnusedImport
                             QSizePolicy, # @Reimport @UnresolvedImport @UnusedImport
                             QMenu) # @Reimport @UnresolvedImport @UnusedImport
    from PyQt6.QtGui import (QAction, QImage, QWindow, # @Reimport @UnresolvedImport @UnusedImport
                                QColor, QDesktopServices, # @Reimport @UnresolvedImport @UnusedImport
                                QCursor) # @Reimport @UnresolvedImport @UnusedImport
    from PyQt6.QtCore import (QLocale, pyqtSignal, pyqtSlot, # type: ignore # @Reimport @UnresolvedImport @UnusedImport
                              QTimer, QSettings, # @Reimport @UnresolvedImport @UnusedImport
                              QUrl, QDir, Qt, QDateTime, QThread, QSemaphore, QObject) # @Reimport @UnresolvedImport @UnusedImport
    from PyQt6 import sip # @Reimport @UnresolvedImport @UnusedImport
except Exception: # type: ignore # pylint: disable=broad-except
    #pylint: disable = E, W, R, C
    from PyQt5.QtWidgets import (QAction, QApplication, QWidget, QMessageBox,  # type: ignore  # @Reimport @UnresolvedImport @UnusedImport
                             QGraphicsEffect,  # type: ignore  # @Reimport @UnresolvedImport @UnusedImport
                             QSizePolicy, # type: ignore  # @Reimport @UnresolvedImport @UnusedImport
                             QMenu) # type: ignore # @Reimport @UnresolvedImport @UnusedImport
    from PyQt5.QtGui import (QImage, QWindow,  # type: ignore # @Reimport @UnresolvedImport @UnusedImport
                                QColor, QDesktopServices, # type: ignore # @Reimport @UnresolvedImport @UnusedImport
                                QCursor) # type: ignore # @Reimport @UnresolvedImport @UnusedImport
    from PyQt5.QtCore import (QLocale, pyqtSignal, pyqtSlot, # type: ignore # @Reimport @UnresolvedImport @UnusedImport
                              QTimer, QSettings, # type: ignore # @Reimport @UnresolvedImport @UnusedImport
                              QUrl, QDir, Qt, QDateTime, QThread, QSemaphore, QObject) # type: ignore # @Reimport @UnresolvedImport @UnusedImport
    try:
        from PyQt5 import sip # type: ignore # @Reimport @UnresolvedImport @UnusedImport
    except Exception: # type: ignore # pylint: disable=broad-except
        import sip # type: ignore # @Reimport @UnresolvedImport @UnusedImport



with suppress_stdout_stderr():
    import matplotlib as mpl

from matplotlib.figure import Figure
from matplotlib import rcParams, patches, transforms, ticker
import matplotlib.patheffects as PathEffects
from matplotlib.patches import Polygon
from matplotlib.transforms import Bbox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # @Reimport

from artisanlib.phidgets import PhidgetManager
from Phidget22.VoltageRange import VoltageRange # type: ignore

try:
    # spanning a second multiprocessing instance (Hottop server) on macOS falils to import the YAPI interface
    from yoctopuce.yocto_api import YAPI # type: ignore
except Exception: # pylint: disable=broad-except
    pass



_log: Final[logging.Logger] = logging.getLogger(__name__)


#######################################################################################
#################### Ambient Data Collection  #########################################
#######################################################################################

class AmbientWorker(QObject): # pylint: disable=too-few-public-methods # pyright: ignore # Argument to class must be a base class (reportGeneralTypeIssues)
    finished = pyqtSignal()

    def __init__(self, aw:'ApplicationWindow') -> None:
        super().__init__()
        self.aw = aw

    def run(self):
        libtime.sleep(2.5) # wait a moment after ON until all other devices are attached
        try:
            if self.aw is not None and self.aw.qmc is not None:
                self.aw.qmc.getAmbientData()
        except Exception as e:  # pylint: disable=broad-except
            _log.exception(e)
        finally:
            self.finished.emit()


# NOTE: to have pylint to verify proper __slot__ definitions one has to remove the super class FigureCanvas here temporarily
#   as this does not has __slot__ definitions and thus __dict__ is contained which suppresses the warnings
class tgraphcanvas(FigureCanvas):
    updategraphicsSignal = pyqtSignal()
    updateLargeLCDsTimeSignal = pyqtSignal(str)
    updateLargeLCDsReadingsSignal = pyqtSignal(str,str)
    updateLargeLCDsSignal = pyqtSignal(str,str,str)
    setTimerLargeLCDcolorSignal = pyqtSignal(str,str)
    showAlarmPopupSignal = pyqtSignal(str,int)
    fileDirtySignal = pyqtSignal()
    fileCleanSignal = pyqtSignal()
    markChargeSignal = pyqtSignal(int)
    markDRYSignal = pyqtSignal()
    markFCsSignal = pyqtSignal()
    markFCeSignal = pyqtSignal()
    markSCsSignal = pyqtSignal()
    markSCeSignal = pyqtSignal()
    markDropSignal = pyqtSignal()
    markCoolSignal = pyqtSignal()
    toggleMonitorSignal = pyqtSignal()
    toggleRecorderSignal = pyqtSignal()
    processAlarmSignal = pyqtSignal(int, bool, int, str)
    alarmsetSignal = pyqtSignal(int)
    moveBackgroundSignal = pyqtSignal(str, int)
    eventRecordSignal = pyqtSignal(int)
    showCurveSignal = pyqtSignal(str, bool)
    showExtraCurveSignal = pyqtSignal(int, str, bool)
    showEventsSignal = pyqtSignal(int, bool)
    showBackgroundEventsSignal = pyqtSignal(bool)

    umlaute_dict : Final[Dict[str, str]] = {
       uchr(228): 'ae',  # U+00E4   \xc3\xa4
       uchr(246): 'oe',  # U+00F6   \xc3\xb6
       uchr(252): 'ue',  # U+00FC   \xc3\xbc
       uchr(196): 'Ae',  # U+00C4   \xc3\x84
       uchr(214): 'Oe',  # U+00D6   \xc3\x96
       uchr(220): 'Ue',  # U+00DC   \xc3\x9c
       uchr(223): 'ss',  # U+00DF   \xc3\x9f
    }

    __slots__ = [ 'aw', 'alignnames', 'locale_str', 'alpha', 'palette', 'palette1', 'EvalueColor_default', 'EvalueTextColor_default', 'artisanflavordefaultlabels', 'customflavorlabels',
        'SCAAflavordefaultlabels', 'SCAflavordefaultlabels', 'CQIflavordefaultlabels', 'SweetMariasflavordefaultlabels', 'Cflavordefaultlabels', 'Eflavordefaultlabels', 'coffeegeekflavordefaultlabels',
        'Intelligentsiaflavordefaultlabels', 'IstitutoInternazionaleAssaggiatoriCaffe', 'WorldCoffeeRoastingChampionship', 'ax1', 'ax2', 'ambiWorker', 'ambiThread', 'afterTP',
        'decay_weights', 'temp_decay_weights', 'flavorlabels', 'flavors', 'flavorstartangle', 'flavoraspect', 'flavorchart_plotf', 'flavorchart_angles', 'flavorchart_plot',
        'flavorchart_fill', 'flavorchart_labels', 'flavorchart_total', 'mode', 'mode_tempsliders', 'errorlog', 'default_delay', 'delay', 'min_delay', 'extra_event_sampling_delay',
        'phases_fahrenheit_defaults', 'phases_celsius_defaults', 'phases', 'phasesbuttonflag', 'phasesfromBackgroundflag', 'watermarksflag', 'step100temp', 'phasesLCDflag',
        'phasesLCDmode', 'phasesLCDmode_l', 'phasesLCDmode_all', 'statisticsflags', 'statisticsmode', 'AUCbegin', 'AUCbase', 'AUCbaseFlag', 'AUCtarget', 'AUCbackground',
        'AUCtargetFlag', 'AUCguideFlag', 'AUClcdFlag', 'AUCLCDmode', 'AUCvalue', 'AUCsinceFCs', 'AUCguideTime', 'AUCshowFlag', 'statisticstimes', 'device', 'device_logging',
        'device_log_file_name', 'device_log_file', 'phidget_dataRatesStrings', 'phidget_dataRatesValues', 'phidget1048_types', 'phidget1048_async', 'phidget1048_changeTriggers',
        'phidget1048_changeTriggersValues', 'phidget1048_changeTriggersStrings', 'phidget1048_dataRate', 'phidget1045_async', 'phidget1045_changeTrigger', 'phidget1045_changeTriggersValues',
        'phidget1045_changeTriggersStrings', 'phidget1045_emissivity', 'phidget1045_dataRate', 'phidget1200_async', 'phidget1200_formula', 'phidget1200_formulaValues', 'phidget1200_wire',
        'phidget1200_wireValues', 'phidget1200_changeTrigger', 'phidget1200_changeTriggersValues', 'phidget1200_changeTriggersStrings', 'phidget1200_dataRate',
        'phidget1200_dataRatesStrings', 'phidget1200_dataRatesValues', 'phidget1200_2_async', 'phidget1200_2_formula', 'phidget1200_2_wire', 'phidget1200_2_changeTrigger',
        'phidget1200_2_dataRate', 'phidget1046_async', 'phidget1046_gain', 'phidget1046_gainValues', 'phidget1046_formula', 'phidget1046_formulaValues', 'phidget1046_dataRate',
        'phidgetRemoteFlag', 'phidgetRemoteOnlyFlag', 'phidgetServerID', 'phidgetPassword', 'phidgetPort', 'phidgetServerAdded', 'phidgetServiceDiscoveryStarted',
        'phidgetManager', 'yoctoRemoteFlag', 'yoctoServerID', 'YOCTOchanUnit', 'YOCTOchan1Unit', 'YOCTOchan2Unit', 'YOCTO_emissivity', 'YOCTO_async',
        'YOCTO_dataRate', 'YOCTO_dataRatesStrings', 'YOCTO_dataRatesValues', 'phidget1018valueFactor', 'phidget1018_async', 'phidget1018_ratio', 'phidget1018_dataRates',
        'phidget1018_changeTriggers', 'phidget1018_changeTriggersValues', 'phidget1018_changeTriggersStrings', 'phidgetVCP100x_voltageRanges', 'phidgetVCP100x_voltageRangeValues',
        'phidgetVCP100x_voltageRangeStrings', 'phidgetDAQ1400_powerSupplyStrings', 'phidgetDAQ1400_powerSupply', 'phidgetDAQ1400_inputModeStrings', 'phidgetDAQ1400_inputMode',
        'devices', 'phidgetDevices', 'nonSerialDevices', 'nonTempDevices', 'extradevices', 'extratimex', 'extradevicecolor1', 'extradevicecolor2', 'extratemp1',
        'extratemp2', 'extrastemp1', 'extrastemp2', 'extractimex1', 'extractimex2', 'extractemp1', 'extractemp2', 'extratemp1lines', 'extratemp2lines',
        'extraname1', 'extraname2', 'extramathexpression1', 'extramathexpression2', 'extralinestyles1', 'extralinestyles2', 'extradrawstyles1', 'extradrawstyles2',
        'extralinewidths1', 'extralinewidths2', 'extramarkers1', 'extramarkers2', 'extramarkersizes1', 'extramarkersizes2', 'devicetablecolumnwidths', 'extraNoneTempHint1',
        'extraNoneTempHint2', 'plotcurves', 'plotcurvecolor', 'overlapList', 'tight_layout_params', 'fig', 'ax', 'delta_ax', 'legendloc', 'legendloc_pos', 'onclick_cid',
        'oncpick_cid', 'ondraw_cid', 'rateofchange1', 'rateofchange2', 'flagon', 'flagstart', 'flagKeepON', 'flagOpenCompleted', 'flagsampling', 'flagsamplingthreadrunning',
        'manuallogETflag', 'zoom_follow', 'alignEvent', 'compareAlignEvent', 'compareEvents', 'compareET', 'compareBT', 'compareDeltaET', 'compareDeltaBT', 'compareMainEvents', 'compareBBP', 'compareRoast',
        'replayType', 'replayedBackgroundEvents', 'beepedBackgroundEvents', 'roastpropertiesflag', 'roastpropertiesAutoOpenFlag', 'roastpropertiesAutoOpenDropFlag',
        'title', 'title_show_always', 'ambientTemp', 'ambientTempSource', 'ambient_temperature_device', 'ambient_pressure', 'ambient_pressure_device', 'ambient_humidity',
        'ambient_humidity_device', 'elevation', 'temperaturedevicefunctionlist', 'humiditydevicefunctionlist', 'pressuredevicefunctionlist', 'moisture_greens', 'moisture_roasted',
        'greens_temp', 'beansize', 'beansize_min', 'beansize_max', 'whole_color', 'ground_color', 'color_systems', 'color_system_idx', 'heavyFC_flag', 'lowFC_flag', 'lightCut_flag',
        'darkCut_flag', 'drops_flag', 'oily_flag', 'uneven_flag', 'tipping_flag', 'scorching_flag', 'divots_flag', 'timex',
        'temp1', 'temp2', 'delta1', 'delta2', 'stemp1', 'stemp2', 'tstemp1', 'tstemp2', 'ctimex1', 'ctimex2', 'ctemp1', 'ctemp2', 'unfiltereddelta1', 'unfiltereddelta2',  'unfiltereddelta1_pure', 'unfiltereddelta2_pure',
        'on_timex', 'on_temp1', 'on_temp2', 'on_ctimex1', 'on_ctimex2', 'on_ctemp1', 'on_ctemp2','on_tstemp1', 'on_tstemp2', 'on_unfiltereddelta1',
        'on_unfiltereddelta2', 'on_delta1', 'on_delta2', 'on_extratemp1', 'on_extratemp2', 'on_extratimex', 'on_extractimex1', 'on_extractemp1', 'on_extractimex2', 'on_extractemp2',
        'timeindex', 'ETfunction', 'BTfunction', 'DeltaETfunction', 'DeltaBTfunction', 'safesaveflag', 'pid', 'background', 'backgroundprofile', 'backgroundprofile_moved_x', 'backgroundprofile_moved_y', 'backgroundDetails',
        'backgroundeventsflag', 'backgroundpath', 'backgroundUUID', 'backgroundUUID', 'backgroundShowFullflag', 'backgroundKeyboardControlFlag', 'titleB', 'roastbatchnrB', 'roastbatchprefixB',
        'roastbatchposB', 'temp1B', 'temp2B', 'temp1BX', 'temp2BX', 'timeB', 'temp1Bdelta', 'temp2Bdelta',
        'stemp1B', 'stemp2B', 'stemp1BX', 'stemp2BX', 'extraname1B', 'extraname2B', 'extratimexB', 'xtcurveidx', 'ytcurveidx', 'delta1B', 'delta2B', 'timeindexB',
        'TP_time_B_loaded', 'backgroundEvents', 'backgroundEtypes', 'backgroundEvalues', 'backgroundEStrings', 'backgroundalpha', 'backgroundmetcolor',
        'backgroundbtcolor', 'backgroundxtcolor', 'backgroundytcolor', 'backgrounddeltaetcolor', 'backgrounddeltabtcolor', 'backmoveflag', 'detectBackgroundEventTime',
        'backgroundReproduce', 'backgroundReproduceBeep', 'backgroundPlaybackEvents', 'backgroundPlaybackDROP', 'Betypes', 'backgroundFlavors', 'flavorbackgroundflag',
        'E1backgroundtimex', 'E2backgroundtimex', 'E3backgroundtimex', 'E4backgroundtimex', 'E1backgroundvalues', 'E2backgroundvalues', 'E3backgroundvalues',
        'E4backgroundvalues', 'l_backgroundeventtype1dots', 'l_backgroundeventtype2dots', 'l_backgroundeventtype3dots', 'l_backgroundeventtype4dots',
        'DeltaETBflag', 'DeltaBTBflag', 'clearBgbeforeprofileload', 'hideBgafterprofileload', 'heating_types', 'operator', 'organization', 'roastertype', 'roastersize', 'roasterheating', 'drumspeed',
        'organization_setup', 'operator_setup', 'roastertype_setup', 'roastersize_setup', 'roasterheating_setup', 'drumspeed_setup', 'last_batchsize', 'machinesetup_energy_ratings',
        'machinesetup', 'roastingnotes', 'cuppingnotes', 'roastdate', 'roastepoch', 'lastroastepoch', 'batchcounter', 'batchsequence', 'batchprefix', 'neverUpdateBatchCounter',
        'roastbatchnr', 'roastbatchprefix', 'roastbatchpos', 'roasttzoffset', 'roastUUID', 'plus_default_store', 'plus_store', 'plus_store_label', 'plus_coffee',
        'plus_coffee_label', 'plus_blend_spec', 'plus_blend_spec_labels', 'plus_blend_label', 'plus_custom_blend', 'plus_sync_record_hash', 'plus_file_last_modified', 'beans', 'projectFlag', 'curveVisibilityCache', 'ETcurve', 'BTcurve',
        'ETlcd', 'BTlcd', 'swaplcds', 'LCDdecimalplaces', 'foregroundShowFullflag', 'DeltaETflag', 'DeltaBTflag', 'DeltaETlcdflag', 'DeltaBTlcdflag',
        'swapdeltalcds', 'PIDbuttonflag', 'Controlbuttonflag', 'deltaETfilter', 'deltaBTfilter', 'curvefilter', 'deltaETspan', 'deltaBTspan',
        'deltaETsamples', 'deltaBTsamples', 'profile_sampling_interval', 'background_profile_sampling_interval', 'profile_meter', 'optimalSmoothing', 'polyfitRoRcalc',
        'patheffects', 'graphstyle', 'graphfont', 'buttonvisibility', 'buttonactions', 'buttonactionstrings', 'extrabuttonactions', 'extrabuttonactionstrings',
        'xextrabuttonactions', 'xextrabuttonactionstrings', 'chargeTimerFlag', 'autoChargeFlag', 'autoDropFlag', 'autoChargeIdx', 'autoDropIdx', 'markTPflag', 'autoTPIdx',
        'autoDRYflag', 'autoFCsFlag', 'autoCHARGEenabled', 'autoDRYenabled', 'autoFCsenabled', 'autoDROPenabled', 'autoDryIdx', 'autoFCsIdx', 'projectionconstant',
        'projectionmode', 'transMappingMode', 'weight', 'volume_units', 'volume', 'density', 'density_roasted', 'volumeCalcUnit', 'volumeCalcWeightInStr',
        'volumeCalcWeightOutStr', 'container_names', 'container_weights', 'container_idx', 'specialevents', 'etypes', 'etypesdefault', 'specialeventstype',
        'specialeventsStrings', 'specialeventsvalue', 'eventsGraphflag', 'clampEvents', 'renderEventsDescr', 'eventslabelschars', 'eventsshowflag',
        'annotationsflag', 'showeventsonbt', 'showEtypes', 'E1timex', 'E2timex', 'E3timex', 'E4timex', 'E1values', 'E2values', 'E3values', 'E4values',
        'EvalueColor', 'EvalueTextColor', 'EvalueMarker', 'EvalueMarkerSize', 'Evaluelinethickness', 'Evaluealpha', 'eventpositionbars', 'specialeventannotations',
        'specialeventannovisibilities', 'specialeventplaybackaid', 'specialeventplayback', 'overlappct', 'linestyle_default', 'drawstyle_default', 'linewidth_min', 'markersize_min', 'linewidth_default', 'back_linewidth_default', 'delta_linewidth_default',
        'back_delta_linewidth_default', 'extra_linewidth_default', 'marker_default', 'markersize_default', 'BTlinestyle', 'BTdrawstyle', 'BTlinewidth', 'BTmarker',
        'BTmarkersize', 'ETlinestyle', 'ETdrawstyle', 'ETlinewidth', 'ETmarker', 'ETmarkersize', 'BTdeltalinestyle', 'BTdeltadrawstyle', 'BTdeltalinewidth',
        'BTdeltamarker', 'BTdeltamarkersize', 'ETdeltalinestyle', 'ETdeltadrawstyle', 'ETdeltalinewidth', 'ETdeltamarker', 'ETdeltamarkersize', 'BTbacklinestyle',
        'BTbackdrawstyle', 'BTbacklinewidth', 'BTbackmarker', 'BTbackmarkersize', 'ETbacklinestyle', 'ETbackdrawstyle', 'ETbacklinewidth', 'ETbackmarker',
        'ETbackmarkersize', 'XTbacklinestyle', 'XTbackdrawstyle', 'XTbacklinewidth', 'XTbackmarker', 'XTbackmarkersize', 'YTbacklinestyle', 'YTbackdrawstyle',
        'YTbacklinewidth', 'YTbackmarker', 'YTbackmarkersize', 'BTBdeltalinestyle', 'BTBdeltadrawstyle', 'BTBdeltalinewidth', 'BTBdeltamarker', 'BTBdeltamarkersize',
        'ETBdeltalinestyle', 'ETBdeltadrawstyle', 'ETBdeltalinewidth', 'ETBdeltamarker', 'ETBdeltamarkersize', 'alarmsetlabel', 'alarmflag', 'alarmguard', 'alarmnegguard', 'alarmtime', 'alarmoffset', 'alarmtime2menuidx', 'menuidx2alarmtime',
        'alarmcond', 'alarmstate', 'alarmsource', 'alarmtemperature', 'alarmaction', 'alarmbeep', 'alarmstrings', 'alarmtablecolumnwidths', 'silent_alarms',
        'alarmsets_count', 'alarmsets', 'loadalarmsfromprofile', 'loadalarmsfrombackground', 'alarmsfile', 'temporaryalarmflag', 'TPalarmtimeindex',
        'rsfile', 'temporary_error', 'temporarymovepositiveslider', 'temporarymovenegativeslider',
        'temporayslider_force_move', 'quantifiedEvent', 'loadaxisfromprofile', 'startofx_default', 'endofx_default', 'xgrid_default', 'ylimit_F_default',
        'ylimit_min_F_default', 'ygrid_F_default', 'zlimit_F_default', 'zlimit_min_F_default', 'zgrid_F_default', 'ylimit_C_default', 'ylimit_min_C_default',
        'ygrid_C_default', 'zlimit_C_default', 'zlimit_min_C_default', 'zgrid_C_default', 'temp_grid', 'time_grid', 'zlimit_max', 'zlimit_min_max',
        'ylimit_max', 'ylimit_min_max', 'ylimit', 'ylimit_min', 'zlimit', 'zlimit_min', 'RoRlimitFlag', 'RoRlimit', 'RoRlimitm', 'maxRoRlimit',
        'endofx', 'startofx', 'resetmaxtime', 'chargemintime', 'fixmaxtime', 'locktimex', 'autotimex', 'autotimexMode', 'autodeltaxET', 'autodeltaxBT', 'locktimex_start',
        'locktimex_end', 'xgrid', 'ygrid', 'zgrid', 'gridstyles', 'gridlinestyle', 'gridthickness', 'gridalpha', 'xrotation',
        'statisticsheight', 'statisticsupper', 'statisticslower', 'autosaveflag', 'autosaveprefix', 'autosavepath', 'autosavealsopath',
        'autosaveaddtorecentfilesflag', 'autosaveimage', 'autosaveimageformat', 'autoasaveimageformat_types', 'ystep_down', 'ystep_up', 'backgroundETcurve', 'backgroundBTcurve',
        'l_temp1', 'l_temp2', 'l_delta1', 'l_delta2', 'l_back1', 'l_back2', 'l_back3', 'l_back4', 'l_delta1B', 'l_delta2B', 'l_BTprojection', 'l_DeltaETprojection', 'l_DeltaBTprojection',
        'l_ETprojection', 'l_AUCguide', 'l_horizontalcrossline', 'l_verticalcrossline', 'l_timeline', 'legend', 'l_eventtype1dots', 'l_eventtype2dots',
        'l_eventtype3dots', 'l_eventtype4dots', 'l_eteventannos', 'l_bteventannos', 'l_eventtype1annos', 'l_eventtype2annos', 'l_eventtype3annos',
        'l_eventtype4annos', 'l_annotations', 'l_background_annotations', 'l_annotations_dict', 'l_annotations_pos_dict', 'l_event_flags_dict',
        'l_event_flags_pos_dict', 'ai', 'timeclock', 'threadserver', 'designerflag', 'designerconnections', 'mousepress', 'indexpoint',
        'workingline', 'eventtimecopy', 'specialeventsStringscopy', 'specialeventsvaluecopy', 'specialeventstypecopy', 'currentx', 'currenty',
        'designertimeinit', 'BTsplinedegree', 'ETsplinedegree', 'reproducedesigner', 'designertemp1init', 'designertemp2init', 'ax_background_designer', 'designer_timez', 'time_step_size',
        '_designer_orange_mark', '_designer_orange_mark_shown', '_designer_blue_mark', '_designer_blue_mark_shown', 'l_temp1_markers', 'l_temp2_markers',
        'l_stat1', 'l_stat2', 'l_stat3', 'l_div1', 'l_div2', 'l_div3', 'l_div4',
        'filterDropOut_replaceRoR_period', 'filterDropOut_spikeRoR_period', 'filterDropOut_tmin_C_default', 'filterDropOut_tmax_C_default',
        'filterDropOut_tmin_F_default', 'filterDropOut_tmax_F_default', 'filterDropOut_spikeRoR_dRoR_limit_C_default', 'filterDropOut_spikeRoR_dRoR_limit_F_default',
        'filterDropOuts', 'filterDropOut_tmin', 'filterDropOut_tmax', 'filterDropOut_spikeRoR_dRoR_limit', 'minmaxLimits',
        'dropSpikes', 'dropDuplicates', 'dropDuplicatesLimit', 'liveMedianRoRfilter', 'liveMedianETfilter', 'liveMedianBTfilter', 'interpolatemax', 'swapETBT', 'wheelflag', 'wheelnames', 'segmentlengths', 'segmentsalpha',
        'wheellabelparent', 'wheelcolor', 'wradii', 'startangle', 'projection', 'wheeltextsize', 'wheelcolorpattern', 'wheeledge',
        'wheellinewidth', 'wheellinecolor', 'wheeltextcolor', 'wheelconnections', 'wheelx', 'wheelz', 'wheellocationx', 'wheellocationz',
        'wheelaspect', 'samplingSemaphore', 'profileDataSemaphore', 'messagesemaphore', 'errorsemaphore', 'serialsemaphore', 'seriallogsemaphore',
        'eventactionsemaphore', 'updateBackgroundSemaphore', 'alarmSemaphore', 'rampSoakSemaphore', 'crossmarker', 'crossmouseid', 'onreleaseid',
        'analyzer_connect_id', 'extra309T3', 'extra309T4', 'extra309TX', 'hottop_ET', 'hottop_BT', 'hottop_HEATER', 'hottop_MAIN_FAN', 'hottop_TX',
        'R1_DT', 'R1_BT', 'R1_BT_ROR', 'R1_EXIT_TEMP', 'R1_HEATER', 'R1_FAN', 'R1_DRUM', 'R1_VOLTAGE', 'R1_TX', 'R1_STATE', 'R1_FAN_RPM', 'R1_STATE_STR',
        'extraArduinoT1', 'extraArduinoT2', 'extraArduinoT3', 'extraArduinoT4', 'extraArduinoT5', 'extraArduinoT6', 'program_t3', 'program_t4', 'program_t5', 'program_t6',
        'program_t7', 'program_t8', 'program_t9', 'program_t10', 'dutycycle', 'dutycycleTX', 'currentpidsv', 'linecount', 'deltalinecount',
        'ax_background', 'block_update', 'fmt_data_RoR', 'fmt_data_curve', 'running_LCDs', 'plotterstack', 'plotterequationresults', 'plottermessage', 'alarm_popup_timout',
        'RTtemp1', 'RTtemp2', 'RTextratemp1', 'RTextratemp2', 'RTextratx', 'idx_met', 'showmet', 'met_annotate', 'met_timex_temp1_delta',
        'extendevents', 'statssummary', 'showtimeguide', 'statsmaxchrperline', 'energyunits', 'powerunits', 'sourcenames', 'loadlabels_setup',
        'loadratings_setup', 'ratingunits_setup', 'sourcetypes_setup', 'load_etypes_setup', 'presssure_percents_setup', 'loadevent_zeropcts_setup',
        'loadevent_hundpcts_setup', 'preheatDuration_setup', 'preheatenergies_setup', 'betweenbatchDuration_setup', 'betweenbatchenergies_setup',
        'coolingDuration_setup', 'coolingenergies_setup', 'betweenbatch_after_preheat_setup', 'electricEnergyMix_setup', 'energyresultunit_setup',
        'kind_list', 'loadlabels', 'loadratings', 'ratingunits', 'sourcetypes', 'load_etypes', 'presssure_percents', 'loadevent_zeropcts',
        'loadevent_hundpcts', 'preheatDuration', 'preheatenergies', 'betweenbatchDuration', 'betweenbatchenergies', 'coolingDuration', 'coolingenergies',
        'betweenbatch_after_preheat', 'electricEnergyMix', 'baseX', 'baseY', 'base_horizontalcrossline', 'base_verticalcrossline',
        'base_messagevisible', 'colorDifferenceThreshold', 'handles', 'labels', 'legend_lines', 'eventmessage', 'backgroundeventmessage',
        'eventmessagetimer', 'resizeredrawing', 'logoimg', 'analysisresultsloc_default', 'analysisresultsloc', 'analysispickflag', 'analysisresultsstr',
        'analysisstartchoice', 'analysisoffset', 'curvefitstartchoice', 'curvefitoffset', 'segmentresultsloc_default', 'segmentresultsloc',
        'segmentpickflag', 'segmentdeltathreshold', 'segmentsamplesthreshold', 'stats_summary_rect', 'title_text', 'title_artist', 'title_width',
        'background_title_width', 'xlabel_text', 'xlabel_artist', 'xlabel_width', 'lazyredraw_on_resize_timer', 'mathdictionary_base',
        'ambient_pressure_sampled', 'ambient_humidity_sampled', 'ambientTemp_sampled', 'backgroundmovespeed', 'chargeTimerPeriod', 'flavors_default_value',
        'fmt_data_ON', 'l_subtitle', 'projectDeltaFlag', 'weight_units']


    def __init__(self, parent, dpi, locale, aw:'ApplicationWindow') -> None:

        self.aw = aw

        #default palette of colors
        self.locale_str:str = locale
        self.alpha:Dict[str,float] = {'analysismask':0.4,'statsanalysisbkgnd':1.0,'legendbg':0.4}
        self.palette:Dict[str,str] = {'background':'#FFFFFF','grid':'#E5E5E5','ylabel':'#808080','xlabel':'#808080','title':'#0C6AA6', 'title_focus':'#cc0f50',
                        'rect1':'#E5E5E5','rect2':'#B2B2B2','rect3':'#E5E5E5','rect4':'#BDE0EE','rect5':'#D3D3D3',
                        'et':'#cc0f50','bt':'#0A5C90','xt':'#404040','yt':'#404040','deltaet':'#cc0f50',
                        'deltabt':'#0A5C90','markers':'#000000','text':'#000000','watermarks':'#FFFF00','timeguide':'#0A5C90',
                        'canvas':'#F8F8F8','legendbg':'#FFFFFF','legendborder':'#A9A9A9',
                        'specialeventbox':'#FF5871','specialeventtext':'#FFFFFF',
                        'bgeventmarker':'#7F7F7F','bgeventtext':'#000000',
                        'mettext':'#FFFFFF','metbox':'#CC0F50',
                        'aucguide':'#0C6AA6','messages':'#000000','aucarea':'#767676',
                        'analysismask':'#BABABA','statsanalysisbkgnd':'#FFFFFF'}
        self.palette1 = self.palette.copy()
        self.EvalueColor_default:Final[List[str]] = ['#43A7CF','#49B160','#800080','#AD0427']
        self.EvalueTextColor_default:Final[List[str]] = ['white','#FFFFFF','white','#FFFFFF']

        # standard math functions allowed in symbolic formulas
        self.mathdictionary_base = {
            'min':min,'max':max,'sin':math.sin,'cos':math.cos,'tan':math.tan,
            'pow':math.pow,'exp':math.exp,'pi':math.pi,'e':math.e,
            'abs':abs,'acos':math.acos,'asin':math.asin,'atan':math.atan,
            'log':math.log,'radians':math.radians,
            'sqrt':math.sqrt,'degrees':math.degrees}


        self.artisanflavordefaultlabels: Final[List[str]] = [QApplication.translate('Textbox', 'Acidity'),
                                            QApplication.translate('Textbox', 'Aftertaste'),
                                            QApplication.translate('Textbox', 'Clean Cup'),
                                            QApplication.translate('Textbox', 'Head'),
                                            QApplication.translate('Textbox', 'Fragrance'),
                                            QApplication.translate('Textbox', 'Sweetness'),
                                            QApplication.translate('Textbox', 'Aroma'),
                                            QApplication.translate('Textbox', 'Balance'),
                                            QApplication.translate('Textbox', 'Body')]

        # custom labels are stored in the application settings and can be edited by the user
        self.customflavorlabels = self.artisanflavordefaultlabels

# old SCAA spec (note the typo in the variable name):
# replaced by the specification below for v2.6.0:
#        self.SCCAflavordefaultlabels: Final[List[str]] = [[QApplication.translate("Textbox", "Sour"),
#                                        QApplication.translate("Textbox", "Flavor"),
#                                        QApplication.translate("Textbox", "Critical\nStimulus"),
#                                        QApplication.translate("Textbox", "Aftertaste"),
#                                        QApplication.translate("Textbox", "Bitter"),
#                                        QApplication.translate("Textbox", "Astringency"),
#                                        QApplication.translate("Textbox", "Solubles\nConcentration"),
#                                        QApplication.translate("Textbox", "Mouthfeel"),
#                                        QApplication.translate("Textbox", "Other"),
#                                        QApplication.translate("Textbox", "Aromatic\nComplexity"),
#                                        QApplication.translate("Textbox", "Roast\nColor"),
#                                        QApplication.translate("Textbox", "Aromatic\nPungency"),
#                                        QApplication.translate("Textbox", "Sweet"),
#                                        QApplication.translate("Textbox", "Acidity"),
#                                        QApplication.translate("Textbox", "pH"),
#                                        QApplication.translate("Textbox", "Balance")]

        self.SCAAflavordefaultlabels: Final[List[str]] = [QApplication.translate('Textbox', 'Fragrance-Aroma'),
                                        QApplication.translate('Textbox', 'Flavor'),
                                        QApplication.translate('Textbox', 'Aftertaste'),
                                        QApplication.translate('Textbox', 'Acidity'),
                                        QApplication.translate('Textbox', 'Body'),
                                        QApplication.translate('Textbox', 'Uniformity'),
                                        QApplication.translate('Textbox', 'Balance'),
                                        QApplication.translate('Textbox', 'Clean Cup'),
                                        QApplication.translate('Textbox', 'Sweetness'),
                                        QApplication.translate('Textbox', 'Overall')]

        self.SCAflavordefaultlabels: Final[List[str]] = [QApplication.translate('Textbox', 'Fragrance-Aroma'),
                                        QApplication.translate('Textbox', 'Flavor'),
                                        QApplication.translate('Textbox', 'Aftertaste'),
                                        QApplication.translate('Textbox', 'Acidity'),
                                        QApplication.translate('Textbox', 'Intensity'),
                                        QApplication.translate('Textbox', 'Body'),
                                        QApplication.translate('Textbox', 'Uniformity'),
                                        QApplication.translate('Textbox', 'Balance'),
                                        QApplication.translate('Textbox', 'Clean Cup'),
                                        QApplication.translate('Textbox', 'Sweetness'),
                                        QApplication.translate('Textbox', 'Overall')]

        self.CQIflavordefaultlabels: Final[List[str]] = [QApplication.translate('Textbox', 'Fragance'),
                                        QApplication.translate('Textbox', 'Aroma'),
                                        QApplication.translate('Textbox', 'Flavor'),
                                        QApplication.translate('Textbox', 'Acidity'),
                                        QApplication.translate('Textbox', 'Body'),
                                        QApplication.translate('Textbox', 'Aftertaste')]

        self.SweetMariasflavordefaultlabels: Final[List[str]] = [QApplication.translate('Textbox', 'Dry Fragrance'),
                                            QApplication.translate('Textbox', 'Uniformity'),
                                            QApplication.translate('Textbox', 'Complexity'),
                                            QApplication.translate('Textbox', 'Clean Cup'),
                                            QApplication.translate('Textbox', 'Sweetness'),
                                            QApplication.translate('Textbox', 'Finish'),
                                            QApplication.translate('Textbox', 'Body'),
                                            QApplication.translate('Textbox', 'Flavor'),
                                            QApplication.translate('Textbox', 'Brightness'),
                                            QApplication.translate('Textbox', 'Wet Aroma')]

        self.Cflavordefaultlabels: Final[List[str]] = [QApplication.translate('Textbox', 'Fragrance'),
                                            QApplication.translate('Textbox', 'Aroma'),
                                            QApplication.translate('Textbox', 'Taste'),
                                            QApplication.translate('Textbox', 'Nose'),
                                            QApplication.translate('Textbox', 'Aftertaste'),
                                            QApplication.translate('Textbox', 'Body'),
                                            QApplication.translate('Textbox', 'Acidity')]

        self.Eflavordefaultlabels: Final[List[str]] = [QApplication.translate('Textbox', 'Fragrance-Aroma'),
                                            QApplication.translate('Textbox', 'Acidity'),
                                            QApplication.translate('Textbox', 'Flavor'),
                                            QApplication.translate('Textbox', 'Body'),
                                            QApplication.translate('Textbox', 'Aftertaste'),
                                            QApplication.translate('Textbox', 'Balance')]


        self.coffeegeekflavordefaultlabels: Final[List[str]] = [QApplication.translate('Textbox', 'Aroma'),
                                            QApplication.translate('Textbox', 'Acidity'),
                                            QApplication.translate('Textbox', 'Mouthfeel'),
                                            QApplication.translate('Textbox', 'Flavour'),
                                            QApplication.translate('Textbox', 'Aftertaste'),
                                            QApplication.translate('Textbox', 'Balance')]

        self.Intelligentsiaflavordefaultlabels: Final[List[str]] = [QApplication.translate('Textbox', 'Sweetness'),
                                            QApplication.translate('Textbox', 'Acidity'),
                                            QApplication.translate('Textbox', 'Body'),
                                            QApplication.translate('Textbox', 'Finish')]

        self.IstitutoInternazionaleAssaggiatoriCaffe: Final[List[str]] = [QApplication.translate('Textbox', 'Roast Color'),
                                            QApplication.translate('Textbox', 'Crema Texture'),
                                            QApplication.translate('Textbox', 'Crema Volume'),
                                            QApplication.translate('Textbox', 'Fragrance'),
                                            QApplication.translate('Textbox', 'Body'),
                                            QApplication.translate('Textbox', 'Acidity'),
                                            QApplication.translate('Textbox', 'Bitterness'),
                                            QApplication.translate('Textbox', 'Defects'),
                                            QApplication.translate('Textbox', 'Aroma Intensity'),
                                            QApplication.translate('Textbox', 'Aroma Persistence'),
                                            QApplication.translate('Textbox', 'Balance')]

        self.WorldCoffeeRoastingChampionship: Final[List[str]] = [QApplication.translate('Textbox', 'Aroma'),
                                            QApplication.translate('Textbox', 'Flavour'),
                                            QApplication.translate('Textbox', 'Aftertaste'),
                                            QApplication.translate('Textbox', 'Acidity'),
                                            QApplication.translate('Textbox', 'Body'),
                                            QApplication.translate('Textbox', 'Sweetness'),
                                            QApplication.translate('Textbox', 'Sweetness'),
                                            QApplication.translate('Textbox', 'Balance'),
                                            QApplication.translate('Textbox', 'Balance'),
                                            QApplication.translate('Textbox', 'Overall')]

        self.ax1:Optional['Axes'] = None
        self.ax2:Optional['Axes'] = None

        # Ambient Data Worker and Thread
        self.ambiWorker:Optional[AmbientWorker] = None
        self.ambiThread:Optional[QThread] = None

        # used by sample_processing
        self.afterTP:bool = False
        self.decay_weights:Optional[List[int]] = None
        self.temp_decay_weights:Optional[List[int]] = None

        self.flavorlabels = list(self.artisanflavordefaultlabels)
        #Initial flavor parameters.
        self.flavors_default_value:float = 5.
        self.flavors:List[float] = [5.]*len(self.flavorlabels)
        self.flavorstartangle:float = 90.
        self.flavoraspect:float = 1.0  #aspect ratio
        # flavor chart graph plots and annotations
        self.flavorchart_plotf:Optional[List[float]] = None
        self.flavorchart_angles:Optional[List[float]] = None
        self.flavorchart_plot:Optional['Line2D'] = None
        self.flavorchart_fill:Optional['PolyCollection'] = None
        self.flavorchart_labels:Optional[List['Annotation']] = None
        self.flavorchart_total:Optional['Text'] = None

        #F = Fahrenheit; C = Celsius
        self.mode:str = 'F'
        if platform.system() == 'Darwin':
            # try to "guess" the users preferred temperature unit
            try:
                if QSettings().value('AppleTemperatureUnit') == 'Celsius':
                    self.mode = 'C'
            except Exception: # pylint: disable=broad-except
                pass

        self.mode_tempsliders = self.mode # the temperature mode of event slider to convert min/max limits

        self.errorlog:List[str] = []

        # default delay between readings in milliseconds
        self.default_delay: Final[int] = 2000 # default 2s
        self.delay:int = self.default_delay
        self.min_delay: Final[int] = 250 #500 # 1000 # Note that a 0.25s min delay puts a lot of performance pressure on the app

        # extra event sampling interval in milliseconds. If 0, then extra sampling commands are sent "in sync" with the standard sampling commands
        self.extra_event_sampling_delay:int = 0 # sync, 0.5s, 1.0s, 1.5s,.., 5s => 0, 500, 1000, 1500, .. # 0, 500, 1000, 1500, ...

        #watermarks limits: dryphase1, dryphase2 (DRY), midphase (FCs), and finish phase Y limits
        self.phases_fahrenheit_defaults: Final[List[int]] = [300,300,390,450]
        self.phases_celsius_defaults: Final[List[int]] = [150,150,200,230]
        self.phases:List[int] = self.phases_fahrenheit_defaults # contains either the phases_filter or phases_espresso, depending on the mode
        #this flag makes the main push buttons DryEnd, and FCstart change the phases[1] and phases[2] respectively
        self.phasesbuttonflag:bool = True #False no change; True make the DRY and FC buttons change the phases during roast automatically
        self.phasesfromBackgroundflag:bool = False # False: no change; True: set phases from background profile on load
        self.watermarksflag:bool = True
        self.step100temp:Optional[int] = None # if set to a temperature value, the 100% event value in step modes is aligned with the given temperature, otherwise with the lowest phases limit

        #show phases LCDs during roasts
        self.phasesLCDflag:bool = True
        self.phasesLCDmode = 1 # one of 0: time, 1: percentage, 2: temp mode
        self.phasesLCDmode_l = [1,1,1]
        self.phasesLCDmode_all:List[bool] = [False,False,True]


        #statistics flags selects to display: stat. time, stat. bar, (stat. flavors), stat. area, stat. deg/min, stat. ETBTarea
        # NOTE: stat. flavors not used anymore. The code has been removed.
        #       statisticsflags[5] area is not used anymore
        self.statisticsflags = [1,1,0,1,0,0,1]
        self.statisticsmode = 1 # one of 0: standard computed values, 1: roast properties, 2: total energy/CO2 data, 3: just roast energy/CO2 data

        # Area Under Curve (AUC)
        self.AUCbegin:int = 1 # counting begins after 0: CHARGE, 1: TP (default), 2: DE, 3: FCs
        self.AUCbase:float = 212 # base temperature above which the area is calculated (default 212F/110C)
        self.AUCbaseFlag:bool = False # if True, base AUC is taken from BT at AUCbegin event
        self.AUCtarget:int = 640 # target AUC for prediction
        self.AUCbackground:float = -1 # AUC of background profile or -1 if none loaded
        self.AUCtargetFlag:bool = False # if True, target is taken from the background else from self.AUCtarget
        self.AUCguideFlag:bool = False # if True a prediction line is drawn at the time the target area is reached considering current RoR
        self.AUClcdFlag:bool = False # if True a AUC LCD is displayed next to the phases LCDs to show current AUC or AUC difference to target
        self.AUCLCDmode:int = 0 # one of 0: abs value, 1: delta to target/background, 2: AUC since FCs
        self.AUCvalue:float = 0 # the running AUC value calculated during recording
        self.AUCsinceFCs:float = 0 # the running AUC since FCs calculated during recording
        self.AUCguideTime:float = 0 # the expected time in seconds the AUC target is reached (calculated by the AUC guide mechanism)
        self.AUCshowFlag:bool = False

        # timing statistics on loaded profile
        self.statisticstimes:List[float] = [0,0,0,0,0] # total, dry phase, mid phase, finish phase  and cooling phase times

        #DEVICES
        self.device:int = 18                                    # default device selected to None (18). Calls appropriate function

        self.device_logging:bool = False # turn on/off device debug logging (MODBUS, ..) # Note that MODBUS log messages are written to the main artisan log file
        # Phidget messages are logged to the artisan device log
        self.device_log_file_name = 'artisan_device'
        self.device_log_file = getDirectory(self.device_log_file_name,'.log')

        # Phidget variables

        self.phidget_dataRatesStrings : Final[List[str]] = ['32ms','64ms','128ms','256ms','512ms','768ms','1s'] # too fast: "8ms","16ms","32ms","64ms","0.12s",
        self.phidget_dataRatesValues : Final[List[int]] = [32,64,128,256,512,768,1024] # 8,16,32,64,128,

        # probe type values (along the Phidgets21 lib): k-type => 1, j-type => 2, e-type => 3, t-type => 4
        # Artisan will keep on using the Phidgets21 mapping
        self.phidget1048_types:List[int] = [1,1,1,1] # defaults all to k-type probes (values are 0-based)
        self.phidget1048_async:List[bool] = [False]*4
        self.phidget1048_changeTriggers:List[float] = [0]*4
        self.phidget1048_changeTriggersValues:List[float] = [x / 10.0 for x in range(0, 11, 1)]
        self.phidget1048_changeTriggersStrings:List[str] = [f'{x:.1f}C' for x in  self.phidget1048_changeTriggersValues]
        # add 0.02C and 0.05C change triggers
        self.phidget1048_changeTriggersValues.insert(1,0.05)
        self.phidget1048_changeTriggersValues.insert(1,0.02)
        self.phidget1048_changeTriggersStrings.insert(1,'0.05C')
        self.phidget1048_changeTriggersStrings.insert(1,'0.02C')
        self.phidget1048_dataRate = 256 # in ms; (Phidgets default 8ms, 16ms if wireless is active on v21 API, 256ms on v22 API)

        self.phidget1045_async:bool = False
        self.phidget1045_changeTrigger:float = 0.
        self.phidget1045_changeTriggersValues = [x / 10.0 for x in range(0, 11, 1)]
        self.phidget1045_changeTriggersStrings = [f'{x}C' for x in self.phidget1045_changeTriggersValues]
        # add 0.02C and 0.05C change triggers
        self.phidget1045_changeTriggersValues.insert(1,0.05)
        self.phidget1045_changeTriggersValues.insert(1,0.02)
        self.phidget1045_changeTriggersStrings.insert(1,'0.05C')
        self.phidget1045_changeTriggersStrings.insert(1,'0.02C')
        self.phidget1045_emissivity = 1.0
        self.phidget1045_dataRate = 256

        self.phidget1200_async:bool = False
        self.phidget1200_formula:int = 0
        self.phidget1200_formulaValues: Final[List[str]] = ['PT100  3850', 'PT100  3920','PT1000 3850', 'PT1000 3920']
        self.phidget1200_wire:int = 0
        self.phidget1200_wireValues: Final[List[str]] = ['2-wire', '3-wire','4-wire']
        self.phidget1200_changeTrigger:float = 0
        self.phidget1200_changeTriggersValues: List[float] = [x / 10.0 for x in range(0, 11, 1)]
        self.phidget1200_changeTriggersStrings: List[str] = [f'{x}C' for x in self.phidget1200_changeTriggersValues]

        # add 0.02C and 0.05C change triggers
        self.phidget1200_changeTriggersValues.insert(1,0.05)
        self.phidget1200_changeTriggersValues.insert(1,0.02)
        self.phidget1200_changeTriggersValues.insert(1,0.01)
        self.phidget1200_changeTriggersValues.insert(1,0.005)
        self.phidget1200_changeTriggersStrings.insert(1,'0.05C')
        self.phidget1200_changeTriggersStrings.insert(1,'0.02C')
        self.phidget1200_changeTriggersStrings.insert(1,'0.01C')
        self.phidget1200_changeTriggersStrings.insert(1,'0.005C')
        self.phidget1200_dataRate:int = 340
        self.phidget1200_dataRatesStrings: Final[List[str]] = ['340ms','500ms','750ms','1s']
        self.phidget1200_dataRatesValues: Final[List[int]] = [340,500,700,1024]

        self.phidget1200_2_async:bool = False
        self.phidget1200_2_formula:int = 0
        self.phidget1200_2_wire:int = 0
        self.phidget1200_2_changeTrigger:float = 0
        self.phidget1200_2_dataRate:int = 340

        self.phidget1046_async: List[bool] = [False]*4
        self.phidget1046_gain: List[int] = [2]*4 # defaults to gain 8 (values are 1-based index into gainValues) # 0 is not value
        self.phidget1046_gainValues: Final[List[str]] = ['1', '8','16','32','64','128'] # 1 for no gain
        self.phidget1046_formula: List[int] = [1]*4 # 0: 1K Ohm Wheatstone Bridge, 1: 1K Ohm Voltage Divider, 2: raw
        self.phidget1046_formulaValues: Final[List[str]] = ['WS', 'Div','raw']
        self.phidget1046_dataRate:int = 256 # in ms; (Phidgets default 8ms, 16ms if wireless is active)

        self.phidgetRemoteFlag:bool = False # if True the specified remote server is harvestd to potentially attached Phidget devices
        self.phidgetRemoteOnlyFlag:bool = False # if True only Phidgets attached to remote servers are attached
        self.phidgetServerID:str = ''
        self.phidgetPassword:str = ''
        self.phidgetPort:int = 5661
        self.phidgetServerAdded:bool = False # this should be set on PhidgetNetwork.addServer and cleared on PhidgetNetwork.removeServer
        self.phidgetServiceDiscoveryStarted:bool = False # this should be set on PhidgetNetwork.addServer and cleared on PhidgetNetwork.removeServer
        self.phidgetManager:Optional[PhidgetManager] = None

        self.yoctoRemoteFlag:bool = False
        self.yoctoServerID = '127.0.0.1'
        self.YOCTOchanUnit = 'C' # indicates the unit ("C" or "F") of the readings as received from the device
        self.YOCTOchan1Unit = 'C' # indicates the unit ("C" or "F") of the readings as received from the device
        self.YOCTOchan2Unit = 'C' # indicates the unit ("C" or "F") of the readings as received from the device
        self.YOCTO_emissivity = 1.0
        self.YOCTO_async = [False]*2
        self.YOCTO_dataRate = 256 # in ms
        self.YOCTO_dataRatesStrings: Final[List[str]] = ['32ms','64ms','128ms','256ms','512ms','768ms','1s','1s*']
        self.YOCTO_dataRatesValues: Final[List[int]] = [32,64,128,256,512,768,1000,1024] # the 1024 mode returns every sec an average over the period, while 1000 returns every second the last sample

        self.phidget1018valueFactor = 1000 # we map the 0-5V voltage returned by the Phidgets22 API to mV (0-5000)
        self.phidget1018_async = [False]*8
        self.phidget1018_ratio = [False]*8 # if True VoltageRatio instead of VoltageInput is returned
        self.phidget1018_dataRates = [256]*8 # in ms; (Phidgets default 256ms, min is 8ms, 16ms if wireless is active), max 1000ms
                # with the new PhidgetsAPI the 1011/1018 dataRate is from 1ms to 1.000ms
        self.phidget1018_changeTriggers = [10]*8
        self.phidget1018_changeTriggersValues: Final[List[int]] = list(range(0,51,1))
        self.phidget1018_changeTriggersStrings: Final[List[str]] = [f'{x*10}mV' for x in self.phidget1018_changeTriggersValues]

        self.phidgetVCP100x_voltageRanges: List[int] = [VoltageRange.VOLTAGE_RANGE_AUTO]*8
        self.phidgetVCP100x_voltageRangeValues: Final[List[int]] = [
            VoltageRange.VOLTAGE_RANGE_AUTO,
            VoltageRange.VOLTAGE_RANGE_10mV,
            VoltageRange.VOLTAGE_RANGE_40mV,
            VoltageRange.VOLTAGE_RANGE_200mV,
            VoltageRange.VOLTAGE_RANGE_312_5mV,
            VoltageRange.VOLTAGE_RANGE_400mV,
            VoltageRange.VOLTAGE_RANGE_1000mV,
            VoltageRange.VOLTAGE_RANGE_2V,
            VoltageRange.VOLTAGE_RANGE_5V,
            VoltageRange.VOLTAGE_RANGE_15V,
            VoltageRange.VOLTAGE_RANGE_40V
        ]
        self.phidgetVCP100x_voltageRangeStrings: Final[List[str]] = [
            'Auto',
            '±10mV',
            '±40mV',
            '±200mV',
            '±312.5mV',
            '±400mV',
            '±1000mV',
            '±2V',
            '±5V',
            '±15V',
            '±40V'
        ]

        self.phidgetDAQ1400_powerSupplyStrings: Final[List[str]] = ['--','12V','24V']
        self.phidgetDAQ1400_powerSupply:int = 1
        self.phidgetDAQ1400_inputModeStrings: Final[List[str]] = ['NPN','PNP']
        self.phidgetDAQ1400_inputMode:int = 0

        #menu of thermocouple devices
        #device with first letter + only shows in extra device tab
        #device with first letter - does not show in any tab (but its position in the list is important)
        # device labels (used in Dialog config).

        # ADD DEVICE: to add a device you have to modify several places. Search for the tag "ADD DEVICE:" in the code
        # (check also the tags in comm.py and devices.py!!)
        # - add to self.devices
        self.devices: Final[List[str]] = [#Fuji PID        #0
                       'Omega HH806AU',         #1
                       'Omega HH506RA',         #2
                       'CENTER 309',            #3
                       'CENTER 306',            #4
                       'CENTER 305',            #5
                       'CENTER 304',            #6
                       'CENTER 303',            #7
                       'CENTER 302',            #8
                       'CENTER 301',            #9
                       'CENTER 300',            #10
                       'VOLTCRAFT K204',        #11
                       'VOLTCRAFT K202',        #12
                       'VOLTCRAFT 300K',        #13
                       'VOLTCRAFT 302KJ',       #14
                       'EXTECH 421509',         #15
                       'Omega HH802U',          #16
                       'Omega HH309',           #17
                       'NONE',                  #18
                       '-ARDUINOTC4',           #19
                       'TE VA18B',              #20
                       '+CENTER 309 34',        #21
                       '+PID SV/DUTY %',        #22
                       'Omega HHM28[6]',        #23
                       '+VOLTCRAFT K204 34',    #24
                       '+Virtual',              #25
                       '-DTAtemperature',       #26
                       'Program',               #27
                       '+ArduinoTC4 34',        #28
                       'MODBUS',                #29
                       'VOLTCRAFT K201',        #30
                       'Amprobe TMD-56',        #31
                       '+ArduinoTC4 56',        #32
                       '+MODBUS 34',            #33
                       'Phidget 1048 4xTC 01',  #34
                       '+Phidget 1048 4xTC 23', #35
                       '+Phidget 1048 4xTC AT', #36
                       'Phidget 1046 4xRTD 01', #37
                       '+Phidget 1046 4xRTD 23',#38
                       'Mastech MS6514',        #39
                       'Phidget IO 01',         #40
                       '+Phidget IO 23',        #41
                       '+Phidget IO 45',        #42
                       '+Phidget IO 67',        #43
                       '+ArduinoTC4 78',        #44
                       'Yocto Thermocouple',    #45
                       'Yocto PT100',           #46
                       'Phidget 1045 IR',       #47
                       '+Program 34',           #48
                       '+Program 56',           #49
                       'DUMMY',                 #50
                       '+CENTER 304 34',        #51
                       'Phidget 1051 1xTC 01',  #52
                       'Hottop BT/ET',          #53
                       '+Hottop Heater/Fan',    #54
                       '+MODBUS 56',            #55
                       'Apollo DT301',          #56
                       'EXTECH 755',            #57
                       'Phidget TMP1101 4xTC 01',  #58
                       '+Phidget TMP1101 4xTC 23', #59
                       '+Phidget TMP1101 4xTC AT', #60
                       'Phidget TMP1100 1xTC',  #61
                       'Phidget 1011 IO 01',    #62
                       'Phidget HUB IO 01', #63
                       '+Phidget HUB IO 23',#64
                       '+Phidget HUB IO 45',#65
                       '-Omega HH806W',         #66 NOT WORKING
                       'VOLTCRAFT PL-125-T2',   #67
                       'Phidget TMP1200 1xRTD A', #68
                       'Phidget IO Digital 01',         #69
                       '+Phidget IO Digital 23',        #70
                       '+Phidget IO Digital 45',        #71
                       '+Phidget IO Digital 67',        #72
                       'Phidget 1011 IO Digital 01',    #73
                       'Phidget HUB IO Digital 01', #74
                       '+Phidget HUB IO Digital 23',#75
                       '+Phidget HUB IO Digital 45',#76
                       'VOLTCRAFT PL-125-T4',       #77
                       '+VOLTCRAFT PL-125-T4 34',   #78
                       'S7',                        #79
                       '+S7 34',                    #80
                       '+S7 56',                    #81
                       '+S7 78',                    #82
                       'Aillio Bullet R1 BT/DT',             #83
                       '+Aillio Bullet R1 Heater/Fan',       #84
                       '+Aillio Bullet R1 BT RoR/Drum',      #85
                       '+Aillio Bullet R1 Voltage/Exhaust',  #86
                       '+Aillio Bullet R1 State/Fan RPM',    #87
                       '+Program 78',               #88
                       '+Program 910',              #89
                       '+Slider 01',                #90
                       '+Slider 23',                #91
                       '-Probat Middleware',                 #92
                       '-Probat Middleware burner/drum',     #93
                       '-Probat Middleware fan/pressure',    #94
                       'Phidget DAQ1400 Current',   #95
                       'Phidget DAQ1400 Frequency', #96
                       'Phidget DAQ1400 Digital',   #97
                       'Phidget DAQ1400 Voltage',   #98
                       'Aillio Bullet R1 IBTS/BT',  #99
                       'Yocto IR',                  #100
                       'Behmor BT/CT',              #101
                       '+Behmor 34',                #102
                       'VICTOR 86B',                #103
                       '+Behmor 56',                #104
                       '+Behmor 78',                #105
                       'Phidget HUB IO 0',          #106
                       'Phidget HUB IO Digital 0',  #107
                       'Yocto 4-20mA Rx',           #108
                       '+MODBUS 78',                #109
                       '+S7 910',                   #110
                       'WebSocket',                 #111
                       '+WebSocket 34',             #112
                       '+WebSocket 56',             #113
                       '+Phidget TMP1200 1xRTD B',  #114
                       'HB BT/ET',                  #115
                       '+HB DT/IT',                 #116
                       '+HB AT',                    #117
                       '+WebSocket 78',             #118
                       '+WebSocket 910',            #119
                       'Yocto 0-10V Rx',            #120
                       'Yocto milliVolt Rx',        #121
                       'Yocto Serial',              #122
                       'Phidget VCP1000',           #123
                       'Phidget VCP1001',           #124
                       'Phidget VCP1002',           #125
                       'ARC BT/ET',                 #126
                       '+ARC MET/IT',               #127
                       '+ARC AT',                   #128
                       'Yocto Power',               #129
                       'Yocto Energy',              #130
                       'Yocto Voltage',             #131
                       'Yocto Current',             #132
                       'Yocto Sensor',              #133
                       'Santoker BT/ET',            #134
                       '+Santoker Power/Fan',       #135
                       '+Santoker Drum',            #136
                       'Phidget DAQ1500'            #137
                       ]

        # ADD DEVICE:
        # ids of (main) Phidget devices (without a + in front of their name string)
        self.phidgetDevices : Final[List[int]] = [
            34, # Phidget 1048
            37, # Phidget 1046
            40, # Phidget IO
            47, # Phidget 1045
            52, # Phidget 1051
            58, # Phidget TMP1101
            61, # Phidget TMP1100
            62, # Phidget 1011
            63, # Phidget HUB IO 01
            68, # Phidget TMP1200
            69, # Phidget IO Digital
            73, # Phidget 1011 IO Digital
            74, # Phidget HUB IO Digital 01
            95, # Phidget DAQ1400 Current
            96, # Phidget DAQ1400 Frequency
            97, # Phidget DAQ1400 Digital
            98, # Phidget DAQ1400 Voltage
            106, # Phidget HUB IO 0
            107, # Phidget HUB IO Digital 0
            123, # Phidget VCP1000
            124, # Phidget VCP1001
            125, # Phidget VCP1002
            137  # Phidget DAQ1500
        ]

        # ADD DEVICE:
        # ids of (main) devices (without a + in front of their name string)
        # that do NOT communicate via any serial port thus do not need any serial port configuration
        self.nonSerialDevices : Final[List[int]] = self.phidgetDevices + [
            27, # Program
            45, # Yocto Thermocouple
            46, # Yocto PT100
            79, # S7
            83, # Aillio Bullet R1 BT/DT
            99, # Aillio Bullet R1 IBTS/BT
            100, # Yocto IR
            108, # Yocto 4-20mA Rx
            111, # WebSocket
            120, # Yocto-0-10V-Rx
            121, # Yocto-milliVolt-Rx
            122, # Yocto-Serial
            129, # Yocto Power
            130, # Yocto Energy
            131, # Yocto Voltage
            132, # Yocto Current
            133, # Yocto Sensor
            134  # Santoker BT/ET
        ]

        # ADD DEVICE:
        # ids of devices temperature conversions should not be applied
        self.nonTempDevices : Final[List[int]] = [
            22, # +PID SV/DUTY %
            25, # +Virtual
            40, # Phidget IO 01
            41, # +Phidget IO 23
            42, # +Phidget IO 45
            43, # +Phidget IO 67
            50, # DUMMY
            54, # +Hottop Heater/Fan
            57, # EXTECH 755
            62, # Phidget 1011 IO 01
            63, # Phidget HUB IO 01
            64, # +Phidget HUB IO 23
            65, # +Phidget HUB IO 45
            69, # Phidget IO Digital 01
            70, # +Phidget IO Digital 23
            71, # +Phidget IO Digital 45
            72, # +Phidget IO Digital 67
            73, # Phidget 1011 IO Digital 01
            74, # Phidget HUB IO Digital 0
            75, # +Phidget HUB IO Digital 23
            76, # +Phidget HUB IO Digital 45
            84, # +Aillio Bullet R1 Heater/Fan
            87, # +Aillio Bullet R1 State
            90, # +Slider 01
            91, # +Slider 23
            95, # Phidget DAQ1400 Current
            96, # Phidget DAQ1400 Frequency
            97, # Phidget DAQ1400 Digital
            98, # Phidget DAQ1400 Voltage
            106, # Phidget HUB IO 0
            107, # Phidget HUB IO Digital 0
            108, # Yocto 4-20mA Rx
            120, # Yocto-0-10V-Rx
            121, # Yocto-milliVolt-Rx
            122, # Yocto-Serial
            123, # Phidget VCP1000
            124, # Phidget VCP1001
            125, # Phidget VCP1002
            129, # Yocto Power
            130, # Yocto Energy
            131, # Yocto Voltage
            132, # Yocto Current
            133, # Yocto Sensor
            135, # Santoker Power/Fan
            136, # Santoker Drum
            137  # Phidget DAQ1500
        ]

        #extra devices
        self.extradevices:List[int] = []                            # list with indexes for extra devices
        self.extratimex:List[List[float]] = []                      # individual time for each extra device (more accurate). List of lists (2 dimension)
        self.extradevicecolor1:List[str] = []                       # extra line 1 color. list with colors.
        self.extradevicecolor2:List[str] = []                       # extra line 2 color. list with colors.
        self.extratemp1:List[List[float]] = []                      # extra temp1. List of lists
        self.extratemp2:List[List[float]] = []                      # extra temp2. List of lists
        self.extrastemp1:List[List[float]] = []                     # smoothed extra temp1. List of lists
        self.extrastemp2:List[List[float]] = []                     # smoothed extra temp2. List of lists
        # variants of extratimex/extratemp1/extratemp2 with -1 dropout values removed (or replaced by None)
        self.extractimex1:List[List[float]] = []
        self.extractimex2:List[List[float]] = []
        self.extractemp1:List[List[Optional[float]]] = []
        self.extractemp2:List[List[Optional[float]]] = []
        # NOTE: those extractimexN, extractempBN lists can be shorter than the regular extratimexN, extratempN lists,
        # however, the invariants len(extractimex1) = len(extractemp1) and len(extractimex2) = len(extractemp2) always hold
        self.extratemp1lines:List['Line2D'] = []                      # lists with extra lines for speed drawing
        self.extratemp2lines:List['Line2D'] = []
        self.extraname1:List[str] = []                              # name of labels for line (like ET or BT) - legend
        self.extraname2:List[str] = []
        self.extramathexpression1:List[str] = []                    # list with user defined math evaluating strings. Example "2*cos(x)"
        self.extramathexpression2:List[str] = []
        self.extralinestyles1:List[str] = []                        # list of extra curve line styles
        self.extralinestyles2:List[str] = []                        # list of extra curve line styles
        self.extradrawstyles1:List[str] = []                        # list of extra curve drawing styles
        self.extradrawstyles2:List[str] = []                        # list of extra curve drawing styles
        self.extralinewidths1:List[float] = []                      # list of extra curve 1 linewidth
        self.extralinewidths2:List[float] = []                      # list of extra curve 2 linewidth
        self.extramarkers1: List[str] = []                          # list of extra curve marker styles
        self.extramarkers2: List[str] = []                          # list of extra curve marker styles
        self.extramarkersizes1: List[float] = []                    # list of extra curve marker size
        self.extramarkersizes2: List[float] = []                    # list of extra curve marker size

        self.devicetablecolumnwidths:List[int] = []

        # the following two list are generated on ON from the extradevices types and might be longer or smaller than len(self.extradevices)
        # if no entry is available, a temperature curve that needs C<->F translation is assumed
        # note that ET/BT main curves are assumed to always hold temperatures
        self.extraNoneTempHint1:List[bool] = []                                # list of flags indicating which extra 1 curves are not holding temperature values
        self.extraNoneTempHint2:List[bool] = []                                # list of flags indicating which extra 2 curves are not holding temperature values

        #holds math expressions to plot
        self.plotcurves:List[str]=['']*9
        self.plotcurvecolor:List[str] = ['black']*9

        self.overlapList:List[Tuple[float,float,float,float]] = []

        self.tight_layout_params: Final[Dict[str,float]] = {'pad':.3,'h_pad':0.0,'w_pad':0.0} # slightly less space for axis labels
        self.fig:Figure = Figure(tight_layout=self.tight_layout_params,frameon=True,dpi=dpi)
        # with tight_layout=True, the matplotlib canvas expands to the maximum using figure.autolayout

        self.fig.patch.set_facecolor(str(self.palette['canvas']))

        self.ax:Optional['Axes']
        self.ax = self.fig.add_subplot(111,facecolor=self.palette['background'])
        self.delta_ax:Optional['Axes'] = self.ax.twinx()

        #legend location
        self.legendloc:int = 7
        self.legendloc_pos:Optional[Tuple[float,float]] = None # holds the custom position of the legend set on profile load and reset after first redraw

        self.fig.subplots_adjust(
            # all values in percent
            top=0.93, # the top of the subplots of the figure (default: 0.9)
            bottom=0.1, # the bottom of the subplots of the figure (default: 0.1)
            left=0.067, # the left side of the subplots of the figure (default: 0.125)
            right=.925) # the right side of the subplots of the figure (default: 0.9
        FigureCanvas.__init__(self, self.fig)

        self.fig.canvas.set_cursor = lambda _: None # deactivate the busy cursor on slow full redraws

        # important to make the Qt canvas transparent (note that this changes stylesheets of children like popups too!):
        self.fig.canvas.setStyleSheet('background-color:transparent;') # default is white

        self.onclick_cid = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        self.oncpick_cid = self.fig.canvas.mpl_connect('pick_event', self.onpick)
        self.ondraw_cid = self.fig.canvas.mpl_connect('draw_event', self._draw_event)

        self.fig.canvas.mpl_connect('button_release_event', self.onrelease_after_pick)

        # set the parent widget
        self.setParent(parent)
        # we define the widget as
        FigureCanvas.setSizePolicy(self,QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)  #@UndefinedVariable
        # notify the system of updated policy
        FigureCanvas.updateGeometry(self)  #@UndefinedVariable

        # the rate of change of temperature
        self.rateofchange1:float = 0.0
        self.rateofchange2:float = 0.0

        #read and plot on/off flag
        self.flagon:bool = False  # Artisan turned on (sampling)
        self.flagstart:bool = False # Artisan logging/recording
        self.flagKeepON:bool = False # turn Artisan ON again after pressing OFF during recording
        self.flagOpenCompleted:bool = False # after completing a recording with OFF, send the saved profile to be opened in the ArtisanViewer
        self.flagsampling:bool = False # if True, Artisan is still in the sampling phase and one has to wait for its end to turn OFF
        self.flagsamplingthreadrunning:bool = False
        #log flag that tells to log ET when using device 18 (manual mode)
        self.manuallogETflag = 0

        self.zoom_follow:bool = False # if True, Artisan "follows" BT in the center by panning during recording. Activated via a click on the HOME icon

        self.alignEvent = 0 # 0:CHARGE, 1:DRY, 2:FCs, 3:FCe, 4:SCs, 5:SCe, 6:DROP, 7:ALL
        self.alignnames = [
            QApplication.translate('Label','CHARGE'),
            QApplication.translate('Label','DRY'),
            QApplication.translate('Label','FCs'),
            QApplication.translate('Label','FCe'),
            QApplication.translate('Label','SCs'),
            QApplication.translate('Label','SCe'),
            QApplication.translate('Label','DROP'),
            QApplication.translate('Label','ALL'),
            ]
        self.compareAlignEvent = 0 # 0:CHARGE, 1:DRY, 2:FCs, 3:FCe, 4:SCs, 5:SCe, 6:DROP
        self.compareEvents = 0 # 0: no events, 1: event type 1, 2: event type 2, 3: event type 3, 4: event type 4
        self.compareET:bool = False
        self.compareBT:bool = True
        self.compareDeltaET:bool = False
        self.compareDeltaBT:bool = True
        self.compareMainEvents:bool = True
        # Comparator: Roast (compareBBP=False & compareRoast=True); BBP+Roast (compareBBP=True & compareRoast=True); BBP (compareBBP=True & compareRoast=False)
        #   the state compareBBP=False and compareRoast=False should never occur
        self.compareBBP:bool = False # if True incl. BBP
        self.compareRoast:bool = True # if False roast should not be compared (self.compareBBP should be True in this case!)

        self.replayType:int = 0 # 0: by time, 1: by BT, 2: by ET
        self.replayedBackgroundEvents:List[int] = [] # set of BackgroundEvent indices that have already been replayed (cleared in ClearMeasurements)
        self.beepedBackgroundEvents:List[int] = []   # set of BackgroundEvent indices that have already been beeped for (cleared in ClearMeasurements)

        self.roastpropertiesflag:int = 1  #resets roast properties if not zero
        self.roastpropertiesAutoOpenFlag:int = 0  #open roast properties dialog on CHARGE if not zero
        self.roastpropertiesAutoOpenDropFlag:int = 0  #open roast properties dialog on DROP if not zero
        self.title:str = QApplication.translate('Scope Title', 'Roaster Scope')
        self.title_show_always:bool = False
        self.ambientTemp:float = 0.
        self.ambientTemp_sampled:float = 0. # keeps the measured ambientTemp over a restart
        self.ambientTempSource:int = 0 # indicates the temperature curve that is used to automatically fill the ambient temperature on DROP
#                                  # 0 : None; 1 : ET, 2 : BT, 3 : 0xT1, 4 : 0xT2,
        self.ambient_temperature_device:int = 0
        self.ambient_pressure:float = 0.
        self.ambient_pressure_sampled:float = 0. # keeps the measured ambient_pressure over a restart/reset
        self.ambient_pressure_device:int = 0
        self.ambient_humidity:float = 0.
        self.ambient_humidity_sampled:float = 0. # keeps the measured ambient_humidity over a restart/reset
        self.ambient_humidity_device:int = 0
        self.elevation:int = 0

        self.temperaturedevicefunctionlist: Final[List[str]] = [
            '',                #0
            'Phidget HUM100x', #1
            'Yocto Meteo',     #2
            'Phidget TMP1000', #3
        ]
        self.humiditydevicefunctionlist: Final[List[str]] = [
            '',                #0
            'Phidget HUM100x', #1
            'Yocto Meteo',     #2
        ]
        self.pressuredevicefunctionlist: Final[List[str]] = [
            '',                #0
            'Phidget PRE1000', #1
            'Yocto Meteo',     #2
        ]

        self.moisture_greens:float = 0.
        self.moisture_roasted:float = 0.
        self.greens_temp:float = 0.

        self.beansize:float = 0.0 # legacy; now mapped to beansize_max on load
        self.beansize_min:int = 0
        self.beansize_max:int = 0

        self.whole_color:int = 0
        self.ground_color:int = 0
        self.color_systems: Final[List[str]] = ['','Tonino','ColorTest','Colorette','ColorTrack','Agtron']
        self.color_system_idx:int = 0

        # roast property flags
        self.heavyFC_flag:bool = False
        self.lowFC_flag:bool = False
        self.lightCut_flag:bool = False
        self.darkCut_flag:bool = False
        self.drops_flag:bool = False
        self.oily_flag:bool = False
        self.uneven_flag:bool = False
        self.tipping_flag:bool = False
        self.scorching_flag:bool = False
        self.divots_flag:bool = False

        #list to store the time in seconds of each reading. Most IMPORTANT variable.
        self.timex:List[float] = []

        #lists to store temps and rates of change. Second most IMPORTANT variables. All need same dimension.
        #self.temp1 = ET ; self.temp2 = BT; self.delta1 = deltaMET; self.delta2 = deltaBT
        self.temp1:List[float] = []
        self.temp2:List[float] = []
        self.delta1:List[Optional[float]] = []
        self.delta2:List[Optional[float]] = []
        self.stemp1:List[float] = [] # smoothed versions of temp1/temp2 used in redraw()
        self.stemp2:List[float] = []
        self.tstemp1:List[float] = [] # (temporarily) smoothed version of temp1/temp2 used in sample() to compute the RoR
        self.tstemp2:List[float] = []
        self.ctimex1:List[float] = [] # (potential shorter) variants of timex/temp1/temp2 with -1 dropout values removed (or replaced by None)
        self.ctimex2:List[float] = []
        self.ctemp1:List[Optional[float]] = []
        self.ctemp2:List[Optional[float]] = []
        # NOTE: those ctimexN, ctempN lists can be shorter than the original timex/tempN lists as some dropout values may have been removed,
        # however, the invariants len(ctimex1) = len(ctemp1) and len(timex2) = len(ctemp2) always hold
        self.unfiltereddelta1:List[float] = [] # Delta mathexpressions applied; used in sample()
        self.unfiltereddelta2:List[float] = []
        self.unfiltereddelta1_pure:List[float] = [] # Delta mathexpressions not applied; used in sample() and by projections
        self.unfiltereddelta2_pure:List[float] = []

        # arrays to use while monitoring but not recording
        self.on_timex:List[float] = []
        self.on_temp1:List[float] = []
        self.on_temp2:List[float] = []
        self.on_ctimex1:List[float] = []
        self.on_ctemp1:List[Optional[float]] = []
        self.on_ctimex2:List[float] = []
        self.on_ctemp2:List[Optional[float]] = []
        self.on_tstemp1:List[float] = []
        self.on_tstemp2:List[float] = []
        self.on_unfiltereddelta1:List[float] = []
        self.on_unfiltereddelta2:List[float] = []
        self.on_delta1:List[Optional[float]] = []
        self.on_delta2:List[Optional[float]] = []
        # list of lists:
        self.on_extratemp1:List[List[float]] = []
        self.on_extratemp2:List[List[float]] = []
        self.on_extratimex:List[List[float]] = []
        self.on_extractimex1:List[List[float]] = []
        self.on_extractemp1:List[List[Optional[float]]] = []
        self.on_extractimex2:List[List[float]] = []
        self.on_extractemp2:List[List[Optional[float]]] = []

        #indexes for CHARGE[0],DRYe[1],FCs[2],FCe[3],SCs[4],SCe[5],DROP[6] and COOLe[7]
        #Example: Use as self.timex[self.timeindex[1]] to get the time of DryEnd
        #Example: Use self.temp2[self.timeindex[4]] to get the BT temperature of SCs

        self.timeindex:List[int] = [-1,0,0,0,0,0,0,0] #CHARGE index init set to -1 as 0 could be an actal index used

        #applies a Y(x) function to ET or BT
        self.ETfunction:str = ''
        self.BTfunction:str = ''

        #applies a Y(x) function to DeltaET or DeltaBT
        self.DeltaETfunction = ''
        self.DeltaBTfunction = ''

        #put a "self.safesaveflag = True" whenever there is a change of a profile like at [DROP], edit properties Dialog, etc
        #prevents accidentally deleting a modified profile. ("dirty file")
        #ATTENTION: never change this flag directly. Use the methods self.fileDirty() and self.fileClean() instead!!
        self.safesaveflag:bool = False

        self.pid = pid.PID()

        #background profile
        self.background:bool = False # set to True if loaded background profile is shown and False if hidden
        self.backgroundprofile:Optional['ProfileData'] = None # if not None, a background profile is loaded
        self.backgroundprofile_moved_x:int = 0 # background profile moved in horizontal direction
        self.backgroundprofile_moved_y:int = 0 # background profile moved in vertical direction
        self.backgroundDetails:bool = True
        self.backgroundeventsflag:bool = True
        self.backgroundpath:str = ''
        self.backgroundUUID:Optional[str] = None
        self.backgroundmovespeed = 30
        self.backgroundShowFullflag:bool = False
        self.backgroundKeyboardControlFlag:bool = True
        self.titleB = ''
        self.roastbatchnrB = 0
        self.roastbatchprefixB = ''
        self.roastbatchposB = 1
        self.temp1B:List[float] = []
        self.temp2B:List[float] = []
        self.temp1BX:List['npt.NDArray[numpy.floating]'] = []
        self.temp2BX:List['npt.NDArray[numpy.floating]'] = []
        self.timeB:List[float] = []
        self.temp1Bdelta:List[float] = []
        self.temp2Bdelta:List[float] = []
        # smoothed versions of the background curves
        self.stemp1B:'npt.NDArray[numpy.floating]' = numpy.empty(0)
        self.stemp2B:'npt.NDArray[numpy.floating]' = numpy.empty(0)
        self.stemp1BX:List['npt.NDArray[numpy.floating]'] = []
        self.stemp2BX:List['npt.NDArray[numpy.floating]'] = []
        self.extraname1B:List[str] = []
        self.extraname2B:List[str] = []
        self.extratimexB:List[List[float]] = []
        self.xtcurveidx:int = 0 # the selected first extra background courve to be displayed
        self.ytcurveidx:int = 0 # the selected second extra background courve to be displayed
        self.delta1B:List[Optional[float]] = []
        self.delta2B:List[Optional[float]] = []
        self.timeindexB:List[int] = [-1,0,0,0,0,0,0,0]
        self.TP_time_B_loaded:Optional[float] = None # the time in seconds the background TP happened. TP_time_B_loaded does not change and should be used for display
        self.backgroundEvents:List[int] = [] #indexes of background events
        self.backgroundEtypes:List[int] = []
        self.backgroundEvalues:List[float] = []
        self.backgroundEStrings:List[str] = []
        self.backgroundalpha:float = 0.2
        self.backgroundmetcolor:str = self.palette['et']
        self.backgroundbtcolor:str = self.palette['bt']
        self.backgroundxtcolor:str = self.palette['xt']
        self.backgroundytcolor:str = self.palette['yt']
        self.backgrounddeltaetcolor:str = self.palette['deltaet']
        self.backgrounddeltabtcolor:str = self.palette['deltabt']
        self.backmoveflag:int = 1 # aligns background on redraw if 1
        self.detectBackgroundEventTime:int = 20 #seconds
        self.backgroundReproduce:bool = False
        self.backgroundReproduceBeep:bool = False
        self.backgroundPlaybackEvents:bool = False
        self.backgroundPlaybackDROP:bool = False
        self.Betypes:List[str] = [QApplication.translate('ComboBox', 'Air'),
                        QApplication.translate('ComboBox', 'Drum'),
                        QApplication.translate('ComboBox', 'Damper'),
                        QApplication.translate('ComboBox', 'Burner'),
                        '--']
        self.backgroundFlavors:List[float] = []
        self.flavorbackgroundflag:bool = False
        #background by value
        self.E1backgroundtimex:List[float] = []
        self.E2backgroundtimex:List[float] = []
        self.E3backgroundtimex:List[float] = []
        self.E4backgroundtimex:List[float] = []
        self.E1backgroundvalues:List[float] = []
        self.E2backgroundvalues:List[float] = []
        self.E3backgroundvalues:List[float] = []
        self.E4backgroundvalues:List[float] = []
        self.l_backgroundeventtype1dots:Optional['Line2D'] = None
        self.l_backgroundeventtype2dots:Optional['Line2D'] = None
        self.l_backgroundeventtype3dots:Optional['Line2D'] = None
        self.l_backgroundeventtype4dots:Optional['Line2D'] = None

        # background Deltas
        self.DeltaETBflag:bool = False
        self.DeltaBTBflag:bool = True
        self.clearBgbeforeprofileload:bool = False
        self.hideBgafterprofileload:bool = False

        self.heating_types: Final[List[str]] = [
            '',
            QApplication.translate('ComboBox', 'Propane Gas (LPG)'),
            QApplication.translate('ComboBox', 'Natural Gas (NG)'),
            QApplication.translate('ComboBox', 'Electric')
        ]

        #General notes. Accessible through "edit graph properties" of graph menu. WYSIWYG viewer/editor.
        # setup of the current profile
        self.operator: str = ''
        self.organization: str = ''
        self.roastertype: str = ''
        self.roastersize: float = 0
        self.roasterheating:int = 0 # 0: ??, 1: LPG, 2: NG, 3: Elec
        self.drumspeed: str = ''
        # kept in app settings
        self.organization_setup:str = ''
        self.operator_setup:str = ''
        self.roastertype_setup:str = ''
        self.roastersize_setup:float = 0 # in kg
        self.roasterheating_setup:int = 0
        self.drumspeed_setup:str = ''
        #
        self.last_batchsize:float = 0 # in unit of self.weight[2]; remember the last batchsize used to be applied as default for the next batch
        #
        self.machinesetup_energy_ratings:Optional[Dict[int,Dict[float, Dict[str,List[Any]]]]] = None # read from predefined machine setups and used if available to set energy defaults
        #
        self.machinesetup:str = ''
        self.roastingnotes:str = ''
        self.cuppingnotes:str = ''
        self.roastdate:QDateTime = QDateTime.currentDateTime()
        # system batch nr system
        self.roastepoch:int = self.roastdate.toSecsSinceEpoch() # in seconds
        self.lastroastepoch:int = self.roastepoch # the epoch of the last roast in seconds
        self.batchcounter:int = -1 # global batch counter; if batchcounter is -1, batchcounter system is inactive
        self.batchsequence:int = 1 # global counter of position in sequence of batches of one session
        self.batchprefix:str = ''
        self.neverUpdateBatchCounter:bool = False
        # profile batch nr
        self.roastbatchnr:int = 0 # batch number of the roast; if roastbatchnr=0, prefix/counter is hidden/inactiv (initialized to 0 on roast START)
        self.roastbatchprefix:str = self.batchprefix # batch prefix of the roast
        self.roastbatchpos:int = 1 # position of the roast in the roast session (first batch, second batch,..)
        self.roasttzoffset:int = libtime.timezone # timezone offset to be added to roastepoch to get time in local timezone; NOTE: this is not set/updated on loading a .alog profile!
        # profile UUID
        self.roastUUID:Optional[str] = None

#PLUS
        # the default store selected by the user (save in the  app settings)
        self.plus_default_store:Optional[str] = None
        # the current profiles coffee or blend and associated store ids (saved in the *.alog profile)
        self.plus_store:Optional[str] = None # holds the plus hr_id of the selected store of the current profile or None
        self.plus_store_label:Optional[str] = None # holds the plus label of the selected store of the current profile or None
        self.plus_coffee:Optional[str] = None # holds the plus hr_id of the selected coffee of the current profile or None
        self.plus_coffee_label:Optional[str] = None # holds the plus label of the selected coffee of the current profile or None
        self.plus_blend_spec:Optional['Blend'] = None # the plus blend structure [<blend_label>,[[<coffee_label>,<hr_id>,<ratio>],...,[<coffee_label>,<hr_id>,<ratio>]]] # label + ingredients
        self.plus_blend_spec_labels:Optional[List[str]] = None # a list of labels as long as the list of ingredients in self.plus_blend_spec or None
        self.plus_blend_label:Optional[str] = None # holds the plus selected label of the selected blend of the current profile or None
        self.plus_custom_blend:Optional['CustomBlend'] = None # holds the one custom blend, an instance of plus.blend.Blend, or None
        self.plus_sync_record_hash:Optional[str] = None
        self.plus_file_last_modified:Optional[float] = None # holds the last_modified timestamp of the loaded profile as EPOCH (float incl. milliseconds as returned by time.time())
        # plus_file_last_modified is set on load, reset on RESET, and updated on save. It is also update, if not None and new data is received from the server (sync:applyServerUpdates)
        # this timestamp is used in sync:fetchServerUpdate to ask server for updated data

        self.beans:str = ''

        self.curveVisibilityCache:Optional[Tuple[bool,bool,bool,bool,List[bool],List[bool]]] = None # caches the users curve visibility settings to be reset after recording

        #flags to show projections, draw Delta ET, and draw Delta BT
        self.projectFlag:bool = True
        self.projectDeltaFlag:bool = False
        self.ETcurve:bool = True
        self.BTcurve:bool = True
        self.ETlcd:bool = True
        self.BTlcd:bool = True
        self.swaplcds:bool = False # if set draw ET curver on top of BT curve and show ET LCD above BT LCD by default
        self.LCDdecimalplaces = 1
        self.foregroundShowFullflag:bool = True
        self.DeltaETflag:bool = False
        self.DeltaBTflag:bool = True
        self.DeltaETlcdflag:bool = False
        self.DeltaBTlcdflag:bool = True
        self.swapdeltalcds:bool = False
        self.PIDbuttonflag:bool = True # TC4 PID firmware available?
        self.Controlbuttonflag:bool = False # PID Control active (either internal/external or Fuji)
        # user filter values x are translated as follows to internal filter values: y = x*2 + 1 (to go the other direction: x = y/2)
        # this is to ensure, that only uneven window values are used and no wrong shift is happening through smoothing
        self.deltaETfilter = 7 # => corresponds to 3 on the user interface
        self.deltaBTfilter = 7 # => corresponds to 3 on the user interface
        self.curvefilter = 3 # => corresponds to 1 on the user interface
        # a deltaET span of 0 indicates that the delta RoR is computed by two succeeding readings
        self.deltaETspan = 20 # the time period taken to compute one deltaET value (1-30sec) # deltaETspan >= 0
        self.deltaBTspan = 20 # the time period taken to compute one deltaBT value (1-30sec) # deltaBTspan >= 0
        # deltaETsamples == 1 (sample) implies that the delta RoR is computed from only two readings:
        self.deltaETsamples: int = 6 # the number of samples that make up the delta span, to be used in the delta computations (>= 1!)
        self.deltaBTsamples: int = 6 # the number of samples that make up the delta span, to be used in the delta computations (>= 1!)
        self.profile_sampling_interval:Optional[float] = None # will be updated on loading a profile
        self.background_profile_sampling_interval:Optional[float] = None # will be updated on loading a profile into the background
        self.profile_meter = 'Unknown' # will be updated on loading a profile

        self.optimalSmoothing:bool = False
        self.polyfitRoRcalc:bool = False

        self.patheffects = 1
        self.graphstyle = 0
        self.graphfont = 0

        #variables to configure the 8 default buttons
        # button = 0:CHARGE, 1:DRY_END, 2:FC_START, 3:FC_END, 4:SC_START, 5:SC_END, 6:DROP, 7:COOL_END;
        self.buttonvisibility = [True,True,True,True,True,False,True,False]
        self.buttonactions = [0]*8
        self.buttonactionstrings = ['']*8
        #variables to configure the 0: ON, 1: OFF, 2: SAMPLE, 3:RESET, 4:START
        self.extrabuttonactions = [0]*3
        self.extrabuttonactionstrings = ['']*3
        #variables to configure the 0:RESET, 1:START
        self.xextrabuttonactions = [0]*2
        self.xextrabuttonactionstrings = ['']*2

        #flag to activate the automatic marking of the CHARGE and DROP events
        self.chargeTimerFlag: bool = False
        self.chargeTimerPeriod: int = 0 # period until CHARGE since START if CHARGE timer is active
        self.autoChargeFlag: bool = True
        self.autoDropFlag: bool = True
        #autodetected CHARGE and DROP index
        self.autoChargeIdx = 0
        self.autoDropIdx = 0

        self.markTPflag:bool = True
        self.autoTPIdx = 0 # set by sample() on recognition and cleared once TP is marked

        # flags to control automatic DRY and FCs events based on phases limits
        self.autoDRYflag:bool = False
        self.autoFCsFlag:bool = False

        self.autoCHARGEenabled:bool = True # gets disabled on undo of the CHARGE event and prevents further autoCHARGE marks
        self.autoDRYenabled:bool = True # gets disabled on undo of the DRY event and prevents further autoDRY marks
        self.autoFCsenabled:bool = True # gets disabled on undo of the FCs event and prevents further autoFCs marks
        self.autoDROPenabled:bool = True # gets disabled on undo of the DROP event and prevents further autoDROP marks

        self.autoDryIdx = 0 # set by sample() on recognition and cleared once DRY is marked
        self.autoFCsIdx = 0 # set by sample() on recognition and cleared once FCs is marked


        # projection variables of change of rate
        self.projectionconstant = 1
        self.projectionmode = 0     # 0 = linear; 1 = quadratic;   # 2 = newton#disabled

        # profile transformator mapping mode
        self.transMappingMode = 0 # 0: discrete, 1: linear, 2: quadratic

        self.weight_units:List[str] = ['g','Kg','lb','oz']
        #[0]weight in, [1]weight out, [2]units (string)
        self.weight:Tuple[float,float,str] = (0,0,self.weight_units[0])

        self.volume_units:List[str] = ['l','gal','qt','pt','cup','ml']
        #[0]volume in, [1]volume out, [2]units (string)
        self.volume:Tuple[float,float,str] = (0,0,self.volume_units[0])

        #[0]probe weight, [1]weight unit, [2]probe volume, [3]volume unit
        self.density:Tuple[float,str,float,str] = (0,'g',1.,'l')
        # density weight and volume units are not to be used any longer and assumed to be fixed to g/l
        # thus also probe volume is not used anymore, and only self.density[0] holds the green been density in g/l

        self.density_roasted:Tuple[float,str,float,str] = (0,'g',1.,'l') # this holds the roasted beans density in g/l


        if platform.system() == 'Darwin':
            # try to "guess" the users preferred temperature unit
            try:
                if not QSettings().value('AppleMetricUnits'):
                    self.weight = (0,0,self.weight_units[2])
                    self.volume = (0,0,self.volume_units[1])
            except Exception: # pylint: disable=broad-except
                pass

        self.volumeCalcUnit:float = 0
        self.volumeCalcWeightInStr:str = ''
        self.volumeCalcWeightOutStr:str = ''

        # container scale tare
        self.container_names:List[str] = []
        self.container_weights:List[int] = [] # all weights in g and as int
        self.container_idx:int = -1 # the empty field (as -1 + 2 = 1)

        #stores _indexes_ of self.timex to record events.
        # Use as self.timex[self.specialevents[x]] to get the time of an event
        # use self.temp2[self.specialevents[x]] to get the BT temperature of an event.
        self.specialevents:List[int] = []
        #ComboBox text event types. They can be modified in eventsDlg()
        self.etypes:List[str] = [QApplication.translate('ComboBox', 'Air'),
                       QApplication.translate('ComboBox', 'Drum'),
                       QApplication.translate('ComboBox', 'Damper'),
                       QApplication.translate('ComboBox', 'Burner'),
                       '--']
        #default etype settings to restore
        self.etypesdefault: Final[List[str]] = [QApplication.translate('ComboBox', 'Air'),
                              QApplication.translate('ComboBox', 'Drum'),
                              QApplication.translate('ComboBox', 'Damper'),
                              QApplication.translate('ComboBox', 'Burner'),
                              '--']
        #stores the type of each event as index of self.etypes. None = 0, Power = 1, etc.
        self.specialeventstype:List[int] = []
        #stores text string descriptions for each event.
        self.specialeventsStrings:List[str] = []
        #event values are from 0-10
        #stores the value for each event
        self.specialeventsvalue:List[float] = []
        #flag that makes the events location type bars (horizontal bars) appear on the plot. flag read on redraw()
        # 0 = no event bars (flags); 1 = type bars (4 bars); 2 = step lines; 3 = step+ (combination of 0 and 2); 4 = combo (as 2, but values rendered on lines instead of flags)
        self.eventsGraphflag:int = 2
        self.clampEvents:bool = False # if True, custom events are drawn w.r.t. the temperature scale
        self.renderEventsDescr:bool = False # if True, descriptions are rendered instead of type/value tags
        self.eventslabelschars:int = 6 # maximal number of chars to render as events label
        #flag that shows events in the graph
        self.eventsshowflag:int = 1
        #flag that shows major event annotations in the graph
        self.annotationsflag:int = 1
        #shows events anchored to the BT curve if true, events anchored to greater of ET or BT curve if false
        self.showeventsonbt:bool = False
        #selectively show/hide event types
        self.showEtypes:List[bool] = [True]*5
        #plot events by value
        self.E1timex:List[float] = []
        self.E2timex:List[float] = []
        self.E3timex:List[float] = []
        self.E4timex:List[float] = []
        self.E1values:List[float] = []
        self.E2values:List[float] = []
        self.E3values:List[float] = []
        self.E4values:List[float] = []
        self.EvalueColor:List[str] = self.EvalueColor_default.copy()
        self.EvalueTextColor:List[str] = self.EvalueTextColor_default.copy()
        self.EvalueMarker:List[str] = ['o','s','h','D']
        self.EvalueMarkerSize:List[float] = [4,4,4,4]
        self.Evaluelinethickness:List[float] = [1,1,1,1]
        self.Evaluealpha:List[float] = [.8,.8,.8,.8]
        #the event value position bars are calculated at redraw()
        self.eventpositionbars:List[float] = [0.]*120
        self.specialeventannotations:List[str] = ['','','','']
        self.specialeventannovisibilities:List[int] = [0,0,0,0]
        self.specialeventplaybackaid:List[bool] = [True, True, True, True] # per event type decides if playback aid is active
        self.specialeventplayback:List[bool] = [True, True, True, True] # per event type decides if background events are playbacked or not
        self.overlappct:int = 100

        #curve styles
        self.linewidth_min: Final[float] = 0.1 # minimum linewidth. NOTE: MPL raises an (unhandled) excpetion if linewidth is 0 with dotted styles in plot()
        self.markersize_min: Final[float] = 0.1

        self.linestyle_default: Final[str] = '-'
        self.drawstyle_default: Final[str] = 'default'
        self.linewidth_default: Final[float] = 1.5
        self.back_linewidth_default: Final[float] = 2
        self.delta_linewidth_default: Final[float] = 1
        self.back_delta_linewidth_default: Final[float] = 1.5
        self.extra_linewidth_default: Final[float] = 1
        self.marker_default: Final[str] = 'None'
        self.markersize_default: Final[float] = 6

        self.BTlinestyle:str = self.linestyle_default
        self.BTdrawstyle:str = self.drawstyle_default
        self.BTlinewidth:float = self.linewidth_default
        self.BTmarker:str = self.marker_default
        self.BTmarkersize:float = self.markersize_default
        self.ETlinestyle:str = self.linestyle_default
        self.ETdrawstyle:str = self.drawstyle_default
        self.ETlinewidth:float = self.linewidth_default
        self.ETmarker:str = self.marker_default
        self.ETmarkersize:float = self.markersize_default
        self.BTdeltalinestyle:str = self.linestyle_default
        self.BTdeltadrawstyle:str = self.drawstyle_default
        self.BTdeltalinewidth:float = self.delta_linewidth_default
        self.BTdeltamarker:str = self.marker_default
        self.BTdeltamarkersize:float = self.markersize_default
        self.ETdeltalinestyle:str = self.linestyle_default
        self.ETdeltadrawstyle:str = self.drawstyle_default
        self.ETdeltalinewidth:float = self.delta_linewidth_default
        self.ETdeltamarker:str = self.marker_default
        self.ETdeltamarkersize:float = self.markersize_default
        self.BTbacklinestyle:str = self.linestyle_default
        self.BTbackdrawstyle:str = self.drawstyle_default
        self.BTbacklinewidth:float = self.back_linewidth_default
        self.BTbackmarker:str = self.marker_default
        self.BTbackmarkersize:float = self.markersize_default
        self.ETbacklinestyle:str = self.linestyle_default
        self.ETbackdrawstyle:str = self.drawstyle_default
        self.ETbacklinewidth:float = self.back_linewidth_default
        self.ETbackmarker:str = self.marker_default
        self.ETbackmarkersize:float = self.markersize_default
        self.XTbacklinestyle:str = self.linestyle_default
        self.XTbackdrawstyle:str = self.drawstyle_default
        self.XTbacklinewidth:float = self.extra_linewidth_default
        self.XTbackmarker:str = self.marker_default
        self.XTbackmarkersize:float = self.markersize_default
        self.YTbacklinestyle:str = self.linestyle_default
        self.YTbackdrawstyle:str = self.drawstyle_default
        self.YTbacklinewidth:float = self.extra_linewidth_default
        self.YTbackmarker:str = self.marker_default
        self.YTbackmarkersize:float = self.markersize_default
        self.BTBdeltalinestyle:str = self.linestyle_default
        self.BTBdeltadrawstyle:str = self.drawstyle_default
        self.BTBdeltalinewidth:float = self.back_delta_linewidth_default
        self.BTBdeltamarker:str = self.marker_default
        self.BTBdeltamarkersize:float = self.markersize_default
        self.ETBdeltalinestyle:str = self.linestyle_default
        self.ETBdeltadrawstyle:str = self.drawstyle_default
        self.ETBdeltalinewidth:float = self.back_delta_linewidth_default
        self.ETBdeltamarker:str = self.marker_default
        self.ETBdeltamarkersize:float = self.markersize_default

        #Temperature Alarms lists. Data is written in  alarmDlg
        self.alarmsetlabel:str = ''
        self.alarmflag: List[int] = []      # 0 = OFF; 1 = ON flags
        self.alarmguard: List[int] = []      # points to another alarm by index that has to be triggered before; -1 indicates no guard
        self.alarmnegguard: List[int] = []   # points to another alarm by index that should not has been triggered before; -1 indicates no guard
        self.alarmtime: List[int] = []      # time event after which each alarm becomes effective. Usage: self.timeindex[self.alarmtime[i]]
#                               # -1 : START.
#                               # 0: CHARGE, 1: DRY END; 2: FCs, 3: FCe, 4: SCs, 5: SCe, 6: DROP, 7: COOL (corresponding to those timeindex positions)
#                               # 8: TP
#                               # 9: ON
#                               # 10: If Alarm
        self.alarmoffset: List[int] = []    # for timed alarms, the seconds after alarmtime the alarm is triggered
        self.alarmtime2menuidx: Final[List[int]] = [2,4,5,6,7,8,9,10,3,0,11,1] # maps self.alarmtime index to menu idx (to move TP in menu from index 9 to 3)
        self.menuidx2alarmtime: Final[List[int]] = [9,-1,0,8,1,2,3,4,5,6,7,10] # inverse of above (note that those two are only inverse in one direction!)
        self.alarmcond: List[int] = []      # 0 = falls below; 1 = rises above
        # alarmstate is set to 'not triggered' on reset(). This is needed so that the user does not have to turn the alarms ON next roast after alarm being used once.
        self.alarmstate:List[int] = []   # <idx>=triggered, -1=not triggered.
        self.alarmsource: List[int] = []    # -3=None, -2=DeltaET, -1=DeltaBT, 0=ET , 1=BT, 2=extratemp1[0], 3=extratemp2[0], 4=extratemp2[1],....
        self.alarmtemperature: List[float] = []  # set temperature number (example 500; can be negative)
        self.alarmaction: List[int] = []         # -1 = no action; 0 = open a window;
                                    # 1 = call program with a filepath equal to alarmstring;
                                    # 2 = activate button with number given in description;
                                    # 3,4,5,6 = move slider with value given in description
                                    # 7 (START), 8 (DRY), 9 (FCs), 10 (FCe), 11 (SCs), 12 (SCe), 13 (DROP), 14 (COOL), 15 (OFF)
                                    # 16 (CHARGE),
                                    # 17 (RampSoak_ON), 18 (RampSoak_OFF), 19 (PID_ON), 20 (PID_OFF)
        self.alarmbeep: List[int] = []           # 0 = OFF; 1 = ON flags
        self.alarmstrings: List[str] = []         # text descriptions, action to take, or filepath to call another program (comments after # are ignored)
        self.alarmtablecolumnwidths:List[int] = []
        self.silent_alarms:bool = False # if this is true (can be set via a + button action "alarm(1)", alarms are triggered, but actions are not fired

        # alarm sets
        self.alarmsets_count: Final[int] = 10 # number of alarm sets
        self.alarmsets:List = []
        for _ in range(self.alarmsets_count):
            self.alarmsets.append([
                '',
                [], # alarmflags
                [], # alarmguards
                [], # alarmnegguards
                [], # alarmtimes
                [], # alarmoffsets
                [], # alarmsources
                [], # alarmconds
                [], # alarmtemperatures
                [], # alarmactions
                [], # alarmbeeps
                [], # alarmstrings
            ])

        self.loadalarmsfromprofile:bool = False # if set, alarms are loaded from profile
        self.loadalarmsfrombackground:bool = False # if set, alarms are loaded from background profiles
        self.alarmsfile:str = '' # filename alarms were loaded from
        self.temporaryalarmflag:int = -3 #holds temporary index value of triggered alarm in updategraphics()
        self.TPalarmtimeindex:Optional[int] = None # is set to the current  self.timeindex by sample(), if alarms are defined and once the TP is detected

        self.rsfile:str = '' # filename Ramp/Soak patterns were loaded from

        self.temporary_error:Optional[str] = None # set by adderror() to a new error message, send to the message line by updategraphics()
        self.temporarymovepositiveslider:Optional[Tuple[int,int]] = None # set by pidcontrol.setEnergy (indirectly called from sample())
                # holds tuple (slidernr,value) and is executed and reset by updategraphics
        self.temporarymovenegativeslider:Optional[Tuple[int,int]] = None
        self.temporayslider_force_move:bool = True # if True move the slider independent of the slider position to fire slider action!

        self.quantifiedEvent:List = [] # holds an event quantified during sample(), a tuple [<eventnr>,<value>,<recordEvent>]

        self.loadaxisfromprofile:bool = False # if set, axis are loaded from profile

        # set initial limits for X and Y axes. But they change after reading the previous seetings at self.aw.settingsload()
        self.startofx_default: Final[float] = -30
        self.endofx_default: Final[float] = 600 # 10min*60

        self.xgrid_default: Final[int] = 120

        self.ylimit_F_default: Final[int] = 500
        self.ylimit_min_F_default: Final[int] = 100
        self.ygrid_F_default: Final[int] = 100
        self.zlimit_F_default: Final[int] = 45
        self.zlimit_min_F_default: Final[int] = 0
        self.zgrid_F_default: Final[int] = 10

        self.ylimit_C_default: Final[int] = 250
        self.ylimit_min_C_default: Final[int] = 0
        self.ygrid_C_default: Final[int] = 50
        self.zlimit_C_default: Final[int] = 25
        self.zlimit_min_C_default: Final[int] = 0
        self.zgrid_C_default: Final[int] = 5

        self.temp_grid:bool = False
        self.time_grid:bool = False

        # maximum accepted min/max settings for y and z axis
        self.zlimit_max:int = 500
        self.zlimit_min_max:int = -500
        self.ylimit_max:int = 9999
        self.ylimit_min_max:int = -9999

        #----
        # set limits to F defaults

        self.ylimit:int = self.ylimit_F_default
        self.ylimit_min:int = self.ylimit_min_F_default
        self.zlimit:int = self.zlimit_F_default
        self.zlimit_min:int = self.zlimit_min_F_default


        # RoR display limits
        # user configurable RoR limits (only applied if flag is True; applied before TP during recording as well as full redraw)
        self.RoRlimitFlag:bool = True
        self.RoRlimit:int = 95
        self.RoRlimitm:int = -95
        # system fixed RoR limits (only applied if flag is True; usually higher than the user configurable once and always applied)
        self.maxRoRlimit: Final[int] = 170
        # axis limits
        self.endofx:float = self.endofx_default     # endofx is the display time in seconds of the right x-axis limit (excluding any shift of CHARGE time)
        self.startofx:float = self.startofx_default # startofx is the time in seconds of the left x-axis limit in data time (display time in seconds of the left x-axis limit plus the CHARGE time in seconds); NOTE: as startofx depends CHARGE it has to be adjusted whenever CHARGE is adjusted
        self.resetmaxtime:int = 600  #time when pressing RESET: 10min*60
        self.chargemintime:float = self.startofx_default  #time when pressing CHARGE: -30sec
        self.fixmaxtime:bool = False # if true, do not automatically extend the endofx by 3min if needed because the measurements get out of the x-axis
        self.locktimex:bool = False # if true, do not set time axis min and max from profile on load
        self.autotimex:bool = True # automatically set time axis min and max from profile CHARGE/DROP on load
        self.autotimexMode = 0 # mode for autotimex with 0: profile (CHARGE/DROP), 1: BBP+profile (START/DROP), 2: BBP (START/CHARGE)
        self.autodeltaxET:bool = False # automatically set the delta axis max to the max(DeltaET)
        self.autodeltaxBT:bool = False # automatically set the delta axis max to the max(DeltaBT)
        self.locktimex_start:float = self.startofx_default # seconds of x-axis min as locked by locktimex (needs to be interpreted wrt. CHARGE index)
        self.locktimex_end:float = self.endofx_default # seconds of x-axis max as locked by locktimex (needs to be interpreted wrt. CHARGE index)
        self.xgrid:int = self.xgrid_default   #initial time separation; 60 = 1 minute
        self.ygrid:int = self.ygrid_F_default  #initial temperature separation
        self.zgrid:int = self.zgrid_F_default   #initial RoR separation
        self.gridstyles:List[str] =    ['-','--','-.',':',' ']  #solid,dashed,dash-dot,dotted,None
        self.gridlinestyle:int = 0
        self.gridthickness:float = 1
        self.gridalpha:float = .2
#        self.xrotation:float = 0

        #height of statistics bar
        self.statisticsheight:int = 650
        self.statisticsupper:int = 655
        self.statisticslower:int = 617

        # autosave
        self.autosaveflag:int = 0
        self.autosaveprefix:str = ''
        self.autosavepath:str = ''
        self.autosavealsopath:str = ''
        self.autosaveaddtorecentfilesflag:bool = False

        self.autosaveimage:bool = False # if true save an image along alog files

        self.autoasaveimageformat_types:List[str] = ['PDF', 'PDF Report', 'SVG', 'PNG', 'JPEG', 'BMP', 'CSV', 'JSON']
        self.autosaveimageformat:str = 'PDF' # one of the supported image file formats PDF, SVG, PNG, JPEG, BMP, CSV, JSON

        #used to place correct height of text to avoid placing text over text (annotations)
        self.ystep_down:int = 0
        self.ystep_up:int = 0

        self.ax.set_xlim(self.startofx, self.endofx)
        self.ax.set_ylim(self.ylimit_min,self.ylimit)

        if self.delta_ax is not None:
            self.delta_ax.set_xlim(self.startofx, self.endofx)
            self.delta_ax.set_ylim(self.zlimit_min,self.zlimit)
            self.delta_ax.set_autoscale_on(False)

        # disable figure autoscale
        self.ax.set_autoscale_on(False)

        #set grid + axis labels + title
        grid_axis = None
        if self.temp_grid and self.time_grid:
            grid_axis = 'both'
        elif self.temp_grid:
            grid_axis = 'y'
        elif self.time_grid:
            grid_axis = 'x'
        if grid_axis is not None:
            self.ax.grid(True,axis=grid_axis,color=self.palette['grid'],linestyle = self.gridstyles[self.gridlinestyle],linewidth = self.gridthickness,alpha = self.gridalpha)

        #change label colors
        for label in self.ax.yaxis.get_ticklabels():
            label.set_color(self.palette['ylabel'])

        for label in self.ax.xaxis.get_ticklabels():
            label.set_color(self.palette['xlabel'])

        self.backgroundETcurve:bool = True
        self.backgroundBTcurve:bool = True

        # generates first "empty" plot (lists are empty) of temperature and deltaT
        self.l_temp1:Optional['Line2D'] = None
        self.l_temp2:Optional['Line2D'] = None
        self.l_delta1:Optional['Line2D'] = None
        self.l_delta2:Optional['Line2D'] = None
        self.l_back1:Optional['Line2D'] = None
        self.l_back2:Optional['Line2D'] = None
        self.l_back3:Optional['Line2D'] = None # first extra background curve
        self.l_back4:Optional['Line2D'] = None # second extra background curve
        self.l_delta1B:Optional['Line2D'] = None
        self.l_delta2B:Optional['Line2D'] = None

        self.l_subtitle:Optional['Text'] = None # the subtitle artist if any as used to render the background title

        self.l_BTprojection:Optional['Line2D'] = None
        self.l_ETprojection:Optional['Line2D'] = None
        self.l_DeltaBTprojection:Optional['Line2D'] = None
        self.l_DeltaETprojection:Optional['Line2D'] = None

        self.l_AUCguide:Optional['Line2D'] = None

        self.l_horizontalcrossline:Optional['Line2D'] = None
        self.l_verticalcrossline:Optional['Line2D'] = None

        self.l_timeline:Optional['Line2D'] = None

        self.legend:Optional[mpl.DraggableLegend] = None

        self.l_eventtype1dots:Optional['Line2D'] = None
        self.l_eventtype2dots:Optional['Line2D'] = None
        self.l_eventtype3dots:Optional['Line2D'] = None
        self.l_eventtype4dots:Optional['Line2D'] = None

        self.l_eteventannos:List['Annotation'] = []
        self.l_bteventannos:List['Annotation'] = []
        self.l_eventtype1annos:List['Annotation'] = []
        self.l_eventtype2annos:List['Annotation'] = []
        self.l_eventtype3annos:List['Annotation'] = []
        self.l_eventtype4annos:List['Annotation'] = []

        self.l_annotations:List['Annotation'] = []
        self.l_background_annotations:List['Annotation'] = []

        # NOTE: the l_annotations_pos_dict is set on profile load and its positions are preferred over those in l_annotations_dict, but deleted at the end of the first redraw()
        self.l_annotations_dict:Dict[int,List['Annotation']] = {} # associating event ids (-1:TP, 0:CHARGE, 1:DRY,...) to its pair of draggable temp and time annotations
        self.l_annotations_pos_dict:Dict[int,Tuple[Tuple,Tuple]] = {} # associating event ids (-1:TP, 0:CHARGE, 1:DRY,...) to its pair of draggable temp and time xyann coordinate pairs
        self.l_event_flags_dict:Dict[int,'Annotation'] = {} # associating event flag annotations id (event number) to its draggable text annotation
        self.l_event_flags_pos_dict:Dict[int,Tuple] = {} # associating event flag annotations id (event number) to its draggable text xyann coordinates

        self.ai:Optional['AxesImage'] = None # holds background logo image

        ###########################  TIME  CLOCK     ##########################
        # create an object time to measure and record time (in milliseconds)

        self.timeclock:ArtisanTime = ArtisanTime()

        ############################  Thread Server #################################################
        #server that spawns a thread dynamically to sample temperature (press button ON to make a thread press OFF button to kill it)
        self.threadserver:Athreadserver = Athreadserver(self.aw)


        ##########################     Designer variables       #################################
        self.designerflag:bool = False
        self.designerconnections:List[Optional[int]] = [None,None,None,None]   #mouse event ids
        self.mousepress:bool = False
        self.indexpoint:int = 0
        self.workingline:int = 2  #selects 1:ET or 2:BT
        self.eventtimecopy:List[float] = []
        self.specialeventsStringscopy:List[str] = []
        self.specialeventsvaluecopy:List[float]   = []
        self.specialeventstypecopy:List[int]    = []
        self.currentx:float = 0               #used to add point when right click
        self.currenty:float = 0               #used to add point when right click
        self.designertimeinit:List[float] = [50,300,540,560,660,700,800,900]
        self.BTsplinedegree:int = 3
        self.ETsplinedegree:int = 3
        self.reproducedesigner:int = 0      #flag to add events to help reproduce (replay) the profile: 0 = none; 1 = sv; 2 = ramp
        self.designertemp1init:List[float] = []
        self.designertemp2init:List[float] = []
        self.ax_background_designer:Optional[mpl.backends._backend_agg.BufferRegion] = None # canvas background in designer mode for bitblitting # pylint: disable=c-extension-no-member
        self.designer_timez:Optional[List[float]] = None
        self.time_step_size:Final[int] = 2 # only every 2sec a point to increase speed of redrawing
        # designer artist line caches
        self._designer_orange_mark:Optional['Line2D'] = None
        self._designer_orange_mark_shown:bool = False
        self._designer_blue_mark:Optional['Line2D'] = None
        self._designer_blue_mark_shown:bool = False
        self.l_temp1_markers:Optional['Line2D'] = None
        self.l_temp2_markers:Optional['Line2D'] = None
        self.l_stat1:Optional['Line2D'] = None
        self.l_stat2:Optional['Line2D'] = None
        self.l_stat3:Optional['Line2D'] = None
        self.l_div1:Optional['Line2D'] = None
        self.l_div2:Optional['Line2D'] = None
        self.l_div3:Optional['Line2D'] = None
        self.l_div4:Optional['Line2D'] = None

        ###########################         filterDropOut variables     ################################

        # constants

        self.filterDropOut_replaceRoR_period:Final[int] = 3
        self.filterDropOut_spikeRoR_period:Final[int] = 3


        # defaults

        self.filterDropOut_tmin_C_default:Final[float] = 10
        self.filterDropOut_tmax_C_default:Final[float] = 700
        self.filterDropOut_tmin_F_default:Final[float] = 50
        self.filterDropOut_tmax_F_default:Final[float] = 1292
        self.filterDropOut_spikeRoR_dRoR_limit_C_default:Final[float] = 4.2
        self.filterDropOut_spikeRoR_dRoR_limit_F_default:Final[float] = 7

        # variables

        self.filterDropOuts:bool = True # Smooth Spikes
        self.filterDropOut_tmin:float = self.filterDropOut_tmin_F_default
        self.filterDropOut_tmax:float = self.filterDropOut_tmax_F_default
        self.filterDropOut_spikeRoR_dRoR_limit:float = self.filterDropOut_spikeRoR_dRoR_limit_F_default # the limit of additional RoR in temp/sec compared to previous readings
        self.minmaxLimits:bool = False
        self.dropSpikes:bool = False
        self.dropDuplicates:bool = False
        self.dropDuplicatesLimit:float = 0.3

        self.liveMedianETfilter:LiveMedian = LiveMedian(3)
        self.liveMedianBTfilter:LiveMedian = LiveMedian(3)
        self.liveMedianRoRfilter:LiveMedian = LiveMedian(5) # the offline filter uses a window length of 5, introducing some delay, compared to the medfilt() in offline mode which does not introduce any delay

        self.interpolatemax:Final[int] = 3 # maximal number of dropped readings (-1) that will be interpolated

        self.swapETBT:bool = False

        ###########################         wheel graph variables     ################################
        self.wheelflag:bool = False

        # set data for a nice demo flavor wheel

        #data containers for wheel
        self.wheelnames: List[List[str]] = [[''], ['Fruity', 'Sour', 'Green', 'Other', 'Roasted', 'Spices', 'Nutty', 'Sweet', 'Floral'], ['Floral', 'Berry', 'Dried fruit', 'Other fruit', 'Citrus fruit', 'Sour', 'Alcohol', 'Olive oil', 'Raw', 'Green', 'Beany', 'Musty', 'Chemical', 'Pipe tobaco', 'Tobaco', 'Burnt', 'Cereal', 'Pungent', 'Pepper', 'Brown spice', 'Nutty', 'Cocoa', 'Brown sugar', 'Vanilla', 'Vanillin', 'Overall sweet', 'Sweet Aromatics', 'Black Tea']]

        self.segmentlengths: List[List[float]] = [[100.0], [11.86125, 11.86125, 11.86125, 11.86125, 11.86125, 11.86125, 11.86125, 11.86125, 5.109999999999999], [2.5549999999999997, 2.9653125, 2.9653125, 2.9653125, 2.9653125, 5.930625, 5.930625, 2.9653125, 2.9653125, 2.9653125, 2.9653125, 5.930625, 5.930625, 2.9653125, 2.9653125, 2.9653125, 2.9653125, 3.95375, 3.95375, 3.95375, 5.930625, 5.930625, 2.37225, 2.37225, 2.37225, 2.37225, 2.37225, 2.5549999999999997]]

        self.segmentsalpha: List[List[float]] = [[0.09], [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0], [0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9]]

        self.wheellabelparent:List[List[int]] = [[0], [0, 0, 0, 0, 0, 0, 0, 0, 0], [9, 1, 1, 1, 1, 2, 2, 3, 3, 3, 3, 4, 4, 5, 5, 5, 5, 6, 6, 6, 7, 7, 8, 8, 8, 8, 8, 9]]

        self.wheelcolor:List[List[str]] = [['#fdfffb'], ['#cd001b', '#dea20e', '#186923', '#1693a6', '#bb3424', '#9b0f2f', '#976751', '#de4126', '#cf0055'], ['#d6588a', '#d33440', '#bb3435', '#ed513b', '#d47e1d', '#d9b913', '#a08727', '#91a41f', '#5e7927', '#309543', '#4d8a6d', '#8ca3a9', '#65b4c0', '#be9452', '#d7b06b', '#b07351', '#d4a04f', '#653540', '#bf2732', '#9f3845', '#ba7456', '#ac623b', '#c84347', '#f4866d', '#ee5e61', '#df4255', '#c33d4d', '#844a5a']]

        #properties
        #store radius of each circle as percentage(sum of all must at all times add up to 100.0%)
        self.wradii = [7.83, 30.9006201171875, 61.2693798828125]
        #starting angle for each circle (0-360).
        self.startangle:List[float] = [0, 42, 33]
        #text projection: 0 = Flat, 1 = perpendicular to center, 2 = radial from center
        self.projection:List[int] = [1, 2, 2]
        self.wheeltextsize:List[int] = [10,10,10,10]
        self.wheelcolorpattern:int = 0              #pattern
        self.wheeledge:float = 0.01                 #overlapping decorative edge
        self.wheellinewidth:float = 2.
        self.wheellinecolor:str = '#ffffff'         #initial color of lines
        self.wheeltextcolor:str = '#ffffff'         #initial color of text
        self.wheelconnections:List[int] = [0,0,0]   #ids of connected signals
        #temp variables to pass index values
        self.wheelx:int = 0
        self.wheelz:int = 0
        #temp vars to pass mouse location (angleX+radiusZ)
        self.wheellocationx:float = 0.
        self.wheellocationz:float = 0.
        self.wheelaspect:float = 1.0

        # a nicer demo flavor wheel


        self.samplingSemaphore = QSemaphore(1)
        self.profileDataSemaphore = QSemaphore(1)
        self.messagesemaphore = QSemaphore(1)
        self.errorsemaphore = QSemaphore(1)
        self.serialsemaphore = QSemaphore(1)
        self.seriallogsemaphore = QSemaphore(1)
        self.eventactionsemaphore = QSemaphore(1)
        self.updateBackgroundSemaphore = QSemaphore(1)
        self.alarmSemaphore = QSemaphore(1)
        self.rampSoakSemaphore = QSemaphore(1)

        #flag to plot cross lines from mouse
        self.crossmarker:bool = False
        self.crossmouseid:Optional[int] = None # connect mouse signal id
        self.onreleaseid:Optional[int] = None # connect release signal id

        #
        self.analyzer_connect_id = None # analyzer connect signal id


        #########  temporary serial variables
        #temporary storage to pass values. Holds extra T3 and T4 values for center 309
        self.extra309T3:float = -1
        self.extra309T4:float = -1
        self.extra309TX:float = 0.

        #temporary storage to pass values. Holds all values retrieved from a Hottop roaster
        self.hottop_ET:float = -1
        self.hottop_BT:float = -1
        self.hottop_HEATER = 0 # 0-100
        self.hottop_MAIN_FAN = 0 # 0-10 (!)
        self.hottop_TX = 0.

        #temporary storage to pass values. Holds all values retrieved from an R1 roaster
        self.R1_DT:float = -1
        self.R1_BT:float = -1
        self.R1_BT_ROR:float = -1
        self.R1_EXIT_TEMP:float = -1
        self.R1_HEATER:float = 0 # 0-9
        self.R1_FAN:float = 0 # 0-12
        self.R1_DRUM:float = 0 # 1-9
        self.R1_VOLTAGE:float = 0 # 0-300
        self.R1_TX:float = 0.
        self.R1_STATE:int = 0
        self.R1_FAN_RPM:float = 0
        self.R1_STATE_STR:str = ''

        #used by extra device +ArduinoTC4_XX to pass values
        self.extraArduinoT1:float = 0.  # Arduino T3: chan 3
        self.extraArduinoT2:float = 0.  # Arduino T4: chan 4
        self.extraArduinoT3:float = 0.  # Arduino T5: heater duty %
        self.extraArduinoT4:float = 0.  # Arduino T6: fan duty %
        self.extraArduinoT5:float = 0.  # Arduino T7: SV
        self.extraArduinoT6:float = 0.  # Arduino T8: TC4 internal ambient temperature

        #used by extra device +Program_34, +Program_56, +Program_78 and +Program_910 to pass values
        self.program_t3:float = -1
        self.program_t4:float = -1
        self.program_t5:float = -1
        self.program_t6:float = -1
        self.program_t7:float = -1
        self.program_t8:float = -1
        self.program_t9:float = -1
        self.program_t10:float = -1

        #temporary storage to pass values. Holds the power % ducty cycle of Fuji PIDs and ET-BT
        self.dutycycle:float = -1
        self.dutycycleTX:float = 0.
        self.currentpidsv:float = 0.

        self.linecount:Optional[int] = None # linecount cache for resetlines(); has to be reset if visibility of ET/BT or extra lines or background ET/BT changes
        self.deltalinecount:Optional[int] = None # deltalinecount cache for resetdeltalines(); has to be reset if visibility of deltaET/deltaBT or background deltaET/deltaBT

        #variables to organize the delayed update of the backgrounds for bitblitting
        self.ax_background:Optional[mpl.backends._backend_agg.BufferRegion] = None # pylint: disable=c-extension-no-member
        self.block_update:bool = False

        # flag to toggle between Temp and RoR scale of xy-display
        self.fmt_data_RoR:bool = False
        self.fmt_data_ON:bool = True #; if False, the xy-display is deactivated
        # toggle between using the 0: y-cursor pos, 1: BT@x, 2: ET@x, 3: BTB@x, 4: ETB@x (thus BT, ET or the corresponding background curve data at cursor position x)
        # to display the y of the cursor coordinates
        self.fmt_data_curve = 0
        self.running_LCDs = 0 # if not 0 and not sampling visible LCDs show the readings at the cursor position of 1: foreground profile, 2: background profile

        #holds last values calculated from plotter
        self.plotterstack:List[float] = [0]*10
        #holds results for each equation (9 total)
        self.plotterequationresults:List[List[float]] = [[],[],[],[],[],[],[],[],[]]
        #message string for plotter
        self.plottermessage:str = ''

        self.alarm_popup_timout:int = 10


        #buffers for real time symbolic evaluation
        self.RTtemp1:float = 0.
        self.RTtemp2:float = 0.
        self.RTextratemp1:List[float] = []
        self.RTextratemp2:List[float] = []
        self.RTextratx:List[float] = []

        #Extras more info
        self.idx_met:Optional[int] = None
        self.showmet:bool = False
        self.met_annotate:Optional['Annotation'] = None
        self.met_timex_temp1_delta:Optional[Tuple[float,float,Optional[float]]] = None # (time, temp, time delta) tuple
        self.extendevents:bool = True
        self.statssummary:bool = False
        self.showtimeguide:bool = True
        self.statsmaxchrperline = 30

        #EnergyUse
        self.energyunits: Final[List[str]] = ['BTU', 'kJ', 'kCal', 'kWh', 'hph']
        self.powerunits: Final[List[str]] = ['BTU/h', 'kJ/h', 'kCal/h', 'kW', 'hp']
        self.sourcenames: Final[List[str]] = ['LPG', 'NG', QApplication.translate('ComboBox','Elec')]
        ## setup defaults (stored in app :
        # Burners
        self.loadlabels_setup:List[str] = ['']*4                   # burner labels
        self.loadratings_setup:List[float] = [0]*4                   # in ratingunits
        self.ratingunits_setup:List[int] = [0]*4                   # index in list self.powerunits
        self.sourcetypes_setup:List[int] = [0]*4                   # index in list self.sourcenames
        self.load_etypes_setup:List[int] = [0]*4                   # index of the etype that is the gas/burner setting
        self.presssure_percents_setup:List[bool] = [False]*4       # event value in pressure percent
        self.loadevent_zeropcts_setup:List[int] = [0]*4            # event value corresponding to 0 percent
        self.loadevent_hundpcts_setup:List[int] = [100]*4          # event value corresponding to 100 percent
        # Protocol
        self.preheatDuration_setup:int = 0                         # length of preheat in seconds
        self.preheatenergies_setup:List[float] = [0]*4             # rating of the preheat burner
        self.betweenbatchDuration_setup:int = 0                    # length of bbp in seconds
        self.betweenbatchenergies_setup:List[float] = [0]*4        # rating of the between batch burner
        self.coolingDuration_setup:int = 0                         # length of cooling in seconds
        self.coolingenergies_setup:List[float] = [0]*4             # rating of the cooling burner
        self.betweenbatch_after_preheat_setup:bool = True          # True adds BBP to pre-heating (and cooling) for the first batch.
        self.electricEnergyMix_setup:int = 0                       # the amount of renewable electric energy in the energy mix in %
        # Others
        self.energyresultunit_setup:int = 0                        # index in list self.powerunits
        self.kind_list: Final[List[str]] = [QApplication.translate('Label','Preheat Measured'),
                          QApplication.translate('Label','Preheat %'),
                          QApplication.translate('Label','BBP Measured'),
                          QApplication.translate('Label','BBP %'),
                          QApplication.translate('Label','Cooling Measured'),
                          QApplication.translate('Label','Cooling %'),
                          QApplication.translate('Label','Continuous'),
                          QApplication.translate('Label','Roast Event')]

        ## working variables (stored in .alog profiles):
        # Burners
        self.loadlabels = self.loadlabels_setup[:]               # burner labels
        self.loadratings = self.loadratings_setup[:]             # in ratingunits
        self.ratingunits = self.ratingunits_setup[:]             # index in list self.heatunits
        self.sourcetypes = self.sourcetypes_setup[:]             # index in list self.sourcetypes
        self.load_etypes = self.load_etypes_setup[:]             # index of the etype that is the gas/burner setting
        self.presssure_percents = self.presssure_percents_setup[:]  # event value in pressure percent
        self.loadevent_zeropcts = self.loadevent_zeropcts_setup[:]  # event value corresponding to 0 percent
        self.loadevent_hundpcts = self.loadevent_hundpcts_setup[:]  # event value corresponding to 100 percent
        # Protocol
        self.preheatDuration = self.preheatDuration_setup               # length of preheat in seconds
        self.preheatenergies = self.preheatenergies_setup[:]            # rating of the preheat burner
        self.betweenbatchDuration = self.betweenbatchDuration_setup     # length of bbp in seconds
        self.betweenbatchenergies = self.betweenbatchenergies_setup[:]  # rating of the between batch burner
        self.coolingDuration = self.coolingDuration_setup               # length of cooling in seconds
        self.coolingenergies = self.coolingenergies_setup[:]            # rating of the cooling burner
        self.betweenbatch_after_preheat = self.betweenbatch_after_preheat_setup # True if after preheat a BBP is done
        self.electricEnergyMix = self.electricEnergyMix_setup        # the amount of renewable electric energy in the energy mix in %

        #mouse cross lines measurement
        self.baseX:Optional[float] = None
        self.baseY:Optional[float] = None
        self.base_horizontalcrossline:Optional['Line2D'] = None
        self.base_verticalcrossline:Optional['Line2D'] = None
        self.base_messagevisible:bool = False

        #threshold for deltaE color difference comparisons
        self.colorDifferenceThreshold = 20

        #references to legend objects
        self.handles:List['Line2D'] = []
        self.labels:List[str] = []
        self.legend_lines:List['Line2D'] = []

        #used for picked event messages
        self.eventmessage = ''
        self.backgroundeventmessage = ''
        self.eventmessagetimer:Optional[QTimer] = None

        self.resizeredrawing = 0 # holds timestamp of last resize triggered redraw

        self.logoimg:Optional['npt.NDArray'] = None # holds the background logo image
        self.analysisresultsloc_default: Final[Tuple[float, float]] = (.49, .5)
        self.analysisresultsloc:Tuple[float, float] = self.analysisresultsloc_default
        self.analysispickflag:bool = False
        self.analysisresultsstr:str = ''
        self.analysisstartchoice:int = 1
        self.analysisoffset:int = 180
        self.curvefitstartchoice:int = 0
        self.curvefitoffset:int = 180
        self.segmentresultsloc_default: Final[Tuple[float, float]] = (.5, .5)
        self.segmentresultsloc:Tuple[float, float] = self.segmentresultsloc_default
        self.segmentpickflag:bool = False
        self.segmentdeltathreshold:float = 0.6
        self.segmentsamplesthreshold:int = 3

        self.stats_summary_rect:Optional[patches.Rectangle] = None

        # temp vars used to truncate title and statistic line (x_label) to width of MPL canvas
        self.title_text:Optional[str] = None
        self.title_artist:Optional['Text'] = None
        self.title_width:Optional[float] = None
        self.background_title_width = 0
        self.xlabel_text:Optional[str] = None
        self.xlabel_artist:Optional['Text'] = None
        self.xlabel_width:Optional[float] = None

        self.lazyredraw_on_resize_timer:QTimer =  QTimer()
        self.lazyredraw_on_resize_timer.timeout.connect(self.lazyredraw_on_resize)
        self.lazyredraw_on_resize_timer.setSingleShot(True)

        self.updategraphicsSignal.connect(self.updategraphics)
        self.updateLargeLCDsSignal.connect(self.updateLargeLCDs)
        self.updateLargeLCDsReadingsSignal.connect(self.updateLargeLCDsReadings)
        self.setTimerLargeLCDcolorSignal.connect(self.setTimerLargeLCDcolor)
        self.showAlarmPopupSignal.connect(self.showAlarmPopup)
        self.updateLargeLCDsTimeSignal.connect(self.updateLargeLCDsTime)
        self.fileDirtySignal.connect(self.fileDirty)
        self.fileCleanSignal.connect(self.fileClean)
        self.markChargeSignal.connect(self.markChargeDelay)
        self.markDRYSignal.connect(self.markDRYTrigger)
        self.markFCsSignal.connect(self.markFCsTrigger)
        self.markFCeSignal.connect(self.markFCeTrigger)
        self.markSCsSignal.connect(self.markSCsTrigger)
        self.markSCeSignal.connect(self.markSCeTrigger)
        self.markDropSignal.connect(self.markDropTrigger)
        self.markCoolSignal.connect(self.markCoolTrigger)
        self.toggleMonitorSignal.connect(self.toggleMonitorTigger)
        self.toggleRecorderSignal.connect(self.toggleRecorderTigger)
        self.processAlarmSignal.connect(self.processAlarm, type=Qt.ConnectionType.QueuedConnection) # type: ignore # queued to avoid deadlock between RampSoak processing and EventRecordAction, both accessing the same critical section protected by profileDataSemaphore
        self.alarmsetSignal.connect(self.selectAlarmSet)
        self.moveBackgroundSignal.connect(self.moveBackgroundAndRedraw)
        self.eventRecordSignal.connect(self.EventRecordSlot)
        self.showCurveSignal.connect(self.showCurve)
        self.showExtraCurveSignal.connect(self.showExtraCurve)
        self.showEventsSignal.connect(self.showEvents)
        self.showBackgroundEventsSignal.connect(self.showBackgroundEvents)

    #NOTE: empty Figure is initially drawn at the end of self.awsettingsload()
    #################################    FUNCTIONS    ###################################
    #####################################################################################

    # toggles the y cursor coordinate see self.qmc.fmt_data_curve
    def nextFmtDataCurve(self):
        self.fmt_data_curve = (self.fmt_data_curve+1) % 5
        if self.backgroundprofile is None and self.fmt_data_curve in [3,4]:
            self.fmt_data_curve = 0
        if len(self.timex)<3 and self.fmt_data_curve in [1,2]:
            if self.backgroundprofile is None:
                self.fmt_data_curve = 0
            else:
                self.fmt_data_curve = 3
        s = 'cursor position'
        if self.fmt_data_curve == 1:
            s = self.aw.BTname
        elif self.fmt_data_curve == 2:
            s = self.aw.ETname
        elif self.fmt_data_curve == 3:
            s = f'{QApplication.translate("Label","Background")} {self.aw.BTname}'
        elif self.fmt_data_curve == 4:
            s = f'{QApplication.translate("Label","Background")} {self.aw.ETname}'
        self.aw.ntb.update_message()
        self.aw.sendmessage(QApplication.translate('Message', 'set y-coordinate to {}').format(s))

    @pyqtSlot(str, bool)
    def showCurve(self, name: str, state: bool):
        changed:bool = False
        if name == 'ET' and self.ETcurve != state:
            self.ETcurve = state
            changed = True
        elif name == 'BT' and self.BTcurve != state:
            self.BTcurve = state
            changed = True
        elif name == 'DeltaET' and self.DeltaETflag != state:
            self.DeltaETflag = state
            changed = True
        elif name == 'DeltaBT' and self.DeltaBTflag != state:
            self.DeltaBTflag = state
            changed = True
        elif name == 'BackgroundET' and self.backgroundETcurve != state:
            self.backgroundETcurve = state
            changed = True
        elif name == 'BackgroundBT' and self.backgroundBTcurve != state:
            self.backgroundBTcurve = state
            changed = True
        if changed:
            self.redraw(recomputeAllDeltas=False,smooth=False)

    @pyqtSlot(int, str, bool)
    def showExtraCurve(self, extra_device: int, curve: str, state: bool):
        assert self.aw is not None
        if curve.strip() == 'T1' and len(self.aw.extraCurveVisibility1) > extra_device and self.aw.extraCurveVisibility1[extra_device] != state:
            self.aw.extraCurveVisibility1[extra_device] = state
            self.redraw(recomputeAllDeltas=False,smooth=False)
        elif curve.strip() == 'T2' and len(self.aw.extraCurveVisibility2) > extra_device and self.aw.extraCurveVisibility2[extra_device] != state:
            self.aw.extraCurveVisibility2[extra_device] = state
            self.redraw(recomputeAllDeltas=False,smooth=False)

    @pyqtSlot(int, bool)
    def showEvents(self, event_type: int, state: bool):
        event_type -= 1
        if len(self.showEtypes) > event_type > 0 and self.showEtypes[event_type] != state:
            self.showEtypes[event_type] = state
            self.redraw(recomputeAllDeltas=False,smooth=False)

    @pyqtSlot(bool)
    def showBackgroundEvents(self, state: bool):
        if state != self.backgroundeventsflag:
            self.backgroundeventsflag = state
            self.redraw(recomputeAllDeltas=False,smooth=False)

    def ax_lines_clear(self):
        if self.ax is not None:
            if isinstance(self.ax.lines,list): # MPL < v3.5
                self.ax.lines = []
            else:
                while len(self.ax.lines) > 0:
                    self.ax.lines[0].remove()

    def ax_annotations_clear(self):
        for la in self.l_annotations + self.l_background_annotations:
            if la:
                try:
                    la.remove()
                except Exception: # pylint: disable=broad-except
                    pass

    # set current burner settings as defaults
    def setEnergyLoadDefaults(self):
        self.loadlabels_setup = self.loadlabels[:]
        self.loadratings_setup = self.loadratings[:]
        self.ratingunits_setup = self.ratingunits[:]
        self.sourcetypes_setup = self.sourcetypes[:]
        self.load_etypes_setup = self.load_etypes[:]
        self.presssure_percents_setup = self.presssure_percents[:]
        self.loadevent_zeropcts_setup = self.loadevent_zeropcts[:]
        self.loadevent_hundpcts_setup = self.loadevent_hundpcts[:]
        self.electricEnergyMix_setup = self.electricEnergyMix

    # restore burner settings to their defaults
    def restoreEnergyLoadDefaults(self):
        self.loadlabels = self.loadlabels_setup[:]
        self.loadratings = self.loadratings_setup[:]
        self.ratingunits = self.ratingunits_setup[:]
        self.sourcetypes = self.sourcetypes_setup[:]
        self.load_etypes = self.load_etypes_setup[:]
        self.presssure_percents = self.presssure_percents_setup[:]
        self.loadevent_zeropcts = self.loadevent_zeropcts_setup[:]
        self.loadevent_hundpcts = self.loadevent_hundpcts_setup[:]
        self.electricEnergyMix = self.electricEnergyMix_setup

    # set current protocol settings as defaults
    def setEnergyProtocolDefaults(self):
        self.preheatDuration_setup = self.preheatDuration
        self.preheatenergies_setup = self.preheatenergies[:]
        self.betweenbatchDuration_setup = self.betweenbatchDuration
        self.betweenbatchenergies_setup = self.betweenbatchenergies[:]
        self.coolingDuration_setup = self.coolingDuration
        self.coolingenergies_setup = self.coolingenergies[:]
        self.betweenbatch_after_preheat_setup = self.betweenbatch_after_preheat

    # restore protocol settings to their defaults
    def restoreEnergyProtocolDefaults(self):
        self.preheatDuration = self.preheatDuration_setup
        self.preheatenergies = self.preheatenergies_setup[:]
        self.betweenbatchDuration = self.betweenbatchDuration_setup
        self.betweenbatchenergies = self.betweenbatchenergies_setup[:]
        self.coolingDuration = self.coolingDuration_setup
        self.coolingenergies = self.coolingenergies_setup[:]
        self.betweenbatch_after_preheat = self.betweenbatch_after_preheat_setup

    @pyqtSlot()
    def fileDirty(self):
        self.safesaveflag = True
        self.aw.updateWindowTitle()

    @pyqtSlot()
    def fileClean(self):
        self.safesaveflag = False
        self.aw.updateWindowTitle()

    def lazyredraw_on_resize(self):
        self.lazyredraw(recomputeAllDeltas=False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # we only trigger a redraw on resize if a watermark is displayed to fix its aspect ratio
        if self.aw.redrawOnResize and self.aw.logofilename != '':
            dw = event.size().width() - event.oldSize().width()   # width change
            dh = event.size().height() - event.oldSize().height() # height change
#            t = libtime.time()
#            # ensure that we redraw during resize only once per second
#            if self.resizeredrawing + 0.5 < t and ((dw != 0) or (dh != 0)):
#                self.resizeredrawing = t
#                QTimer.singleShot(1, lazyredraw_on_resize)
            if ((dw != 0) or (dh != 0)):
                self.lazyredraw_on_resize_timer.start(10)


    # update the self.deltaBTspan and deltaETspan from the given sampling interval, self.deltaETsamples and self.deltaBTsamples
    # interval is expected in seconds (either from the profile on load or from the sampling interval set for recording)
    # both deltaBTsamples and deltaETsamples are at least one
    def updateDeltaSamples(self):
        if self.flagstart or self.profile_sampling_interval is None:
            speed = self.timeclock.getBase()/1000
            interval = speed * (self.delay / 1000)
        else:
            interval = self.profile_sampling_interval
        self.deltaBTsamples = max(1,int(round(self.deltaBTspan / interval)))
        self.deltaETsamples = max(1,int(round(self.deltaETspan / interval)))

    def updateBackground(self):
        if not self.block_update and self.ax is not None:
            try:
                self.updateBackgroundSemaphore.acquire(1)
                self.block_update = True
                self.doUpdate()
            finally:
                if self.updateBackgroundSemaphore.available() < 1:
                    self.updateBackgroundSemaphore.release(1)

    def doUpdate(self):
        if not self.designerflag:
            self.resetlinecountcaches() # ensure that the line counts are up to date
            self.resetlines() # get rid of projection, cross lines and AUC line

            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    self.fig.canvas.draw() # this triggers _draw_event(self,evt)
                #self.fig.canvas.draw_idle() # ask the canvas to kindly draw it self some time in the future when Qt thinks it is convenient
                # make sure that the GUI framework has a chance to run its event loop
                # and clear any GUI events.  This needs to be in a try/except block
                # because the default implementation of this method is to raise
                # NotImplementedError
                #self.fig.canvas.flush_events() # don't FLUSH event as this can lead to a second redraw started from within the same GUI thread and
                # causen a hang by the blocked semaphore
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            if self.ax is not None:
                self.ax_background = self.fig.canvas.copy_from_bbox(self.ax.get_figure().bbox)

        self.block_update = False

    def getetypes(self):
        if len(self.etypes) == 4:
            self.etypes.append('--')
        return self.etypes

    def etypesf(self, i:int) -> str:
        if len(self.etypes) == 4:
            self.etypes.append('--')
        if i > 4:
            return self.etypes[i-5]
        return self.etypes[i]

    def Betypesf(self, i, prefix=False):
        if len(self.Betypes) == 4:
            self.Betypes.append('--')
        if prefix and i < 4:
            return 'Background'+self.Betypes[i]
        return self.Betypes[i]

    def ambientTempSourceAvg(self) -> Optional[float]:
        res:Optional[float] = None
        if self.ambientTempSource:
            try:
                start = 0
                end = len(self.temp1) - 1
                if self.timeindex[0] > -1: # CHARGE
                    start = self.timeindex[0]
                if self.timeindex[6] > 0: # DROP
                    end = self.timeindex[6]
                if self.ambientTempSource == 1: # from ET
                    res = float(numpy.mean([e for e in self.temp1[start:end] if e is not None and e != -1]))
                elif self.ambientTempSource == 2: # from BT
                    res = float(numpy.mean([e for e in self.temp2[start:end] if e is not None and e != -1]))
                elif self.ambientTempSource > 2 and ((self.ambientTempSource - 3) < (2*len(self.extradevices))):
                    # from an extra device
                    if (self.ambientTempSource)%2==0:
                        res = float(numpy.mean([e for e in self.extratemp2[(self.ambientTempSource - 3)//2][start:end] if e is not None and e != -1]))
                    else:
                        res = float(numpy.mean([e for e in self.extratemp1[(self.ambientTempSource - 3)//2][start:end] if e is not None and e != -1]))
            except Exception as ex: # pylint: disable=broad-except # the array to average over might get empty and mean thus invoking an exception
                _log.exception(ex)
        if res is not None:
            res = self.aw.float2float(res)
        return res

    def updateAmbientTempFromPhidgetModulesOrCurve(self):
        if not self.ambientTempSource:
            AT_device = None
            try:
                AT_device = self.extradevices.index(36)
            except Exception: # pylint: disable=broad-except
                try:
                    AT_device = self.extradevices.index(60)
                except Exception: # pylint: disable=broad-except
                    pass
            if AT_device is not None:
                # 1048_AT channel #36, TMP1101_AT channel #60
                # we try to access that devices first channel to retrieve the temperature data
                try:
                    ser = self.aw.extraser[AT_device]
                    if ser.PhidgetTemperatureSensor is not None:
                        at = ser.PhidgetTemperatureSensor[0].getTemperature()
                        if self.mode == 'F':
                            at = self.aw.float2float(fromCtoF(at))
                        self.ambientTemp = self.aw.float2float(at)
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
            # in case the AT channel of the 1048 or the TMP1101 is not used as extra device, we try to attach to it anyhow and read the temp off
            elif self.ambientTemp == 0.0 and self.device in [34,58]: # Phidget 1048 or TMP1101 channel 4 (use internal temp)
                try:
                    if self.aw.ser.PhidgetTemperatureSensor is not None and self.aw.ser.PhidgetTemperatureSensor[0].getAttached():
                        from Phidget22.Devices.TemperatureSensor import TemperatureSensor as PhidgetTemperatureSensor # type: ignore
                        ambient = PhidgetTemperatureSensor()
                        ambient.setDeviceSerialNumber(self.aw.ser.PhidgetTemperatureSensor[0].getDeviceSerialNumber())
                        if self.device == 58:
                            ambient.setHubPort(self.aw.ser.PhidgetTemperatureSensor[0].getHubPort())
                        ambient.setChannel(4)
                        ambient.openWaitForAttachment(1000) # timeout in ms
                        if self.phidgetRemoteOnlyFlag:
                            libtime.sleep(.8)
                        else:
                            libtime.sleep(.5)
                        t = ambient.getTemperature()
                        if self.mode == 'F':
                            self.ambientTemp = self.aw.float2float(fromCtoF(t))
                        else:
                            self.ambientTemp = self.aw.float2float(t)
                        if ambient.getAttached():
                            ambient.close()
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
        res = self.ambientTempSourceAvg()
        if res is not None and (isinstance(res, (float,int))) and not math.isnan(res):
            self.ambientTemp = self.aw.float2float(float(res))

    def updateAmbientTemp(self):
        self.updateAmbientTempFromPhidgetModulesOrCurve()
        try:
            self.startPhidgetManager()
            self.getAmbientData()
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    # eventsvalues maps the given internal event value v to an external event int value as displayed to the user as special event value
    # v is expected to be float value of range [-11.0,11.0]
    # negative values are not used as event values, but as step arguments in extra button definitions
    #   11.0 => 100
    #   10.1 => 91
    #   10.0 => 90
    #   1.1 => 1
    #   1.0 => 0
    #     0 => 0
    #  -1.0 => 0
    #  -1.1 => -1
    # -10.0 => -90
    # -10.1 => -91
    # -11.0 => -100
    @staticmethod
    def eventsInternal2ExternalValue(v:Optional[float]) -> int:
        if v is None:
            return 0
        if -1.0 <= v <= 1.0:
            return 0
        if v < -1.0:
            return -(int(round(abs(v)*10)) - 10)
        return int(round(v*10)) - 10

    # the inverse of eventsInternal2ExternalValue, converting an external to an internal event value
    @staticmethod
    def eventsExternal2InternalValue(v:float) -> float:
        if -1.0 < v < 1.0:
            return 1.0
        if v >= 1.0:
            return v/10. + 1.
        return v/10. - 1.

    # eventsvalues maps the given number v to a string to be displayed to the user as special event value
    # v is expected to be float value of range [0-10]
    # negative values are mapped to ""
    # 0.1 to "1"
    # ..
    # 1.0 to "10"
    # ..
    # 10.0 to "100"
    def eventsvalues(self, v:float) -> str:
        return str(self.eventsInternal2ExternalValue(v))

    # 100.0 to "10" and 10.1 to "1"
    @staticmethod
    def eventsvaluesShort(v:float) -> str:
        value = v*10. - 10.
        if value == -10:
            return '0'
        if value < 0:
            return ''
        return str(int(round(value)))

    # the inverse to eventsvalues above (string -> value)
    def str2eventsvalue(self, s:str) -> float:
        st = s.strip()
        if st is None or len(st) == 0:
            return -1
        return self.eventsExternal2InternalValue(float(st))

    def fit_titles(self):
        #truncate title and statistic line to width of axis system to avoid that the MPL canvas goes into miser mode
        try:
            if self.ax is not None:
                r = None
                try:
                    r = self.fig.canvas.get_renderer() # MPL fails on savePDF with 'FigureCanvasPdf' object has no attribute 'get_renderer'
                except Exception: # pylint: disable=broad-except
                    pass
                if r is None:
                    ax_width = self.ax.get_window_extent().width
                else:
                    ax_width = self.ax.get_window_extent(renderer=r).width
                ax_width_for_title = ax_width - self.background_title_width
                redraw = False
                if self.title_text is not None and self.title_artist is not None and self.title_width is not None:
                    try:
                        prev_title_text = self.title_artist.get_text()
                        render = None
                        try:
                            render = self.fig.canvas.get_renderer()
                        except Exception: # pylint: disable=broad-except
                            # FigureCanvasPdf does not feature a renderer and thus the abbreviation mechanism does not work for PDF export
                            pass
                        if render is not None and ax_width_for_title <= self.title_width:
                            chars = max(3,int(ax_width_for_title / (self.title_width / len(self.title_text))) - 2)
                            self.title_artist.set_text(f'{self.title_text[:chars].strip()}...')
                        else:
                            self.title_artist.set_text(self.title_text)
                        if prev_title_text != self.title_artist.get_text():
                            redraw = True
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                if self.xlabel_text is not None and self.xlabel_artist is not None and self.xlabel_width is not None:
                    try:
                        prev_xlabel_text = self.xlabel_artist.get_text()
                        if ax_width <= self.xlabel_width:
                            chars = max(3,int(ax_width / (self.xlabel_width / len(self.xlabel_text))) - 2)
                            self.xlabel_artist.set_text(f'{self.xlabel_text[:chars].strip()}...')
                        else:
                            self.xlabel_artist.set_text(self.xlabel_text)
                        if prev_xlabel_text != self.xlabel_artist.get_text():
                            redraw = True
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                try:
                    if redraw:
                        # Temporarily disconnect any callbacks to the draw event...
                        # (To avoid recursion)
                        func_handles = self.fig.canvas.callbacks.callbacks['draw_event']
                        self.fig.canvas.callbacks.callbacks['draw_event'] = {}
                        # Re-draw the figure..
                        with warnings.catch_warnings():
                            warnings.simplefilter('ignore')
                            self.fig.canvas.draw()
                        # Reset the draw event callbacks
                        self.fig.canvas.callbacks.callbacks['draw_event'] = func_handles
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    # hook up to mpls event handling framework for draw events
    # this is emitted after the canvas has finished a full redraw
    def _draw_event(self, _):
        #self.fig.canvas.flush_events() # THIS prevents the black border on >Qt5.5, but slows down things (especially resizings) on redraw otherwise!!!
        self.ax_background = None
        # we trigger a re-fit of the titles to fit to the resized MPL canvas
        self.fit_titles()

    @pyqtSlot()
    def sendeventmessage(self):
        self.eventmessagetimer = None
        if len(self.backgroundeventmessage) != 0:
            self.aw.sendmessage(self.backgroundeventmessage,append=True)
            self.backgroundeventmessage = ''
            self.starteventmessagetimer(2)  #hack to ensure that the background event message is written first
            return
        if len(self.eventmessage) != 0:
            self.aw.sendmessage(self.eventmessage,append=True)
            self.eventmessage = ''

    def starteventmessagetimer(self,time=120):
        if self.eventmessagetimer is not None:
            self.eventmessagetimer.stop()
            self.eventmessagetimer.deleteLater()
        self.eventmessagetimer = QTimer()
        self.eventmessagetimer.timeout.connect(self.sendeventmessage)
        self.eventmessagetimer.setSingleShot(True)
        self.eventmessagetimer.start(time)

    def onpick(self,event):
        try:
            # display MET information by clicking on the MET marker
            if (isinstance(event.artist, mpl.text.Annotation) and self.showmet and event.artist in [self.met_annotate] and
                    self.met_timex_temp1_delta is not None and self.met_timex_temp1_delta[2] is not None):
                if  self.met_timex_temp1_delta[2] >= 0:
                    met_time_str = str(self.met_timex_temp1_delta[2])
                    met_time_msg = QApplication.translate('Message','seconds before FCs')
                else:
                    met_time_str = str(-1*self.met_timex_temp1_delta[2])
                    met_time_msg = QApplication.translate('Message','seconds after FCs')

                self.aw.sendmessage(f'MET {self.aw.float2float(self.met_timex_temp1_delta[1],1)}{self.mode} @ {stringfromseconds(self.met_timex_temp1_delta[0])}, {met_time_str} {met_time_msg}')

            # the analysis results were clicked
            elif self.aw.analysisresultsanno is not None and isinstance(event.artist, mpl.text.Annotation) and event.artist in [self.aw.analysisresultsanno]:
                self.analysispickflag = True

            # the segment results were clicked
            elif self.aw.segmentresultsanno is not None and isinstance(event.artist, mpl.text.Annotation) and event.artist in [self.aw.segmentresultsanno]:
                self.segmentpickflag = True

            # toggle visibility of graph lines by clicking on the legend
            elif self.legend is not None and event.artist != self.legend and isinstance(event.artist, (mpl.lines.Line2D, mpl.text.Text)) \
                and event.artist not in [self.l_backgroundeventtype1dots,self.l_backgroundeventtype2dots,self.l_backgroundeventtype3dots,self.l_backgroundeventtype4dots] \
                and event.artist not in [self.l_eventtype1dots,self.l_eventtype2dots,self.l_eventtype3dots,self.l_eventtype4dots]:
                idx = None
                # deltaLabelMathPrefix (legend label)
                # deltaLabelUTF8 (artist)
                if isinstance(event.artist, mpl.text.Text):
                    artist = None
                    label = None
                    try:
                        label = event.artist.get_text()
                        idx = self.labels.index(label)
                    except Exception: # pylint: disable=broad-except
                        pass
                    if label is not None and idx is not None:
                        if label == self.aw.ETname:
                            label = 'ET'  #allows for a match below to the label in legend_lines
                            try:
                                for a in self.l_eteventannos:
                                    a.set_visible(not a.get_visible())
                                if self.met_annotate is not None:
                                    self.met_annotate.set_visible(not self.met_annotate.get_visible())
                            except Exception: # pylint: disable=broad-except
                                pass
                        elif label == self.aw.BTname:
                            label = 'BT'  #allows for a match below to the label in legend_lines
                            try:
                                for a in self.l_bteventannos:
                                    a.set_visible(not a.get_visible())
                            except Exception: # pylint: disable=broad-except
                                pass
                        try:
                            # toggle also the visibility of the legend handle
                            clean_label = label.replace(deltaLabelMathPrefix,deltaLabelUTF8)
                            artist = next((x for x in self.legend_lines if x.get_label() == clean_label), None)
                            if artist:
                                artist.set_visible(not artist.get_visible())
                        except Exception: # pylint: disable=broad-except
                            pass
                    # toggle the visibility of the corresponding line
                    if idx is not None and artist:
                        artist = self.handles[idx]
                        artist.set_visible(not artist.get_visible())
                        if self.eventsGraphflag in [2,3,4]:
                            # if events are rendered in Combo style we need to hide also the corresponding annotations:
                            try:
                                i = [self.aw.arabicReshape(et) for et in self.etypes[:4]].index(label)
                                if i == 0:
                                    for a in self.l_eventtype1annos:
                                        a.set_visible(not a.get_visible())
                                elif i == 1:
                                    for a in self.l_eventtype2annos:
                                        a.set_visible(not a.get_visible())
                                elif i == 2:
                                    for a in self.l_eventtype3annos:
                                        a.set_visible(not a.get_visible())
                                elif i == 3:
                                    for a in self.l_eventtype4annos:
                                        a.set_visible(not a.get_visible())
                            except Exception: # pylint: disable=broad-except
                                pass


            # show event information by clicking on event lines in step, step+ and combo modes
            elif isinstance(event.artist, mpl.lines.Line2D):
                if isinstance(event.ind, int):
                    ind = event.ind
                else:
                    if not any(event.ind):
                        return
                    ind = event.ind[0]
                digits = (1 if self.LCDdecimalplaces else 0)
                if event.artist in [self.l_backgroundeventtype1dots,self.l_backgroundeventtype2dots,self.l_backgroundeventtype3dots,self.l_backgroundeventtype4dots]:
                    timex = self.backgroundtime2index(event.artist.get_xdata()[ind])
                    for i, bge in enumerate(self.backgroundEvents):
                        if (re.search(
                                    f'(Background{self.Betypesf(self.backgroundEtypes[i])})',
                                    str(event.artist))
                                and (timex in [bge,bge -1,bge + 1])):
                            if self.timeindex[0] != -1:
                                start = self.timex[self.timeindex[0]]
                            else:
                                start = 0
                            if len(self.backgroundeventmessage) != 0:
                                self.backgroundeventmessage += ' | '
                            else:
                                self.backgroundeventmessage += 'Background: '
                            self.backgroundeventmessage = f'{self.backgroundeventmessage}{self.Betypesf(self.backgroundEtypes[i])} = {self.eventsvalues(self.backgroundEvalues[i])}'
                            if self.renderEventsDescr and self.backgroundEStrings[i] and self.backgroundEStrings[i]!='':
                                self.backgroundeventmessage = f'{self.backgroundeventmessage} ({self.backgroundEStrings[i].strip()[:self.eventslabelschars]})'
                            self.backgroundeventmessage = f'{self.backgroundeventmessage} @ {(stringfromseconds(self.timeB[bge] - start))} {self.aw.float2float(self.temp2B[bge],digits)}{self.mode}'
                            self.starteventmessagetimer()
                            break
                elif event.artist in [self.l_eventtype1dots,self.l_eventtype2dots,self.l_eventtype3dots,self.l_eventtype4dots]:
                    timex = self.time2index(event.artist.get_xdata()[ind])
                    for i, spe in enumerate(self.specialevents):
                        if (re.search(
                                    f'({self.etypesf(self.specialeventstype[i])})',
                                    str(event.artist))
                                and (timex in [spe, spe + 1, spe -1])):
                            if self.timeindex[0] != -1:
                                start = self.timex[self.timeindex[0]]
                            else:
                                start = 0
                            if len(self.eventmessage) != 0:
                                self.eventmessage = f'{self.eventmessage} | '
                            self.eventmessage = f'{self.eventmessage}{self.etypesf(self.specialeventstype[i])} = {self.eventsvalues(self.specialeventsvalue[i])}'
                            if self.renderEventsDescr and self.specialeventsStrings[i] and self.specialeventsStrings[i]!='':
                                self.eventmessage = f'{self.eventmessage} ({self.specialeventsStrings[i].strip()[:self.eventslabelschars]})'
                            self.eventmessage = f'{self.eventmessage} @ {stringfromseconds(self.timex[spe] - start)} {self.aw.float2float(self.temp2[spe],digits)}{self.mode}'
                            self.starteventmessagetimer()
                            break
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' onpick() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))

    def onrelease_after_pick(self,_):
        if self.legend is not None:
            QTimer.singleShot(1,self.updateBackground)

    def onrelease(self,event):     # NOTE: onrelease() is connected/disconnected in togglecrosslines()
        try:
            if self.ax is None:
                return
            if event.button == 1:
                self.baseX,self.baseY = None, None
                try:
                    self.ax.lines.remove(self.base_horizontalcrossline)
                except Exception: # pylint: disable=broad-except
                    pass
                try:
                    self.ax.lines.remove(self.base_verticalcrossline)
                except Exception: # pylint: disable=broad-except
                    pass
                self.base_horizontalcrossline, self.base_verticalcrossline = None, None
            # save the location of analysis results after dragging
            if self.analysispickflag and self.aw.analysisresultsanno is not None:
                self.analysispickflag = False
                corners = self.ax.transAxes.inverted().transform(self.aw.analysisresultsanno.get_bbox_patch().get_extents())
                self.analysisresultsloc = (corners[0][0], corners[0][1] + (corners[1][1] - corners[0][1])/2)
            # save the location of segment results after dragging
            if self.segmentpickflag and self.aw.segmentresultsanno is not None:
                self.segmentpickflag = False
                corners = self.ax.transAxes.inverted().transform(self.aw.segmentresultsanno.get_bbox_patch().get_extents())
                self.segmentresultsloc = (corners[0][0], corners[0][1] + (corners[1][1] - corners[0][1])/2)
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' onclick() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))


    def disconnect_draggableannotations_motion_notifiers(self):
        cids = []
        try:
            if 'motion_notify_event' in self.fig.canvas.callbacks.callbacks:
                motion_notify_event_handlers = self.fig.canvas.callbacks.callbacks['motion_notify_event']
                for cid, func_ref in motion_notify_event_handlers.items():
                    func = func_ref()
                    if func.__self__ is not None: # a bound method
                        c = func.__self__.__class__
                        if c == mpl.offsetbox.DraggableAnnotation:
                            cids.append(cid)
            # disconnecting all established motion_notify_event_handlers of DraggableAnnotations
            for cid in cids:
                self.fig.canvas.mpl_disconnect(cid)
        except Exception: # pylint: disable=broad-except
            pass

    def onclick(self,event):
        try:
            if self.ax is None:
                return
            if not self.designerflag and not self.wheelflag and event.inaxes is None and not self.flagstart and not self.flagon and event.button == 3:
                self.statisticsmode = (self.statisticsmode + 1)%4
                self.writecharacteristics()
                self.fig.canvas.draw_idle()
                return

#PLUS
            if not self.designerflag and not self.wheelflag and event.inaxes is None and not self.flagstart and not self.flagon and event.button == 1 and event.dblclick and \
                    event.x < event.y and self.roastUUID is not None:
                QDesktopServices.openUrl(QUrl(roastLink(self.roastUUID), QUrl.ParsingMode.TolerantMode))
                return

            if not self.designerflag and not self.wheelflag and event.inaxes is None and not self.flagstart and not self.flagon and event.button == 1 and event.dblclick and event.x > event.y:
                fig = self.ax.get_figure()
                s = fig.get_size_inches()*fig.dpi
                if event.x > s[0]*2/3 and event.y > s[1]*2/3:
                    if self.backgroundprofile is None and __release_sponsor_domain__ and __release_sponsor_url__:
                        QDesktopServices.openUrl(QUrl(__release_sponsor_url__, QUrl.ParsingMode.TolerantMode))
                        return
                    if self.backgroundprofile is not None:
                        # toggle background if right top corner above canvas where the subtitle is clicked
                        self.background = not self.background
                        self.aw.autoAdjustAxis(background=self.background and (not len(self.timex) > 3))
                        self.redraw(recomputeAllDeltas=True)
                        return

            if event.button == 1 and event.inaxes and self.crossmarker and not self.designerflag and not self.wheelflag and not self.flagon:
                self.baseX,self.baseY = event.xdata, event.ydata
                if self.base_horizontalcrossline is None and self.base_verticalcrossline is None:
                    # Mark starting point of click-and-drag with a marker
                    self.base_horizontalcrossline, = self.ax.plot(self.baseX,self.baseY,'r+', markersize=20)
                    self.base_verticalcrossline, = self.ax.plot(self.baseX,self.baseY,'wo', markersize = 2)
            elif event.button == 3 and event.inaxes and not self.designerflag and not self.wheelflag and self.aw.ntb.mode not in ['pan/zoom', 'zoom rect']:# and not self.flagon:
                # popup not available if pan/zoom or zoom rect is active as it interacts
                timex = self.time2index(event.xdata)
                if timex > 0:
                    # reset the zoom rectangles
                    menu = QMenu(self.aw) # if we bind this to self, we inherit the background-color: transparent from self.fig
#                    menu.setStyleSheet("QMenu::item {background-color: palette(window); selection-color: palette(window); selection-background-color: darkBlue;}")
                    # populate menu
                    ac = QAction(menu)
                    bt = self.temp2[timex]
                    btdelta = 50 if self.mode == 'C' else 70
                    if bt != -1 and abs(bt-event.ydata) < btdelta:
                        # we suppress the popup if not clicked close enough to the BT curve
                        if self.timeindex[0] > -1:
                            ac.setText(f"{QApplication.translate('Label', 'at')} {stringfromseconds(event.xdata - self.timex[self.timeindex[0]])}")
                        else:
                            ac.setText(f"{QApplication.translate('Label', 'at')} {stringfromseconds(event.xdata)}")
                        ac.setEnabled(False)
                        menu.addAction(ac)
                        for k in [(QApplication.translate('Label','CHARGE'),0),
                                  (QApplication.translate('Label','DRY END'),1),
                                  (QApplication.translate('Label','FC START'),2),
                                  (QApplication.translate('Label','FC END'),3),
                                  (QApplication.translate('Label','SC START'),4),
                                  (QApplication.translate('Label','SC END'),5),
                                  (QApplication.translate('Label','DROP'),6),
                                  (QApplication.translate('Label','COOL'),7)]:
                            idx_before = idx_after = 0
                            for i in range(k[1]):
                                if self.timeindex[i] and self.timeindex[i] != -1:
                                    idx_before = self.timeindex[i]
                            for i in range(6,k[1],-1) :
                                if self.timeindex[i] and self.timeindex[i] != -1:
                                    idx_after = self.timeindex[i]
                            if (((not idx_before) or timex > idx_before) and ((not idx_after) or timex < idx_after) and
                                (not self.flagstart or (k[1] == 0) or (k[1] != 0 and self.timeindex[k[1]] != 0))): # only add menu item during recording if already a value is set (via a button); but for CHARGE
                                ac = QAction(menu)
                                ac.key = (k[1],timex) # type: ignore # key a custom attribute of QAction which should be defined in a custom subclass
                                ac.setText(' ' + k[0])
                                menu.addAction(ac)
                        # add user EVENT entry
                        ac = QAction(menu)
                        ac.setText(' ' + QApplication.translate('Label', 'EVENT'))
                        ac.key = (-1,timex)  # type: ignore # key a custom attribute of QAction which should be defined in a custom subclass
                        menu.addAction(ac)

                        # we deactivate all active motion_notify_event_handlers of draggable annotations that might have been connected by this click to
                        # avoid redraw conflicts between Artisan canvas bitblit caching and the matplotlib internal bitblit caches.
                        self.disconnect_draggableannotations_motion_notifiers()

                        # show menu
                        menu.triggered.connect(self.event_popup_action)
                        menu.popup(QCursor.pos())
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' onclick() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))

    @pyqtSlot('QAction*')
    def event_popup_action(self,action):
        if action.key[0] >= 0:
            # we check if this is the first DROP mark on this roast
            firstDROP = (action.key[0] == 6 and self.timeindex[6] == 0)
            timeindex_before = self.timeindex[action.key[0]]
            self.timeindex[action.key[0]] = action.key[1]
            # clear custom label positions cache entry
            if action.key[0] in self.l_annotations_dict:
                del self.l_annotations_dict[action.key[0]]
            try:
                # clear the event mark position cache
                self.l_annotations_dict.pop(action.key[0])
            except Exception: # pylint: disable=broad-except
                pass
            if action.key[0] == 0: # CHARGE
                try:
                    # clear the TP mark position cache (TP depends on CHARGE!)
                    self.l_annotations_dict.pop(-1)
                except Exception: # pylint: disable=broad-except
                    pass
                # realign to background
                if self.flagstart:
                    try:
                        if self.locktimex:
                            self.startofx = self.locktimex_start + self.timex[self.timeindex[0]]
                        else:
                            self.startofx = self.chargemintime + self.timex[self.timeindex[0]] # we set the min x-axis limit to the CHARGE Min time
                    except Exception: # pylint: disable=broad-except
                        pass
                    if not self.aw.buttonCHARGE.isFlat():
                        self.aw.buttonCHARGE.setFlat(True)
                        self.aw.buttonCHARGE.stopAnimation()
                        self.aw.onMarkMoveToNext(self.aw.buttonCHARGE)
                else:
                    # we keep xaxis limit the same but adjust to updated timeindex[0] mark
                    if timeindex_before > -1:
                        self.startofx += (self.timex[self.timeindex[0]] - self.timex[timeindex_before])
                    else:
                        self.startofx += self.timex[self.timeindex[0]]
                    self.aw.autoAdjustAxis(deltas=False)
                self.timealign(redraw=True,recompute=False) # redraws at least the canvas if redraw=True, so no need here for doing another canvas.draw()
            elif action.key[0] == 6: # DROP
                try:
                    # clear the TP mark position cache (TP depends on DROP!)
                    self.l_annotations_dict.pop(-1)
                except Exception: # pylint: disable=broad-except
                    pass
                try:
                    # update ambient temperature if a ambient temperature source is configured and no value yet established
                    self.updateAmbientTempFromPhidgetModulesOrCurve()
                except Exception: # pylint: disable=broad-except
                    pass
#PLUS
                # only on first setting the DROP event (not set yet and no previous DROP undone), we upload to PLUS
                if firstDROP and self.autoDROPenabled and self.aw.plus_account is not None:
                    try:
                        self.aw.updatePlusStatus()
                    except Exception: # pylint: disable=broad-except
                        pass
                        # add to out-queue
                    try:
                        addRoast()
                    except Exception: # pylint: disable=broad-except
                        pass
                if not self.flagstart:
                    self.aw.autoAdjustAxis(deltas=False)
#                elif firstDROP: # not needed as DROP cannot be occur in popup
#                    self.aw.buttonDROP.setFlat(True)
#                    self.aw.buttonCHARGE.setFlat(True)
#                    self.aw.buttonCHARGE.stopAnimation()
#                    self.aw.buttonDRY.setFlat(True)
#                    self.aw.buttonFCs.setFlat(True)
#                    self.aw.buttonFCe.setFlat(True)
#                    self.aw.buttonSCs.setFlat(True)
#                    self.aw.buttonSCe.setFlat(True)


            # update phases
            elif action.key[0] == 1 and self.phasesbuttonflag: # DRY
                self.phases[1] = int(round(self.temp2[self.timeindex[1]]))
            elif action.key[0] == 2 and self.phasesbuttonflag: # FCs
                self.phases[2] = int(round(self.temp2[self.timeindex[2]]))

            self.fileDirtySignal.emit()
            self.redraw(recomputeAllDeltas=(action.key[0] in [0,6])) # on moving CHARGE or DROP, we have to recompute the Deltas
        else:
            # add a special event at the current timepoint
            from artisanlib.events import customEventDlg
            dlg = customEventDlg(self.aw, self.aw, action.key[1])
            if dlg.exec():
                self.specialevents.append(action.key[1]) # absolute time index
                self.specialeventstype.append(dlg.type) # default: "--"
                self.specialeventsStrings.append(dlg.description)
                self.specialeventsvalue.append(dlg.value)
                self.aw.orderEvents()
                self.fileDirtySignal.emit()
                self.redraw(recomputeAllDeltas=(action.key[0] in [0,6])) # on moving CHARGE or DROP, we have to recompute the Deltas
            try:
                dlg.dialogbuttons.accepted.disconnect()
                dlg.dialogbuttons.rejected.disconnect()
                QApplication.processEvents() # we ensure events concerning this dialog are processed before deletion
                try: # sip not supported on older PyQt versions (RPi!)
                    sip.delete(dlg)
                    #print(sip.isdeleted(dlg))
                except Exception: # pylint: disable=broad-except
                    pass
            except Exception: # pylint: disable=broad-except
                pass

    def updateWebLCDs(self, bt:Optional[str] = None, et:Optional[str] = None, time:Optional[str] = None, alertTitle:Optional[str] = None, alertText:Optional[str] = None, alertTimeout:Optional[int] = None) -> None:
        try:
            url = f'http://127.0.0.1:{self.aw.WebLCDsPort}/send'
            headers = {'content-type': 'application/json'}
            payload:Dict[str,Dict[str,Union[str,int]]] = {'data': {}}
            if not (bt is None and et is None) and self.flagon and not self.flagstart:
                # in monitoring only mode, timer might be set by PID RS
                time = None
            if bt is not None:
                payload['data']['bt'] = bt
            if et is not None:
                payload['data']['et'] = et
            if time is not None:
                payload['data']['time'] = time
            if alertText is not None:
                payload['alert'] = {}
                payload['alert']['text'] = alertText
                if alertTitle:
                    payload['alert']['title'] = alertTitle
                if alertTimeout:
                    payload['alert']['timeout'] = alertTimeout
            import requests
            from json import dumps as json_dumps
            requests.post(url, data=json_dumps(payload), headers=headers, timeout=0.3)
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    # note that partial values might be given here (time might update, but not the values)
    @pyqtSlot(str,str,str)
    # pylint: disable=no-self-use # used as slot
    def updateLargeLCDs(self, bt, et, time):
        try:
            if self.aw.largeLCDs_dialog is not None:
                if self.flagon and not self.flagstart:
                    # in monitoring only mode, timer might be set by PID RS
                    time = None
                self.aw.largeLCDs_dialog.updateValues([et],[bt],time=time)
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    @pyqtSlot(str,str)
    # pylint: disable=no-self-use # used as slot
    def setTimerLargeLCDcolor(self, fc, bc):
        try:
            if self.aw.largeLCDs_dialog is not None:
                self.aw.largeLCDs_dialog.setTimerLCDcolor(fc,bc)
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    @pyqtSlot(str,int)
    # pylint: disable=no-self-use # used as slot
    def showAlarmPopup(self, message, timeout):
        # alarm popup message with <self.alarm_popup_timout>sec timeout
        amb = ArtisanMessageBox(self.aw, QApplication.translate('Message', 'Alarm notice'),message,timeout=timeout,modal=False)
        amb.show()
        #send alarm also to connected WebLCDs clients
        if self.aw.WebLCDs and self.aw.WebLCDsAlerts:
            self.updateWebLCDs(alertText=message,alertTimeout=timeout)

    @pyqtSlot(str,str)
    # pylint: disable=no-self-use # used as slot
    def updateLargeLCDsReadings(self, bt, et):
        try:
            if self.aw.largeLCDs_dialog is not None:
                self.aw.largeLCDs_dialog.updateValues([et],[bt])
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    @pyqtSlot(str)
    # pylint: disable=no-self-use # used as slot
    def updateLargeLCDsTime(self, time):
        try:
            if self.aw.largeLCDs_dialog is not None:
                self.aw.largeLCDs_dialog.updateValues([],[],time=time)
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    # note that partial values might be given here
    def updateLargeDeltaLCDs(self, deltabt=None, deltaet=None):
        try:
            if self.aw.largeDeltaLCDs_dialog is not None:
                self.aw.largeDeltaLCDs_dialog.updateValues([deltaet],[deltabt])
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    # note that partial values might be given here
    def updateLargePIDLCDs(self, sv=None, duty=None):
        try:
            if self.aw.largePIDLCDs_dialog is not None:
                self.aw.largePIDLCDs_dialog.updateValues([sv],[duty])
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    # note that partial values might be given here
    def updateLargeScaleLCDs(self, weight=None, total=None):
        try:
            if self.aw.largeScaleLCDs_dialog is not None:
                self.aw.largeScaleLCDs_dialog.updateValues([weight],[total])
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    def updateLargeExtraLCDs(self, extra1=None, extra2=None):
        try:
            if self.aw.largeExtraLCDs_dialog is not None:
                self.aw.largeExtraLCDs_dialog.updateValues(extra1,extra2)
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    # returns True if the extra device n, channel c, is of type MODBUS or S7, has no factor defined, nor any math formula, and is of type int
    # channel c is either 0 or 1
    def intChannel(self,n,c):
        if self.aw is not None and len(self.extradevices) > n:
            no_math_formula_defined:bool = False
            if c == 0:
                no_math_formula_defined = bool(self.extramathexpression1[n] == '')
            if c == 1:
                no_math_formula_defined = bool(self.extramathexpression2[n] == '')
            if self.extradevices[n] == 29: # MODBUS
                if c == 0:
                    return ((self.aw.modbus.inputFloatsAsInt[0] or self.aw.modbus.inputBCDsAsInt[0] or not self.aw.modbus.inputFloats[0]) and
                        self.aw.modbus.inputDivs[0] == 0 and
                        self.aw.modbus.inputModes[0] == '' and
                        no_math_formula_defined)
                return ((self.aw.modbus.inputFloatsAsInt[1] or self.aw.modbus.inputBCDsAsInt[1] or not self.aw.modbus.inputFloats[1]) and
                    self.aw.modbus.inputDivs[1] == 0 and
                    self.aw.modbus.inputModes[1] == '' and
                    no_math_formula_defined)
            if self.extradevices[n] == 33: # MODBUS_34
                if c == 0:
                    return ((self.aw.modbus.inputFloatsAsInt[2] or self.aw.modbus.inputBCDsAsInt[2] or not self.aw.modbus.inputFloats[2]) and
                        self.aw.modbus.inputDivs[2] == 0 and
                        self.aw.modbus.inputModes[2] == '' and
                        no_math_formula_defined)
                return ((self.aw.modbus.inputFloatsAsInt[3] or self.aw.modbus.inputBCDsAsInt[3] or not self.aw.modbus.inputFloats[3]) and
                    self.aw.modbus.inputDivs[3] == 0 and
                    self.aw.modbus.inputModes[3] == '' and
                    no_math_formula_defined)
            if self.extradevices[n] == 55: # MODBUS_56
                if c == 0:
                    return ((self.aw.modbus.inputFloatsAsInt[4] or self.aw.modbus.inputBCDsAsInt[4] or not self.aw.modbus.inputFloats[4]) and
                        self.aw.modbus.inputDivs[4] == 0 and
                        self.aw.modbus.inputModes[4] == '' and
                        no_math_formula_defined)
                return ((self.aw.modbus.inputFloatsAsInt[5] or self.aw.modbus.inputBCDsAsInt[5] or not self.aw.modbus.inputFloats[5]) and
                    self.aw.modbus.inputDivs[5] == 0 and
                    self.aw.modbus.inputModes[5] == '' and
                    no_math_formula_defined)
            if self.extradevices[n] == 109: # MODBUS_78
                if c == 0:
                    return ((self.aw.modbus.inputFloatsAsInt[6] or self.aw.modbus.inputBCDsAsInt[6] or not self.aw.modbus.inputFloats[6]) and
                        self.aw.modbus.inputDivs[6] == 0 and
                        self.aw.modbus.inputModes[6] == '' and
                        no_math_formula_defined)
                return ((self.aw.modbus.inputFloatsAsInt[7] or self.aw.modbus.inputBCDsAsInt[7] or not self.aw.modbus.inputFloats[7]) and
                    self.aw.modbus.inputDivs[7] == 0 and
                    self.aw.modbus.inputModes[7] == '' and
                    no_math_formula_defined)
            if self.extradevices[n] == 70: # S7
                return self.aw.s7.type[0+c] != 1 and self.aw.s7.mode[0+c] == 0 and (self.aw.s7.div[0+c] == 0 or self.aw.s7.type[0+c] == 2) and no_math_formula_defined
            if self.extradevices[n] == 80: # S7_34
                return self.aw.s7.type[2+c] != 1 and self.aw.s7.mode[2+c] == 0 and (self.aw.s7.div[2+c] == 0 or self.aw.s7.type[2+c] == 2) and no_math_formula_defined
            if self.extradevices[n] == 81: # S7_56
                return self.aw.s7.type[4+c] != 1 and self.aw.s7.mode[4+c] == 0 and (self.aw.s7.div[4+c] == 0 or self.aw.s7.type[4+c] == 2) and no_math_formula_defined
            if self.extradevices[n] == 82: # S7_78
                return self.aw.s7.type[6+c] != 1 and self.aw.s7.mode[6+c] == 0 and (self.aw.s7.div[6+c] == 0 or self.aw.s7.type[6+c] == 2) and no_math_formula_defined
            if self.extradevices[n] == 110: # S7_910
                return self.aw.s7.type[8+c] != 1 and self.aw.s7.mode[8+c] == 0 and (self.aw.s7.div[8+c] == 0 or self.aw.s7.type[8+c] == 2) and no_math_formula_defined
            if self.extradevices[n] in [54,90,91,135,136]: # Hottop Heater/Fan, Slider 12, Slider 34, Santoker Power / Fan
                return True
            if self.extradevices[n] == 136 and c == 0: # Santoker Drum
                return True
            return False
        return False

    def update_additional_artists(self):
        if self.ax is not None:
            if self.flagstart and ((self.device == 18 and self.aw.simulator is None) or self.showtimeguide): # not NONE device
                tx = self.timeclock.elapsedMilli()
                if self.l_timeline is None:
                    self.l_timeline = self.ax.axvline(tx,color = self.palette['timeguide'],
                                            label=self.aw.arabicReshape(QApplication.translate('Label', 'TIMEguide')),
                                            linestyle = '-', linewidth= 1, alpha = .5,sketch_params=None,path_effects=[])
                else:
                    self.l_timeline.set_xdata(tx)
                    self.ax.draw_artist(self.l_timeline)
            if self.projectFlag:
                if self.l_BTprojection is not None and self.BTcurve:
                    self.ax.draw_artist(self.l_BTprojection)
                if self.l_ETprojection is not None and self.ETcurve:
                    self.ax.draw_artist(self.l_ETprojection)
                if self.projectDeltaFlag:
                    if self.l_DeltaBTprojection is not None and self.DeltaBTflag:
                        self.ax.draw_artist(self.l_DeltaBTprojection)
                    if self.l_DeltaETprojection is not None and self.DeltaETflag:
                        self.ax.draw_artist(self.l_DeltaETprojection)

            if self.AUCguideFlag and self.AUCguideTime and self.AUCguideTime > 0:
                self.ax.draw_artist(self.l_AUCguide)

    # input filter
    # if temp (the actual reading) is outside of the interval [tmin,tmax] or
    # a spike is detected, the previous value is repeated or if that happened already before, -1 is returned
    # note that here we assume that the actual measured temperature time/temp was not already added to the list of previous measurements timex/tempx
    def inputFilter(self, timex, tempx, time, temp, BT=False):
        try:
            wrong_reading = 0
            #########################
            # a) detect duplicates: remove a reading if it is equal to the previous or if that is -1 to the one before that
            if self.dropDuplicates and ((len(tempx)>1 and tempx[-1] == -1 and abs(temp - tempx[-2]) <= self.dropDuplicatesLimit) or (len(tempx)>0 and abs(temp - tempx[-1]) <= self.dropDuplicatesLimit)):
                wrong_reading = 2 # replace by previous reading not by -1
            #########################
            # b) detect overflows
            if self.minmaxLimits and (temp < self.filterDropOut_tmin or temp > self.filterDropOut_tmax):
                wrong_reading = 1
            #########################
            # c) detect spikes (on BT only after CHARGE if autoChargeFlag=True not to have a conflict here)
            n = self.filterDropOut_spikeRoR_period
            dRoR_limit = self.filterDropOut_spikeRoR_dRoR_limit # the limit of additional RoR in temp/sec (4C for C / 7F for F) compared to previous readings
            if self.dropSpikes and ((not self.autoChargeFlag) or (not BT) or (self.timeindex[0] != -1 and (self.timeindex[0] + n) < len(timex))) and not wrong_reading and len(tempx) >= n:
                # no min/max overflow detected
                # check if RoR caused by actual measurement is way higher then the previous one
                # calc previous RoR (pRoR) taking the last n samples into account
                pdtemp = tempx[-1] - tempx[-n]
                pdtime = timex[-1] - timex[-n]
                if pdtime > 0:
                    pRoR = abs(pdtemp/pdtime)
                    dtemp = tempx[-1] - temp
                    dtime = timex[-1] - time
                    if dtime > 0:
                        RoR = abs(dtemp/dtime)
                        if RoR > (pRoR + dRoR_limit):
                            wrong_reading = 2
            #########################
            # c) handle outliers if it could be detected
            if wrong_reading:
                if len(tempx) > 0 and tempx[-1] != -1:
                    # repeate last correct reading if not done before in the last two fixes (min/max violation are always filtered)
                    if len(tempx) == 1 or (len(tempx) > 3 and (tempx[-1] != tempx[-2] or tempx[-2] != tempx[-3])):
                        return tempx[-1]
                    if wrong_reading == 1:
                        return -1
                    # no way to correct this
                    return temp
                if wrong_reading == 1:
                    return -1
                # no way to correct this
                return temp
            # try to improve a previously corrected reading timex/temp[-1] based on the current reading time/temp (just in this case the actual reading is not a drop)
            if (self.minmaxLimits or self.dropSpikes or self.dropDuplicates):
                if len(tempx) > 2 and tempx[-1] == tempx[-2] == tempx[-3] and tempx[-1] != -1 and tempx[-1] != temp and temp!=-1: # previous reading was a drop and replaced by reading[-2] and same for the one before
                    delta = (tempx[-3] - temp) / 3.0
                    tempx[-1] = tempx[-3] - 2*delta
                    tempx[-2] = tempx[-3] - delta
                elif len(tempx) > 1 and tempx[-1] == tempx[-2] and tempx[-1] != -1 and tempx[-1] != temp and temp!=-1: # previous reading was a drop and replaced by reading[-2]
                    tempx[-1] = (tempx[-2] + temp) / 2.0
            return temp
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' filterDropOuts() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
            return temp

    # the temp gets averaged using the given decay weights after resampling
    # to linear time based on tx and the current sampling interval
    # -1 and None values are skipped/ignored
    def decay_average(self, tx_in,temp_in,decay_weights):
        if len(tx_in) != len(temp_in):
            if len(temp_in)>0:
                return temp_in[-1]
            return -1
        # remove items where temp[i]=None to fulfil precond. of numpy.interp
        tx = []
        temp = []
        for i, tempin in enumerate(temp_in):
            if tempin not in [None, -1] and not numpy.isnan(tempin):
                tx.append(tx_in[i])
                temp.append(tempin)
        if len(temp) == 0:
            return -1
        #
        l = min(len(decay_weights),len(temp))
        d = self.delay / 1000.
        tx_org = tx[-l:] # as len(tx)=len(temp) here, it is guaranteed that len(tx_org)=l
        # we create a linearly spaced time array starting from the newest timestamp in sampling interval distance
        tx_lin = numpy.flip(numpy.arange(tx_org[-1],tx_org[-1]-l*d,-d), axis=0) # by construction, len(tx_lin)=len(tx_org)=l
        temp_trail = temp[-l:] # by construction, len(temp_trail)=len(tx_lin)=len(tx_org)=l
        temp_trail_re = numpy.interp(tx_lin, tx_org, temp_trail) # resample data into that linear spaced time
        try:
            return numpy.average(temp_trail_re[-len(decay_weights):],axis=0,weights=decay_weights[-l:])  # len(decay_weights)>len(temp_trail_re)=l is possible
        except Exception: # pylint: disable=broad-except
            # in case something goes very wrong we at least return the standard average over temp, this should always work as len(tx)=len(temp)
            return numpy.average(tx,temp)

    # returns true after BT passed the TP
    def checkTPalarmtime(self):
        seconds_since_CHARGE = int(self.timex[-1]-self.timex[self.timeindex[0]])
        # if v[-1] is the current temperature then check if
        #   we are 20sec after CHARGE
        #   len(BT) > 4
        # BT[-5] <= BT[-4] abd BT[-5] <= BT[-3] and BT[-5] <= BT[-2] and BT[-5] <= BT[-1] and BT[-5] < BT[-1]
        if seconds_since_CHARGE > 20 and not self.afterTP and len(self.temp2) > 3 and (self.temp2[-5] <= self.temp2[-4]) and (self.temp2[-5] <= self.temp2[-3]) and (self.temp2[-5] <= self.temp2[-2]) and (self.temp2[-5] <= self.temp2[-1]) and (self.temp2[-5] < self.temp2[-1]):
            self.afterTP = True
        return self.afterTP

    # sample devices at interval self.delay milliseconds.
    # we can assume within the processing of sample_processing() that flagon=True
    # NOTE: sample_processing is processed in the GUI thread NOT the sample thread!
    def sample_processing(self, local_flagstart:bool, temp1_readings:List[float], temp2_readings:List[float], timex_readings:List[float]): # pyright: ignore # Code is too complex to analyze; reduce complexity by refactoring into subroutines or reducing conditional code paths (reportGeneralTypeIssues)
        ##### (try to) lock resources  #########
        wait_period = 200  # we try to catch a lock within the next 200ms
        if self.delay < 500:
            wait_period = 10 # on tight sampling rate we only wait 10ms
        gotlock = self.profileDataSemaphore.tryAcquire(1, wait_period) # we try to catch the lock, if we fail we just skip this sampling round (prevents stacking of waiting calls)
        if not gotlock:
            _log.info('sample_processing(): failed to get profileDataSemaphore lock')
        else:
            try:
                # duplicate system state flag flagstart locally and only refer to this copy within this function to make it behaving uniquely (either append or overwrite mode)

                # initialize the arrays modified depending on the recording state
                if local_flagstart:
                    sample_timex = self.timex
                    sample_temp1 = self.temp1
                    sample_temp2 = self.temp2
                    sample_ctimex1 = self.ctimex1
                    sample_ctemp1 = self.ctemp1
                    sample_ctimex2 = self.ctimex2
                    sample_ctemp2 = self.ctemp2
                    sample_tstemp1 = self.tstemp1
                    sample_tstemp2 = self.tstemp2
                    sample_unfiltereddelta1 = self.unfiltereddelta1 # no sample_unfiltereddelta1_pure as used only during recording for projections
                    sample_unfiltereddelta2 = self.unfiltereddelta2 # no sample_unfiltereddelta2_pure as used only during recording for projections
                    sample_delta1 = self.delta1
                    sample_delta2 = self.delta2
                    # list of lists:
                    sample_extratimex = self.extratimex
                    sample_extratemp1 = self.extratemp1
                    sample_extratemp2 = self.extratemp2
                    sample_extractimex1 = self.extractimex1
                    sample_extractemp1 = self.extractemp1
                    sample_extractimex2 = self.extractimex2
                    sample_extractemp2 = self.extractemp2
                else:
                    m_len = self.curvefilter #*2
                    sample_timex = self.on_timex = self.on_timex[-m_len:]
                    sample_temp1 = self.on_temp1 = self.on_temp1[-m_len:]
                    sample_temp2 = self.on_temp2 = self.on_temp2[-m_len:]
                    sample_ctimex1 = self.on_ctimex1 = self.on_ctimex1[-m_len:]
                    sample_ctemp1 = self.on_ctemp1 = self.on_ctemp1[-m_len:]
                    sample_ctimex2 = self.on_ctimex2 = self.on_ctimex2[-m_len:]
                    sample_ctemp2 = self.on_ctemp2 = self.on_ctemp2[-m_len:]
                    sample_tstemp1 = self.on_tstemp1 = self.on_tstemp1[-m_len:]
                    sample_tstemp2 = self.on_tstemp2 = self.on_tstemp2[-m_len:]
                    sample_unfiltereddelta1 = self.on_unfiltereddelta1 = self.on_unfiltereddelta1[-m_len:] # no sample_unfiltereddelta1_pure as used only during recording for projections
                    sample_unfiltereddelta2 = self.on_unfiltereddelta2 = self.on_unfiltereddelta2[-m_len:] # no sample_unfiltereddelta2_pure as used only during recording for projections
                    sample_delta1 = self.on_delta1 = self.on_delta1[-m_len:]
                    sample_delta2 = self.on_delta2 = self.on_delta2[-m_len:]
                    # list of lists:
                    for i in range(len(self.extradevices)):
                        self.on_extratimex[i] = self.on_extratimex[i][-m_len:]
                        self.on_extratemp1[i] = self.on_extratemp1[i][-m_len:]
                        self.on_extratemp2[i] = self.on_extratemp2[i][-m_len:]
                        self.on_extractimex1[i] = self.on_extractimex1[i][-m_len:]
                        self.on_extractemp1[i] = self.on_extractemp1[i][-m_len:]
                        self.on_extractimex2[i] = self.on_extractimex2[i][-m_len:]
                        self.on_extractemp2[i] = self.on_extractemp2[i][-m_len:]
                    sample_extratimex = self.on_extratimex
                    sample_extratemp1 = self.on_extratemp1
                    sample_extratemp2 = self.on_extratemp2
                    sample_extractimex1 = self.on_extractimex1
                    sample_extractemp1 = self.on_extractemp1
                    sample_extractimex2 = self.on_extractimex2
                    sample_extractemp2 = self.on_extractemp2

                #if using a meter (thermocouple device)
                if self.device != 18 or self.aw.simulator is not None: # not NONE device

                    t1 = temp1_readings[0]
                    t2 = temp2_readings[0]
                    tx = timex_readings[0]

                    self.RTtemp1 = t1 # store readings for real-time symbolic evaluation
                    self.RTtemp2 = t2
                    ##############  if using Extra devices
                    nxdevices = len(self.extradevices)
                    if nxdevices:
                        les,led,let =  len(self.aw.extraser),nxdevices,len(sample_extratimex)
                        if les == led == let:
                            xtra_dev_lines1 = 0
                            xtra_dev_lines2 = 0
                            #1 clear extra device buffers
                            self.RTextratemp1,self.RTextratemp2,self.RTextratx = [],[],[]
                            #2 load RT buffers
                            self.RTextratemp1 = temp1_readings[1:]
                            self.RTextratemp2 = temp2_readings[1:]
                            self.RTextratx = timex_readings[1:]
                            #3 evaluate symbolic expressions
                            for i in range(nxdevices):
                                extratx = self.RTextratx[i]
                                extrat1 = self.RTextratemp1[i]
                                extrat2 = self.RTextratemp2[i]
                                if len(self.extramathexpression1) > i and self.extramathexpression1[i] is not None and len(self.extramathexpression1[i].strip()):
                                    try:
                                        extrat1 = self.eval_math_expression(self.extramathexpression1[i],self.RTextratx[i],RTsname='Y'+str(2*i+3),RTsval=self.RTextratemp1[i])
                                        self.RTextratemp1[i] = extrat1
                                    except Exception as e: # pylint: disable=broad-except
                                        _log.exception(e)
                                if len(self.extramathexpression2) > i and self.extramathexpression2[i] is not None and len(self.extramathexpression2[i].strip()):
                                    try:
                                        extrat2 = self.eval_math_expression(self.extramathexpression2[i],self.RTextratx[i],RTsname='Y'+str(2*i+4),RTsval=self.RTextratemp2[i])
                                        self.RTextratemp2[i] = extrat2
                                    except Exception as e: # pylint: disable=broad-except
                                        _log.exception(e)

                                et1_prev = et2_prev = None
                                et1_prevprev = et2_prevprev = None
                                if self.extradevices[i] != 25: # don't apply input filters to virtual devices

                                    ## Apply InputFilters. As those might modify destructively up to two older readings in temp1/2 via interpolation for drop outs we try to detect this and copy those
                                    # changes back to the ctemp lines that are rendered.
                                    if (self.minmaxLimits or self.dropSpikes or self.dropDuplicates):
                                        if len(sample_extratemp1[i])>0:
                                            et1_prev = sample_extratemp1[i][-1]
                                            if len(sample_extratemp1[i])>1:
                                                et1_prevprev = sample_extratemp1[i][-2]
                                        if len(sample_extratemp2[i])>0:
                                            et2_prev = sample_extratemp2[i][-1]
                                            if len(sample_extratemp2[i])>1:
                                                et2_prevprev = sample_extratemp2[i][-2]
                                    extrat1 = self.inputFilter(sample_extratimex[i],sample_extratemp1[i],extratx,extrat1)
                                    extrat2 = self.inputFilter(sample_extratimex[i],sample_extratemp2[i],extratx,extrat2)

                                    # now copy the destructively modified values from temp1/2 to ctemp1/2 if any (to ensure to pick the right elements we compare the timestamps at those indices)
                                    if (self.minmaxLimits or self.dropSpikes or self.dropDuplicates):
                                        if len(sample_extractimex1[i])>0:
                                            if et1_prev is not None and sample_extractimex1[i][-1] == sample_extratimex[i][-1] and et1_prev != sample_extratemp1[i][-1]:
                                                sample_extractemp1[i][-1] = sample_extratemp1[i][-1]
                                            if len(sample_extractimex1[i])>1 and et1_prevprev is not None and sample_extractimex1[i][-2] == sample_extratimex[i][-2] and et1_prevprev != sample_extratemp1[i][-2]:
                                                sample_extractemp1[i][-2] = sample_extratemp1[i][-2]
                                        if len(sample_extractimex2[i])>0:
                                            if et2_prev is not None and sample_extractimex2[i][-1] == sample_extratimex[i][-1] and et2_prev != sample_extratemp2[i][-1]:
                                                sample_extractemp2[i][-1] = sample_extratemp2[i][-1]
                                            if len(sample_extractimex2[i])>1 and et2_prevprev is not None and sample_extractimex2[i][-2] == sample_extratimex[i][-2] and et2_prevprev != sample_extratemp2[i][-2]:
                                                sample_extractemp2[i][-2] = sample_extratemp2[i][-2]

                                sample_extratimex[i].append(extratx)
                                sample_extratemp1[i].append(float(extrat1))
                                sample_extratemp2[i].append(float(extrat2))

                                # gaps larger than 3 readings are not connected in the graph (as util.py:fill_gaps() is not interpolating them)
                                if extrat1 != -1:
                                    sample_extractimex1[i].append(float(extratx))
                                    sample_extractemp1[i].append(float(extrat1))
                                elif len(sample_extratemp1[i])>(self.interpolatemax+1) and all(v == -1 for v in sample_extratemp1[i][-(self.interpolatemax+1):]):
                                    sample_extractimex1[i].append(float(extratx))
                                    sample_extractemp1[i].append(None)
                                if extrat2 != -1:
                                    sample_extractimex2[i].append(float(extratx))
                                    sample_extractemp2[i].append(float(extrat2))
                                elif len(sample_extratemp2[i])>(self.interpolatemax+1) and all(v == -1 for v in sample_extratemp2[i][-(self.interpolatemax+1):]):
                                    sample_extractimex2[i].append(float(extratx))
                                    sample_extractemp2[i].append(None)

                                # update extra lines

                                if self.aw.extraCurveVisibility1[i] and len(self.extratemp1lines) > xtra_dev_lines1 and self.extratemp1lines[xtra_dev_lines1] is not None:
                                    self.extratemp1lines[xtra_dev_lines1].set_data(sample_extractimex1[i], sample_extractemp1[i])
                                    xtra_dev_lines1 = xtra_dev_lines1 + 1
                                if self.aw.extraCurveVisibility2[i] and len(self.extratemp2lines) > xtra_dev_lines2 and self.extratemp2lines[xtra_dev_lines2] is not None:
                                    self.extratemp2lines[xtra_dev_lines2].set_data(sample_extractimex2[i], sample_extractemp2[i])
                                    xtra_dev_lines2 = xtra_dev_lines2 + 1
                        #ERROR FOUND
                        else:
                            lengths = [les,led,let]
                            location = ['Extra-Serial','Extra-Devices','Extra-Temp']
                            #find error
                            if nxdevices-1 in lengths:
                                indexerror =  lengths.index(nxdevices-1)
                            elif nxdevices+1 in lengths:
                                indexerror =  lengths.index(nxdevices+1)
                            else:
                                indexerror = 1000
                            if indexerror != 1000:
                                errormessage = f'ERROR: length of {location[indexerror]} (={lengths[indexerror]}) does not have the necessary length (={nxdevices})'
                                errormessage += '\nPlease Reset: Extra devices'
                            else:
                                errormessage = f"ERROR: extra devices lengths don't match: {location[0]}= {lengths[0]} {location[1]}= {lengths[1]} {location[2]}= {lengths[2]}"
                                errormessage += '\nPlease Reset: Extra devices'
                            raise Exception(errormessage) # pylint: disable=broad-exception-raised

                    ####### all values retrieved

                    if self.ETfunction is not None and self.ETfunction.strip():
                        try:
                            t1 = self.eval_math_expression(self.ETfunction,tx,RTsname='Y1',RTsval=t1)
                            self.RTtemp1 = t1
                        except Exception as e: # pylint: disable=broad-except
                            _log.exception(e)
                    if self.BTfunction is not None and self.BTfunction.strip():
                        try:
                            t2 = self.eval_math_expression(self.BTfunction,tx,RTsname='Y2',RTsval=t2)
                            self.RTtemp2 = t2
                        except Exception as e: # pylint: disable=broad-except
                            _log.exception(e)
                    # if modbus device do the C/F conversion if needed (done after mathexpression, not to mess up with x/10 formulas)
                    # modbus channel 1+2, respect input temperature scale setting

                    ## Apply InputFilters. As those might modify destructively up to two older readings in temp1/2 via interpolation for drop outs we try to detect this and copy those
                    # changes back to the ctemp lines that are rendered.
                    t1_prev = t2_prev = None
                    t1_prevprev = t2_prevprev = None
                    if (self.minmaxLimits or self.dropSpikes or self.dropDuplicates):
                        if len(sample_temp1)>0:
                            t1_prev = sample_temp1[-1]
                            if len(sample_temp1)>1:
                                t1_prevprev = sample_temp1[-2]
                        if len(sample_temp2)>0:
                            t2_prev = sample_temp2[-1]
                            if len(sample_temp2)>1:
                                t2_prevprev = sample_temp2[-2]
                    t1 = self.inputFilter(sample_timex,sample_temp1,tx,t1)
                    t2 = self.inputFilter(sample_timex,sample_temp2,tx,t2,True)


                    length_of_qmc_timex = len(sample_timex)

                    # now copy the destructively modified values from temp1/2 to ctemp1/2 if any (to ensure to pick the right elements we compare the timestamps at those indices)
                    if (self.minmaxLimits or self.dropSpikes or self.dropDuplicates):
                        if len(sample_ctimex1)>0:
                            if t1_prev is not None and sample_ctimex1[-1] == sample_timex[-1] and t1_prev != sample_temp1[-1]:
                                sample_ctemp1[-1] = sample_temp1[-1]
                            if len(sample_ctimex1)>1 and t1_prevprev is not None and sample_ctimex1[-2] == sample_timex[-2] and t1_prevprev != sample_temp1[-2]:
                                sample_ctemp1[-2] = sample_temp1[-2]
                        if len(sample_ctimex2)>0:
                            if t2_prev is not None and sample_ctimex2[-1] == sample_timex[-1] and t2_prev != sample_temp2[-1]:
                                sample_ctemp2[-1] = sample_temp2[-1]
                            if len(sample_ctimex2)>1 and t2_prevprev is not None and sample_ctimex2[-2] == sample_timex[-2] and t2_prevprev != sample_temp2[-2]:
                                sample_ctemp2[-2] = sample_temp2[-2]
                    t1_final = t1
                    t2_final = t2
                    sample_temp1.append(t1_final)
                    sample_temp2.append(t2_final)
                    sample_timex.append(tx)
                    length_of_qmc_timex += 1
                    if t1_final != -1:
                        sample_ctimex1.append(tx)
                        sample_ctemp1.append(t1_final)
                    elif len(sample_temp1)>(self.interpolatemax+1) and all(v == -1 for v in sample_temp1[-(self.interpolatemax+1):]):
                        sample_ctimex1.append(tx)
                        sample_ctemp1.append(None)
                    if t2_final != -1:
                        sample_ctimex2.append(tx)
                        sample_ctemp2.append(t2_final)
                    elif len(sample_temp2)>(self.interpolatemax+1) and all(v == -1 for v in sample_temp2[-(self.interpolatemax+1):]):
                        sample_ctimex2.append(tx)
                        sample_ctemp2.append(None)


                    #we populate the temporary smoothed ET/BT data arrays (with readings cleansed from -1 dropouts)
                    cf = self.curvefilter #*2 - 1 # we smooth twice as heavy for PID/RoR calcuation as for normal curve smoothing
                    if self.temp_decay_weights is None or len(self.temp_decay_weights) != cf: # recompute only on changes
                        self.temp_decay_weights = list(numpy.arange(1,cf+1))
                    # we don't smooth st'x if last, or butlast temperature value were a drop-out not to confuse the RoR calculation
                    if -1 in sample_temp1[-(cf+1):]:
                        dw1 = [1]
                    else:
                        dw1 = self.temp_decay_weights
                    if -1 in sample_temp2[-(cf+1):]:
                        dw2 = [1]
                    else:
                        dw2 = self.temp_decay_weights
                    # average smoothing
                    if len(sample_ctemp1) > 0:
                        st1 = self.decay_average(sample_ctimex1,sample_ctemp1,dw1)
                    else:
                        st1 = -1
                    if len(sample_ctemp2) > 0:
                        st2 = self.decay_average(sample_ctimex2,sample_ctemp2,dw2)
                    else:
                        st2 = -1

                    # we apply a minimal live median spike filter minimizing the delay by choosing a window smaller than in the offline medfilt
                    if self.filterDropOuts and self.delay <= 2000:
                        if st1 is not None and st1 != -1:
                            st1 = self.liveMedianETfilter(st1)
                        if st1 is not None and st2 != -1:
                            st2 = self.liveMedianBTfilter(st2)

                    # register smoothed values
                    sample_tstemp1.append(st1)
                    sample_tstemp2.append(st2)

                    if local_flagstart:
                        if self.ETcurve and self.l_temp1 is not None:
                            self.l_temp1.set_data(sample_ctimex1, sample_ctemp1)
                        if self.BTcurve and self.l_temp2 is not None:
                            self.l_temp2.set_data(sample_ctimex2, sample_ctemp2)

                    #NOTE: the following is no longer restricted to self.aw.pidcontrol.pidActive==True
                    # as now the software PID is also update while the PID is off (if configured).
                    if (self.Controlbuttonflag and \
                            not self.aw.pidcontrol.externalPIDControl()): # any device and + Artisan Software PID lib
                        if self.aw.pidcontrol.pidSource in [0,1]:
                            self.pid.update(st2) # smoothed BT
                        elif self.aw.pidcontrol.pidSource == 2:
                            self.pid.update(st1) # smoothed ET
                        else:
                            # pidsource = 3 => extra device 1, channel 1 => sample_extratemp1[0]
                            # pidsource = 4 => extra device 1, channel 2 => sample_extratemp2[0]
                            # pidsource = 5 => extra device 2, channel 3 => sample_extratemp1[1]
                            #...
                            ps = self.aw.pidcontrol.pidSource - 3
                            if ps % 2 == 0 and len(sample_extratemp1)>(ps // 2) and len(sample_extratemp1[ps // 2])>0:
                                self.pid.update(sample_extratemp1[ps // 2][-1])
                            elif len(sample_extratemp1)>(ps // 2) and len(sample_extratemp2[ps // 2])>0:
                                self.pid.update(sample_extratemp2[ps // 2][-1])

                    rateofchange1plot:Optional[float]
                    rateofchange2plot:Optional[float]

                    #we need a minimum of two readings to calculate rate of change
                    if length_of_qmc_timex > 1:
                        # compute T1 RoR
                        if t1_final == -1 or len(sample_ctimex1)<2:  # we repeat the last RoR if underlying temperature dropped
                            if sample_unfiltereddelta1:
                                self.rateofchange1 = sample_unfiltereddelta1[-1]
                            else:
                                self.rateofchange1 = 0.
                        else: # normal data received
                            #   Delta T = (changeTemp/ChangeTime)*60. =  degrees per minute;
                            left_index = min(len(sample_ctimex1),len(sample_tstemp1),max(2, self.deltaETsamples + 1))
                            # ****** Instead of basing the estimate on the window extremal points,
                            #        grab the full set of points and do a formal LS solution to a straight line and use the slope estimate for RoR
                            if self.polyfitRoRcalc:
                                try:
                                    time_vec = sample_ctimex1[-left_index:]
                                    temp_samples = sample_tstemp1[-left_index:]
                                    with warnings.catch_warnings():
                                        warnings.simplefilter('ignore')
                                        # using stable polyfit from numpy polyfit module
                                        LS_fit = numpy.polynomial.polynomial.polyfit(time_vec, temp_samples, 1)
                                        self.rateofchange1 = LS_fit[1]*60.
                                except Exception: # pylint: disable=broad-except
                                    # a numpy/OpenBLAS polyfit bug can cause polyfit to throw an exception "SVD did not converge in Linear Least Squares" on Windows Windows 10 update 2004
                                    # https://github.com/numpy/numpy/issues/16744
                                    # we fall back to the two point algo
                                    timed = sample_ctimex1[-1] - sample_ctimex1[-left_index]   #time difference between last self.deltaETsamples readings
                                    self.rateofchange1 = ((sample_tstemp1[-1] - sample_tstemp1[-left_index])/timed)*60.  #delta ET (degrees/minute)
                            else:
                                timed = sample_ctimex1[-1] - sample_ctimex1[-left_index]   #time difference between last self.deltaETsamples readings
                                self.rateofchange1 = ((sample_tstemp1[-1] - sample_tstemp1[-left_index])/timed)*60.  #delta ET (degrees/minute)

                        # compute T2 RoR
                        if t2_final == -1 or len(sample_ctimex2)<2:  # we repeat the last RoR if underlying temperature dropped
                            if sample_unfiltereddelta2:
                                self.rateofchange2 = sample_unfiltereddelta2[-1]
                            else:
                                self.rateofchange2 = 0.
                        else: # normal data received
                            #   Delta T = (changeTemp/ChangeTime)*60. =  degrees per minute;
                            left_index = min(len(sample_ctimex2),len(sample_tstemp2),max(2, self.deltaBTsamples + 1))
                            # ****** Instead of basing the estimate on the window extremal points,
                            #        grab the full set of points and do a formal LS solution to a straight line and use the slope estimate for RoR
                            if self.polyfitRoRcalc:
                                try:
                                    time_vec = sample_ctimex2[-left_index:]
                                    temp_samples = sample_tstemp2[-left_index:]
                                    with warnings.catch_warnings():
                                        warnings.simplefilter('ignore')
                                        LS_fit = numpy.polynomial.polynomial.polyfit(time_vec, temp_samples, 1)
                                        self.rateofchange2 = LS_fit[1]*60.
                                except Exception: # pylint: disable=broad-except
                                    # a numpy/OpenBLAS polyfit bug can cause polyfit to throw an exception "SVD did not converge in Linear Least Squares" on Windows Windows 10 update 2004
                                    # https://github.com/numpy/numpy/issues/16744
                                    # we fall back to the two point algo
                                    timed = sample_ctimex2[-1] - sample_ctimex2[-left_index]   #time difference between last self.deltaBTsamples readings
                                    self.rateofchange2 = ((sample_tstemp2[-1] - sample_tstemp2[-left_index])/timed)*60.  #delta BT (degrees/minute)
                            else:
                                timed = sample_ctimex2[-1] - sample_ctimex2[-left_index]   #time difference between last self.deltaBTsamples readings
                                self.rateofchange2 = ((sample_tstemp2[-1] - sample_tstemp2[-left_index])/timed)*60.  #delta BT (degrees/minute)


                        # self.unfiltereddelta{1,2}_pure contain the RoR values respecting the delta_span, but without any delta smoothing NOR delta mathformulas applied
                        self.unfiltereddelta1_pure.append(self.rateofchange1)
                        self.unfiltereddelta2_pure.append(self.rateofchange2)

                        # apply the math formula before the delta smoothing
                        if self.DeltaETfunction is not None and self.DeltaETfunction.strip():
                            try:
                                self.rateofchange1 = self.eval_math_expression(self.DeltaETfunction,tx,RTsname='R1',RTsval=self.rateofchange1)
                            except Exception as e: # pylint: disable=broad-except
                                _log.exception(e)
                        if self.DeltaBTfunction is not None and self.DeltaBTfunction.strip():
                            try:
                                self.rateofchange2 = self.eval_math_expression(self.DeltaBTfunction,tx,RTsname='R2',RTsval=self.rateofchange2)
                            except Exception as e: # pylint: disable=broad-except
                                _log.exception(e)

                        # unfiltereddelta1/2 contains the RoRs respecting the delta_span, but without any delta smoothing AND delta mathformulas applied
                        # we apply a minimal live median spike filter minimizing the delay by choosing a window smaller than in the offline medfilt
                        if self.filterDropOuts and self.delay <= 2000:
                            if self.rateofchange1 is not None and self.rateofchange1 != -1:
                                self.rateofchange1 = self.liveMedianRoRfilter(self.rateofchange1)
                            if self.rateofchange2 is not None and self.rateofchange2 != -1:
                                self.rateofchange2 = self.liveMedianRoRfilter(self.rateofchange2)

                        sample_unfiltereddelta1.append(self.rateofchange1)
                        sample_unfiltereddelta2.append(self.rateofchange2)

                        #######   filter deltaBT deltaET
                        # decay smoothing
                        if self.deltaETfilter:
                            user_filter = int(round(self.deltaETfilter/2.))
                            if user_filter and length_of_qmc_timex > user_filter and (len(sample_unfiltereddelta1) > user_filter):
                                if self.decay_weights is None or len(self.decay_weights) != user_filter: # recompute only on changes
                                    self.decay_weights = list(numpy.arange(1,user_filter+1))
                                self.rateofchange1 = self.decay_average(sample_timex,sample_unfiltereddelta1,self.decay_weights)
                        if self.deltaBTfilter:
                            user_filter = int(round(self.deltaBTfilter/2.))
                            if user_filter and length_of_qmc_timex > user_filter and (len(sample_unfiltereddelta2) > user_filter):
                                if self.decay_weights is None or len(self.decay_weights) != user_filter: # recompute only on changes
                                    self.decay_weights = list(numpy.arange(1,user_filter+1))
                                self.rateofchange2 = self.decay_average(sample_timex,sample_unfiltereddelta2,self.decay_weights)
                        rateofchange1plot = self.rateofchange1
                        rateofchange2plot = self.rateofchange2
                    else:
                        sample_unfiltereddelta1.append(0.)
                        sample_unfiltereddelta2.append(0.)
                        self.rateofchange1,self.rateofchange2,rateofchange1plot,rateofchange2plot = 0.,0.,0.,0.

                    # limit displayed RoR #(only before TP is recognized) # WHY?
                    if self.RoRlimitFlag: # not self.TPalarmtimeindex and self.RoRlimitFlag:
                        if not max(-self.maxRoRlimit,self.RoRlimitm) < rateofchange1plot < min(self.maxRoRlimit,self.RoRlimit):
                            rateofchange1plot = None
                        if not max(-self.maxRoRlimit,self.RoRlimitm) < rateofchange2plot < min(self.maxRoRlimit,self.RoRlimit):
                            rateofchange2plot = None

                    # append new data to the rateofchange arrays
                    sample_delta1.append(rateofchange1plot)
                    sample_delta2.append(rateofchange2plot)

                    if local_flagstart:
                        ror_start = 0
                        ror_end = length_of_qmc_timex
                        if self.timeindex[6] > 0:
                            ror_end = self.timeindex[6]+1
                        if self.DeltaETflag and self.l_delta1 is not None:
                            if self.timeindex[0] > -1:
                                ror_start = max(self.timeindex[0],self.timeindex[0]+int(round(self.deltaETfilter/2.)) + max(2,(self.deltaETsamples + 1)))
                                self.l_delta1.set_data(sample_timex[ror_start:ror_end], sample_delta1[ror_start:ror_end])
                            else:
                                self.l_delta1.set_data([], [])
                        if self.DeltaBTflag and self.l_delta2 is not None:
                            if self.timeindex[0] > -1:
                                ror_start = max(self.timeindex[0],self.timeindex[0]+int(round(self.deltaBTfilter/2.)) + max(2,(self.deltaBTsamples + 1)))
                                self.l_delta2.set_data(sample_timex[ror_start:ror_end], sample_delta2[ror_start:ror_end])
                            else:
                                self.l_delta2.set_data([], [])

                        #readjust xlimit of plot if needed
                        if  not self.fixmaxtime and not self.locktimex:
                            now = (sample_timex[-1] if self.timeindex[0] == -1 else sample_timex[-1] - sample_timex[self.timeindex[0]])
                            if now > (self.endofx - 45):            # if difference is smaller than 45 seconds
                                self.endofx = int(now + 180.)       # increase x limit by 3 minutes
                                self.xaxistosm()
                        if self.projectFlag:
                            self.updateProjection()

                        # autodetect CHARGE event
                        # only if BT > 77C/170F
                        if not self.autoChargeIdx and self.autoChargeFlag and self.autoCHARGEenabled and self.timeindex[0] < 0 and length_of_qmc_timex >= 5 and \
                            ((self.mode == 'C' and sample_temp2[-1] > 77) or (self.mode == 'F' and sample_temp2[-1] > 170)):
                            o = 0.5 if self.mode == 'C' else 0.5 * 1.8
                            b = self.aw.BTbreak(length_of_qmc_timex - 1,o) # call BTbreak with last index
                            if b > 0:
                                # we found a BT break at the current index minus b
                                self.autoChargeIdx = length_of_qmc_timex - b
                        # check for TP event if already CHARGEed and not yet recognized (earliest in the next call to sample())
                        elif not self.TPalarmtimeindex and self.timeindex[0] > -1 and not self.timeindex[1] and self.timeindex[0]+8 < len(sample_temp2) and self.checkTPalarmtime():
                            try:
                                tp = self.aw.findTP()
                                if ((self.mode == 'C' and sample_temp2[tp] > 50 and sample_temp2[tp] < 150) or \
                                    (self.mode == 'F' and sample_temp2[tp] > 100 and sample_temp2[tp] < 300)): # only mark TP if not an error value!
                                    self.autoTPIdx = 1
                                    self.TPalarmtimeindex = tp
                            except Exception as e: # pylint: disable=broad-except
                                _log.exception(e)
                            try:
                                # if 2:30min into the roast and TPalarmtimeindex alarmindex not yet set,
                                # we place the TPalarmtimeindex at the current index to enable in airoasters without TP the autoDRY and autoFCs functions and activate the TP Phases LCDs
                                if self.TPalarmtimeindex is None and ((sample_timex[-1] - sample_timex[self.timeindex[0]]) > 150):
                                    self.TPalarmtimeindex = length_of_qmc_timex - 1
                            except Exception as e: # pylint: disable=broad-except
                                _log.exception(e)
                        # autodetect DROP event
                        # only if 8min into roast and BT>160C/320F
                        if not self.autoDropIdx and self.autoDropFlag and self.autoDROPenabled and self.timeindex[0] > -1 and not self.timeindex[6] and \
                            length_of_qmc_timex >= 5 and ((self.mode == 'C' and sample_temp2[-1] > 160) or (self.mode == 'F' and sample_temp2[-1] > 320)) and\
                            ((sample_timex[-1] - sample_timex[self.timeindex[0]]) > 420):
                            o = 0.2 if self.mode == 'C' else 0.2 * 1.8
                            b = self.aw.BTbreak(length_of_qmc_timex - 1,o)
                            if b > 0:
                                # we found a BT break at the current index minus b
                                self.autoDropIdx = length_of_qmc_timex - b
                        #check for autoDRY: # only after CHARGE and TP and before FCs if not yet set
                        if self.autoDRYflag and self.autoDRYenabled and self.TPalarmtimeindex and self.timeindex[0] > -1 and not self.timeindex[1] and not self.timeindex[2] and sample_temp2[-1] >= self.phases[1]:
                            # if DRY event not yet set check for BT exceeding Dry-max as specified in the phases dialog
                            self.autoDryIdx = 1
                        #check for autoFCs: # only after CHARGE and TP and before FCe if not yet set
                        if self.autoFCsFlag and self.autoFCsenabled and self.TPalarmtimeindex and self.timeindex[0] > -1 and not self.timeindex[2] and not self.timeindex[3] and sample_temp2[-1] >= self.phases[2]:
                            # after DRY (if FCs event not yet set) check for BT exceeding FC-min as specified in the phases dialog
                            self.autoFCsIdx = 1

                    #process active quantifiers
                    try:
                        self.aw.process_active_quantifiers()
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)

                    #update SV on Arduino/TC4, Hottop, or MODBUS if in Ramp/Soak or Background Follow mode and PID is active
                    if self.flagon: # only during sampling
                        #update SV on FujiPIDs
                        if self.device == 0 and self.aw.fujipid.followBackground and self.flagstart: # no SV updates while not yet recording for Fuji PIDs
                            # calculate actual SV
                            sv = self.aw.fujipid.calcSV(tx)
                            # update SV (if needed)
                            if sv is not None and sv != self.aw.fujipid.sv:
                                sv = max(0,sv) # we don't send SV < 0
                                self.aw.fujipid.setsv(sv,silent=True) # this is called in updategraphics() within the GUI thread to move the sliders
                        elif (self.aw.pidcontrol.pidActive and self.aw.pidcontrol.svMode == 1) or self.aw.pidcontrol.svMode == 2:
                            # in BackgroundFollow mode we update the SV even if not active, just we do not move the SV slider
                            # calculate actual SV
                            sv = self.aw.pidcontrol.calcSV(tx)
                            # update SV (if needed)
                            if sv is not None and sv != self.aw.pidcontrol.sv:
                                sv = max(0,sv) # we don't send SV < 0
                                self.aw.pidcontrol.setSV(sv,init=False)

                    # update AUC running value
                    if local_flagstart: # only during recording
                        try:
                            self.aw.updateAUC()
                            if self.AUCguideFlag:
                                self.aw.updateAUCguide()
                        except Exception as e: # pylint: disable=broad-except
                            _log.exception(e)

                    #output ET, BT, ETB, BTB to output program
                    if self.aw.ser.externaloutprogramFlag:
                        try:
                            if self.background:
                                if self.timeindex[0] != -1:
                                    j = self.backgroundtime2index(tx - sample_timex[self.timeindex[0]])
                                else:
                                    j = self.backgroundtime2index(tx)
                                ETB = self.temp1B[j]
                                BTB = self.temp2B[j]
                            else:
                                ETB = -1
                                BTB = -1
#                            from subprocess import call as subprocesscall# @Reimport
#                            subprocesscall([self.aw.ser.externaloutprogram,
#                                f'{sample_temp1[-1]:.1f}',
#                                f'{sample_temp2[-1]:.1f}',
#                                f'{ETB:.1f}',
#                                f'{BTB:.1f}'])
                            self.aw.call_prog_with_args(f'{self.aw.ser.externaloutprogram} {sample_temp1[-1]:.1f} {sample_temp2[-1]:.1f} {ETB:.1f} {BTB:.1f}')
                        except Exception as e: # pylint: disable=broad-except
                            _log.exception(e)

                    #check for each alarm that was not yet triggered
                    try:
                        self.alarmSemaphore.acquire(1)
                        for i, aflag in enumerate(self.alarmflag):
                            #if alarm on, and not triggered, and time is after set time:
                            # menu: 0:ON, 1:START, 2:CHARGE, 3:TP, 4:DRY, 5:FCs, 6:FCe, 7:SCs, 8:SCe, 9:DROP, 10:COOL
                            # qmc.alarmtime = -1 (None == START)
                            # qmc.alarmtime = 0 (CHARGE)
                            # qmc.alarmtime = 1 (DRY)
                            # qmc.alarmtime = 2 (FCs)
                            # qmc.alarmtime = 3 (FCe)
                            # qmc.alarmtime = 4 (SCs)
                            # qmc.alarmtime = 5 (SCe)
                            # qmc.alarmtime = 6 (DROP)
                            # qmc.alarmtime = 7 (COOL)
                            # qmc.alarmtime = 8 (TP)
                            # qmc.alarmtime = 9 (ON)
                            # qmc.alamrtime = 10 (If Alarm)
                            # Cases: (only between CHARGE and DRY we check for TP if alarmtime[i]=8)
                            # 1) the alarm From is START
                            # 2) the alarm was not triggered yet
                            # 3) the alarm From is ON
                            # 4) the alarm From is CHARGE
                            # 5) the alarm From is any other event but TP
                            # 6) the alarm From is TP, it is CHARGED and the TP pattern is recognized
                            if aflag \
                              and self.alarmstate[i] == -1 \
                              and (self.alarmguard[i] < 0 or (0 <= self.alarmguard[i] < len(self.alarmstate) and self.alarmstate[self.alarmguard[i]] != -1)) \
                              and (self.alarmnegguard[i] < 0 or (0 <= self.alarmnegguard[i] < len(self.alarmstate) and self.alarmstate[self.alarmnegguard[i]] == -1)) \
                              and ((self.alarmtime[i] == 9) or (self.alarmtime[i] < 0 and local_flagstart) \
                                or (local_flagstart and self.alarmtime[i] == 0 and self.timeindex[0] > -1) \
                                or (local_flagstart and self.alarmtime[i] > 0 and self.alarmtime[i] < 8 and self.timeindex[self.alarmtime[i]] > 0) \
                                or (self.alarmtime[i] == 10 and self.alarmguard[i] != -1)  \
                                or (local_flagstart and self.alarmtime[i] == 8 and self.timeindex[0] > -1 \
                                    and self.TPalarmtimeindex)):
                                #########
                                # check alarmoffset (time after From event):
                                if self.alarmoffset[i] > 0:
                                    alarm_time = self.timeclock.elapsed()/1000.
                                    if self.alarmtime[i] < 0: # time after START
                                        pass # the alarm_time is the clock time
                                    elif local_flagstart and self.alarmtime[i] == 0 and self.timeindex[0] > -1: # time after CHARGE
                                        alarm_time = alarm_time - sample_timex[self.timeindex[0]]
                                    elif local_flagstart and self.alarmtime[i] == 8 and self.TPalarmtimeindex: # time after TP
                                        alarm_time = alarm_time - sample_timex[self.TPalarmtimeindex]
                                    elif local_flagstart and self.alarmtime[i] < 8 and self.timeindex[self.alarmtime[i]] > 0: # time after any other event
                                        alarm_time = alarm_time - sample_timex[self.timeindex[self.alarmtime[i]]]
                                    elif local_flagstart and self.alarmtime[i] == 10: # time or temp after the trigger of the alarmguard (if one is set)
                                        # we know here that the alarmstate of the guard is valid as it has triggered
                                        alarm_time = alarm_time - sample_timex[self.alarmstate[self.alarmguard[i]]]

                                    if alarm_time >= self.alarmoffset[i]:
                                        self.temporaryalarmflag = i
                                #########
                                # check alarmtemp:
                                alarm_temp = None
                                if self.alarmtime[i] == 10: # IF ALARM and only during recording as otherwise no data to refer to is available
                                    # and this is a conditional alarm with alarm_time set to IF ALARM
                                    if_alarm_state = self.alarmstate[self.alarmguard[i]] # reading when the IF ALARM triggered
                                    if if_alarm_state != -1:
                                        if if_alarm_state < len(sample_timex):
                                            alarm_idx = if_alarm_state
                                        else:
                                            alarm_idx = -1
                                    # we subtract the reading at alarm_idx from the current reading of the channel determined by alarmsource
                                else:
                                    alarm_idx = None
                                if self.alarmsource[i] == -2 and sample_delta1[-1] is not None:  #check DeltaET (might be None)
                                    alarm_temp = sample_delta1[-1]
                                    if alarm_idx is not None:
                                        sd1 = sample_delta1[alarm_idx]
                                        if sd1 is not None:
                                            alarm_temp -= sd1 # subtract the reading at alarm_idx for IF ALARMs
                                elif self.alarmsource[i] == -1 and sample_delta2[-1] is not None: #check DeltaBT (might be None
                                    alarm_temp = sample_delta2[-1]
                                    if alarm_idx is not None:
                                        sd2 = sample_delta2[alarm_idx]
                                        if sd2 is not None:
                                            alarm_temp -= sd2 # subtract the reading at alarm_idx for IF ALARMs
                                elif self.alarmsource[i] == 0:                      #check ET
                                    alarm_temp = sample_temp1[-1]
                                    if alarm_idx is not None:
                                        alarm_temp -= sample_temp1[alarm_idx] # subtract the reading at alarm_idx for IF ALARMs
                                elif self.alarmsource[i] == 1:                      #check BT
                                    alarm_temp = sample_temp2[-1]
                                    if alarm_idx is not None:
                                        alarm_temp -= sample_temp2[alarm_idx] # subtract the reading at alarm_idx for IF ALARMs
                                elif self.alarmsource[i] > 1 and ((self.alarmsource[i] - 2) < (2*len(self.extradevices))):
                                    if (self.alarmsource[i])%2==0:
                                        alarm_temp = sample_extratemp1[(self.alarmsource[i] - 2)//2][-1]
                                        if alarm_idx is not None:
                                            alarm_temp -= sample_extratemp1[(self.alarmsource[i] - 2)//2][alarm_idx] # subtract the reading at alarm_idx for IF ALARMs
                                    else:
                                        alarm_temp = sample_extratemp2[(self.alarmsource[i] - 2)//2][-1]
                                        if alarm_idx is not None:
                                            alarm_temp -= sample_extratemp2[(self.alarmsource[i] - 2)//2][alarm_idx] # subtract the reading at alarm_idx for IF ALARMs

                                alarm_limit = self.alarmtemperature[i]

                                if alarm_temp is not None and alarm_temp != -1 and (
                                        (self.alarmcond[i] == 1 and alarm_temp > alarm_limit) or
                                        (self.alarmcond[i] == 0 and alarm_temp < alarm_limit) or
                                        (alarm_idx is not None and alarm_temp == alarm_limit)): # for relative IF_ALARMS we include the equality
                                    self.temporaryalarmflag = i
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                    finally:
                        if self.alarmSemaphore.available() < 1:
                            self.alarmSemaphore.release(1)

                #############    if using DEVICE 18 (no device). Manual mode
                # temperatures are entered when pressing push buttons like for example at self.markDryEnd()
                else:
                    tx = int(self.timeclock.elapsed()/1000.)
                    #readjust xlimit of plot if needed
                    if  not self.fixmaxtime and not self.locktimex:
                        now = (tx if self.timeindex[0] == -1 else tx - sample_timex[self.timeindex[0]])
                        if now > (self.endofx - 45):            # if difference is smaller than 45 seconds
                            self.endofx = now + 180              # increase x limit by 3 minutes (180)
                            if self.ax is not None:
                                self.ax.set_xlim(self.startofx,self.endofx)
                            self.xaxistosm()
                    # also in the manual case we check for TP
                    # check for TP event if already CHARGEed and not yet recognized
                    if local_flagstart and not self.TPalarmtimeindex and self.timeindex[0] > -1 and self.timeindex[0]+5 < len(sample_temp2) and self.checkTPalarmtime():
                        self.autoTPIdx = 1
                        self.TPalarmtimeindex = self.aw.findTP()
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
                _, _, exc_tb = sys.exc_info()
                self.adderror((QApplication.translate('Error Message','Exception:') + ' sample() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
            finally:
                if self.profileDataSemaphore.available() < 1:
                    self.profileDataSemaphore.release(1)
                #update screen in main GUI thread
                self.updategraphicsSignal.emit()


    # idx is the index to be displayed, by default -1 (the last item of each given array)
    # if idx is None, the default error values are displayed
    # all other parameters are expected to be lists of values, but for PID_SV and PID_DUTY
    # time is the time at in second to be displayed (might be negative, but negative times are rendered as 00:00)
    # if time is None, the timer LCD is not updated
    # time is only updated if not sampling (self.flagon=False)
    # values of -1 are suppressed to their default "off" representation
    # XTs1 and XTs2 are lists of lists of values for the corresponding extra LCDs
    def updateLCDs(self, time:Optional[float], temp1:List[float], temp2:List[float], delta1:List[Optional[float]], delta2:List[Optional[float]], XTs1:Union[List[List[float]], List['npt.NDArray[numpy.floating]']], XTs2:Union[List[List[float]], List['npt.NDArray[numpy.floating]']], PID_SV:float=-1., PID_DUTY:float=-1, idx:Optional[int]=-1):
        try:
            if self.LCDdecimalplaces:
                lcdformat = '%.1f'
                resLCD = '-.-' if idx is None else 'u.u'
            else:
                lcdformat = '%.0f'
                resLCD = '--' if idx is None else 'uu'
            timestr = None
            ## TIMER LCDS:
            if not self.flagon and time is not None:
                timestr = '00:00'
                if time > 0:
                    try:
                        timestr = stringfromseconds(time)
                    except Exception: # pylint: disable=broad-except
                        pass
                self.setLCDtimestr(timestr)

            ## ET LCD:
            etstr = resLCD
            try: # if temp1 is None, which should never be the case, this fails
                if temp1 and idx is not None and idx < len(temp1) and temp1[idx] not in [None, -1] and not numpy.isnan(temp1[idx]):
                    if -100 < temp1[idx] < 1000:
                        etstr = lcdformat%temp1[idx]
                    elif self.LCDdecimalplaces and -10000 < temp1[idx] < 100000:
                        etstr = f'{temp1[idx]:.0f}'
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            self.aw.lcd2.display(etstr)

            ## BT LCD:
            btstr = resLCD
            try:
                if temp2 and idx is not None and idx < len(temp2) and temp2[idx] not in [None, -1] and not numpy.isnan(temp2[idx]):
                    if -100 < temp2[idx] < 1000:
                        btstr = lcdformat%temp2[idx]            # BT
                    elif self.LCDdecimalplaces and -10000 < temp2[idx] < 100000:
                        btstr = f'{temp2[idx]:.0f}'
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            self.aw.lcd3.display(btstr)

            ## Delta LCDs:
            deltaetstr = resLCD
            deltabtstr = resLCD
            try:
                if delta1 and idx is not None and idx < len(delta1):
                    d1:Optional[float] = delta1[idx]
                    if d1 is not None and d1 != -1 and -100 < d1 < 1000:
                        deltaetstr = lcdformat%d1        # rate of change ET (degrees per minute)
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            try:
                if delta2 and idx is not None and idx < len(delta2):
                    d2:Optional[float] = delta2[idx]
                    if d2 is not None and d2 != -1 and  -100 < d2 < 1000:
                        deltabtstr = lcdformat%d2        # rate of change BT (degrees per minute)
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            self.aw.lcd4.display(deltaetstr)
            self.aw.lcd5.display(deltabtstr)
            try:
                self.updateLargeDeltaLCDs(deltabt=deltabtstr,deltaet=deltaetstr)
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            # Fuji/Delta LCDs
            try:
                if self.aw.ser.showFujiLCDs and self.device in (0, 26):
                    pidsvstr = resLCD
                    piddutystr = resLCD
                    if PID_SV not in [None, -1] and not numpy.isnan(PID_SV) and PID_DUTY not in [None, -1] and not numpy.isnan(PID_DUTY):
                        pidsvstr = lcdformat%PID_SV
                        piddutystr = lcdformat%PID_DUTY
                    self.aw.lcd6.display(pidsvstr)
                    self.aw.lcd7.display(piddutystr)
                    self.updateLargePIDLCDs(sv=pidsvstr,duty=piddutystr)
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            # LargeLCDs and WebLCDs
            if self.aw.WebLCDs:
                self.updateWebLCDs(bt=btstr,et=etstr,time=timestr)
            try:
                if timestr is None:
                    self.updateLargeLCDsReadingsSignal.emit(btstr,etstr)
                else:
                    self.updateLargeLCDsSignal.emit(btstr,etstr,timestr)
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            # Extra LCDs
            ndev = min(len(XTs1),len(XTs2))
            extra1_values = []
            extra2_values = []
            for i in range(ndev):
                if i < self.aw.nLCDS:
                    try:
                        extra1_value = resLCD
                        if idx is not None and XTs1[i] and idx < len(XTs1[i]):
                            fmt = lcdformat
                            v = float(XTs1[i][idx])
                            if v is not None and v != -1:
                                if self.intChannel(i,0):
                                    fmt = '%.0f'
                                if -100 < v < 1000:
                                    extra1_value = fmt%v # everything fits
                                elif self.LCDdecimalplaces and -10000 < v < 100000:
                                    fmt = '%.0f'
                                    extra1_value = fmt%v
                            elif self.intChannel(i,0):
                                extra1_value = 'uu'
                        self.aw.extraLCD1[i].display(extra1_value)
                        extra1_values.append(extra1_value)
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                        extra1_value = '--'
                        extra1_values.append(extra1_value)
                        self.aw.extraLCD1[i].display(extra1_value)
                    try:
                        extra2_value = resLCD
                        if idx is not None and XTs2[i] and idx < len(XTs2[i]):
                            fmt = lcdformat
                            v = float(XTs2[i][idx])
                            if v is not None and v != -1:
                                if self.intChannel(i,1):
                                    fmt = '%.0f'
                                if -100 < v < 1000:
                                    extra2_value = fmt%v # everything fits
                                elif self.LCDdecimalplaces and -10000 < v < 100000:
                                    fmt = '%.0f'
                                    extra2_value = fmt%v
                            elif self.intChannel(i,1):
                                extra2_value = 'uu'
                        self.aw.extraLCD2[i].display(extra2_value)
                        extra2_values.append(extra2_value)
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                        extra2_value = '--'
                        extra2_values.append(extra2_value)
                        self.aw.extraLCD2[i].display(extra2_value)

            self.updateLargeExtraLCDs(extra1=extra1_values,extra2=extra2_values)

        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    # runs from GUI thread.
    # this function is called by a signal at the end of the thread sample()
    # during sample, updates to GUI widgets or anything GUI must be done here (never from thread)
    @pyqtSlot()
    def updategraphics(self):
        QApplication.processEvents() # without this we see some flickers (canvas redraws) on using multiple button event actions on macOS!?
        try:
            if self.flagon and self.ax is not None:
                #### lock shared resources #####
                self.profileDataSemaphore.acquire(1)
                try:
                    # initialize the arrays depending on the recording state
                    if (self.flagstart and len(self.timex) > 0) or not self.flagon: # on recording or off we use the standard data structures
                        sample_timex = self.timex
                        sample_temp1 = self.temp1
                        sample_temp2 = self.temp2
                        sample_extratimex = self.extratimex
                        sample_extratemp1 = self.extratemp1
                        sample_extratemp2 = self.extratemp2

                        sample_delta1 = self.delta1
                        sample_delta2 = self.delta2

                    else: # only on ON we use the temporary sampling datastructures
                        sample_timex = self.on_timex
                        sample_temp1 = self.on_temp1
                        sample_temp2 = self.on_temp2
                        sample_extratimex = self.extratimex
                        sample_extratemp1 = self.on_extratemp1
                        sample_extratemp2 = self.on_extratemp2

                        sample_delta1 = self.on_delta1
                        sample_delta2 = self.on_delta2

                    if sample_timex:
                        # update all LCDs (small, large, Web,..)
                        self.updateLCDs(
                            None,
                            sample_temp1,
                            sample_temp2,
                            sample_delta1,
                            sample_delta2,
                            sample_extratemp1,
                            sample_extratemp2,
                            self.currentpidsv,
                            self.dutycycle)

                finally:
                    if self.profileDataSemaphore.available() < 1:
                        self.profileDataSemaphore.release(1)

                #check move slider pending actions
                if self.temporarymovepositiveslider is not None:
                    slidernr,value = self.temporarymovepositiveslider # pylint: disable=unpacking-non-sequence
                    if self.aw.sliderpos(slidernr) != value or self.temporayslider_force_move:
                        self.aw.moveslider(slidernr,value) # move slider
                        self.aw.fireslideraction(slidernr) # fire action
                        self.aw.extraeventsactionslastvalue[slidernr] = int(round(value)) # remember last value for relative event buttons
                        self.temporayslider_force_move = False
                self.temporarymovepositiveslider = None
                if self.temporarymovenegativeslider is not None:
                    slidernr,value = self.temporarymovenegativeslider # pylint: disable=unpacking-non-sequence
                    if self.aw.sliderpos(slidernr) != value or self.temporayslider_force_move:
                        self.aw.moveslider(slidernr,value) # move slider
                        self.aw.fireslideraction(slidernr) # fire action
                        self.aw.extraeventsactionslastvalue[slidernr] = int(round(value)) # remember last value for relative event buttons
                        self.temporayslider_force_move = False
                self.temporarymovenegativeslider = None

                #write error message
                if self.temporary_error is not None:
                    self.aw.sendmessage(self.temporary_error)
                    self.temporary_error = None # clear flag
                    # update error dlg
                    if self.aw.error_dlg:
                        self.aw.error_dlg.update()

                #update serial_dlg
                if self.aw.serial_dlg:
                    try:
                        #### lock shared resources #####
                        self.seriallogsemaphore.acquire(1)
                        self.aw.serial_dlg.update()
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                    finally:
                        if self.seriallogsemaphore.available() < 1:
                            self.seriallogsemaphore.release(1)

                #update message_dlg
                if self.aw.message_dlg:
                    self.aw.message_dlg.update()

                #check quantified events; do this before the canvas is redraw as additional annotations might be added here, but do not recursively call updategraphics
                # NOTE: that EventRecordAction has to be called from outside the critical section protected by the profileDataSemaphore as it is itself accessing this section!!
                for el in self.quantifiedEvent:
                    try:
                        self.aw.moveslider(el[0],el[1])
                        if self.flagstart:
                            evalue = self.aw.float2float((el[1] + 10.0) / 10.0)
                            self.EventRecordAction(extraevent = 1,eventtype=el[0],eventvalue=evalue,eventdescription='Q'+self.eventsvalues(evalue),doupdategraphics=False)
                        if self.flagon and self.aw.eventquantifieraction[el[0]]:
                            self.aw.fireslideractionSignal.emit(el[0])
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                self.quantifiedEvent = []

                if self.flagstart:
                    if  self.zoom_follow: # self.aw.ntb._active == 'ZOOM'
                        if not self.fmt_data_RoR:
                            # center current temp reading on canvas
                            temp = None
                            if self.temp2 and len(self.temp2)>0:
                                temp = self.temp2[-1]
                                if temp is not None:
                                    tx = self.timex[-1]
                                    # get current limits
                                    xlim = self.ax.get_xlim()
                                    xlim_offset = (xlim[1] - xlim[0]) / 2.
                                    xlim_new = (tx - xlim_offset, tx + xlim_offset)
                                    ylim = self.ax.get_ylim()
                                    ylim_offset = (ylim[1] - ylim[0]) / 2.
                                    ylim_new = (temp - ylim_offset, temp + ylim_offset)
                                    if ylim != ylim_new or xlim != xlim_new:
                                        # set new limits to center current temp on canvas
                                        self.ax.set_xlim(xlim_new)
                                        self.ax.set_ylim(ylim_new)
                                        if self.twoAxisMode() and self.delta_ax is not None:
                                            # keep the RoR axis constant
                                            zlim = self.delta_ax.get_ylim()
                                            zlim_offset = (zlim[1] - zlim[0]) / 2.
                                            tempd = (self.delta_ax.transData.inverted().transform((0,self.ax.transData.transform((0,temp))[1]))[1])
                                            zlim_new = (tempd - zlim_offset, tempd + zlim_offset)
                                            self.delta_ax.set_ylim(zlim_new)
                                        self.ax_background = None
                        else:
                            # center current RoR reading on canvas
                            ror = None
                            two_ax_mode = (self.DeltaETflag or self.DeltaBTflag or (self.background and (self.DeltaETBflag or self.DeltaBTBflag)))
                            if two_ax_mode and self.delta_ax is not None:
                                if self.delta2 and len(self.delta2)>0:
                                    ror = self.delta2[-1]
                                if ror is not None:
                                    tx = self.timex[-1]
                                    # get current limits
                                    xlim = self.ax.get_xlim()
                                    xlim_offset = (xlim[1] - xlim[0]) / 2.
                                    xlim_new = (tx - xlim_offset, tx + xlim_offset)
                                    ylim = self.ax.get_ylim()
                                    ylim_offset = (ylim[1] - ylim[0]) / 2.
                                    rord = (self.ax.transData.inverted().transform((0,self.delta_ax.transData.transform((0,ror))[1]))[1])
                                    ylim_new = (rord - ylim_offset, rord + ylim_offset)
                                    if ylim != ylim_new or xlim != xlim_new:
                                        # set new limits to center current temp on canvas
                                        self.ax.set_xlim(xlim_new)
                                        self.ax.set_ylim(ylim_new)
                                        # keep the RoR axis constant
                                        zlim = self.delta_ax.get_ylim()
                                        zlim_offset = (zlim[1] - zlim[0]) / 2.
                                        zlim_new = (ror - zlim_offset, ror + zlim_offset)
                                        self.delta_ax.set_ylim(zlim_new)
                                        self.ax_background = None

                    if self.patheffects:
                        rcParams['path.effects'] = [PathEffects.withStroke(linewidth=self.patheffects, foreground=self.palette['background'])]
                    else:
                        rcParams['path.effects'] = []

                    #auto mark CHARGE (this forces a realignment/redraw by resetting the cache ax_background)
                    if self.autoChargeIdx and self.timeindex[0] < 0:
                        self.markCharge() # we do not reset the autoChargeIdx to avoid another trigger
                        self.autoChargeIdx = 0

                    #auto mark TP/DRY/FCs/DROP
                    # we set marks already here to have the canvas, incl. the projections, immediately redrawn
                    if self.autoTPIdx != 0:
                        self.markTP()
                        self.autoTPIdx = 0
                    if self.autoDryIdx != 0:
                        self.markDryEnd()
                        self.autoDryIdx = 0
                    if self.autoFCsIdx != 0:
                        self.mark1Cstart()
                        self.autoFCsIdx = 0
                    if self.autoDropIdx > 0 and self.timeindex[0] > -1 and not self.timeindex[6]:
                        self.markDrop() # we do not reset the autoDropIdx here to avoid another trigger
                        self.autoDropIdx = -1 # we set the autoDropIdx to a negative value to prevent further triggers after undo markDROP

                    ##### updated canvas
                    try:
                        if not self.block_update:
                        #-- start update display
                            #### lock shared resources to ensure that no other redraw is interfering with this one here #####
                            self.profileDataSemaphore.acquire(1)
                            try:
                                if self.ax_background is not None:
                                    self.fig.canvas.restore_region(self.ax_background)
                                    # draw eventtypes
# this seems not to be needed and hides partially event by value "Combo-type" annotations
#                                    if self.eventsshowflag != 0 and self.eventsGraphflag in [2,3,4]:
#                                        self.ax.draw_artist(self.l_eventtype1dots)
#                                        self.ax.draw_artist(self.l_eventtype2dots)
#                                        self.ax.draw_artist(self.l_eventtype3dots)
#                                        self.ax.draw_artist(self.l_eventtype4dots)
                                    # draw delta lines

                                    if self.swapdeltalcds:
                                        if self.DeltaETflag and self.l_delta1 is not None:
                                            try:
                                                self.ax.draw_artist(self.l_delta1)
                                            except Exception as e: # pylint: disable=broad-except
                                                _log.exception(e)
                                        if self.DeltaBTflag and self.l_delta2 is not None:
                                            try:
                                                self.ax.draw_artist(self.l_delta2)
                                            except Exception as e: # pylint: disable=broad-except
                                                _log.exception(e)
                                    else:
                                        if self.DeltaBTflag and self.l_delta2 is not None:
                                            try:
                                                self.ax.draw_artist(self.l_delta2)
                                            except Exception as e: # pylint: disable=broad-except
                                                _log.exception(e)
                                        if self.DeltaETflag and self.l_delta1 is not None:
                                            try:
                                                self.ax.draw_artist(self.l_delta1)
                                            except Exception as e: # pylint: disable=broad-except
                                                _log.exception(e)

                                    # draw extra curves
                                    xtra_dev_lines1 = 0
                                    xtra_dev_lines2 = 0

                                    try:
                                        for i in range(min(len(self.aw.extraCurveVisibility1),len(self.aw.extraCurveVisibility1),len(sample_extratimex),len(sample_extratemp1),len(self.extradevicecolor1),len(self.extraname1),len(sample_extratemp2),len(self.extradevicecolor2),len(self.extraname2))):
                                            if self.aw.extraCurveVisibility1[i] and len(self.extratemp1lines) > xtra_dev_lines1:
                                                try:
                                                    self.ax.draw_artist(self.extratemp1lines[xtra_dev_lines1])
                                                except Exception as e: # pylint: disable=broad-except
                                                    _log.exception(e)
                                                xtra_dev_lines1 = xtra_dev_lines1 + 1
                                            if self.aw.extraCurveVisibility2[i] and len(self.extratemp2lines) > xtra_dev_lines2:
                                                try:
                                                    self.ax.draw_artist(self.extratemp2lines[xtra_dev_lines2])
                                                except Exception as e: # pylint: disable=broad-except
                                                    _log.exception(e)
                                                xtra_dev_lines2 = xtra_dev_lines2 + 1
                                    except Exception: # pylint: disable=broad-except
                                        pass
                                    if self.swaplcds:
                                        # draw ET
                                        if self.ETcurve:
                                            try:
                                                self.ax.draw_artist(self.l_temp1)
                                            except Exception as e: # pylint: disable=broad-except
                                                _log.exception(e)
                                        # draw BT
                                        if self.BTcurve:
                                            try:
                                                self.ax.draw_artist(self.l_temp2)
                                            except Exception as e: # pylint: disable=broad-except
                                                _log.exception(e)
                                    else:
                                        # draw BT
                                        if self.BTcurve:
                                            try:
                                                self.ax.draw_artist(self.l_temp2)
                                            except Exception as e: # pylint: disable=broad-except
                                                _log.exception(e)
                                        # draw ET
                                        if self.ETcurve:
                                            try:
                                                self.ax.draw_artist(self.l_temp1)
                                            except Exception as e: # pylint: disable=broad-except
                                                _log.exception(e)

                                    try:
                                        if self.BTcurve:
                                            for a in self.l_annotations:
                                                self.ax.draw_artist(a)
                                    except Exception as e : # pylint: disable=broad-except
                                        _log.exception(e)

                                    try:
                                        self.update_additional_artists()
                                    except Exception as e: # pylint: disable=broad-except
                                        _log.exception(e)

                                    self.fig.canvas.blit(self.ax.get_figure().bbox)

                                else:
                                    # we do not have a background to bitblit, so do a full redraw
                                    self.updateBackground() # does the canvas draw, but also fills the ax_background cache
                                    self.update_additional_artists()
                            finally:
                                if self.profileDataSemaphore.available() < 1:
                                    self.profileDataSemaphore.release(1)
                        #-- end update display
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                        _, _, exc_tb = sys.exc_info()
                        self.adderror((QApplication.translate('Error Message','Exception:') + ' updategraphics() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))

                    try:
                        if self.backgroundprofile is not None and (self.timeindex[0] > -1 or self.timeindexB[0] < 0):
                            if self.backgroundReproduce or self.backgroundPlaybackEvents:
                                self.playbackevent()
                            if self.backgroundPlaybackDROP:
                                self.playbackdrop()
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                        _, _, exc_tb = sys.exc_info()
                        self.adderror((QApplication.translate('Error Message','Exception:') + ' updategraphics() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))

                    #####
                    if self.patheffects:
                        rcParams['path.effects'] = []

                    #update phase lcds
                    self.aw.updatePhasesLCDs()

                    #update AUC lcd
                    if self.AUClcdFlag:
                        self.aw.updateAUCLCD()

                #check triggered alarms
                if self.temporaryalarmflag > -3:
                    i = self.temporaryalarmflag  # reset self.temporaryalarmflag before calling alarm
                    self.temporaryalarmflag = -3 # self.setalarm(i) can take longer to run than the sampling interval
                    self.setalarm(i)

        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' updategraphics() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))

    def setLCDtimestr(self, timestr):
        self.aw.lcd1.display(timestr)
        # update connected WebLCDs
        if self.aw.WebLCDs:
            self.updateWebLCDs(time=timestr)
        if self.aw.largeLCDs_dialog:
            self.updateLargeLCDsTimeSignal.emit(timestr)

    def setLCDtime(self,ts):
        timestr = stringfromseconds(ts)
        self.setLCDtimestr(timestr)

    def updateLCDtime(self):
        if self.flagstart and self.flagon:
            tx = self.timeclock.elapsedMilli()
            if self.aw.simulator is not None:
                speed = self.timeclock.getBase()/1000
                nextreading = (1000. - 1000.*(tx%1.) ) / speed
            else:
                nextreading = 1000. - 1000.*(tx%1.)

            try:
                if self.aw.sample_loop_running and isinstance(self.timeindex, list) and len(self.timeindex) == 8: # ensure we have a valid self.timeindex array

                    if self.timeindex[0] != -1 and isinstance(self.timex, list) and len(self.timex) > self.timeindex[0]:
                        ts = tx - self.timex[self.timeindex[0]]
                    else:
                        ts = tx

                    # if more than max cool (from statistics) past DROP and not yet COOLend turn the time LCD red:
                    if self.timeindex[0]!=-1 and self.timeindex[6] and not self.timeindex[7] and ((len(self.timex) == 1+self.timeindex[6]) or (4*60+2 > (tx - self.timex[self.timeindex[6]]) > 4*60)):
                        # switch LCD color to "cooling" color (only after 4min cooling we switch to slowcoolingtimer color)
                        if (tx - self.timex[self.timeindex[6]]) > 4*60:
                            timer_color = 'slowcoolingtimer'
                        else:
                            timer_color = 'rstimer'
                        self.aw.setTimerColor(timer_color)

                    if self.chargeTimerFlag and self.timeindex[0] == -1 and self.chargeTimerPeriod!= 0:
                        if self.chargeTimerPeriod > ts:
                            ts = self.chargeTimerPeriod - ts
                        else:
                            ts = 0

                    self.setLCDtime(ts)
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            finally:
                QTimer.singleShot(int(round(nextreading)),self.updateLCDtime)

    # redraws at least the canvas if redraw=True and force=True
    def timealign(self,redraw=True,recompute=False,force=False):
        try:
            ptime = None
            btime = None
            if self.alignEvent in [6,7] and self.timeindexB[6] and self.timeindex[6]: # DROP
                ptime = self.timex[self.timeindex[6]]
                btime = self.timeB[self.timeindexB[6]]
            elif self.alignEvent in [5,7] and self.timeindexB[5] and self.timeindex[5]: # SCe
                ptime = self.timex[self.timeindex[5]]
                btime = self.timeB[self.timeindexB[5]]
            elif self.alignEvent in [4,7] and self.timeindexB[4] and self.timeindex[4]: # SCs
                ptime = self.timex[self.timeindex[4]]
                btime = self.timeB[self.timeindexB[4]]
            elif self.alignEvent in [3,7] and self.timeindexB[3] and self.timeindex[3]: # FCe
                ptime = self.timex[self.timeindex[3]]
                btime = self.timeB[self.timeindexB[3]]
            elif self.alignEvent in [2,7] and self.timeindexB[2] and self.timeindex[2]: # FCs
                ptime = self.timex[self.timeindex[2]]
                btime = self.timeB[self.timeindexB[2]]
            elif self.alignEvent in [1,7] and self.timeindexB[1] and self.timeindex[1]: # DRY
                ptime = self.timex[self.timeindex[1]]
                btime = self.timeB[self.timeindexB[1]]
            elif self.timeindexB[0] != -1 and self.timeindex[0] != -1: # CHARGE
                ptime = self.timex[self.timeindex[0]]
                btime = self.timeB[self.timeindexB[0]]
            elif self.timeindexB[0] != -1: # if no foreground profile, align 0:00 to the CHARGE event of the background profile
                ptime = 0
                if self.flagstart:
                    btime = self.timeB[0] if len(self.timeB) > 0 else 0
                elif len(self.timeB)>self.timeindexB[0]:
                    btime = self.timeB[self.timeindexB[0]]
                else:
                    btime = 0
            if ptime is not None and btime is not None:
                difference = ptime - btime
                if difference > 0:
                    self.movebackground('right',abs(difference))
                    self.backmoveflag = 0
                    if redraw:
                        self.redraw(recompute)
                elif difference < 0:
                    self.movebackground('left',abs(difference))
                    self.backmoveflag = 0
                    if redraw:
                        self.redraw(recompute)
                elif redraw and force: # ensure that we at least redraw the canvas
                    self.updateBackground()
            elif redraw and force: # only on aligning with CHARGE we redraw even if nothing is moved to redraw the time axis
                self.updateBackground()
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' timealign() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))

    # we count
    # - foreground curves
    # . ET/BT, even if not visible
    # . all visible extra curves
    # . all foreground event curves
    # - background curves
    # . background ET/BT, even if not visible
    # . 3rd background curve only if visible
    # . background event curves if not empty
    def lenaxlines(self) -> int:
        active_curves = len(self.extratimex)
        curves = self.aw.extraCurveVisibility1[0:active_curves] + self.aw.extraCurveVisibility2[0:active_curves] + [self.ETcurve,self.BTcurve]
        c = curves.count(True)
        if self.background:
            c += 2 # those are alwyays populated
            if self.xtcurveidx > 0: # 3rd background curve set?
                idx3 = self.xtcurveidx - 1
                n3 = idx3 // 2
                if len(self.stemp1BX) > n3 and len(self.stemp2BX) > n3 and len(self.extratimexB) > n3:
                    c += 1
            if self.ytcurveidx > 0: # 4th background curve set?
                idx4 = self.xtcurveidx - 1
                n4 = idx4 // 2
                if len(self.stemp1BX) > n4 and len(self.stemp2BX) > n4 and len(self.extratimexB) > n4:
                    c += 1
            if self.backgroundeventsflag and self.eventsGraphflag in [2,3,4]:
                unique_etypes = set(self.backgroundEtypes)
                # only those background event lines exists that are active and hold events
                active_background_events = [e < 4 and self.showEtypes[e] for e in unique_etypes] # we remove the "untyped" event as this is only drawn as annotation
                c += sum(active_background_events)
        if self.eventsshowflag and self.eventsGraphflag in [2,3,4]:
            c += 4 # the foreground event lines (in contrast to the background ones) are always all present in those modes
        return c

    # we count
    # - deltaET if visible
    # - deltaBT if visible
    # - background deltaET if visible
    # - background deltaBT if visible
    def lendeltaaxlines(self) -> int:
        linecount = 0
        if self.DeltaETflag:
            linecount += 1
        if  self.DeltaBTflag:
            linecount += 1
        if self.background:
            if self.DeltaETBflag:
                linecount += 1
            if self.DeltaBTBflag:
                linecount += 1
        return linecount

    def resetlinecountcaches(self):
        self.linecount = None
        self.deltalinecount = None

    # NOTE: delta lines are also drawn on the main ax
    # ATTENTION: all lines that should be populated need to established in self.ax.lines thus for example delta lines should be established (with empty point lists)
    #   even if they are not drawn before CHARGE to ensure that the linecount corresponds to the fixes lines in self.ax.lines!!
    def resetlines(self):
        if self.ax is not None and not bool(self.aw.comparator):
            #note: delta curves are now in self.delta_ax and have been removed from the count of resetlines()
            if self.linecount is None:
                self.linecount = self.lenaxlines()
            if self.deltalinecount is None:
                self.deltalinecount = self.lendeltaaxlines()
            total_linecount = self.linecount+self.deltalinecount
            # remove lines beyond the max limit of self.linecount)
            if isinstance(self.ax.lines,list): # MPL < v3.5
                self.ax.lines = self.ax.lines[0:total_linecount]
            else:
                for i in range(len(self.ax.lines)-1,-1,-1):
                    if i >= total_linecount:
                        self.ax.lines[i].remove()
                    else:
                        break

    @pyqtSlot(int)
    def getAlarmSet(self,n):
        try:
            self.alarmSemaphore.acquire(1)
            if 0<= n < len(self.alarmsets):
                return self.alarmsets[n]
            return None
        finally:
            if self.alarmSemaphore.available() < 1:
                self.alarmSemaphore.release(1)

    def setAlarmSet(self,n,alarmset):
        try:
            self.alarmSemaphore.acquire(1)
            self.alarmsets[n] = alarmset
        finally:
            if self.alarmSemaphore.available() < 1:
                self.alarmSemaphore.release(1)

    @pyqtSlot(int)
    def selectAlarmSet(self,n):
        alarmset = self.getAlarmSet(n)
        if alarmset is not None:
            try:
                self.alarmSemaphore.acquire(1)
                #
                self.alarmsetlabel = alarmset[0]
                self.alarmflag = alarmset[1][:]
                self.alarmguard = alarmset[2][:]
                self.alarmnegguard = alarmset[3][:]
                self.alarmtime = alarmset[4][:]
                self.alarmoffset = alarmset[5][:]
                self.alarmsource = alarmset[6][:]
                self.alarmcond = alarmset[7][:]
                self.alarmtemperature = alarmset[8][:]
                self.alarmaction = alarmset[9][:]
                self.alarmbeep = alarmset[10][:]
                self.alarmstrings = alarmset[11][:]
                # update the alarmstate array to the new size:
                self.alarmstate = [-1]*len(self.alarmflag)
            finally:
                if self.alarmSemaphore.available() < 1:
                    self.alarmSemaphore.release(1)

    @pyqtSlot(str,int)
    def moveBackgroundAndRedraw(self,direction,step):
        self.movebackground(direction,step)
        self.backmoveflag = 0 # do not align background automatically during redraw!
        self.redraw(recomputeAllDeltas=(direction in ['left', 'right']),sampling=self.flagon)

    def findAlarmSet(self,label):
        try:
            self.alarmSemaphore.acquire(1)
            for i, alrmset in enumerate(self.alarmsets):
                if alrmset[0] == label:
                    return i
            return None
        finally:
            if self.alarmSemaphore.available() < 1:
                self.alarmSemaphore.release(1)

    @staticmethod
    def makeAlarmSet(label, flag, guard, negguard, time, offset, source, cond, temperature, action, beep, alarmstrings):
        return [label,flag,guard,negguard,time,offset,source,cond,temperature,action,beep,alarmstrings]

    # number is alarmnumber+1 (the 1-based alarm number the user sees), for alarms triggered from outside the alarmtable (like PID RS alarms) number is 0
    @pyqtSlot(int,bool,int,str)
    def processAlarm(self,number,beep,action,string):
        if not self.silent_alarms:
            try:
                if beep:
                    QApplication.beep()
                if action == 0:
                    self.showAlarmPopupSignal.emit(string,self.alarm_popup_timout)
                elif action == 1:
                    # alarm call program
                    fname = string.split('#')[0]
        # take c the QDir().current() directory changes with loads and saves
        #            QDesktopServices.openUrl(QUrl("file:///" + str(QDir().current().absolutePath()) + "/" + fname, QUrl.ParsingMode.TolerantMode))
#                    if False: # and platform.system() == 'Windows': # this Windows version fails on commands with arguments # pylint: disable=condition-evals-to-constant,using-constant-test
#                        f = f'file:///{QApplication.applicationDirPath()}/{fname}'
#                        res = QDesktopServices.openUrl(QUrl(f, QUrl.ParsingMode.TolerantMode))
                    # MacOS X: script is expected to sit next to the Artisan.app or being specified with its full path
                    # Linux: script is expected to sit next to the artisan binary or being specified with its full path
                    #
                    # to get the effect of speaking alarms a text containing the following two lines called "say.sh" could do
                    #                #!/bin/sh
                    #                say "Hello" &
                    # don't forget to do
                    #                # cd
                    #                # chmod +x say.sh
                    #
                    # alternatively use "say $@ &" as command and send text strings along
                    # Voices:
                    #  -v Alex (male english)
                    #  -v Viki (female english)
                    #  -v Victoria (female english)
                    #  -v Yannick (male german)
                    #  -v Anna (female german)
                    #  -v Paolo (male italian)
                    #  -v Silvia (female italian)
                    self.aw.call_prog_with_args(fname)
                    res = True
                    if res:
                        self.aw.sendmessage(QApplication.translate('Message','Alarm is calling: {0}').format(fname))
                    else:
                        self.adderror(QApplication.translate('Message','Calling alarm failed on {0}').format(fname))
                elif action == 2:
                    # alarm event button
                    button_number = None
                    text = string.split('#')[0]
                    bnrs = text.split(',')
                    for bnr in bnrs:
                        try:
                            button_number = int(str(bnr.strip())) - 1 # the event buttons presented to the user are numbered from 1 on
                        except Exception: # pylint: disable=broad-except
                            self.aw.sendmessage(QApplication.translate('Message',"Alarm trigger button error, description '{0}' not a number").format(string))
                        if button_number is not None and -1 < button_number < len(self.aw.buttonlist):
                            self.aw.recordextraevent(button_number)
                elif action in [3,4,5,6]:
                    # alarm slider 1-4
                    slidernr = None
                    try:
                        text = string.split('#')[0].strip()
                        if action == 3:
                            slidernr = 0
                        elif action == 4:
                            slidernr = 1
                        elif action == 5:
                            slidernr = 2
                        elif action == 6:
                            slidernr = 3
                        if slidernr is not None:
                            slidervalue = max(self.aw.eventslidermin[slidernr],min(self.aw.eventslidermax[slidernr],int(str(text))))
                            self.aw.moveslider(slidernr,slidervalue)
                            # we set the last value to be used for relative +- button action as base
                            self.aw.extraeventsactionslastvalue[slidernr] = int(round(slidervalue))
                            if self.flagstart:
                                value = self.aw.float2float((slidervalue + 10.0) / 10.0)
                                self.EventRecordAction(extraevent = 1,eventtype=slidernr,eventvalue=value,eventdescription=f'A{number:%d} (S{slidernr:%d})')
                            self.aw.fireslideraction(slidernr)
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                        _, _, exc_tb = sys.exc_info()
                        self.adderror((QApplication.translate('Error Message','Exception:') + ' setalarm() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
                        self.aw.sendmessage(QApplication.translate('Message',"Alarm trigger slider error, description '{0}' not a valid number [0-100]").format(string))

                elif action == 7:
                    # START
                    if self.aw.buttonSTARTSTOP.isEnabled():
                        self.ToggleRecorder()
                elif action == 8:
                    # DRY
                    self.autoDryIdx = len(self.timex)
                elif action == 9:
                    # FCs
                    self.autoFCsIdx = len(self.timex)
                elif action == 10:
                    # FCe
                    if self.aw.buttonFCe.isEnabled():
                        self.mark1Cend()
                elif action == 11:
                    # SCs
                    if self.aw.buttonSCs.isEnabled():
                        self.mark2Cstart()
                elif action == 12:
                    # SCe
                    if self.aw.buttonSCe.isEnabled():
                        self.mark2Cend()
                elif action == 13:
                    # DROP
                    #if self.aw.buttonDROP.isEnabled():
                    #    self.markDrop()
                    self.autoDropIdx = len(self.timex)
                elif action == 14:
                    # COOL
                    if self.aw.buttonCOOL.isEnabled():
                        self.markCoolEnd()
                elif action == 15:
                    # OFF
                    if self.aw.buttonONOFF.isEnabled():
                        self.ToggleMonitor()
                elif action == 16:
                    # CHARGE
                    self.autoChargeIdx = len(self.timex)
                elif action == 17 and self.Controlbuttonflag:
                    # RampSoak ON
                    if self.device == 0 and self.aw.fujipid: # FUJI PID
                        self.aw.fujipid.setrampsoak(1)
                    elif self.aw.pidcontrol: # internal or external MODBUS PID control
                        self.aw.pidcontrol.svMode = 1
                        self.aw.pidcontrol.pidOn()
                elif action == 18 and self.Controlbuttonflag:
                    # RampSoak OFF
                    if self.device == 0 and self.aw.fujipid: # FUJI PID
                        self.aw.fujipid.setrampsoak(0)
                    elif self.aw.pidcontrol:  # internal or external MODBUS PID control
                        self.aw.pidcontrol.svMode = 0
                        self.aw.pidcontrol.pidOff()
                elif action == 19 and self.Controlbuttonflag:
                    # PID ON
                    if self.device == 0 and self.aw.fujipid: # FUJI PID
                        self.aw.fujipid.setONOFFstandby(0)
                    elif self.aw.pidcontrol: # internal or external MODBUS PID control or Arduino TC4 PID
                        self.aw.pidcontrol.pidOn()
                elif action == 20 and self.Controlbuttonflag:
                    # PID OFF
                    if self.device == 0 and self.aw.fujipid: # FUJI PID
                        self.aw.fujipid.setONOFFstandby(1)
                    elif self.aw.pidcontrol: # internal or external MODBUS PID control or Arduino TC4 PID
                        self.aw.pidcontrol.pidOff()
                elif action == 21:
                    # SV slider alarm
                    try:
                        text = string.split('#')[0]
                        sv = float(str(text))
                        if self.device == 0:
                            if sv is not None and sv != self.aw.fujipid.sv:
                                sv = max(0,sv) # we don't send SV < 0
                                self.aw.fujipid.setsv(sv,silent=True)
                        #elif self.aw.pidcontrol.pidActive:
                        elif sv is not None and sv != self.aw.pidcontrol.sv:
                            sv = max(0,sv) # we don't send SV < 0
                            self.aw.pidcontrol.setSV(sv,init=False)
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                        _, _, exc_tb = sys.exc_info()
                        self.adderror((QApplication.translate('Error Message','Exception:') + ' processAlarm() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
                        self.aw.sendmessage(QApplication.translate('Message',"Alarm trigger SV slider error, description '{0}' not a valid number").format(string))
                elif action == 22:
                    # Playback ON
                    self.backgroundPlaybackEvents = True
                elif action == 23:
                    # Playback OFF
                    self.backgroundPlaybackEvents = False
                elif action == 24:
                    # grab only the color definition
                    m = re.match('#[0-9,a-f,A-F]{6}',string.strip())
                    if m is not None:
                        c = m.group()
                        # Set Canvas Color
                        self.aw.setCanvasColorSignal.emit(c)
                elif action == 25:
                    # Reset Canvas Color
                    self.aw.resetCanvasColorSignal.emit()

            except Exception as ex: # pylint: disable=broad-except
                _log.exception(ex)
                _, _, exc_tb = sys.exc_info()
                self.adderror((QApplication.translate('Error Message','Exception:') + ' processAlarm() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))


    def setalarm(self,alarmnumber):
        try:
            self.alarmSemaphore.acquire(1)
            self.alarmstate[alarmnumber] = max(0,len(self.timex) - 1) # we have to ensure that alarmstate of triggered alarms is never negative
            alarm_beep = len(self.alarmbeep) > alarmnumber and self.alarmbeep[alarmnumber] # beep?
            alarm_action = self.alarmaction[alarmnumber]
            alarm_string = self.alarmstrings[alarmnumber]
        finally:
            if self.alarmSemaphore.available() < 1:
                self.alarmSemaphore.release(1)
        self.aw.sendmessage(QApplication.translate('Message','Alarm {0} triggered').format(alarmnumber + 1))
        self.processAlarmSignal.emit(alarmnumber+1,alarm_beep,alarm_action,alarm_string)

    # called only after CHARGE
    def playbackdrop(self):
        try:
            #needed when using device NONE
            if (self.timex and self.timeindexB[6] and not self.timeindex[6] and
                ((self.replayType == 0 and self.timeB[self.timeindexB[6]] - self.timeclock.elapsed()/1000. <= 0) or # by time
                    (self.replayType == 1 and self.TPalarmtimeindex and self.ctemp2[-1] is not None and self.stemp2B[self.timeindexB[6]] - self.ctemp2[-1] <= 0) or # by BT
                    (self.replayType == 2 and self.TPalarmtimeindex and self.ctemp1[-1] is not None and self.stemp1B[self.timeindexB[6]] - self.ctemp1[-1] <= 0))): # by ET
                self.autoDropIdx = len(self.timex) - 2
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' playbackdrop() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))

    # called only after CHARGE
    def playbackevent(self):
        try:
            reproducing = None # index of the event that is currently replaying (suppress other replays in this round)
            #needed when using device NONE
            if self.timex:
                #find time or temp distances
                slider_events = {} # keep event type value pairs to move sliders (but only once per slider and per interval!)
                next_byTemp_checked:bool = False # we take care to reply events by temperature in order!
                now = self.timeclock.elapsedMilli()
                for i, bge in enumerate(self.backgroundEvents):
                    if (i not in self.replayedBackgroundEvents and # never replay one event twice
                        (self.timeindexB[6]==0 or bge < self.timeindexB[6])): # don't replay events that happend after DROP in the backgroundprofile
                        timed = self.timeB[bge] - now
                        delta:float = 1 # by default don't trigger this one
                        if self.replayType == 0: # replay by time
                            delta = timed
                        elif not next_byTemp_checked and self.replayType == 1: # replay by BT (after TP)
                            if self.TPalarmtimeindex:
                                if self.ctemp2[-1] is not None:
                                    delta = self.stemp2B[bge] - self.ctemp2[-1]
                                    next_byTemp_checked = True
                            else: # before TP we switch back to time-based
                                delta = timed
                                next_byTemp_checked = True
                        elif not next_byTemp_checked and self.replayType == 2: # replay by ET (after TP)
                            if self.TPalarmtimeindex:
                                if self.ctemp1[-1] is not None:
                                    delta = self.stemp1B[bge] - self.ctemp1[-1]
                                    next_byTemp_checked = True
                            else: # before TP we switch back to time-based
                                delta = timed
                                next_byTemp_checked = True
                        else:
                            delta = 1 # don't trigger this one
                        if (reproducing is None and
                                self.backgroundEtypes[i] < 4 and self.specialeventplaybackaid[self.backgroundEtypes[i]] and  # only show playback aid for event types with activated playback aid
                                self.backgroundReproduce and 0 < timed < self.detectBackgroundEventTime):
                            if i not in self.beepedBackgroundEvents and self.backgroundReproduceBeep:
                                self.beepedBackgroundEvents.append(i)
                                QApplication.beep()
                            #write text message
                            message = f'> [{self.Betypesf(self.backgroundEtypes[i])}] [{self.eventsvalues(self.backgroundEvalues[i])}] : <b>{stringfromseconds(timed)}</b> : {self.backgroundEStrings[i]}'
                            #rotate colors to get attention
                            if int(round(timed))%2:
                                style = "background-color:'transparent';"
                            else:
                                style = "background-color:'yellow';"

                            self.aw.sendmessage(message,style=style)
                            reproducing = i

                        if delta <= 0:
                            #for devices that support automatic roaster control
                            #if Fuji PID
                            if self.device == 0 and '::' in self.backgroundEStrings[i]:

                                # COMMAND SET STRINGS
                                #  (adjust the SV PID to the float VALUE1)
                                # SETRS::VALUE1::VALUE2::VALUE3  (VALUE1 = target SV. float VALUE2 = time to reach int VALUE 1 (ramp) in minutes. int VALUE3 = hold (soak) time in minutes)

                                # IMPORTANT: VALUES are for controlling ET only (not BT). The PID should control ET not BT. The PID should be connected to ET only.
                                # Therefore, these values don't reflect a BT defined profile. They define an ET profile.
                                # They reflect the changes in ET, which indirectly define BT after some time lag

                                # There are two ways to record a roast. One is by changing Set Values (SV) during the roast,
                                # the other is by using ramp/soaks segments (RS).
                                # Examples:

                                # SETSV::560.3           sets an SV value of 560.3F in the PID at the time of the recorded background event

                                # SETRS::440.2::2::0     starts Ramp Soak mode so that it reaches 440.2F in 2 minutes and holds (soaks) 440.2F for zero minutes

                                # SETRS::300.0::2::3::SETRS::540.0::6::0::SETRS::560.0::4::0::SETRS::560::0::0
                                #       this command has 4 comsecutive commands inside (4 segments)
                                #       1 SETRS::300.0::2::3 reach 300.0F in 2 minutes and hold it for 3 minutes (ie. total dry phase time = 5 minutes)
                                #       2 SETRS::540.0::6::0 then reach 540.0F in 6 minutes and hold it there 0 minutes (ie. total mid phase time = 6 minutes )
                                #       3 SETRS::560.0::4::0 then reach 560.0F in 4 minutes and hold it there 0 minutes (ie. total finish phase time = 4 minutes)
                                #       4 SETRS::560::0::0 then do nothing (because ramp time and soak time are both 0)
                                #       END ramp soak mode

                                self.aw.fujipid.replay(self.backgroundEStrings[i])
                                libtime.sleep(.5)  #avoid possible close times (rounding off)


                            # if playbackevents is active, we fire the event by moving the slider, but only if
                            # a event type is given (type!=4), the background event type is named exactly as the one of the foreground
                            # the event slider is active/visible and has an action defined
                            if (self.backgroundPlaybackEvents and self.backgroundEtypes[i] < 4 and
                                    self.specialeventplayback[self.backgroundEtypes[i]] and # only replay event types activated for replay
                                    (str(self.etypesf(self.backgroundEtypes[i]) == str(self.Betypesf(self.backgroundEtypes[i])))) and
                                    self.aw.eventslidervisibilities[self.backgroundEtypes[i]]): #  and self.aw.eventslideractions[self.backgroundEtypes[i]]
                                slider_events[self.backgroundEtypes[i]] = self.eventsInternal2ExternalValue(self.backgroundEvalues[i]) # add to dict (later overwrite earlier slider moves!)
                                # we move sliders only after processing all pending events (from the collected dict)
                                #self.aw.moveslider(self.backgroundEtypes[i],self.eventsInternal2ExternalValue(self.backgroundEvalues[i])) # move slider and update slider LCD
                                #self.aw.sliderReleased(self.backgroundEtypes[i],force=True) # record event

                            self.replayedBackgroundEvents.append(i) # in any case we mark this event as processed

                # now move the sliders to the new values (if any)
                for k,v in slider_events.items():
                    self.aw.moveslider(k,v)
                    self.aw.sliderReleased(k,force=True)

                #delete existing message
                if reproducing is None:
                    text = self.aw.messagelabel.text()
                    if len(text) and text[0] == '>':
                        self.aw.clearMessageLine(style="background-color:'transparent';")
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' playbackevent() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))

    #make a projection of change of rate of BT on the graph
    def updateProjection(self):
        try:
            # projections are only drawn after CHARGE and before DROP
            if self.ax is not None and self.timeindex[0] != -1 and self.timeindex[6] == 0 and len(self.timex)>0:
                charge = self.timex[self.timeindex[0]] # in data time (corresponds to display time 00:00)
                now = self.timex[-1]                   # in data time (incl. time to charge)
                _,xlim_right = self.ax.get_xlim()      # in data time like timex (incl. time to charge)
                #self.resetlines()
                if self.projectionmode == 0 or (self.projectionmode == 1 and (self.timex[-1]-charge)<=60*5): # linear temperature projection mode based on current RoR
                    #calculate the temperature endpoint at endofx according to the latest rate of change
                    if self.l_BTprojection is not None:
                        if self.BTcurve and len(self.unfiltereddelta2_pure) > 0 and self.unfiltereddelta2_pure[-1] is not None and len(self.ctemp2) > 0 and self.ctemp2[-1] is not None and self.ctemp2[-1] != -1 and not numpy.isnan(self.ctemp2[-1]):
                            # projection extended to the plots current endofx
                            left = now
                            right = max(left, xlim_right + charge) # never have the right point be left of left;)
                            BTprojection = self.ctemp2[-1] + self.unfiltereddelta2_pure[-1]*(right - left)/60.
                            #plot projection
                            self.l_BTprojection.set_data([left,right], [self.ctemp2[-1], BTprojection])
                        else:
                            self.l_BTprojection.set_data([],[])
                    if self.l_ETprojection is not None:
                        if self.ETcurve and len(self.unfiltereddelta1_pure) > 0 and self.unfiltereddelta1_pure[-1] is not None and len(self.ctemp1) > 0 and self.ctemp1[-1] is not None and self.ctemp1[-1] != -1 and not numpy.isnan(self.ctemp1[-1]):
                            # projection extended to the plots current endofx
                            left = now
                            right = max(left,xlim_right + charge) # never have the right point be left of left;)
                            ETprojection = self.ctemp1[-1] + self.unfiltereddelta1_pure[-1]*(right - left)/60.
                            #plot projection
                            self.l_ETprojection.set_data([left,right], [self.ctemp1[-1], ETprojection])
                        else:
                            self.l_ETprojection.set_data([],[])

                # quadratic temperature projection based on linear RoR approximation
                # only active 5min after CHARGE
                elif self.projectionmode == 1 and (self.timex[-1]-charge)>60*5:
                    delta_interval_BT = max(10, self.deltaBTsamples) # at least a span of 10 readings
                    delta_interval_ET = max(10, self.deltaETsamples) # at least a span of 10 readings
                    deltadeltalimit = 0.002
                    delay = self.delay/1000.

                    # NOTE: we use the unfiltered deltas here to make this work also with a delta symbolic formula like x/2 to render RoR in C/30sec
                    if self.l_BTprojection is not None:
                        if (len(self.ctemp2) > 0 and self.ctemp2[-1] is not None and self.ctemp2[-1] != -1 and not numpy.isnan(self.ctemp2[-1]) and
                                len(self.unfiltereddelta2_pure)>delta_interval_BT and
                                self.unfiltereddelta2_pure[-1] and
                                self.unfiltereddelta2_pure[-1]>0 and
                                self.unfiltereddelta2_pure[-delta_interval_BT] and
                                self.unfiltereddelta2_pure[-delta_interval_BT]>0):

                            deltadelta_secsec = (((self.unfiltereddelta2_pure[-1] - self.unfiltereddelta2_pure[-delta_interval_BT])/60) /
                                    (now - self.timex[-delta_interval_BT])) # linear BT RoRoR   C/sec/sec
                            # limit deltadelta
                            deltadelta_secsec = max(-deltadeltalimit,min(deltadeltalimit,deltadelta_secsec))
                            xpoints = numpy.arange(now, xlim_right, delay)
                            ypoints = [self.ctemp2[-1]]
                            delta_sec = self.unfiltereddelta2_pure[-1]/60
                            for _ in range(len(xpoints)-1):
                                ypoints.append(ypoints[-1] + delta_sec*delay)
                                delta_sec = delta_sec + deltadelta_secsec*delay
                            #plot BT curve
                            self.l_BTprojection.set_data(xpoints, ypoints)
                        else:
                            self.l_BTprojection.set_data([],[])

                    if self.l_ETprojection is not None:
                        if (len(self.ctemp1) > 0 and self.ctemp1[-1] is not None and self.ctemp1[-1] != -1 and not numpy.isnan(self.ctemp1[-1]) and
                                len(self.unfiltereddelta1_pure)>delta_interval_BT and
                                self.unfiltereddelta1_pure[-1] and
                                self.unfiltereddelta1_pure[-1]>0 and
                                self.unfiltereddelta1_pure[-delta_interval_BT] and
                                self.unfiltereddelta1_pure[-delta_interval_BT]>0):

                            deltadelta_secsec = (((self.unfiltereddelta1_pure[-1] - self.unfiltereddelta1_pure[-delta_interval_ET])/60) /
                                    (self.timex[-1] - self.timex[-delta_interval_ET])) # linear ET RoRoR   C/sec/sec
                            # limit deltadelta
                            deltadelta_secsec = max(-deltadeltalimit,min(deltadeltalimit,deltadelta_secsec))
                            xpoints = numpy.arange(now, xlim_right, delay)
                            ypoints = [self.ctemp1[-1]]
                            delta_sec = self.unfiltereddelta1_pure[-1]/60
                            for _ in range(len(xpoints)-1):
                                ypoints.append(ypoints[-1] + delta_sec*delay)
                                delta_sec = delta_sec + deltadelta_secsec*delay
                            #plot ET curve
                            self.l_ETprojection.set_data(xpoints, ypoints)
                        else:
                            self.l_ETprojection.set_data([],[])

                # RoR projections
                if self.projectDeltaFlag and (self.timex[-1]-charge)>60*5:
                    delay = self.delay/1000.

                    if self.l_DeltaBTprojection is not None:
                        delta_interval_BT = max(10, self.deltaBTsamples*2) # at least a span of 10 readings
                        if (self.DeltaBTflag and len(self.delta2)>0 and len(self.delta2)>delta_interval_BT):
                            d2_last = self.delta2[-1]
                            d2_left = self.delta2[-delta_interval_BT]
                            if d2_last is not None and d2_left is not None and d2_last>0 and d2_left>0:
                                # compute deltadelta_secsec from delta2 adjusted to delta math formulas
                                deltadelta_secsec = (((d2_last - d2_left)/60) /
                                    (now - self.timex[-delta_interval_BT])) # linear BT RoRoR   C/sec/sec
                                left = now
                                right = max(left, xlim_right) # never have the right point be left of left;)
                                DeltaBTprojection = d2_last + deltadelta_secsec * (right - left) * 60
                                # projection extended to the plots current endofx
                                self.l_DeltaBTprojection.set_data([left,right], [d2_last, DeltaBTprojection])
                            else:
                                self.l_DeltaBTprojection.set_data([],[])
                        else:
                            self.l_DeltaBTprojection.set_data([],[])

                    if self.l_DeltaETprojection is not None:
                        delta_interval_ET = max(10, self.deltaETsamples*2) # at least a span of 10 readings
                        if (self.DeltaETflag and len(self.delta1)>0 and len(self.delta1)>delta_interval_ET):
                            d1_last = self.delta1[-1]
                            d1_left = self.delta1[-delta_interval_ET]
                            if d1_last is not None and d1_left is not None and d1_last>0 and d1_left>0:
                                # compute deltadelta_secsec from delta1 adjusted to delta math formulas
                                deltadelta_secsec = (((d1_last - d1_left)/60) /
                                    (now - self.timex[-delta_interval_ET])) # linear ET RoRoR   C/sec/sec
                                left = now
                                right = max(left, xlim_right) # never have the right point be left of left;)
                                DeltaETprojection = d1_last + deltadelta_secsec * (right - left) * 60
                                # projection extended to the plots current endofx
                                self.l_DeltaETprojection.set_data([left,right], [d1_last, DeltaETprojection])
                            else:
                                self.l_DeltaETprojection.set_data([],[])
                        else:
                            self.l_DeltaETprojection.set_data([],[])

# disabled
#                elif self.projectionmode == 2:
#                    # Under Test. Newton's Law of Cooling
#                    # This comes from the formula of heating (with ET) a cool (colder) object (BT).
#                    # The difference equation (discrete with n elements) is: DeltaT = T(n+1) - T(n) = K*(ET - BT)
#                    # The formula is a natural decay towards ET. The closer BT to ET, the smaller the change in DeltaT
#                    # projectionconstant is a multiplier factor. It depends on
#                    # 1 Damper or fan. Heating by convection is _faster_ than heat by conduction,
#                    # 2 Mass of beans. The heavier the mass, the _slower_ the heating of BT
#                    # 3 Gas or electric power: gas heats BT _faster_ because of hoter air.
#                    # Every roaster will have a different constantN (self.projectionconstant).
#
#                    if self.l_BTprojection is not None:
#                        if len(self.ctemp2) > 0 and self.ctemp2[-1] not in [None, -1] and not numpy.isnan(self.ctemp2[-1]) and len(self.ctemp1) > 0 and self.ctemp1[-1] not in [None, -1] and  not numpy.isnan(self.ctemp1[-1]):
#                            den = self.ctemp1[-1] - self.ctemp2[-1]  #denominator ETn - BTn
#                            if den > 0 and len(self.delta2)>0 and self.delta2[-1]: # if ETn > BTn
#                                starttime = self.timex[self.timeindex[0]]
#                                #get x points
#                                xpoints = list(numpy.arange(self.timex[-1],self.endofx + starttime, self.delay/1000.))
#                                #get y points
#                                ypoints = [self.ctemp2[-1]]                                  # start initializing with last BT
#                                K =  self.projectionconstant*self.delta2[-1]/den/60.         # multiplier
#                                for _ in range(len(xpoints)-1):                              # create new points from previous points
#                                    DeltaT = K*(self.ctemp1[-1]- ypoints[-1])                # DeltaT = K*(ET - BT)
#                                    ypoints.append(ypoints[-1]+ DeltaT)                      # add DeltaT to the next ypoint
#                                self.l_BTprojection.set_data(xpoints, ypoints)
#                            else:
#                                self.l_BTprojection.set_data([],[])
#                        else:
#                            self.l_BTprojection.set_data([],[])
#                    if self.l_ETprojection is not None:
#                        if len(self.ctemp1) > 0 and self.ctemp1[-1] not in [None, -1] and not numpy.isnan(self.ctemp1[-1]):
#                            starttime = self.timex[self.timeindex[0]]
#                            self.l_ETprojection.set_data([self.timex[-1],self.endofx + starttime], [self.ctemp1[-1], self.ctemp1[-1]])
#                        else:
#                            self.l_ETprojection.set_data([],[])
            else:
                if self.l_BTprojection is not None:
                    self.l_BTprojection.set_data([],[])
                if self.l_ETprojection is not None:
                    self.l_ETprojection.set_data([],[])
                if self.l_DeltaBTprojection is not None:
                    self.l_DeltaBTprojection.set_data([],[])
                if self.l_DeltaETprojection is not None:
                    self.l_DeltaETprojection.set_data([],[])


        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' updateProjection() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
            if self.l_BTprojection is not None:
                self.l_BTprojection.set_data([],[])
            if self.l_ETprojection is not None:
                self.l_ETprojection.set_data([],[])
            if self.l_DeltaBTprojection is not None:
                self.l_DeltaBTprojection.set_data([],[])
            if self.l_DeltaETprojection is not None:
                self.l_DeltaETprojection.set_data([],[])

    # takes array with readings, the current index, the sign of the shift as character and the shift value
    # returns val, evalsign
    @staticmethod
    def shiftValueEvalsign(readings,index,sign,shiftval):
        if sign == '-': #  ie. original [1,2,3,4,5,6]; shift right 2 = [1,1,1,2,3,4]
            evalsign = '0'      # "-" becomes digit "0" for python eval compatibility
            shiftedindex = index - shiftval
        else: # sign == '+': #"+" original [1,2,3,4,5,6]; shift left 2  = [3,4,5,6,6,6]
            evalsign = '1'      #digit 1 = "+"
            shiftedindex = index + shiftval
        if len(readings) > 0:
            if shiftedindex >= len(readings):
                shiftedindex = len(readings)- 1
            if shiftedindex < 0:
                return -1, evalsign
            return readings[shiftedindex], evalsign
        return -1, evalsign

    # Computes the shifted value and and sign of the background data (readings), based on the index interpreted w.r.t. foreground time
    # takes array with readings, the current index, the sign of the shift as character and the shift value
    # timex is the time array of the foreground and timeb is that of the background
    # the index is computed w.r.t. the foreground and then mapped to the corresponding index in the given background readings w.r.t. its time array timeb
    # result is clipped w.r.t. foreground data thus data beyond foreground cannot be accessed in the background
    # returns val, evalsign
    def shiftValueEvalsignBackground(self, timex,timeb,readings,index,sign,shiftval):
        if sign == '-': #  ie. original [1,2,3,4,5,6]; shift right 2 = [1,1,1,2,3,4]
            evalsign = '0'      # "-" becomes digit "0" for python eval compatibility
            shiftedindex = index - shiftval
        else: # sign == '+': #"+" original [1,2,3,4,5,6]; shift left 2  = [3,4,5,6,6,6]
            evalsign = '1'      #digit 1 = "+"
            shiftedindex = index + shiftval
        if len(timex) > 0 and len(timeb)>0:
            if shiftedindex < 0:
                return -1, evalsign
            if shiftedindex >= len(timex):
                if len(timex)>2:
                    # we extend the time beyond the foreground
                    tx = timex[-1] + (1+shiftedindex-len(timex))*(timex[-1] - timex[-2])
                else:
                    tx = timex[-1]
            else:
                tx = timex[shiftedindex]
            if timeb[0] <= tx <= timeb[-1]:
                idx = self.timearray2index(timeb, tx)
                if -1 < idx < len(readings):
                    return readings[idx], evalsign
        return -1, evalsign

    # mathexpression = formula; t = a number to evaluate(usually time);
    # equeditnumber option = plotter edit window number; RTsname = option RealTime var name; RTsval = RealTime var val
    # The given mathexpression has to be a non-empty string!
    def eval_math_expression(self,mathexpression,t,equeditnumber=None, RTsname:Optional[str]=None,RTsval:Optional[float]=None,t_offset:float=0.):
        if len(mathexpression):
            mathdictionary = {}
            mathdictionary.update(self.mathdictionary_base) # extend by the standard math symbolic formulas

            if self.flagstart or not self.flagon:
                sample_timex = self.timex
                sample_temp1 = self.temp1
                sample_temp2 = self.temp2
                sample_delta1 = self.delta1
                sample_delta2 = self.delta2
                sample_extratimex = self.extratimex
                sample_extratemp1 = self.extratemp1
                sample_extratemp2 = self.extratemp2
            else:
                sample_timex = self.on_timex
                sample_temp1 = self.on_temp1
                sample_temp2 = self.on_temp2
                sample_delta1 = self.on_delta1
                sample_delta2 = self.on_delta2
                sample_extratimex = self.on_extratimex
                sample_extratemp1 = self.on_extratemp1
                sample_extratemp2 = self.on_extratemp2

            #if sampling
            if RTsname is not None and RTsname != '':
                index = len(sample_timex) - 1 if sample_timex else 0
                #load real time buffers acquired at sample() to the dictionary
                mathdictionary['Y1'] = self.RTtemp1 # ET
                mathdictionary['Y2'] = self.RTtemp2 # BT

                mathdictionary['R1'] = self.rateofchange1 # ET RoR
                mathdictionary['R2'] = self.rateofchange2 # BT RoR

                for d,_ in enumerate(self.RTextratemp1):
                    mathdictionary[f'Y{(d*2+3):.0f}'] = self.RTextratemp1[d]
                    mathdictionary[f'Y{(d*2+4):.0f}'] = self.RTextratemp2[d]
                if RTsname not in mathdictionary and RTsval is not None:
                    mathdictionary[RTsname] = RTsval

            # get index from the time.
            elif sample_timex:
                index = self.time2index(t)  # If using the plotter with loaded profile. Background index done below at "B"
            else:
                index = 0      #if plotting but nothing loaded.
            #if background
            if self.backgroundprofile is not None and 'B' in mathexpression:
                bindex = self.backgroundtime2index(t)         #use background time
            else:
                bindex = None

            replacements = {'+':'p','-':'m','*':'m','/':'d','(':'o',')':'c'} # characters to be replaced from symb variable for substitution

            #symbolic variables holding the index of main events from self.timeindex to be used to retrieve time and temp data from the corresponding t and Y variables
            #using the absolute access symbolic variables t{<i>} and Y{<i>} defined below
            #those variable are set to the error item -1 if no index is yet available

            main_events = ['CHARGE','DRY','FCs','FCe','SCs','SCe','DROP', 'COOL']
            for i,v in enumerate(main_events):
                if (i == 0 and self.timeindex[i] > -1) or (self.timeindex[i] > 0):
                    mathdictionary[v] = self.timeindex[i]
                else:
                    mathdictionary[v] = -1

            if self.background:
                background_main_events = ['bCHARGE','bDRY','bFCs','bFCe','bSCs','bSCe','bDROP', 'bCOOL']
                for i,v in enumerate(background_main_events):
                    if (i == 0 and self.timeindexB[i] > -1) or (self.timeindexB[i] > 0):
                        mathdictionary[v] = self.timeindexB[i]
                    else:
                        mathdictionary[v] = -1

            # time in seconds after those events. If an event was not issued yet this evaluates to 0
            delta_main_events = ['dCHARGE','dDRY','dFCs','dFCe','dSCs','dSCe','dDROP', 'dCOOL']
            try:
                for i,v in enumerate(delta_main_events):
                    if len(sample_timex)>0 and (i == 0 and self.timeindex[i] > -1) or (self.timeindex[i] > 0) and len(sample_timex)>self.timeindex[i]:
                        # we return the time after the event in seconds
                        mathdictionary[v] = sample_timex[-1] - sample_timex[self.timeindex[i]]
                    else:
                        # before the event we return 0
                        mathdictionary[v] = 0
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            try:
                mathdictionary['aTMP'] = self.ambientTemp
                mathdictionary['aHUM'] = self.ambient_humidity
                mathdictionary['aPRE'] = self.ambient_pressure
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            # prediction of the time to DRY and FCs before the event
            # this evaluates to None before TP and 0 after the event
            try:
                for v in ['pDRY','pFCs']:
                    if len(sample_delta2) > 0 and sample_delta2[-1] and sample_delta2[-1] > 0:
                        mathdictionary[v] = 0
                        if v == 'pDRY':
                            if self.backgroundprofile is not None and self.timeindexB[1] and not self.autoDRYflag: # with AutoDRY, we always use the set DRY phase temperature as target
                                drytarget = self.temp2B[self.timeindexB[1]] # Background DRY BT temperature
                            else:
                                drytarget = self.phases[1] # Drying max phases definition
                            if drytarget > sample_temp2[-1]:
                                mathdictionary[v] = (drytarget - sample_temp2[-1])/(sample_delta2[-1]/60.)
                        elif v == 'pFCs':
                            # display expected time to reach FCs as defined in the background profile or the phases dialog
                            if self.backgroundprofile is not None and self.timeindexB[2]:
                                fcstarget = self.temp2B[self.timeindexB[2]] # Background FCs BT temperature
                            else:
                                fcstarget = self.phases[2] # FCs min phases definition
                            if fcstarget > sample_temp2[-1]:
                                mathdictionary[v] = (fcstarget - sample_temp2[-1])/(sample_delta2[-1]/60.)
                    else:
                        # if a prediction is not possible (before TP), we return the error value -1
                        mathdictionary[v] = -1
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            # add AUC variables (AUCbase, AUCtarget, AUCvalue)
            try:
                mathdictionary['AUCvalue'] = self.AUCvalue
                if self.AUCbaseFlag:
                    if self.AUCbegin == 0 and self.timeindex[0] > -1: # start after CHARGE
                        idx = self.timeindex[0]
                    elif self.AUCbegin == 1 and self.TPalarmtimeindex: # start ater TP
                        idx = self.TPalarmtimeindex
                    elif self.AUCbegin == 2 and self.timeindex[1] > 0: # DRY END
                        idx = self.timeindex[1]
                    elif self.AUCbegin == 3 and self.timeindex[2] > 0: # FC START
                        idx = self.timeindex[2]
                    else:
                        idx = -1
                    if idx > -1: # we passed the AUCbegin event
                        mathdictionary['AUCbase'] = sample_temp2[idx]
                    else:
                        mathdictionary['AUCbase'] = None # Event not set yet, no AUCbase
                else:
                    mathdictionary['AUCbase'] = self.AUCbase
                if self.AUCtargetFlag and self.backgroundprofile is not None and self.AUCbackground > 0:
                    mathdictionary['AUCtarget'] = self.AUCbackground
                else:
                    mathdictionary['AUCtarget'] = self.AUCtarget
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            # add Roast Properties
            try:
                # weight-in in g
                mathdictionary['WEIGHTin'] = int(round(self.aw.convertWeight(self.weight[0],self.weight_units.index(self.weight[2]),0)))
                mathdictionary['MOISTUREin'] = self.moisture_greens
                mathdictionary['TEMPunit'] = (0 if self.mode == 'C' else 1) # 0:C and 1:F
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            #timeshift working vars
            timeshiftexpressions = []           #holds strings like "Y10040" as explained below
            timeshiftexpressionsvalues = []     #holds the evaluated values (float) for the above

            try:
                t = float(t)
                #extract Ys
                Yval = []                   #stores value number example Y9 = 9 => Yval = ['9']
                mlen = len(mathexpression)
                for i in range(mlen):
                    #Start symbolic assignment
                    #Y + one digit
                    if mathexpression[i] == 'Y' and i+1 < mlen and mathexpression[i+1].isdigit():
                        #find Y number for ET,BT,Extras (up to 9)
                        #check for out of range
                        seconddigitstr = ''
                        if i+2 < mlen and mathexpression[i+2].isdigit():
                            offset = 1
                            nint = int(f'{mathexpression[i+1]}{mathexpression[i+2]}')  # two digits Ynumber int
                        else:
                            offset = 0
                            nint = int(mathexpression[i+1])                      # one digit Ynumber int
                        #check for TIMESHIFT 0-9 (one digit). Example: "Y1[-2]"
                        if i+5+offset < mlen and mathexpression[i+2+offset] == '[':
                            Yshiftval = int(mathexpression[i+offset+4])
                            sign = mathexpression[i+offset+3]

                            #timeshift with two digits
                            if mathexpression[i+offset+5].isdigit():
                                seconddigitstr = mathexpression[i+offset+5]
                                mathexpression = f'{mathexpression[:i+offset+5]}{mathexpression[i+offset+6:]}'
                                Yshiftval = 10*Yshiftval + int(seconddigitstr)

                            if nint == 1: #ET
                                readings = sample_temp1
                            elif nint == 2: #BT
                                readings = sample_temp2
                            else: # nint > 2:
                                #map the extra device
                                edindex = (nint-1)//2 - 1
                                if nint%2:
                                    readings = sample_extratemp1[edindex]
                                else:
                                    readings = sample_extratemp2[edindex]
                            val, evalsign = self.shiftValueEvalsign(readings,index,sign,Yshiftval)

                            #add expression and values found
                            evaltimeexpression = f'Y{mathexpression[i+1:i+2+offset]}{evalsign*2}{mathexpression[i+offset+4]}{seconddigitstr}{evalsign}'
                            timeshiftexpressions.append(evaltimeexpression)
                            timeshiftexpressionsvalues.append(val)
                            #convert "Y2[+9]" to Ynumber compatible for python eval() to add to dictionary
                            #METHOD USED: replace all non digits chars with sign value.
                            #Example1 "Y2[-7]" = "Y20070"   Example2 "Y2[+9]" = "Y21191"
                            mathexpression = evaltimeexpression.join((mathexpression[:i],mathexpression[i+offset+6:]))
                        #direct index access: e.g. "Y2{CHARGE}" or "Y2{12}"
                        elif i+5+offset < len(mathexpression) and mathexpression[i+offset+2] == '{' and mathexpression.find('}',i+offset+3) > -1:
                            end_idx = mathexpression.index('}',i+offset+3)
                            body = mathexpression[i+3:end_idx]
                            val = -1
                            try:
                                absolute_index = eval(body,{'__builtins__':None},mathdictionary) # pylint: disable=eval-used
                                if absolute_index > -1:
                                    if nint == 1: #ET
                                        val = sample_temp1[absolute_index]
                                    elif nint == 2: #BT
                                        val = sample_temp2[absolute_index]
                                    elif nint > 2:
                                        #map the extra device
                                        edindex = (nint-1)//2 - 1
                                        if nint%2:
                                            val = sample_extratemp1[edindex][absolute_index]
                                        else:
                                            val = sample_extratemp2[edindex][absolute_index]
                            except Exception: # pylint: disable=broad-except
                                pass
                            #add expression and values found
                            literal_body = body
                            for kk, v in replacements.items():
                                literal_body = literal_body.replace(kk,v)
                            evaltimeexpression = f'Y{mathexpression[i+1]}u{literal_body}u' # curle brackets replaced by "u"
                            timeshiftexpressions.append(evaltimeexpression)
                            timeshiftexpressionsvalues.append(val)
                            mathexpression = evaltimeexpression.join((mathexpression[:i],mathexpression[end_idx+1:]))
                        # Y + TWO digits. Y10-Y99 . 4+ extra devices. No timeshift
                        elif i+2 < mlen and mathexpression[i+2].isdigit():
                            Yval.append(f'{mathexpression[i+1]}{mathexpression[i+2]}')
                        # No timeshift Y1,Y2,Y3,etc.
                        else:
                            Yval.append(mathexpression[i+1])

                    #the actual value
                    elif mathexpression[i] == 'x':
                        if 'x' not in mathdictionary:
                            if RTsval is not None:                   # zero could be a valid value
                                mathdictionary['x'] = RTsval         # add x to the math dictionary
                            else:
                                mathdictionary['x'] = -1

                    #the factor to plot C/min delta_ax values on the standard temperature axis
                    elif mathexpression[i] == 'k':
                        if 'k' not in mathdictionary:
                            try:
                                mathdictionary['k'] = (self.ylimit - self.ylimit_min) / float(self.zlimit - self.zlimit_min)
                            except Exception: # pylint: disable=broad-except
                                mathdictionary['k'] = 1

                    #the offset to plot C/min delta_ax values on the standard temperature axis
                    elif mathexpression[i] == 'o':
                        if 'o' not in mathdictionary:
                            try:
                                mathdictionary['o'] = self.ylimit_min - (self.zlimit_min * (self.ylimit - self.ylimit_min) / float(self.zlimit - self.zlimit_min))
                            except Exception: # pylint: disable=broad-except
                                mathdictionary['o'] = 0

                    elif mathexpression[i] == 'R':
                        try:
                            if i+1 < mlen:
                                k:int
                                if mathexpression[i+1] == 'B': # RBnn : RoR of Background Profile
                                    k = 1
                                    c = 'RB'
                                else:
                                    k = 0
                                    c = 'R'
                                delta_readings: List[Optional[float]]
                                seconddigitstr = ''
                                if mathexpression[i+k+1].isdigit():
                                    nint = int(mathexpression[i+k+1])              #Rnumber int
                                    #check for TIMESHIFT 0-9 (one digit). Example: "R1[-2]" or RB1[-2]
                                    if i+k+5 < len(mathexpression) and mathexpression[i+k+2] == '[':
                                        Yshiftval = int(mathexpression[i+k+4])
                                        sign = mathexpression[i+k+3]

                                        # TWO digits shifting
                                        if mathexpression[i+k+5].isdigit():
                                            seconddigit = int(mathexpression[i+k+5])
                                            seconddigitstr = mathexpression[i+k+5]
                                            mathexpression = f'{mathexpression[:i+k+5]}{mathexpression[i+k+6:]}'
                                            Yshiftval = 10*Yshiftval + seconddigit
                                        if nint == 1: #DeltaET
                                            if k == 0:
                                                delta_readings = sample_delta1
                                            else:
                                                delta_readings = self.delta1B
                                        #nint == 2: #DeltaBT
                                        elif k == 0:
                                            delta_readings = sample_delta2
                                        else:
                                            delta_readings = self.delta2B
                                        if k == 0:
                                            val, evalsign = self.shiftValueEvalsign(delta_readings,index,sign,Yshiftval)
                                        else:
                                            #if sampling
                                            if RTsname is not None and RTsname != '':
                                                idx = index + 1
                                            else:
                                                idx = index
                                            val, evalsign = self.shiftValueEvalsignBackground(sample_timex, self.timeB,delta_readings,idx,sign,Yshiftval)

                                        #add expression and values found
                                        evaltimeexpression = ''.join((c,mathexpression[i+k+1],evalsign*2,mathexpression[i+k+4],seconddigitstr,evalsign))
                                        timeshiftexpressions.append(evaltimeexpression)
                                        timeshiftexpressionsvalues.append(val)
                                        #convert "R2[+9]" to Rnumber compatible for python eval() to add to dictionary
                                        #METHOD USED: replace all non digits chars with numbers value.
                                        #Example1 "R2[-7]" = "R20070"   Example2 "R2[+9]" = "R21191" Example3 "RB2[-1]" = "RB23313
                                        mathexpression = evaltimeexpression.join((mathexpression[:i],mathexpression[i+k+6:]))

                                    #direct index access: e.g. "R2{CHARGE}" or "R2{12}"
                                    elif i+k+5 < len(mathexpression) and mathexpression[i+k+2] == '{' and mathexpression.find('}',i+k+3) > -1:
                                        end_idx = mathexpression.index('}',i+k+3)
                                        body = mathexpression[i+k+3:end_idx]
                                        val = -1
                                        try:
                                            absolute_index = eval(body,{'__builtins__':None},mathdictionary)  # pylint: disable=eval-used
                                            if absolute_index > -1:
                                                if nint == 1: #DeltaET
                                                    if k == 0:
                                                        val = sample_delta1[absolute_index]
                                                    else:
                                                        val = self.delta1B[absolute_index]
                                                # nint == 2: #DeltaBT
                                                elif k == 0:
                                                    val = sample_delta2[absolute_index]
                                                else:
                                                    val = self.delta2B[absolute_index]
                                        except Exception: # pylint: disable=broad-except
                                            pass
                                        #add expression and values found
                                        literal_body = body
                                        for j, v in replacements.items():
                                            literal_body = literal_body.replace(j,v)
                                        evaltimeexpression = ''.join((c,mathexpression[i+1],'z',literal_body,'z')) # curle brackets replaced by "z"
                                        timeshiftexpressions.append(evaltimeexpression)
                                        timeshiftexpressionsvalues.append(val)
                                        mathexpression = evaltimeexpression.join((mathexpression[:i],mathexpression[end_idx+1:]))

                                    #no shift
                                    elif mathexpression[i+k+1] == '1':
                                        if k == 0:
                                            mathdictionary['R1'] = sample_delta1[index]
                                        else:
                                            #if sampling
                                            if RTsname is not None and RTsname != '':
                                                idx = index + 1
                                            else:
                                                idx = index
                                            # the index is resolved relative to the time of the foreground profile if available
                                            if not sample_timex:
                                                mathdictionary['RB1'] = self.delta1B[idx]
                                            else:
                                                if RTsname is not None and RTsname != '':
                                                    if len(sample_timex)>2:
                                                        sample_interval = sample_timex[-1] - sample_timex[-2]
                                                        tx = sample_timex[index] + sample_interval
                                                    else:
                                                        tx = sample_timex[index]
                                                else:
                                                    tx = sample_timex[index]
                                                idx = self.timearray2index(self.timeB, tx)
                                                if -1 < idx < len(self.delta1B):
                                                    res = self.delta1B[idx]
                                                else:
                                                    res = -1
                                                mathdictionary['RB1'] = res
                                    elif mathexpression[i+k+1] == '2':
                                        if k == 0:
                                            mathdictionary['R2'] = sample_delta2[index]
                                        else:
                                            if RTsname is not None and RTsname != '':
                                                idx = index + 1
                                            else:
                                                idx = index
                                            # the index is resolved relative to the time of the foreground profile if available
                                            if not sample_timex:
                                                mathdictionary['RB2'] = self.delta2B[idx]
                                            else:
                                                if RTsname is not None and RTsname != '':
                                                    if len(sample_timex)>2:
                                                        sample_interval = sample_timex[-1] - sample_timex[-2]
                                                        tx = sample_timex[index] + sample_interval
                                                    else:
                                                        tx = sample_timex[index]
                                                else:
                                                    tx = sample_timex[index]
                                                idx = self.timearray2index(self.timeB, tx)
                                                if -1 < idx < len(self.delta2B):
                                                    res = self.delta2B[idx]
                                                else:
                                                    res = -1
                                                mathdictionary['RB2'] = res
                        except Exception: # pylint: disable=broad-except
                            # if deltas of backgrounds are not visible the data is not calculated and thus this fails with an exception
                            pass

                    #Add to dict Event1-4 external value
                    elif mathexpression[i] == 'E' and i+1 < mlen and mathexpression[i+1].isdigit():                          #check for out of range
                        nint = int(mathexpression[i+1])-1              #Enumber int
                        #find right most occurrence before index of given event type
                        if nint in self.specialeventstype and nint < 4:
                            spevtylen = len(self.specialeventstype)-1
                            iii = None
                            for iii in range(spevtylen,-1,-1):
                                if self.specialeventstype[iii] == nint and index >= self.specialevents[iii]:
                                    break  #index found
                            if iii is None:
                                val = 0 # type: ignore # mypy: Statement is unreachable  [unreachable]
                            else:
                                val = self.eventsInternal2ExternalValue(self.specialeventsvalue[iii])
                        else:
                            val = 0
                        e_string = f'E{mathexpression[i+1]}'
                        if e_string not in mathdictionary:
                            mathdictionary[e_string] = val

                    # time timeshift of absolute time (not relative to CHARGE)
                    # t : to access the foreground profiles time (sample_timex)
                    # b : to access the background profiles time (self.timeB)
                    elif mathexpression[i] in ['t','b']:
                        if mathexpression[i] == 't':
                            timex = sample_timex
                        else:
                            timex = self.timeB
                        seconddigitstr = ''
                        if i+4 < len(mathexpression) and mathexpression[i+1] == '[':
                            Yshiftval = int(mathexpression[i+3])
                            sign = mathexpression[i+2]

                            if mathexpression[i+4].isdigit():
                                seconddigit = int(mathexpression[i+4])
                                seconddigitstr = mathexpression[i+4]
                                mathexpression = f'{mathexpression[:i+4]}{mathexpression[i+5:]}'
                                Yshiftval = 10*Yshiftval + seconddigit

                            val, evalsign = self.shiftValueEvalsign(timex,index,sign,Yshiftval)

                            val = val - t_offset
                            evaltimeexpression = ''.join((mathexpression[i],evalsign*2,mathexpression[i+3],seconddigitstr,evalsign))
                            timeshiftexpressions.append(evaltimeexpression)
                            timeshiftexpressionsvalues.append(val)
                            mathexpression = evaltimeexpression.join((mathexpression[:i],mathexpression[i+5:]))
                        #direct index access: e.g. "t{CHARGE}" or "t{12}"
                        elif i+3 < len(mathexpression) and mathexpression[i+1] == '{' and mathexpression.find('}',i+2) > -1:
                            end_idx = mathexpression.index('}',i+2)
                            body = mathexpression[i+2:end_idx]
                            val = -1
                            try:
                                absolute_index = eval(body,{'__builtins__':None},mathdictionary)  # pylint: disable=eval-used
                                if absolute_index > -1:
                                    val = timex[absolute_index]
                            except Exception: # pylint: disable=broad-except
                                pass
                            literal_body = body
                            for kv, v in replacements.items():
                                literal_body = literal_body.replace(kv,v)
                            evaltimeexpression = ''.join((mathexpression[i],'q',literal_body,'q')) # curle brackets replaced by "q"
                            timeshiftexpressions.append(evaltimeexpression)
                            timeshiftexpressionsvalues.append(val)
                            mathexpression = evaltimeexpression.join((mathexpression[:i],mathexpression[end_idx+1:]))
                        #no timeshift
                        elif mathexpression[i] == 't' and 't' not in mathdictionary:
                            mathdictionary['t'] = t - t_offset         #add t to the math dictionary
                        # b is only valid with index

                    #Add to dict plotter Previous results (cascading) from plotter field windows (1-9)
                    elif mathexpression[i] == 'P' and i+1 < mlen and mathexpression[i+1].isdigit():                          #check for out of range
                        nint = int(mathexpression[i+1])              #Ynumber int
                        #check for TIMESHIFT 0-9 (one digit). Example: "Y1[-2]"
                        if i+5 < len(mathexpression) and mathexpression[i+2] == '[' and mathexpression[i+5] == ']':
                            Yshiftval = int(mathexpression[i+4])
                            sign = mathexpression[i+3]
                            evaltimeexpression = ''.join(('P',mathexpression[i+1],'1'*2,mathexpression[i+4],'1'))
                            timeshiftexpressions.append(evaltimeexpression)
                            timeshiftexpressionsvalues.append(-1000)
                            mathexpression = evaltimeexpression.join((mathexpression[:i],mathexpression[i+6:]))
                        #no shift
                        else:
                            if index < len(self.plotterequationresults[nint-1]):
                                val = self.plotterequationresults[nint-1][index]
                            else:
                                val = -1000
                            p_string = f'P{mathexpression[i+1]}'
                            if p_string not in mathdictionary:
                                mathdictionary[p_string] = val

                    #Background B1 = ETbackground; B2 = BTbackground
                    elif mathexpression[i] == 'B':
                        if i+1 < mlen:
                            seconddigitstr = ''
                            if mathexpression[i+1].isdigit():
                                nint = int(mathexpression[i+1])              #Bnumber int
                                #check for TIMESHIFT 0-9 (one digit). Example: "B1[-2]"
                                if i+5 < len(mathexpression) and mathexpression[i+2] == '[':
                                    Yshiftval = int(mathexpression[i+4])
                                    sign = mathexpression[i+3]

                                    # TWO digits shifting
                                    if mathexpression[i+5].isdigit():
                                        seconddigit = int(mathexpression[i+5])
                                        seconddigitstr = mathexpression[i+5]
                                        mathexpression = f'{mathexpression[:i+5]}{mathexpression[i+6:]}'
                                        Yshiftval = 10*Yshiftval + seconddigit

                                    if not self.timeB:
                                        # no background, set to 0
                                        val = 0
                                        evalsign = '0'
                                    else:
                                        readings = None
                                        readings_time = None
                                        if nint == 1: #ETbackground
                                            readings = self.temp1B
                                            readings_time = self.timeB
                                        elif nint == 2: #BTbackground
                                            readings = self.temp2B
                                            readings_time = self.timeB
                                        #B3, B4, B5, ...
                                        elif nint > 2:
                                            idx3 = self.xtcurveidx - 1
                                            n3 = idx3//2
                                            if self.xtcurveidx%2:
                                                readings = list(self.temp1BX[n3])
                                            else:
                                                readings = list(self.temp2BX[n3])
                                            readings_time = self.extratimexB[n3]
#                                        # variant operating directly on the background curve via the given index
#                                        val, evalsign = self.shiftValueEvalsign(readings,index,sign,Yshiftval)
                                        # variant operating on the background curve with the given index interpreted as time relative to the foreground curve:
                                        if RTsname is not None and RTsname != '':
                                            idx = index + 1
                                        else:
                                            idx = index
                                        if readings is None or readings_time is None:
                                            val = 0
                                            evalsign = 0
                                        else:
                                            val, evalsign = self.shiftValueEvalsignBackground(sample_timex, readings_time, readings, idx, sign, Yshiftval)
                                    evaltimeexpression = ''.join(('B',mathexpression[i+1],evalsign*2,mathexpression[i+4],seconddigitstr,evalsign))
                                    timeshiftexpressions.append(evaltimeexpression)
                                    timeshiftexpressionsvalues.append(val)
                                    mathexpression = evaltimeexpression.join((mathexpression[:i],mathexpression[i+6:]))
                                #direct index access: e.g. "B2{CHARGE}" or "B2{12}"
                                elif i+5 < len(mathexpression) and mathexpression[i+2] == '{' and mathexpression.find('}',i+3) > -1:
                                    end_idx = mathexpression.index('}',i+3)
                                    body = mathexpression[i+3:end_idx]
                                    val = -1
                                    try:
                                        absolute_index = eval(body,{'__builtins__':None},mathdictionary)  # pylint: disable=eval-used
                                        if absolute_index > -1:
                                            if nint == 1: #ET
                                                val = self.temp1B[absolute_index]
                                            elif nint == 2: #BT
                                                val = self.temp2B[absolute_index]
                                            else:
                                                idx3 = self.xtcurveidx - 1
                                                n3 = idx3//2
                                                #map the extra device
                                                b = [0,0,1,1,2,2,3]
                                                edindex = b[nint-3]
                                                if self.xtcurveidx%2:
                                                    val = self.temp1BX[n3][absolute_index]
                                                else:
                                                    val = self.temp2BX[n3][absolute_index]
                                    except Exception: # pylint: disable=broad-except
                                        pass
                                    #add expression and values found
                                    literal_body = body
                                    for vk, v in replacements.items():
                                        literal_body = literal_body.replace(vk,v)
                                    evaltimeexpression = ''.join(('B',mathexpression[i+1],'z',literal_body,'z')) # curle brackets replaced by "z"
                                    timeshiftexpressions.append(evaltimeexpression)
                                    timeshiftexpressionsvalues.append(val)
                                    mathexpression = evaltimeexpression.join((mathexpression[:i],mathexpression[end_idx+1:]))
                                #no shift
                                elif not self.timeB:
                                    # no background, set to 0
                                    mathdictionary[f'B{mathexpression[i+1]}'] = 0
                                else:
                                    if nint == 1:
                                        readings = self.temp1B
                                    elif nint == 2:
                                        readings = self.temp2B
                                    else:
                                        idx3 = self.xtcurveidx - 1
                                        n3 = idx3//2
                                        if self.xtcurveidx%2:
                                            readings = list(self.temp1BX[n3])
                                        else:
                                            readings = list(self.temp2BX[n3])
                                    if sample_timex:
                                        if RTsname is not None and RTsname != '':
                                            if len(sample_timex)>2:
                                                sample_interval = sample_timex[-1] - sample_timex[-2]
                                                tx = sample_timex[index] + sample_interval
                                            else:
                                                tx = sample_timex[index]
                                        else:
                                            tx = sample_timex[index]
                                        # the index is resolved relative to the time of the foreground profile if available
                                        idx = self.timearray2index(self.timeB, tx)
                                        if -1 < idx < len(readings):
                                            val = readings[idx]
                                        else:
                                            val = -1
                                    elif bindex is not None:
                                        val = readings[bindex]
                                    else:
                                        val = -1

                                    mathdictionary[f'B{mathexpression[i+1]}'] = val

                    # Feedback from previous result. Stack = [10,9,8,7,6,5,4,3,2,1]
                    # holds the ten previous formula results (same window) in order.
                    # F1 is the last result. F5 is the past 5th result
                    elif mathexpression[i] == 'F' and i+1 < mlen and mathexpression[i+1].isdigit():
                        nint = int(mathexpression[i+1])
                        val = self.plotterstack[-1*nint]
                        f_string = f'F{mathexpression[i+1]}'
                        if f_string not in mathdictionary:
                            mathdictionary[f_string] = val

                    # add channel tare values (T1 => ET, T2 => BT, T3 => E1c1, T4 => E1c2, T5 => E2c1,
                    # set by clicking on the corresponding LCD
                    elif mathexpression[i] == 'T' and i+1 < mlen:                          #check for out of range
                        nint = -1 #Enumber int
                        if i+2 < mlen and mathexpression[i+2].isdigit():
                            nint = int(f'{mathexpression[i+1]}{mathexpression[i+2]}')-1
                            mexpr = f'T{mathexpression[i+1]}{mathexpression[i+2]}'
                        elif mathexpression[i+1].isdigit():
                            nint = int(mathexpression[i+1])-1
                            mexpr = f'T{mathexpression[i+1]}'
                        else:
                            mexpr = None
                        if nint != -1 and mexpr is not None:
                            if len(self.aw.channel_tare_values) > nint:
                                mathdictionary[mexpr] = self.aw.channel_tare_values[nint]
                            else:
                                mathdictionary[mexpr] = 0.0

                    #############   end of mathexpression loop ##########################

                #created Ys values
                try:
                    if len(sample_timex)>0:
                        if RTsname:
                            Y = [sample_temp1[-1], sample_temp2[-1]] # in realtime mode we take the last value
                        else:
                            Y = [sample_temp1[index], sample_temp2[index]]
                        if sample_extratimex:
                            for i in range(len(self.extradevices)):
                                if len(sample_extratimex[i]):
                                    if RTsname:
                                        Y.append(sample_extratemp1[i][-1])
                                        Y.append(sample_extratemp2[i][-1])
                                    else:
                                        Y.append(sample_extratemp1[i][index])
                                        Y.append(sample_extratemp2[i][index])

                        #add Ys and their value to math dictionary
                        for yv in Yval:
                            y_string = f'Y{yv}'
                            if y_string not in mathdictionary:
                                idx = int(yv)-1
                                if len(Y) > idx > -1:
                                    mathdictionary[y_string] = Y[idx]

                        #add other timeshifted expressions to the math dictionary: shifted t and P
                        for i,tsexpr in enumerate(timeshiftexpressions):
                            if tsexpr not in mathdictionary:
                                mathdictionary[tsexpr] = timeshiftexpressionsvalues[i]
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)

                reslt:float = -1
                #background symbols just in case there was no profile loaded but a background loaded.
                if len(self.timeB) > 0:
                    for i,tsexpr in enumerate(timeshiftexpressions):
                        if tsexpr not in mathdictionary:
                            mathdictionary[tsexpr] = timeshiftexpressionsvalues[i]
                try:
                    # we exclude the main_events as they occur as substrings in others like CHARGE in dCHARGE
                    # the special case of a variable Y1 overlapping with a variable Y11,..,Y12 in this simple test has to be excluded to avoid
                    # that if mathexpression="Y11" and mathdictionary contains {"Y1":-1} -1 is returned instead of the correct value of Y11
                    # "x" occurs in "max" and has also to be excluded, as "t" and "b"
                    me = mathexpression.strip()
                    propagate_error:bool = True # if any variable occurring in me is bound to -1 the whole me evals to -1
                    try:
                        if me[0] == '(' and me[-1] == ')':
                            # only if the whole expression is in brackets, errors bound to variables are not propagated
                            propagate_error = False
                    except Exception: # pylint: disable=broad-except
                        pass
                    if propagate_error and any((((k in me) if k not in (['Y1','x','t','b'] if ('max' in me) else ['Y1','t','b']) else False) for k,v in mathdictionary.items() if (v == -1 and (k not in main_events)))):
                        # if any variable is bound to the error value -1 we return -1 for the full formula
                        reslt = -1
                    else:
                        reslt = float(eval(me,{'__builtins__':None},mathdictionary)) # pylint: disable=eval-used
                except TypeError:
                    reslt = -1
                except ValueError:
                    reslt = -1
                except ZeroDivisionError:
                    reslt = -1
                except IndexError:
                    reslt = -1
                #stack (use in feedback "F" in same formula)
                self.plotterstack.insert(10,reslt)
                self.plotterstack.pop(0)
                #Pnumber results storage
                if equeditnumber:
                    self.plotterequationresults[equeditnumber-1].append(reslt)
                return reslt

            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
                #if plotter
                if equeditnumber:
                    self.plottermessage = f'P{equeditnumber}: {e}'
                    return -1
                #if sample()
                #virtual devices with symbolic may need 2 samples min.
                if len(sample_timex) > 2:
                    _, _, exc_tb = sys.exc_info()
                    mathexpression = mathexpression.replace('{','(').replace('}',')') # avoid {x} leading to key arrows
                    self.adderror(f"{QApplication.translate('Error Message', 'Exception:')} eval_curve_expression(): {mathexpression} {e}",getattr(exc_tb, 'tb_lineno', '?'))
                return -1
        return -1


    #format X axis labels
    def xaxistosm(self,redraw=True,min_time=None,max_time=None):
        if self.ax is None:
            return
        try:
            startofx:float
            endofx:float
            starttime:float
            endtime:float

            startofx = self.startofx if min_time is None else min_time
            endofx = self.endofx if max_time is None else max_time

            if bool(self.aw.comparator):
                starttime = 0
            elif self.timeindex[0] != -1 and self.timeindex[0] < len(self.timex):
                starttime = self.timex[self.timeindex[0]]
            else:
                starttime = 0

            endtime = endofx + starttime

            self.ax.set_xlim(startofx,endtime)

            if self.xgrid != 0:

                mfactor1 =  round(float(2. + abs(int(round(startofx-starttime))/int(round(self.xgrid)))))
                mfactor2 =  round(float(2. + abs(int(round(endofx))/int(round(self.xgrid)))))

                majorloc = numpy.arange(starttime-(self.xgrid*mfactor1),starttime+(self.xgrid*mfactor2), self.xgrid)
                if self.xgrid == 60:
                    minorloc = numpy.arange(starttime-(self.xgrid*mfactor1),starttime+(self.xgrid*mfactor2), 30)
                else:
                    minorloc = numpy.arange(starttime-(self.xgrid*mfactor1),starttime+(self.xgrid*mfactor2), 60)

                majorlocator = ticker.FixedLocator(majorloc)
                minorlocator = ticker.FixedLocator(minorloc)

                self.ax.xaxis.set_major_locator(majorlocator)
                self.ax.xaxis.set_minor_locator(minorlocator)

                formatter = ticker.FuncFormatter(self.formtime)
                self.ax.xaxis.set_major_formatter(formatter)


                #adjust the length of the minor ticks
                for i in self.ax.xaxis.get_minorticklines() + self.ax.yaxis.get_minorticklines():
                    i.set_markersize(4)

                #adjust the length of the major ticks
                for i in self.ax.get_xticklines() + self.ax.get_yticklines():
                    i.set_markersize(6)
                    #i.set_markeredgewidth(2)   #adjust the width

#                # check x labels rotation
#                if self.xrotation != 0:
#                    for label in self.ax.xaxis.get_ticklabels():
#                        label.set_rotation(self.xrotation)

            if not self.LCDdecimalplaces:
                if self.ax:
                    self.ax.minorticks_off()
                if self.delta_ax is not None:
                    self.delta_ax.minorticks_off()

            # we have to update the canvas cache
            if redraw:
                self.updateBackground()
            else:
                self.ax_background = None
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    def fmt_timedata(self,x):
        starttime:float

        if bool(self.aw.comparator):
            starttime = 0
        elif self.timeindex[0] != -1 and self.timeindex[0] < len(self.timex):
            starttime = self.timex[self.timeindex[0]]
        else:
            starttime = 0
        sign = '' if x >= starttime else '-'
        m,s = divmod(abs(x - starttime), 60)
#        return '%s%d:%02d'%(sign,m,s)
        return f'{sign}{m:.0f}:{s:02.0f}'

    def fmt_data(self,x):
        res = x
        if self.fmt_data_ON and self.delta_ax is not None and self.ax is not None and self.fmt_data_RoR and self.twoAxisMode():
            try:
                # depending on the z-order of ax vs delta_ax the one or the other one is correct
                #res = (self.ax.transData.inverted().transform((0,self.delta_ax.transData.transform((0,x))[1]))[1])
                res = (self.delta_ax.transData.inverted().transform((0,self.ax.transData.transform((0,x))[1]))[1])
            except Exception: # pylint: disable=broad-except
                pass
        if self.LCDdecimalplaces:
            return self.aw.float2float(res)
        return int(round(res))

    #used by xaxistosm(). Provides also negative time
    def formtime(self,x,_):
        starttime:float
        if bool(self.aw.comparator):
            starttime = 0
        elif self.timeindex[0] != -1 and self.timeindex[0] < len(self.timex):
            starttime = self.timex[self.timeindex[0]]
        else:
            starttime = 0

        if x >=  starttime:
            m,s = divmod((x - round(starttime)), 60)  #**NOTE**: divmod() returns here type numpy.float64, which could create problems
            #print type(m),type(s)                    #it is used in: formatter = ticker.FuncFormatter(self.formtime) in xaxistosm()
            s = int(round(s))
            m = int(m)

            if s >= 59:
                return f'{m+1:.0f}'
            if abs(s - 30) < 1:
                return f'{m:d.5}'
            if s > 1:
                return  f'{m:.0f}:{s:02.0f}'
            return f'{m:.0f}'

        m,s = divmod(abs(x - round(starttime)), 60)
        s = int(round(s))
        m = int(m)

        if s >= 59:
            return f'-{m+1:.0f}'
        if abs(s-30) < 1:
            return f'-{m:d.5}'
        if s > 1:
            return  '-{m:.0f}:{s:02.0f}'
        if m == 0:
            return '0'
        return f'-{m:.0f}'

    # returns True if nothing to save, discard or save was selected and False if canceled by the user
    def checkSaved(self,allow_discard:bool = True) -> bool:
        #prevents deleting accidentally a finished roast
        if self.safesaveflag and len(self.timex) > 3:
            if allow_discard:
                string = QApplication.translate('Message','Save the profile, Discard the profile (Reset), or Cancel?')
                buttons = QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Cancel
            else:
                string = QApplication.translate('Message','Save the profile or Cancel?')
                buttons = QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Cancel
            reply = QMessageBox.warning(self.aw, QApplication.translate('Message','Profile unsaved'), string,
                                buttons)
            if reply == QMessageBox.StandardButton.Save:
                return self.aw.fileSave(self.aw.curFile)  #if accepted, calls fileClean() and thus turns safesaveflag = False
            if reply == QMessageBox.StandardButton.Discard:
                self.fileCleanSignal.emit()
                return True
            if reply == QMessageBox.StandardButton.Cancel:
                self.aw.sendmessage(QApplication.translate('Message','Action canceled'))
            return False
        # nothing to be saved
        return True

    def clearLCDs(self):
        zz = '-.-' if self.LCDdecimalplaces else '--'
        self.aw.lcd2.display(zz)
        self.aw.lcd3.display(zz)
        self.aw.lcd4.display(zz)
        self.aw.lcd5.display(zz)
        self.aw.lcd6.display(zz)
        self.aw.lcd7.display(zz)
        for i in range(self.aw.nLCDS):
            zz0 = '--' if self.intChannel(i, 0) else zz
            self.aw.extraLCD1[i].display(zz0)
            zz1 = '--' if self.intChannel(i, 1) else zz
            self.aw.extraLCD2[i].display(zz1)
        if self.aw.largeLCDs_dialog is not None:
            self.aw.largeLCDs_dialog.updateDecimals()
        if self.aw.largeDeltaLCDs_dialog is not None:
            self.aw.largeDeltaLCDs_dialog.updateDecimals()
        if self.aw.largePIDLCDs_dialog is not None:
            self.aw.largePIDLCDs_dialog.updateDecimals()
        if self.aw.largeExtraLCDs_dialog is not None:
            self.aw.largeExtraLCDs_dialog.updateDecimals()
        if self.aw.largePhasesLCDs_dialog is not None:
            self.aw.largePhasesLCDs_dialog.updateDecimals()

    def clearMeasurements(self,andLCDs=True):
        try:
            #### lock shared resources #####
            self.profileDataSemaphore.acquire(1)
            self.fileCleanSignal.emit()
            self.rateofchange1 = 0.0
            self.rateofchange2 = 0.0
            charge:float= 0
            if self.timeindex[0] > -1:
                charge = self.timex[self.timeindex[0]]
            self.temp1, self.temp2, self.delta1, self.delta2, self.timex, self.stemp1, self.stemp2, self.ctimex1, self.ctimex2, self.ctemp1, self.ctemp2 = [],[],[],[],[],[],[],[],[],[],[]
            self.tstemp1,self.tstemp2 = [],[]
            self.unfiltereddelta1,self.unfiltereddelta2 = [],[]
            self.unfiltereddelta1_pure,self.unfiltereddelta2_pure = [],[]
            self.timeindex = [-1,0,0,0,0,0,0,0]
            # we set startofx to x-axis min limit as timeindex[0] is no cleared, to keep the axis limits constant (note that startx depends on timeindex[0]!)
            self.startofx = self.startofx - charge
            #extra devices
            for i in range(min(len(self.extradevices),len(self.extratimex),len(self.extratemp1),len(self.extratemp2),len(self.extrastemp1),len(self.extrastemp2))):
                self.extratimex[i],self.extratemp1[i],self.extratemp2[i],self.extrastemp1[i],self.extrastemp2[i] = [],[],[],[],[]            #reset all variables that need to be reset (but for the actually measurements that will be treated separately at the end of this function)
                self.extractimex1[i],self.extractimex2[i],self.extractemp1[i],self.extractemp2[i] = [],[],[],[]
            self.replayedBackgroundEvents=[]
            self.beepedBackgroundEvents=[]
            self.specialevents=[]
            self.aw.lcd1.display('00:00')
            if self.aw.WebLCDs:
                self.updateWebLCDs(time='00:00')
            if self.aw.largeLCDs_dialog:
                self.updateLargeLCDsTimeSignal.emit('00:00')
            if andLCDs:
                self.clearLCDs()

        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' clearMeasurements() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
        finally:
            if self.profileDataSemaphore.available() < 1:
                self.profileDataSemaphore.release(1)

    @pyqtSlot(bool)
    def resetButtonAction(self,_=False):
        self.disconnectProbes() # release serial/S7/MODBUS connections
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.AltModifier:  #alt click
            # detach IO Phidgets
            try:
                self.closePhidgetOUTPUTs()
            except Exception as e:  # pylint: disable=broad-except
                _log.exception(e)
            try:
                self.closePhidgetAMBIENTs()
            except Exception as e:  # pylint: disable=broad-except
                _log.exception(e)
        self.reset()

    #Resets graph. Called from reset button. Deletes all data. Calls redraw() at the end
    # returns False if action was canceled, True otherwise
    # if keepProperties=True (a call from OnMonitor()), we keep all the pre-set roast properties
    def reset(self,redraw=True,soundOn=True,sampling=False,keepProperties=False,fireResetAction=True) -> bool:
        try:
            focused_widget = QApplication.focusWidget()
            if focused_widget and focused_widget != self.aw.centralWidget():
                focused_widget.clearFocus()
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

        if not self.checkSaved():
            return False

        # restore and clear extra device settings which might have been created on loading a profile with different extra devices settings configuration
        self.aw.restoreExtraDeviceSettingsBackup()

        if sampling and self.flagOpenCompleted and self.aw.curFile is not None:
            # always if ON is pressed while a profile is loaded, the profile is send to the Viewer
            # the file URL of the saved profile (if any) is send to the ArtisanViewer app to be opened if already running
            try:
                fileURL = QUrl.fromLocalFile(self.aw.curFile)
                fileURL.setQuery('background') # open the file URL without raising the app to the foreground
                QTimer.singleShot(10,lambda : self.aw.app.sendMessage2ArtisanInstance(fileURL.toString(),self.aw.app._viewer_id)) # pylint: disable=protected-access
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

        if soundOn:
            self.aw.soundpopSignal.emit()

        if fireResetAction:
            try:
                # the RESET button action needs to be fired outside of the semaphore to avoid lockups
                self.aw.eventactionx(self.xextrabuttonactions[0],self.xextrabuttonactionstrings[0])
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
        try:
            #### lock shared resources #####
            self.profileDataSemaphore.acquire(1)
            #reset time
            self.resetTimer()

            self.roastUUID = None # reset UUID
            self.roastbatchnr = 0 # initialized to 0, set to increased batchcounter on DROP
            self.roastbatchpos = 1 # initialized to 1, set to increased batchsequence on DROP
            self.roastbatchprefix = self.batchprefix

            self.aw.sendmessage(QApplication.translate('Message','Scope has been reset'))
            self.aw.AUClcd.setNumDigits(3)
            self.aw.buttonFCs.setDisabled(False)
            self.aw.buttonFCe.setDisabled(False)
            self.aw.buttonSCs.setDisabled(False)
            self.aw.buttonSCe.setDisabled(False)
            self.aw.buttonRESET.setDisabled(False)
            self.aw.buttonCHARGE.setDisabled(False)
            self.aw.buttonDROP.setDisabled(False)
            self.aw.buttonDRY.setDisabled(False)
            self.aw.buttonCOOL.setDisabled(False)
            self.aw.buttonFCs.setFlat(False)
            self.aw.buttonFCe.setFlat(False)
            self.aw.buttonSCs.setFlat(False)
            self.aw.buttonSCe.setFlat(False)
            self.aw.buttonRESET.setFlat(False)
            self.aw.buttonCHARGE.setFlat(False)
            self.aw.buttonCHARGE.stopAnimation()
            self.aw.buttonDROP.setFlat(False)
            self.aw.buttonDRY.setFlat(False)
            self.aw.buttonCOOL.setFlat(False)
            self.aw.buttonONOFF.setText(QApplication.translate('Button', 'ON'))
            if self.aw.simulator:
                self.aw.buttonONOFF.setStyleSheet(self.aw.pushbuttonstyles_simulator['OFF'])
            else:
                self.aw.buttonONOFF.setStyleSheet(self.aw.pushbuttonstyles['OFF'])
            self.aw.buttonSTARTSTOP.setText(QApplication.translate('Button', 'START'))
            if self.aw.simulator:
                self.aw.buttonSTARTSTOP.setStyleSheet(self.aw.pushbuttonstyles_simulator['STOP'])
            else:
                self.aw.buttonSTARTSTOP.setStyleSheet(self.aw.pushbuttonstyles['STOP'])

            # quantification is blocked if lock_quantification_sampling_ticks is not 0
            # (eg. after a change of the event value by button or slider actions)
            self.aw.block_quantification_sampling_ticks = [0,0,0,0]
            #self.aw.extraeventsactionslastvalue = [None,None,None,None] # used by +-% event buttons in ON mode when no event was registered yet

            # reset plus sync
            self.plus_sync_record_hash = None
            self.plus_file_last_modified = None

            # initialize recording version to be stored to new profiles recorded
            self.aw.recording_version = str(__version__)
            self.aw.recording_revision = str(__revision__)
            self.aw.recording_build = str(__build__)

            # if we are in KeepON mode, the reset triggered by ON should respect the roastpropertiesflag ("Delete Properties on Reset")
            if self.roastpropertiesflag and (self.flagKeepON or not keepProperties):
                self.title = QApplication.translate('Scope Title', 'Roaster Scope')
                self.roastingnotes = ''
                self.cuppingnotes = ''
                self.beans = ''
                self.plus_store = None
                self.plus_coffee = None
                self.plus_blend_spec = None
                # copy setup
                self.organization = self.organization_setup
                self.operator = self.operator_setup
                self.roastertype = self.roastertype_setup
                self.roastersize = self.roastersize_setup
                self.roasterheating = self.roasterheating_setup
                self.drumspeed = self.drumspeed_setup
                # set energy defaults
                self.restoreEnergyLoadDefaults()
                self.restoreEnergyProtocolDefaults()
                #
                self.weight = (self.last_batchsize,0,self.weight[2])
                self.volume = (0,0,self.volume[2])
                self.density = (0,self.density[1],1,self.density[3])
                # we reset ambient values to the last sampled readings in this session
                self.ambientTemp = self.ambientTemp_sampled
                self.ambient_humidity = self.ambient_humidity_sampled
                self.ambient_pressure = self.ambient_pressure_sampled
                self.beansize = 0.
                self.beansize_min = 0
                self.beansize_max = 0
                self.moisture_greens = 0.
                self.greens_temp = 0.
                self.volumeCalcWeightInStr = ''
                self.volumeCalcWeightOutStr = ''
            else:
                self.weight = (self.weight[0],0,self.weight[2])
                self.volume = (self.volume[0],0,self.volume[2])
            self.whole_color = 0
            self.ground_color = 0
            self.moisture_roasted = 0.
            self.density_roasted = (0,self.density_roasted[1],1,self.density_roasted[3])

            # reset running AUC values
            self.AUCvalue = 0
            self.AUCsinceFCs = 0
            self.AUCguideTime = 0

            self.profile_sampling_interval = None

            self.statisticstimes = [0,0,0,0,0]

            self.roastdate = QDateTime.currentDateTime()
            self.roastepoch = QDateTime.currentDateTime().toSecsSinceEpoch()
            self.roasttzoffset = libtime.timezone
            if not sampling: # just if the RESET button is manually pressed we clear the error log
                self.errorlog = []
                self.aw.seriallog = []

            self.zoom_follow = False # reset the zoom follow feature

            self.specialevents = []
            self.specialeventstype = []
            self.specialeventsStrings = []
            self.specialeventsvalue = []

            self.E1timex,self.E2timex,self.E3timex,self.E4timex = [],[],[],[]
            self.E1values,self.E2values,self.E3values,self.E4values = [],[],[],[]
            self.aw.eNumberSpinBox.setValue(0)
            self.aw.lineEvent.setText('')
            self.aw.etypeComboBox.setCurrentIndex(0)
            self.aw.valueEdit.setText('')
            #used to find length of arms in annotations
            self.ystep_down = 0
            self.ystep_up = 0

            # reset keyboard mode
            self.aw.keyboardmoveindex = 0 # points to the last activated button in keyboardButtonList; we start with the CHARGE button
            self.aw.resetKeyboardButtonMarks()

            self.aw.setTimerColor('timer')

            try:
                self.aw.ntb.update() # reset the MPL navigation history
            except Exception as e: # pylint: disable=broad-except
                _log.error(e)

            #roast flags
            self.heavyFC_flag = False
            self.lowFC_flag = False
            self.lightCut_flag = False
            self.darkCut_flag = False
            self.drops_flag = False
            self.oily_flag = False
            self.uneven_flag = False
            self.tipping_flag = False
            self.scorching_flag = False
            self.divots_flag = False

            # renable autoCHARGE/autoDRY/autoFCs/autoDROP; all of those get set to False on UNDO of the event for the current roast
            self.autoCHARGEenabled = True
            self.autoDRYenabled = True
            self.autoFCsenabled = True
            self.autoDROPenabled = True

            #Designer variables
            self.indexpoint = 0
            self.workingline = 2            #selects ET or BT
            self.currentx = 0               #used to add point when right click
            self.currenty = 0               #used to add point when right click
            self.designertemp1init = []
            self.designertemp2init = []
#            if self.mode == 'C':
#                #CH, DE, FCs,FCe,SSs,SCe,DROP, COOL
#                self.designertemp1init = [290.,290.,290.,290.,280.,270.,260.,250]
#                self.designertemp2init = [230.,150.,190.,212.,218.,225.,230.,230.]
#            elif self.mode == 'F':
#                self.designertemp1init = [500,500,500,500,500,500,500]
#                self.designertemp2init = [380,300,390,395,410,412,420]
            self.disconnect_designer()  #sets designer flag false
            self.setCursor(Qt.CursorShape.ArrowCursor)

            # disconnect analyzer signal
            self.fig.canvas.mpl_disconnect(self.analyzer_connect_id)

            #reset cupping flavor values
            self.flavors = [5.]*len(self.flavorlabels)

            try:
                # reset color of last pressed button
                if self.aw.lastbuttonpressed != -1:
                    self.aw.setExtraEventButtonStyle(self.aw.lastbuttonpressed, style='normal')
                # reset lastbuttonpressed
                self.aw.lastbuttonpressed = -1
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            #self.aw.pidcontrol.sv = None
            self.aw.fujipid.sv = None
            self.dutycycle = -1
            self.dutycycleTX = 0.
            self.currentpidsv = 0.

            # we remove the filename to force writing a new file
            # and avoid accidental overwriting of existing data
            #current file name
            self.aw.curFile = None
            self.aw.updateWindowTitle()

            # if on turn mouse crosslines off
            if self.crossmarker:
                self.togglecrosslines()

            #remove the analysis results annotation if it exists
            self.analysisresultsstr = ''

            #autodetected CHARGE and DROP index
            self.autoChargeIdx = 0
            self.autoDropIdx = 0
            self.autoTPIdx = 0
            self.autoDryIdx = 0
            self.autoFCsIdx = 0

            self.l_annotations = [] # initiate the event annotations
            # we initialize the annotation position dict of the foreground profile
            self.deleteAnnoPositions(foreground=True, background=False)
            self.l_event_flags_dict = {} # initiate the event id to temp/time annotation dict for flags
            self.l_background_annotations = [] # initiate the background event annotations

            if not sampling:
                self.aw.hideDefaultButtons()
                self.aw.updateExtraButtonsVisibility()
                self.aw.enableEditMenus()

            #reset alarms
            self.temporaryalarmflag = -3
            self.alarmstate = [-1]*len(self.alarmflag)  #1- = not triggered; any other value = triggered; value indicates the index in self.timex at which the alarm was triggered
            #reset TPalarmtimeindex to trigger a new TP recognition during alarm processing
            self.TPalarmtimeindex = None

            self.aw.pidcontrol.pidActive = False

            self.wheelflag = False
            self.designerflag = False

            #check and turn off mouse cross marker
            if self.crossmarker:
                self.togglecrosslines()

            if self.aw is not None:
                self.aw.updatePlusStatus()

        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' reset() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
        finally:
            if self.profileDataSemaphore.available() < 1:
                self.profileDataSemaphore.release(1)
        # now clear all measurements and redraw

        self.clearMeasurements()
        #clear PhasesLCDs
        self.aw.updatePhasesLCDs()
        #clear AUC LCD
        self.aw.updateAUCLCD()

        # if background is loaded we move it back to its original position (after regular load):
        if self.backgroundprofile is not None:
            moved = self.backgroundprofile_moved_x != 0 or self.backgroundprofile_moved_y != 0
            if self.backgroundprofile_moved_x != 0:
                self.movebackground('left',self.backgroundprofile_moved_x)
            if self.backgroundprofile_moved_y != 0:
                self.movebackground('down',self.backgroundprofile_moved_y)
            if moved:
                self.timealign(redraw=False)

        if not (self.autotimex and self.background):
            if self.locktimex:
                self.startofx = self.locktimex_start
                self.endofx = self.locktimex_end
            elif keepProperties:
                self.startofx = self.chargemintime
                self.endofx = self.resetmaxtime
        if self.endofx < 1:
            self.endofx = 60

        ### REDRAW  ##
        if redraw:
            self.aw.autoAdjustAxis(background=not keepProperties) # if reset() triggered by ON, we ignore background on adjusting the axis and adjust according to RESET min/max
            self.redraw(True,sampling=sampling,smooth=self.optimalSmoothing) # we need to re-smooth with standard smoothing if ON and optimal-smoothing is ticked

        # write memory stats to the log
        try:
            vm = psutil.virtual_memory()
            _log.info('memory used %s, %s (%s%%) available', bytes2human(psutil.Process().memory_full_info().uss),bytes2human(vm[1]),int(round(100-vm[2])))
        except Exception: # pylint: disable=broad-except
            pass

        #QApplication.processEvents() # this one seems to be needed for a proper redraw in fullscreen mode on OS X if a profile was loaded and NEW is pressed
        #   this processEvents() seems not to be needed any longer!?
        return True

    # https://gist.github.com/bhawkins/3535131
    @staticmethod
    def medfilt(x, k):
        """Apply a length-k median filter to a 1D array x.
        Boundaries are extended by repeating endpoints.
        """
        assert k % 2 == 1, 'Median filter length must be odd.'
        assert x.ndim == 1, 'Input must be one-dimensional.'
        if len(x) == 0:
            return x
        k2 = (k - 1) // 2
        y = numpy.zeros ((len (x), k), dtype=x.dtype)
        y[:,k2] = x
        for i in range (k2):
            j = k2 - i
            y[j:,i] = x[:-j]
            y[:j,i] = x[0]
            y[:-j,-(i+1)] = x[j:]
            y[-j:,-(i+1)] = x[-1]
        return numpy.median(y, axis=1)
#        return numpy.nanmedian(y, axis=1) # produces artefacts

    # smoothes a list (or numpy.array) of values 'y' at taken at times indicated by the numbers in list 'x'
    # 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
    # 'flat' results in moving average
    # window_len should be odd
    # based on http://wiki.scipy.org/Cookbook/SignalSmooth
    # returns a smoothed numpy array or the original y argument
    def smooth(self, x, y, window_len=15, window='hanning'):
        try:
            if len(x) == len(y) and len(x) > 1:
                if window_len > 2:
                    # smooth curves
                    #s = numpy.r_[2*x[0]-y[window_len:1:-1],y,2*y[-1]-y[-1:-window_len:-1]]
                    #s=numpy.r_[y[window_len-1:0:-1],y,y[-2:-window_len-1:-1]]
                    #s = y
                    s=numpy.r_[y[window_len-1:0:-1],y,y[-1:-window_len:-1]]
                    if window == 'flat': #moving average
                        w = numpy.ones(window_len,'d')
                    else:
                        w = eval('numpy.'+window+'(window_len)') # pylint: disable=eval-used
                    try:
                        ys = numpy.convolve(w/w.sum(),s,mode='valid')
                    except Exception: # pylint: disable=broad-except
                        return y
                    hwl = int(window_len/2)
                    res = ys[hwl:-hwl]
                    if len(res)+1 == len(y) and len(res) > 0:
                        try:
                            return ys[hwl-1:-hwl]
                        except Exception: # pylint: disable=broad-except
                            return y
                    elif len(res) != len(y):
                        return y
                    else:
                        return res
                else:
                    return y
            else:
                return y
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' smooth() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
            return x

    # re-sample, filter and smooth slice
    # takes numpy arrays a (time) and b (temp) of the same length and returns a numpy array representing the processed b values
    # precondition: (self.filterDropOuts or window_len>2)
    def smooth_slice(self, a, b,
        window_len=7, window='hanning',decay_weights=None,decay_smoothing=False,
        re_sample=True,back_sample=True,a_lin=None):

        # 1. re-sample
        if re_sample:
            if a_lin is None or len(a_lin) != len(a):
                a_mod = numpy.linspace(a[0],a[-1],len(a))
            else:
                a_mod = a_lin
            b = numpy.interp(a_mod, a, b) # resample data to linear spaced time
        else:
            a_mod = a
        res = b # just in case the precondition (self.filterDropOuts or window_len>2) does not hold
        # 2. filter spikes
        if self.filterDropOuts:
            try:
                b = self.medfilt(b,5)  # k=3 seems not to catch all spikes in all cases; k=5 and k=7 seems to be ok; 13 might be the maximum; k must be odd!
# scipyernative which performs equal, but produces larger artefacts at the borders and for intermediate NaN values for k>3
#                from scipy.signal import medfilt as scipy_medfilt
#                b = scipy_medfilt(b,3)
                res = b
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
                res = b
        # 3. smooth data
        if window_len>2:
            if decay_smoothing:
                # decay smoothing
                if decay_weights is None:
                    decay_weights = numpy.arange(1,window_len+1)
                else:
                    window_len = len(decay_weights)
                # invariant: window_len = len(decay_weights)
                if decay_weights.sum() == 0:
                    res = b
                else:
                    res = []
                    # ignore -1 readings in averaging and ensure a good ramp
                    for i, v in enumerate(b):
                        seq = b[max(0,i-window_len + 1):i+1]
#                        # we need to suppress -1 drop out values from this
#                        seq = list(filter(lambda item: item != -1,seq)) # -1 drop out values in b have already been replaced by numpy.nan above

                        w = decay_weights[max(0,window_len-len(seq)):]  # preCond: len(decay_weights)=window_len and len(seq) <= window_len; postCond: len(w)=len(seq)
                        if len(w) == 0:
                            res.append(v) # we don't average if there is are no weights (e.g. if the original seq did only contain -1 values and got empty)
                        else:
                            res.append(numpy.average(seq,weights=w)) # works only if len(seq) = len(w)
                    # postCond: len(res) = len(b)
            else:
                # optimal smoothing (the default)
                win_len = max(0,window_len)
                if win_len != 1: # at the lowest level we turn smoothing completely off
                    res = self.smooth(a_mod,b,win_len,window)
                else:
                    res = b
        # 4. sample back
        if re_sample and back_sample:
            res = numpy.interp(a, a_mod, res) # re-sampled back to original timestamps
        return res

    # takes lists a (time array) and b (temperature array) containing invalid segments of -1/None values and returns a list with all segments of valid values smoothed
    # a: list of timestamps
    # b: list of readings
    # re_sample: if true re-sample readings to a linear spaced time before smoothing
    # back_sample: if true results are back-sampled to original timestamps given in "a" after smoothing
    # a_lin: pre-computed linear spaced timestamps of equal length than a
    # NOTE: result can contain NaN items on places where the input array contains the error element -1
    # result is a numpy array or the b as numpy array with drop out readings -1 replaced by NaN
    def smooth_list(self, a, b, window_len=7, window='hanning',decay_weights=None,decay_smoothing=False,fromIndex=-1,toIndex=0,re_sample=True,back_sample=True,a_lin=None):
        if len(a) > 1 and len(a) == len(b) and (self.filterDropOuts or window_len>2):
            #pylint: disable=E1103
            # 1. truncate
            if fromIndex > -1: # if fromIndex is set, replace prefix up to fromIndex by None
                if toIndex==0: # no limit
                    toIndex=len(a)
            else: # smooth list on full length
                fromIndex = 0
                toIndex = len(a)
            a = numpy.array(a[fromIndex:toIndex], dtype=numpy.double)
            # we mask the error value -1 and Numpy  in the temperature array
            mb = numpy.ma.masked_equal(numpy.ma.masked_equal(b[fromIndex:toIndex], -1), None)
            # split in masked and
            unmasked_slices = [(x,False) for x in numpy.ma.clump_unmasked(mb)] # the valid readings
            masked_slices = [(x,True) for x in numpy.ma.clump_masked(mb)] # the dropped values
            sorted_slices = sorted(unmasked_slices + masked_slices, key=lambda tup: tup[0].start)
            b_smoothed = [] # b_smoothed collects the smoothed segments in order
            b_smoothed.append(numpy.full(fromIndex, numpy.nan, dtype=numpy.double)) # append initial segment to the list of resulting segments
            # we just smooth the unmsked slices and add the unmasked slices with NaN values
            for (s, m) in sorted_slices:
                if m:
                    # a slice with all masked (invalid) readings
                    b_smoothed.append(numpy.full(s.stop - s.start, numpy.nan, dtype=numpy.double))
                else:
                    # a slice with proper data
                    b_smoothed.append(self.smooth_slice(a[s], mb[s], window_len, window, decay_weights, decay_smoothing, re_sample, back_sample, a_lin))
            b_smoothed.append(numpy.full(len(a)-toIndex, numpy.nan, dtype=numpy.double)) # append the final segment to the list of resulting segments
            return numpy.concatenate(b_smoothed)
        b = numpy.array(b, dtype=numpy.double)
        b[b == -1] = numpy.nan
        return b


# REPLACED BY above slicing smooth_list
#    # a: list of timestamps
#    # b: list of readings
#    # re_sample: if true re-sample readings to a linear spaced time before smoothing
#    # back_sample: if true results are back-sampled to original timestamps given in "a" after smoothing
#    # a_lin: pre-computed linear spaced timestamps of equal length than a
#    # NOTE: result can contain NaN items on places where the input array contains the error element -1
#    # result is always a list (and not a numpy array)
#    def smooth_list(self, a, b, window_len=7, window='hanning',decay_weights=None,decay_smoothing=False,fromIndex=-1,toIndex=0,re_sample=True,back_sample=True,a_lin=None):  # default 'hanning'
#        if len(a) > 1 and len(a) == len(b) and (self.filterDropOuts or window_len>2):
#            #pylint: disable=E1103
#            # 1. truncate
#            if fromIndex > -1: # if fromIndex is set, replace prefix up to fromIndex by None
#                if toIndex==0: # no limit
#                    toIndex=len(a)
#            else: # smooth list on full length
#                fromIndex = 0
#                toIndex = len(a)
#            # we replace the error value -1  in the temperature array by numpy.nan to avoid strange smoothing artifacts
#            # no need to substitute anything in the time array!
#            a = numpy.array(a[fromIndex:toIndex], dtype=numpy.double)
#            b = numpy.array(b[fromIndex:toIndex], dtype=numpy.double) # None replaced by numpy.nan
#            b[b==-1] = numpy.nan # -1 replaced by numpy.nan
#            # 2. re-sample
#            if re_sample:
#                if a_lin is None or len(a_lin) != len(a):
#                    a_mod = numpy.linspace(a[0],a[-1],len(a))
#                else:
#                    a_mod = a_lin
#                b = numpy.interp(a_mod, a, b) # resample data to linear spaced time
#            else:
#                a_mod = a
#            # 3. filter spikes
#            if self.filterDropOuts:
#                try:
#                    b = self.medfilt(b,5)  # k=3 seems not to catch all spikes in all cases; k must be odd!
### scipy alternative which performs equal, but produces larger artefacts at the borders and for intermediate NaN values for k>3
##                    from scipy.signal import medfilt as scipy_medfilt
##                    b = scipy_medfilt(b,3)
#                    res = b
#                except Exception as e: # pylint: disable=broad-except
#                    _log.error(e)
#                    res = b
#            # 4. smooth data
#            if window_len>2:
#                if decay_smoothing:
#                    # decay smoothing
#                    if decay_weights is None:
#                        decay_weights = numpy.arange(1,window_len+1)
#                    else:
#                        window_len = len(decay_weights)
#                    # invariant: window_len = len(decay_weights)
#                    if decay_weights.sum() == 0:
#                        res = b
#                    else:
#                        res = []
#                        # ignore -1 readings in averaging and ensure a good ramp
#                        for i in range(len(b)):
#                            seq = b[max(0,i-window_len + 1):i+1]
##                            # we need to suppress -1 drop out values from this
##                            seq = list(filter(lambda item: item != -1,seq)) # -1 drop out values in b have already been replaced by numpy.nan above
#
#                            w = decay_weights[max(0,window_len-len(seq)):]  # preCond: len(decay_weights)=window_len and len(seq) <= window_len; postCond: len(w)=len(seq)
#                            if len(w) == 0:
#                                res.append(b[i]) # we don't average if there is are no weights (e.g. if the original seq did only contain -1 values and got empty)
#                            else:
#                                res.append(numpy.average(seq,weights=w)) # works only if len(seq) = len(w)
#                        # postCond: len(res) = len(b)
#                else:
#                    # optimal smoothing (the default)
#                    win_len = max(0,window_len)
#                    if win_len != 1: # at the lowest level we turn smoothing completely off
#                        res = self.smooth(a_mod,b,win_len,window)
#                    else:
#                        res = b
#            # 4. sample back
#            if re_sample and back_sample:
#                res = numpy.interp(a, a_mod, res) # re-sampled back to original timestamps
#            # Note: at this point res might be a list or a numpy array as decay smoothing generates a list which might not be back_sampled and optimal smoothing a numpy array.
#            return numpy.concatenate(([None]*(fromIndex),res,[None]*(len(a)-toIndex))).tolist()
#        return b

    # deletes saved annotation positions from l_annotations_dict
    # foreground annotations have position keys <=6, background annotation positions have keys > 6,
    def deleteAnnoPositions(self, foreground:bool = False, background:bool = False):
        if background and foreground:
            self.l_annotations_dict = {}
        else:
            for k in list(self.l_annotations_dict.keys()):
                if (background and k > 6) or (foreground and k <= 6):
                    self.l_annotations_dict.pop(k)

    def moveBackgroundAnnoPositionsX(self, step):
        for k in list(self.l_annotations_dict.keys()):
            if k > 6:
                for anno in self.l_annotations_dict[k]:
                    x,y = anno.get_position()
                    anno.set_position((x+step,y))

    def moveBackgroundAnnoPositionsY(self, step):
        for k in list(self.l_annotations_dict.keys()):
            if k > 6:
                for anno in self.l_annotations_dict[k]:
                    x,y = anno.get_position()
                    anno.set_position((x,y+step))

    # returns the position of the main event annotations as list of lists of the form
    #   [[id,temp_x,temp_y,time_x,time_y],...]
    # with id the main event id like -1 for TP, 0 for CHARGE, 1 for DRY,.., 6 for DROP (keys above 6 as used for background profile annotations are ignored)
    def getAnnoPositions(self) -> List[List[float]]:
        res:List[List[float]] = []
        for k,v in self.l_annotations_dict.items():
            if k<7:
                temp_anno = v[0].xyann
                time_anno = v[1].xyann
                if all(not numpy.isnan(e) for e in temp_anno + time_anno):
                    # we add the entry only if all of the coordinates are proper numpers and not nan
                    res.append([k,temp_anno[0],temp_anno[1],time_anno[0],time_anno[1]])
        return res

    def setAnnoPositions(self,anno_positions):
        for ap in anno_positions:
            if len(ap) == 5:
                i = ap[0]
                temp_x = ap[1]
                temp_y = ap[2]
                time_x = ap[3]
                time_y = ap[4]
                self.l_annotations_pos_dict[i] = ((temp_x,temp_y),(time_x,time_y))

    # returns the position of the custom event flag annotations as list of lists of the form
    #   [[id,x,y],...]
    # with id the event id
    def getFlagPositions(self) -> List[List[float]]:
        res = []
        for k,v in self.l_event_flags_dict.items():
            flag_anno = v.xyann
            if all(not numpy.isnan(e) for e in flag_anno):
                res.append([k,flag_anno[0],flag_anno[1]])
        return res

    def setFlagPositions(self,flag_positions):
        for fp in flag_positions:
            if len(fp) == 3:
                i = fp[0]
                x = fp[1]
                y = fp[2]
                self.l_event_flags_pos_dict[i] = (x,y)

    # temp and time are the two annotation
    # x,y is the position of the annotation line start
    # e is the x-axis offset, yup/ydown are the y-axis offsets of the annotations line ends and the annotation text
    # a is the alpha value
    def annotate(self, temp, time_str, x, y, yup, ydown,e=0,a=1.,draggable=True,draggable_anno_key=None):
        if self.ax is None:
            return None
        fontprop_small = self.aw.mpl_fontproperties.copy()
        fontsize = 'x-small'
        fontprop_small.set_size(fontsize)
        if self.patheffects:
            rcParams['path.effects'] = [PathEffects.withStroke(linewidth=self.patheffects, foreground=self.palette['background'])]
        else:
            rcParams['path.effects'] = []
        #annotate temp
        fmtstr = '%.1f' if self.LCDdecimalplaces else '%.0f'
        if draggable and draggable_anno_key is not None and draggable_anno_key in self.l_annotations_pos_dict:
            # we first look into the position dictionary loaded from file, those are removed after first rendering
            xytext = self.l_annotations_pos_dict[draggable_anno_key][0]
        elif draggable and draggable_anno_key is not None and draggable_anno_key in self.l_annotations_dict:
            # next we check the "live" dictionary
            xytext = self.l_annotations_dict[draggable_anno_key][0].xyann
        else:
            xytext = (x+e,y + yup)
        temp_anno = self.ax.annotate(fmtstr%(temp), xy=(x,y),xytext=xytext,
                            color=self.palette['text'],
                            arrowprops={'arrowstyle':'-','color':self.palette['text'],'alpha':a},
                            fontsize=fontsize,
                            alpha=a,
                            fontproperties=fontprop_small)
        try:
            temp_anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
            if draggable:
                temp_anno.draggable(use_blit=True)
                temp_anno.set_picker(self.aw.draggable_text_box_picker)
        except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
            pass
        #anotate time
        if draggable and draggable_anno_key is not None and draggable_anno_key in self.l_annotations_pos_dict:
            # we first look into the position dictionary loaded from file
            xytext = self.l_annotations_pos_dict[draggable_anno_key][1]
        elif draggable and draggable_anno_key is not None and draggable_anno_key in self.l_annotations_dict:
            xytext = self.l_annotations_dict[draggable_anno_key][1].xyann
        else:
            xytext = (x+e,y - ydown)
        time_anno = self.ax.annotate(time_str,xy=(x,y),xytext=xytext,
                             color=self.palette['text'],arrowprops={'arrowstyle':'-','color':self.palette['text'],'alpha':a},
                             fontsize=fontsize,alpha=a,fontproperties=fontprop_small)
        try:
            time_anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
            if draggable:
                time_anno.draggable(use_blit=True)
                time_anno.set_picker(self.aw.draggable_text_box_picker)
        except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
            pass
        if self.patheffects:
            rcParams['path.effects'] = []
        if draggable and draggable_anno_key is not None:
            self.l_annotations_dict[draggable_anno_key] = [temp_anno, time_anno]
        return [temp_anno, time_anno]

    def place_annotations(self,TP_index,d,timex,timeindex,temp,stemp,startB=None,timeindex2=None,TP_time_loaded=None,draggable=True):
        ystep_down = ystep_up = 0
        anno_artists:List[Tuple['Annotation','Annotation']] = []
        if self.ax is None:
            return anno_artists
        #Add markers for CHARGE
        # add offset to annotation keys for background annotations to prevent them from being confused with those of the foreground profile and to prevent persisting them to alog files
        anno_key_offset = 0 if startB is None else 10
        try:
            if len(timex) > 0:
                if timeindex[0] != -1 and len(timex) > timeindex[0]:
                    t0idx = timeindex[0] # time idx at CHARGE
                    t0 = timex[t0idx]    # time at CHARGE in sec.
                else:
                    t0idx = 0
                    t0 = 0
                if timeindex[0] != -1:
                    y = stemp[t0idx]
                    ystep_down,ystep_up = self.findtextgap(ystep_down,ystep_up,y,y,d)
                    if startB is not None:
                        st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation', 'CHARGE'))
                        e = 0
                        a = self.backgroundalpha
                    else:
                        st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation', 'CHARGE'))
                        if self.graphfont == 1:
                            st1 = self.__to_ascii(st1)
                        e = 0
                        a = 1.
                    time_temp_annos = self.annotate(temp[t0idx],st1,t0,y,ystep_up,ystep_down,e,a,draggable,0+anno_key_offset)
                    if time_temp_annos is not None:
                        anno_artists += time_temp_annos

                #Add TP marker
                if self.markTPflag:
                    if TP_index and TP_index > 0:
                        ystep_down,ystep_up = self.findtextgap(ystep_down,ystep_up,stemp[t0idx],stemp[TP_index],d)
                        st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','TP {0}'), stringfromseconds(timex[TP_index]-t0,False))
                        a = 1.
                        e = 0
                        time_temp_annos = self.annotate(temp[TP_index],st1,timex[TP_index],stemp[TP_index],ystep_up,ystep_down,e,a,draggable,-1+anno_key_offset)
                        if time_temp_annos is not None:
                            anno_artists += time_temp_annos
                    elif TP_time_loaded is not None:
                        a = self.backgroundalpha if timeindex2 else 1.0
                        e = 0
                        shift = timex[timeindex[0]] if timeindex[0] > 0 else 0
                        TP_index = self.backgroundtime2index(TP_time_loaded + shift)
                        ystep_down,ystep_up = self.findtextgap(ystep_down,ystep_up,stemp[t0idx],stemp[TP_index],d)
                        st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','TP {0}'),stringfromseconds(TP_time_loaded,False))
                        time_temp_annos = self.annotate(temp[TP_index],st1,timex[TP_index],stemp[TP_index],ystep_up,ystep_down,e,a,draggable,-1+anno_key_offset)
                        if time_temp_annos is not None:
                            anno_artists += time_temp_annos
                #Add Dry End markers
                if timeindex[1]:
                    tidx = timeindex[1]
                    ystep_down,ystep_up = self.findtextgap(ystep_down,ystep_up,stemp[t0idx],stemp[tidx],d)
                    st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','DE {0}'),stringfromseconds(timex[tidx]-t0,False))
                    a = self.backgroundalpha if timeindex2 else 1.0
                    e = 0
                    time_temp_annos = self.annotate(temp[tidx],st1,timex[tidx],stemp[tidx],ystep_up,ystep_down,e,a,draggable,1+anno_key_offset)
                    if time_temp_annos is not None:
                        anno_artists += time_temp_annos

                #Add 1Cs markers
                if timeindex[2]:
                    tidx = timeindex[2]
                    if timeindex[1]: #if dryend
                        ystep_down,ystep_up = self.findtextgap(ystep_down,ystep_up,stemp[timeindex[1]],stemp[tidx],d)
                    else:
                        ystep_down,ystep_up = self.findtextgap(0,0,stemp[tidx],stemp[tidx],d)
                    st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','FCs {0}'),stringfromseconds(timex[tidx]-t0,False))
                    a = self.backgroundalpha if timeindex2 else 1.0
                    e = 0
                    time_temp_annos = self.annotate(temp[tidx],st1,timex[tidx],stemp[tidx],ystep_up,ystep_down,e,a,draggable,2+anno_key_offset)
                    if time_temp_annos is not None:
                        anno_artists += time_temp_annos
                #Add 1Ce markers
                if timeindex[3]:
                    tidx = timeindex[3]
                    ystep_down,ystep_up = self.findtextgap(ystep_down,ystep_up,stemp[timeindex[2]],stemp[tidx],d)
                    st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','FCe {0}'),stringfromseconds(timex[tidx]-t0,False))
                    a = self.backgroundalpha if timeindex2 else 1.0
                    e = 0
                    time_temp_annos = self.annotate(temp[tidx],st1,timex[tidx],stemp[tidx],ystep_up,ystep_down,e,a,draggable,3+anno_key_offset)
                    if time_temp_annos is not None:
                        anno_artists += time_temp_annos
                    #add a water mark if FCs
                    if timeindex[2] and not timeindex2 and self.watermarksflag:
                        self.ax.axvspan(timex[timeindex[2]],timex[tidx], facecolor=self.palette['watermarks'], alpha=0.2)
                #Add 2Cs markers
                if timeindex[4]:
                    tidx = timeindex[4]
                    if timeindex[3]:
                        ystep_down,ystep_up = self.findtextgap(ystep_down,ystep_up,stemp[timeindex[3]],stemp[tidx],d)
                    else:
                        ystep_down,ystep_up = self.findtextgap(0,0,stemp[tidx],stemp[tidx],d)
                    st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','SCs {0}'),stringfromseconds(timex[tidx]-t0,False))
                    a = self.backgroundalpha if timeindex2 else 1.0
                    e = 0
                    time_temp_annos = self.annotate(temp[tidx],st1,timex[tidx],stemp[tidx],ystep_up,ystep_down,e,a,draggable,4+anno_key_offset)
                    if time_temp_annos is not None:
                        anno_artists += time_temp_annos
                #Add 2Ce markers
                if timeindex[5]:
                    tidx = timeindex[5]
                    ystep_down,ystep_up = self.findtextgap(ystep_down,ystep_up,stemp[timeindex[4]],stemp[tidx],d)
                    st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','SCe {0}'),stringfromseconds(timex[tidx]-t0,False))
                    a = self.backgroundalpha if timeindex2 else 1.0
                    e = 0
                    time_temp_annos = self.annotate(temp[tidx],st1,timex[tidx],stemp[tidx],ystep_up,ystep_down,e,a,draggable,5+anno_key_offset)
                    if time_temp_annos is not None:
                        anno_artists += time_temp_annos
                    #do water mark if SCs
                    if timeindex[4] and not timeindex2 and self.watermarksflag:
                        self.ax.axvspan(timex[timeindex[4]],timex[tidx], facecolor=self.palette['watermarks'], alpha=0.2)
                #Add DROP markers
                if timeindex[6]:
                    tidx = timeindex[6]
                    if timeindex[5]:
                        tx = timeindex[5]
                    elif timeindex[4]:
                        tx = timeindex[4]
                    elif timeindex[3]:
                        tx = timeindex[3]
                    elif timeindex[2]:
                        tx = timeindex[2]
                    elif timeindex[1]:
                        tx = timeindex[1]
                    else:
                        tx = t0idx
                    ystep_down,ystep_up = self.findtextgap(ystep_down,ystep_up,stemp[tx],stemp[tidx],d)
                    st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','DROP {0}'),stringfromseconds(timex[tidx]-t0,False))
                    if self.graphfont == 1:
                        st1 = self.__to_ascii(st1)
                    a = self.backgroundalpha if timeindex2 else 1.0
                    e = 0

                    time_temp_annos = self.annotate(temp[tidx],st1,timex[tidx],stemp[tidx],ystep_up,ystep_down,e,a,draggable,6+anno_key_offset)
                    if time_temp_annos is not None:
                        anno_artists += time_temp_annos

                    #do water mark if FCs, but no FCe nor SCs nor SCe
                    if timeindex[2] and not timeindex[3] and not timeindex[4] and not timeindex[5] and not timeindex2 and self.watermarksflag:
                        fc_artist = self.ax.axvspan(timex[timeindex[2]],timex[tidx], facecolor=self.palette['watermarks'], alpha=0.2)
                        try:
                            fc_artist.set_in_layout(False) # remove title from tight_layout calculation
                        except Exception: # pylint: disable=broad-except # set_in_layout not available in mpl<3.x
                            pass
                    #do water mark if SCs, but no SCe
                    if timeindex[4] and not timeindex[5] and not timeindex2 and self.watermarksflag:
                        sc_artist = self.ax.axvspan(timex[timeindex[4]],timex[tidx], facecolor=self.palette['watermarks'], alpha=0.2)
                        try:
                            sc_artist.set_in_layout(False) # remove title from tight_layout calculation
                        except Exception: # pylint: disable=broad-except # set_in_layout not available in mpl<3.x
                            pass
                # add COOL mark
                if timeindex[7] and not timeindex2:
                    tidx = timeindex[7]
                    # as the right most data value of the axis in self.ax.get_xlim()[1] is only correctly set after the initial draw,
                    # we simply set it to twice as wide and trust that the clipping will cut of the part not within the axis system
                    endidx = 2*max(self.timex[-1],self.endofx,self.ax.get_xlim()[0],self.ax.get_xlim()[1])
                    if timex[tidx] < endidx and self.watermarksflag:
                        cool_mark = self.ax.axvspan(timex[tidx],endidx, facecolor=self.palette['rect4'], ec='none', alpha=0.3, clip_on=True, lw=None)#,lod=False)
                        try:
                            cool_mark.set_in_layout(False) # remove title from tight_layout calculation
                        except Exception: # pylint: disable=broad-except # set_in_layout not available in mpl<3.x
                            pass
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' place_annotations() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
        return anno_artists

    def apply_symbolic_delta_formula(self, fct, deltas, timex, RTsname):
        try:
            if len(deltas) == len(timex):
                return [self.eval_math_expression(fct,timex[i],RTsname=RTsname,RTsval=d) for i,d in enumerate(deltas)]
            return deltas
        except Exception: # pylint: disable=broad-except
            return deltas

    # computes the RoR over the time and temperature arrays tx and temp via polynoms of degree 1 at index i using a window of wsize
    # the window size wsize needs to be at least 1 (two succeeding readings)
    @staticmethod
    def polyRoR(tx, temp, wsize, i):
        if i == 0: # we duplicate the first possible RoR value instead of returning a 0
            i = 1
        if 0 < i < min(len(tx), len(temp)):
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                left_index = max(0,i-wsize)
                LS_fit = numpy.polynomial.polynomial.polyfit(tx[left_index:i+1],temp[left_index:i+1], 1)
                return LS_fit[1]*60.
        else:
            return 0

    @staticmethod
    # with window size wsize=1 the RoR is computed over succeeding readings; tx and temp assumed to be of type numpy.array
    def arrayRoR(tx, temp, wsize): # with wsize >=1
        # length compensation done downstream, not necessary here!
        return (temp[wsize:] - temp[:-wsize]) / ((tx[wsize:] - tx[:-wsize])/60.)


    # returns deltas and linearized timex;  both results can be None
    # timex: the time array
    # temp: the temperature array
    # ds: the number of delta samples
    # timex_lin: the linearized time array or None
    # delta_symbolic_function: the symbolic function to be applied to the delta or None
    # RTsname: the symbolic variable name of the delta
    # deltaFilter: the deltaFilter setting
    # roast_start_idx: the index of CHARGE
    # roast_end_idx: the index of DROP
    def computeDeltas(self, timex, temp, ds, optimalSmoothing, timex_lin, delta_symbolic_function, RTsname, deltaFilter, roast_start_idx, roast_end_idx) -> Tuple[Optional[List[Optional[float]]], 'npt.NDArray[numpy.floating]']:
        if temp is not None:
            with numpy.errstate(divide='ignore'):
                lt = len(timex)
                ntemp = numpy.array([0 if x is None else x for x in temp]) # ERROR None Type object not scriptable! t==None on ON

                if optimalSmoothing and self.polyfitRoRcalc:
                    # optimal RoR computation using polynoms with out timeshift
                    dss = ds + 1 if ds % 2 == 0 else ds
                    if len(ntemp) > dss:
                        try:
                            # ntemp is not linearized yet:
                            if timex_lin is None or len(timex_lin) != len(ntemp):
                                timex_lin = numpy.linspace(timex[0],timex[-1],lt)
                            lin = timex_lin
                            ntemp_lin = numpy.interp(lin, timex, ntemp) # resample data in ntemp to linear spaced time
                            dist = (lin[-1] - lin[0]) / (len(lin) - 1)
                            from scipy.signal import savgol_filter # type: ignore # @Reimport
                            z1 = savgol_filter(ntemp_lin, dss, 1, deriv=1, delta=dss)
                            z1 = z1 * (60./dist) * dss
                        except Exception: # pylint: disable=broad-except
                            # a numpy/OpenBLAS polyfit bug can cause polyfit to throw an exception "SVD did not converge in Linear Least Squares" on Windows Windows 10 update 2004
                            # https://github.com/numpy/numpy/issues/16744
                            # original version just picking the corner values:
                            z1 = self.arrayRoR(timex,ntemp,ds)
                    else:
                        # in this case we use the standard algo
                        try:
                            # variant using incremental polyfit RoR computation
                            z1 = [self.polyRoR(timex,ntemp,ds,i) for i in range(len(ntemp))]
                        except Exception: # pylint: disable=broad-except
                            # a numpy/OpenBLAS polyfit bug can cause polyfit to throw an exception "SVD did not converge in Linear Least Squares" on Windows Windows 10 update 2004
                            # https://github.com/numpy/numpy/issues/16744
                            # original version just picking the corner values:
                            z1 = self.arrayRoR(timex,ntemp,ds)
                elif self.polyfitRoRcalc:
                    try:
                        # variant using incremental polyfit RoR computation
                        z1 = [self.polyRoR(timex,ntemp,ds,i) for i in range(len(ntemp))] # windows size ds needs to be at least 2
                    except Exception: # pylint: disable=broad-except
                        # a numpy/OpenBLAS polyfit bug can cause polyfit to throw an exception "SVD did not converge in Linear Least Squares" on Windows Windows 10 update 2004
                        # https://github.com/numpy/numpy/issues/16744
                        # original version just picking the corner values:
                        z1 = self.arrayRoR(timex,ntemp,ds)
                else:
                    z1 = self.arrayRoR(timex,ntemp,ds)

            ld1 = len(z1)
            # make lists equal in length
            if lt > ld1:
                z1 = numpy.append([z1[0] if ld1 else 0.]*(lt - ld1),z1)
            # apply smybolic formula
            if delta_symbolic_function is not None and len(delta_symbolic_function):
                z1 = self.apply_symbolic_delta_formula(delta_symbolic_function,z1,timex,RTsname=RTsname)
            # apply smoothing
            if optimalSmoothing:
                user_filter = deltaFilter
            else:
                user_filter = int(round(deltaFilter/2.))
            delta1 = self.smooth_list(timex,z1,window_len=user_filter,decay_smoothing=(not optimalSmoothing),a_lin=timex_lin)

            # cut out the part after DROP and before CHARGE and remove values beyond the RoRlimit
            delta1 = [
                d if ((roast_start_idx <= i <= roast_end_idx) and (d is not None and (not self.RoRlimitFlag or
                    max(-self.maxRoRlimit,self.RoRlimitm) < d < min(self.maxRoRlimit,self.RoRlimit))))
                else None
                for i,d in enumerate(delta1)
            ]

            if isinstance(delta1, (numpy.ndarray, numpy.generic)):
                delta1 = delta1.tolist()
            return delta1, timex_lin
        return None, timex_lin

    # computes the RoR deltas and returns the smoothed versions for both temperature channels
    # if t1 or t2 is not given (None), its RoR signal is not computed and None is returned instead
    # timex_lin: a linear spaced version of timex
    def recomputeDeltas(self,timex,CHARGEidx,DROPidx,t1,t2,optimalSmoothing=True,timex_lin=None,deltaETsamples=None,deltaBTsamples=None) -> Tuple[Optional[List[Optional[float]]], Optional[List[Optional[float]]]]:
        try:
            tx_roast = numpy.array(timex) # timex non-linearized as numpy array
            lt = len(tx_roast)
            roast_start_idx = CHARGEidx if CHARGEidx > -1 else 0
            roast_end_idx = DROPidx if DROPidx > 0 else lt
            if deltaBTsamples is None:
                dsBT = max(1, self.deltaBTsamples) # now as in sample_processing()
            else:
                dsBT = deltaBTsamples
            if deltaETsamples is None:
                dsET = max(1, self.deltaETsamples) # now as in sample_processing()
            else:
                dsET = deltaETsamples
            if timex_lin is not None:
                if len(timex_lin) == len(timex):
                    timex_lin = numpy.array(timex_lin)
                else:
                    timex_lin = None
            delta1, timex_lin = self.computeDeltas(
                    tx_roast,
                    t1,
                    dsET,
                    optimalSmoothing,
                    timex_lin,
                    self.DeltaETfunction,
                    'R1',
                    self.deltaETfilter,
                    roast_start_idx,
                    roast_end_idx)
            delta2, _ = self.computeDeltas(
                    tx_roast,
                    t2,
                    dsBT,
                    optimalSmoothing,
                    timex_lin,
                    self.DeltaBTfunction,
                    'R2',
                    self.deltaBTfilter,
                    roast_start_idx,
                    roast_end_idx)

            return delta1, delta2
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' recomputeDeltas() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
            return None, None

    @staticmethod
    def bisection(array, value):
        '''Given an ``array`` , and given a ``value`` , returns an index j such that ``value`` is between array[j]
        and array[j+1]. ``array`` must be monotonic increasing. j=-1 or j=len(array) is returned
        to indicate that ``value`` is out of range below and above respectively.'''
        #Algorithm presumes 'array' is monotonic increasing.  This is not guaranteed for profiles so there
        #may be results that are not strictly correct.
        n = len(array)
        if value < array[0]:
            return -1
        if value > array[n-1]:
            return n
        if value == array[0]: # edge cases at bottom
            return 0
        if value == array[n-1]: # and top
            return n-1
        jl = 0   # Initialize lower
        ju = n-1 # and upper limits.
        while ju-jl > 1:# If we are not yet done,
            jm=(ju+jl) >> 1 # compute a midpoint with a bitshift
            if value >= array[jm]:
                jl=jm # and replace either the lower limit
            else:
                ju=jm # or the upper limit, as appropriate.
            # Repeat until the test condition is satisfied.
        if abs(value - array[jl]) > abs(array[ju] - value):
            return ju
        return jl

    def drawAUC(self):
        if self.ax is None:
            return
        try:
            TP_Index = self.aw.findTP()
            if self.AUCbaseFlag:
                _,_,_,idx = self.aw.ts()
                # ML: next line seems not to alter the idx in any way and is just not needed
#                idx = TP_Index + self.bisection(self.stemp2[TP_Index:self.timeindex[6]],self.stemp2[idx])
            else:
                idx = TP_Index + self.bisection(self.stemp2[TP_Index:self.timeindex[6]],self.AUCbase)
            rtbt = self.stemp2[idx]

            ix = self.timex[idx:self.timeindex[6]+1]
            iy = self.stemp2[idx:self.timeindex[6]+1]

            # Create the shaded region
            a = ix[0]
            b = ix[-1]
            verts = [ xy for xy in [(a, rtbt)] + list(zip(ix, iy)) + [(b, rtbt)] if xy[1] > 0 ]
            if verts:
                poly = Polygon(verts, facecolor=self.palette['aucarea'], edgecolor='0.5', alpha=0.3)
                self.ax.add_patch(poly)
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    def set_xlabel(self,xlabel):
        fontprop_medium = self.aw.mpl_fontproperties.copy()
        fontprop_medium.set_size('medium')
        self.xlabel_text = xlabel
        if self.ax is not None:
            self.xlabel_artist = self.ax.set_xlabel(xlabel,color = self.palette['xlabel'],
                fontsize='medium',
                fontfamily=fontprop_medium.get_family())
        if self.xlabel_artist is not None:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    self.xlabel_width = self.xlabel_artist.get_window_extent(renderer=self.fig.canvas.get_renderer()).width
            except Exception: # pylint: disable=broad-except
                pass
            try:
                self.xlabel_artist.set_in_layout(False) # remove x-axis labels from tight_layout calculation
            except Exception: # pylint: disable=broad-except # set_in_layout not available in mpl<3.x
                pass

    def setProfileBackgroundTitle(self,backgroundtitle):
        suptitleX = 1
        try:
            if self.ax is not None:
                ax_width = self.ax.get_window_extent(renderer=self.fig.canvas.get_renderer()).width # total width of axis in display coordinates
                ax_begin = self.ax.transAxes.transform((0,0))[0] # left of axis in display coordinates
                suptitleX = self.fig.transFigure.inverted().transform((ax_width + ax_begin,0))[0]
        except Exception: # pylint: disable=broad-except
            pass

        self.background_title_width = 0
        backgroundtitle = backgroundtitle.strip()
        if backgroundtitle != '':
            if self.graphfont in [1,9]: # if selected font is Humor we translate the unicode title into pure ascii
                backgroundtitle = self.__to_ascii(backgroundtitle)
            backgroundtitle = f'\n{abbrevString(backgroundtitle, 32)}'

        self.l_subtitle = self.fig.suptitle(backgroundtitle,
                horizontalalignment='right',verticalalignment='top',
                fontsize='x-small',
                x=suptitleX,y=1,
                color=(self.palette['title_focus'] if (self.backgroundprofile is not None and self.backgroundPlaybackEvents) else self.palette['title']))
        try:
            self.l_subtitle.set_in_layout(False)  # remove title from tight_layout calculation
        except Exception: # pylint: disable=broad-except  # set_in_layout not available in mpl<3.x
            pass
        try:
            if len(backgroundtitle)>0:
                self.background_title_width = self.l_subtitle.get_window_extent(renderer=self.fig.canvas.get_renderer()).width
            else:
                self.background_title_width = 0
        except Exception: # pylint: disable=broad-except
            self.background_title_width = 0

    # if updatebackground is True, the profileDataSemaphore is caught and updatebackground() is called
    @pyqtSlot(str,bool)
    def setProfileTitle(self,title:str,updatebackground=False):
        if ((self.flagon and not self.aw.curFile) or self.flagstart):
            bprefix = self.batchprefix
            bnr = self.batchcounter + 1
        else:
            bprefix = self.roastbatchprefix
            bnr = self.roastbatchnr
        if bnr != 0 and title != '':
            title = f'{bprefix}{str(bnr)} {title}'
        elif bnr == 0 and title != '' and title != self.title != QApplication.translate('Scope Title', 'Roaster Scope') and bprefix != '':
            title = f'{bprefix} {title}'

        if self.graphfont in [1,9]: # if selected font is Humor or Dijkstra we translate the unicode title into pure ascii
            title = self.__to_ascii(title)

        self.title_text = self.aw.arabicReshape(title.strip())
        if self.ax is not None:
            self.title_artist = self.ax.set_title(self.title_text, color=self.palette['title'], loc='left',
                        fontsize='xx-large',
                        horizontalalignment='left',verticalalignment='top',x=0)
        if self.title_artist is not None:
            try: # this one seems not to work for titles, subtitles and axis!?
                self.title_artist.set_in_layout(False) # remove title from tight_layout calculation
            except Exception: # pylint: disable=broad-except # set_in_layout not available in mpl<3.x
                pass
            try:
                self.title_width = self.title_artist.get_window_extent(renderer=self.fig.canvas.get_renderer()).width
            except Exception: # pylint: disable=broad-except
                pass

        if updatebackground:
            #### lock shared resources #####
            self.profileDataSemaphore.acquire(1)
            try:
                self.updateBackground()
            finally:
                if self.profileDataSemaphore.available() < 1:
                    self.profileDataSemaphore.release(1)

    # resize the given list to the length ln by cutting away elements or padding with trailing -1 items
    # used to resize temperature data to the length of the corresponding timex times
    @staticmethod
    def resizeList(lst, ln):
        if lst is None:
            return None
        return (lst + [-1]*(ln-len(lst)))[:ln]

    def drawET(self,temp):
        if self.ETcurve and self.ax is not None:
            try:
                if self.l_temp1 is not None:
                    self.l_temp1.remove()
            except Exception: # pylint: disable=broad-except
                pass
            # don't draw -1:
#            temp = [r if r !=-1 else None for r in temp]
            temp = numpy.ma.masked_where(temp == -1, temp)
            self.l_temp1, = self.ax.plot(
                self.timex,
                temp,
                markersize=self.ETmarkersize,
                marker=self.ETmarker,
                sketch_params=None,
                path_effects=[PathEffects.withStroke(linewidth=self.ETlinewidth+self.patheffects,foreground=self.palette['background'])],
                linewidth=self.ETlinewidth,
                linestyle=self.ETlinestyle,
                drawstyle=self.ETdrawstyle,
                color=self.palette['et'],
                label=self.aw.arabicReshape(QApplication.translate('Label', 'ET')))

    def drawBT(self,temp):
        if self.BTcurve and self.ax is not None:
            try:
                if self.l_temp2 is not None:
                    self.l_temp2.remove()
            except Exception: # pylint: disable=broad-except
                pass
            # don't draw -1:
#            temp = [r if r !=-1 else None for r in temp]
            temp = numpy.ma.masked_where(temp == -1, temp)
            self.l_temp2, = self.ax.plot(
                self.timex,
                temp,
                markersize=self.BTmarkersize,
                marker=self.BTmarker,
                sketch_params=None,
                path_effects=[PathEffects.withStroke(linewidth=self.BTlinewidth+self.patheffects,foreground=self.palette['background'])],
                linewidth=self.BTlinewidth,
                linestyle=self.BTlinestyle,
                drawstyle=self.BTdrawstyle,
                color=self.palette['bt'],
                label=self.aw.arabicReshape(QApplication.translate('Label', 'BT')))

    def drawDeltaET(self,trans,start,end):
        if self.DeltaETflag and self.ax is not None:
            try:
                if self.l_delta1 is not None:
                    self.l_delta1.remove()
            except Exception: # pylint: disable=broad-except
                pass
            self.l_delta1, = self.ax.plot(
                    [],
                    [],
                    transform=trans,
                    markersize=self.ETdeltamarkersize,
                    marker=self.ETdeltamarker,
                    sketch_params=None,
                    path_effects=[PathEffects.withStroke(linewidth=self.ETdeltalinewidth+self.patheffects,foreground=self.palette['background'])],
                    linewidth=self.ETdeltalinewidth,
                    linestyle=self.ETdeltalinestyle,
                    drawstyle=self.ETdeltadrawstyle,
                    color=self.palette['deltaet'],
                    label=self.aw.arabicReshape(f'{deltaLabelUTF8}{QApplication.translate("Label", "ET")}'))
            if start < end < len(self.timex):
                self.l_delta1.set_data(self.timex[start:end],self.delta1[start:end])
            else:
                self.l_delta1.set_data([],[])

    def drawDeltaBT(self,trans,start,end):
        if self.DeltaBTflag and self.ax is not None:
            try:
                if self.l_delta2 is not None:
                    self.l_delta2.remove()
            except Exception: # pylint: disable=broad-except
                pass
            self.l_delta2, = self.ax.plot(
                    [],
                    [],
                    transform=trans,
                    markersize=self.BTdeltamarkersize,
                    marker=self.BTdeltamarker,
                    sketch_params=None,
                    path_effects=[PathEffects.withStroke(linewidth=self.BTdeltalinewidth+self.patheffects,foreground=self.palette['background'])],
                    linewidth=self.BTdeltalinewidth,
                    linestyle=self.BTdeltalinestyle,
                    drawstyle=self.BTdeltadrawstyle,
                    color=self.palette['deltabt'],
                    label=self.aw.arabicReshape(f'{deltaLabelUTF8}{QApplication.translate("Label", "BT")}'))
            if start < end < len(self.timex):
                self.l_delta2.set_data(self.timex[start:end],self.delta2[start:end])
            else:
                self.l_delta2.set_data([],[])

    # if profileDataSemaphore lock cannot be fetched the redraw is not performed
    def lazyredraw(self, recomputeAllDeltas=True, smooth=True,sampling=False):
        gotlock = self.profileDataSemaphore.tryAcquire(1,0) # we try to catch a lock if available but we do not wait, if we fail we just skip this redraw round (prevents stacking of waiting calls)
        if gotlock:
            try:
                self.redraw(recomputeAllDeltas,smooth,sampling,takelock=False)
            finally:
                if self.profileDataSemaphore.available() < 1:
                    self.profileDataSemaphore.release(1)
        else:
            _log.info('lazyredraw(): failed to get profileDataSemaphore lock')

    def smoothETBT(self,smooth,recomputeAllDeltas,sampling,decay_smoothing_p):
        try:
            # we resample the temperatures to regular interval timestamps
            if self.timex is not None and self.timex and len(self.timex)>1:
                timex_lin = numpy.linspace(self.timex[0],self.timex[-1],len(self.timex))
            else:
                timex_lin = None
            temp1_nogaps = fill_gaps(self.resizeList(self.temp1,len(self.timex)))
            temp2_nogaps = fill_gaps(self.resizeList(self.temp2,len(self.timex)))

            if smooth or len(self.stemp1) != len(self.timex):
                if self.flagon: # we don't smooth, but remove the dropouts
                    self.stemp1 = temp1_nogaps
                else:
                    self.stemp1 = list(self.smooth_list(self.timex,temp1_nogaps,window_len=self.curvefilter,decay_smoothing=decay_smoothing_p,a_lin=timex_lin))
            if smooth or len(self.stemp2) != len(self.timex):
                if self.flagon:  # we don't smooth, but remove the dropouts
                    self.stemp2 = temp2_nogaps
                else:
                    self.stemp2 = list(self.smooth_list(self.timex,temp2_nogaps,window_len=self.curvefilter,decay_smoothing=decay_smoothing_p,a_lin=timex_lin))

            #populate delta ET (self.delta1) and delta BT (self.delta2)
            # calculated here to be available for parsepecialeventannotations(). the curve are plotted later.
            if (recomputeAllDeltas or (self.DeltaETflag and self.delta1 == []) or (self.DeltaBTflag and self.delta2 == [])) and not self.flagstart: # during recording we don't recompute the deltas
                cf = self.curvefilter #*2 # we smooth twice as heavy for PID/RoR calcuation as for normal curve smoothing
                decay_smoothing_p = not self.optimalSmoothing or sampling or self.flagon
                t1 = self.smooth_list(self.timex,temp1_nogaps,window_len=cf,decay_smoothing=decay_smoothing_p,a_lin=timex_lin)
                t2 = self.smooth_list(self.timex,temp2_nogaps,window_len=cf,decay_smoothing=decay_smoothing_p,a_lin=timex_lin)
                # we start RoR computation 10 readings after CHARGE to avoid this initial peak
                if self.timeindex[0]>-1:
                    RoR_start = min(self.timeindex[0]+10, len(self.timex)-1)
                else:
                    RoR_start = -1
                d1, d2 = self.recomputeDeltas(self.timex,RoR_start,self.timeindex[6],t1,t2,optimalSmoothing=not decay_smoothing_p,timex_lin=timex_lin)
                if d1 is not None and d2 is not None:
                    self.delta1 = d1
                    self.delta2 = d2
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' smoothETBT() anno {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))

    def smoothETBTBkgnd(self,recomputeAllDeltas,decay_smoothing_p):
        try:
            if recomputeAllDeltas or (self.DeltaETBflag and self.delta1B == []) or (self.DeltaBTBflag and self.delta2B == []):

                # we resample the temperatures to regular interval timestamps
                if self.timeB is not None and self.timeB:
                    timeB_lin = numpy.linspace(self.timeB[0],self.timeB[-1],len(self.timeB))
                else:
                    timeB_lin = None

                # we populate temporary smoothed ET/BT data arrays
                cf = self.curvefilter #*2 # we smooth twice as heavy for PID/RoR calcuation as for normal curve smoothing
                st1 = self.smooth_list(self.timeB,fill_gaps(self.temp1B),window_len=cf,decay_smoothing=decay_smoothing_p,a_lin=timeB_lin)
                st2 = self.smooth_list(self.timeB,fill_gaps(self.temp2B),window_len=cf,decay_smoothing=decay_smoothing_p,a_lin=timeB_lin)
                # we start RoR computation 10 readings after CHARGE to avoid this initial peak
                if self.timeindexB[0]>-1:
                    RoRstart = min(self.timeindexB[0]+10, len(self.timeB)-1)
                else:
                    RoRstart = -1
                if self.background_profile_sampling_interval is None:
                    dsET = None
                else:
                    dsET = max(1,int(round(self.deltaETspan / self.background_profile_sampling_interval)))
                if self.background_profile_sampling_interval is None:
                    dsBT = None
                else:
                    dsBT = max(1,int(round(self.deltaBTspan / self.background_profile_sampling_interval)))
                d1B, d2B = self.recomputeDeltas(self.timeB,RoRstart,self.timeindexB[6],st1,st2,optimalSmoothing=not decay_smoothing_p,timex_lin=timeB_lin,deltaETsamples=dsET,deltaBTsamples=dsBT)
                if d1B is not None and d2B is not None:
                    self.delta1B = d1B
                    self.delta2B = d2B
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' smmothETBTBkgnd() anno {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))

    def twoAxisMode(self):
        return (self.DeltaETflag or self.DeltaBTflag or
                    (self.background and self.backgroundprofile is not None and (self.DeltaETBflag or self.DeltaBTBflag)))

    #Redraws data
    # if recomputeAllDeltas, the delta arrays; if smooth the smoothed line arrays are recomputed (incl. those of the background curves)
    def redraw(self, recomputeAllDeltas=True, smooth=True, sampling=False, takelock=True, forceRenewAxis=False): # pyright: ignore # Code is too complex to analyze; reduce complexity by refactoring into subroutines or reducing conditional code paths (reportGeneralTypeIssues)
        if self.designerflag:
            self.redrawdesigner(force=True)
        elif self.aw.comparator is not None:
            self.aw.comparator.redraw()
            self.aw.qpc.redraw_phases()
        else:
            try:
                #### lock shared resources   ####
                if takelock:
                    self.profileDataSemaphore.acquire(1)
                try:
                    # prevent interleaving of updateBackground() and redraw()
                    self.updateBackgroundSemaphore.acquire(1)

                    if self.flagon:
                        # on redraw during recording we reset the linecounts to avoid issues with projection lines
                        self.resetlines()

                    decay_smoothing_p = (not self.optimalSmoothing) or sampling or self.flagon

                    rcParams['path.effects'] = []
                    scale = 1 if self.graphstyle == 1 else 0
                    length = 700 # 100 (128 the default)
                    randomness = 12 # 2 (16 default)
                    rcParams['path.sketch'] = (scale, length, randomness)

                    rcParams['axes.linewidth'] = 0.8 # 1.5
                    rcParams['xtick.major.size'] = 6 # 8
                    rcParams['xtick.major.width'] = 1
    #                rcParams['xtick.major.pad'] = 5
                    rcParams['xtick.minor.width'] = 0.8

                    rcParams['ytick.major.size'] = 4 # 8
                    rcParams['ytick.major.width'] = 1
    #                rcParams['ytick.major.pad'] = 5
                    rcParams['ytick.minor.width'] = 1

                    rcParams['xtick.color'] = self.palette['xlabel']
                    rcParams['ytick.color'] = self.palette['ylabel']

                    #rcParams['text.antialiased'] = True

                    if forceRenewAxis:
                        self.fig.clf()
                    if self.ax is None or forceRenewAxis:
                        self.ax = self.fig.add_subplot(111,facecolor=self.palette['background'])
                    if self.delta_ax is None or forceRenewAxis:
                        self.delta_ax = self.ax.twinx()

                    # instead to remove and regenerate the axis object (we just clear and reuse it)

                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        self.ax.clear()
                    self.ax.set_facecolor(self.palette['background'])
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        self.delta_ax.clear()
                    self.ax.set_yticks([])
                    self.ax.set_xticks([])
                    self.delta_ax.set_yticks([])
                    self.delta_ax.set_xticks([])

                    self.ax.set_ylim(self.ylimit_min, self.ylimit)
                    self.ax.set_autoscale_on(False)

                    prop = self.aw.mpl_fontproperties.copy()
                    prop.set_size('small')
                    fontprop_small = self.aw.mpl_fontproperties.copy()
                    fontprop_small.set_size('xx-small')

                    grid_axis = None
                    if self.temp_grid and self.time_grid:
                        grid_axis = 'both'
                    elif self.temp_grid:
                        grid_axis = 'y'
                    elif self.time_grid:
                        grid_axis = 'x'
                    if grid_axis is not None:
                        self.ax.grid(True,axis=grid_axis,color=self.palette['grid'],linestyle=self.gridstyles[self.gridlinestyle],linewidth=self.gridthickness,alpha=self.gridalpha,sketch_params=0,path_effects=[])

                    if self.flagstart and not self.title_show_always:
                        self.setProfileTitle('')
                    else:
                        self.setProfileTitle(self.title)

                    # extra event names with substitution of event names applied
                    extraname1_subst = self.extraname1[:]
                    extraname2_subst = self.extraname2[:]
                    for i in range(len(self.extratimex)):
                        try:
                            extraname1_subst[i] = extraname1_subst[i].format(self.etypes[0],self.etypes[1],self.etypes[2],self.etypes[3])
                        except Exception: # pylint: disable=broad-except
                            pass
                        try:
                            extraname2_subst[i] = extraname2_subst[i].format(self.etypes[0],self.etypes[1],self.etypes[2],self.etypes[3])
                        except Exception: # pylint: disable=broad-except
                            pass

                    if self.flagstart or self.ygrid == 0:
                        y_label = self.ax.set_ylabel('')
                    else:
                        y_label = self.ax.set_ylabel(self.mode,color=self.palette['ylabel'],rotation=0,labelpad=10,
                                fontsize='medium',
                                fontfamily=prop.get_family())
                    if self.flagstart or self.xgrid == 0:
                        self.set_xlabel('')
                    else:
                        self.set_xlabel(self.aw.arabicReshape(QApplication.translate('Label', 'min','abbrev. of minutes')))

                    try:
                        y_label.set_in_layout(False) # remove y-axis labels from tight_layout calculation
                    except Exception: # pylint: disable=broad-except # set_in_layout not available in mpl<3.x
                        pass

                    two_ax_mode = (self.twoAxisMode() or
                        any(self.aw.extraDelta1[:len(self.extratimex)]) or
                        any(self.aw.extraDelta2[:len(self.extratimex)]))

                    titleB = ''
                    if not ((self.flagstart and not self.title_show_always) or self.title is None or self.title.strip() == ''):
                        if self.backgroundprofile is not None:
                            if self.roastbatchnrB == 0:
                                titleB = self.titleB
                            else:
                                titleB = f'{self.roastbatchprefixB}{self.roastbatchnrB} {self.titleB}'
                        elif __release_sponsor_domain__:
                            sponsor = QApplication.translate('About','sponsored by {}').format(__release_sponsor_domain__)
                            titleB = f'\n{sponsor}'

                    tick_dir = 'in' if self.flagon or sampling else 'inout'
                    self.ax.tick_params(\
                        axis='x',           # changes apply to the x-axis
                        which='both',       # both major and minor ticks are affected
                        bottom=True,        # ticks along the bottom edge are on
                        top=False,          # ticks along the top edge are off
                        direction=tick_dir,
                        labelbottom=True)   # labels along the bottom edge are on
                    self.ax.tick_params(\
                        axis='y',           # changes apply to the y-axis
                        which='both',       # both major and minor ticks are affected
                        right=False,
                        bottom=True,        # ticks along the bottom edge are on
                        top=False,          # ticks along the top edge are off
                        direction=tick_dir,
                        labelbottom=True)   # labels along the bottom edge are on

                    # format temperature as int, not float in the cursor position coordinate indicator
                    self.ax.fmt_ydata = self.fmt_data
                    self.ax.fmt_xdata = self.fmt_timedata

                    self.ax.set_zorder(self.delta_ax.get_zorder()+1) # put ax in front of delta_ax (which remains empty!)
                    if two_ax_mode:
                        #create a second set of axes in the same position as self.ax
                        self.delta_ax.tick_params(\
                            axis='y',           # changes apply to the y-axis
                            which='both',       # both major and minor ticks are affected
                            left=False,         # ticks along the left edge are off
                            bottom=False,       # ticks along the bottom edge are off
                            top=False,          # ticks along the top edge are off
                            direction='inout', # tick_dir # this does not work as ticks are not drawn at all in ON mode with this!?
                            labelright=True,
                            labelleft=False,
                            labelbottom=False)   # labels along the bottom edge are off

                        self.ax.patch.set_visible(True)
                        if self.flagstart or self.zgrid == 0:
                            y_label = self.delta_ax.set_ylabel('')
                        else:
                            y_label = self.delta_ax.set_ylabel(f'{self.mode}{self.aw.arabicReshape("/min")}',
                                color = self.palette['ylabel'],
                                fontsize='medium',
                                fontfamily=prop.get_family()
                                )
                        self.delta_ax.yaxis.set_label_position('right')
                        try:
                            y_label.set_in_layout(False) # remove y-axis labels from tight_layout calculation
                        except Exception: # pylint: disable=broad-except # set_in_layout not available in mpl<3.x
                            pass
                        self.delta_ax.set_ylim(self.zlimit_min,self.zlimit)
                        if self.zgrid > 0:
                            self.delta_ax.yaxis.set_major_locator(ticker.MultipleLocator(self.zgrid))
                            self.delta_ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
                            for ii in self.delta_ax.get_yticklines():
                                ii.set_markersize(10)
                            for iiii in self.delta_ax.yaxis.get_minorticklines():
                                iiii.set_markersize(5)
                            for label in self.delta_ax.get_yticklabels() :
                                label.set_fontsize('small')
                            if not self.LCDdecimalplaces:
                                self.delta_ax.minorticks_off()

                        # translate y-coordinate from delta into temp range to ensure the cursor position display (x,y) coordinate in the temp axis
                        self.delta_ax.fmt_ydata = self.fmt_data
                        self.delta_ax.fmt_xdata = self.fmt_timedata
                    #put a right tick on the graph
                    else:
                        self.ax.tick_params(\
                            axis='y',
                            which='both',
                            right=False,
                            labelright=False)

                    self.ax.spines['top'].set_color('0.40')
                    self.ax.spines['bottom'].set_color('0.40')
                    self.ax.spines['left'].set_color('0.40')
                    self.ax.spines['right'].set_color('0.40')

                    self.ax.spines.top.set_visible(self.xgrid != 0 and self.ygrid != 0 and self.zgrid != 0)
                    self.ax.spines.bottom.set_visible(self.xgrid != 0)
                    self.ax.spines.left.set_visible(self.ygrid != 0)
                    self.ax.spines.right.set_visible(self.zgrid != 0)

                    try:
                        if self.l_eventtype1dots is not None:
                            self.l_eventtype1dots.remove()
                    except Exception: # pylint: disable=broad-except
                        pass
                    try:
                        if self.l_eventtype2dots is not None:
                            self.l_eventtype2dots.remove()
                    except Exception: # pylint: disable=broad-except
                        pass
                    try:
                        if self.l_eventtype3dots is not None:
                            self.l_eventtype3dots.remove()
                    except Exception: # pylint: disable=broad-except
                        pass
                    try:
                        if self.l_eventtype4dots is not None:
                            self.l_eventtype4dots.remove()
                    except Exception: # pylint: disable=broad-except
                        pass
                    self.l_eventtype1dots = None
                    self.l_eventtype2dots = None
                    self.l_eventtype3dots = None
                    self.l_eventtype4dots = None
                    self.l_eteventannos = []
                    self.l_bteventannos = []
                    self.l_eventtype1annos = []
                    self.l_eventtype2annos = []
                    self.l_eventtype3annos = []
                    self.l_eventtype4annos = []
                    self.l_backgroundeventtype1dots = None
                    self.l_backgroundeventtype2dots = None
                    self.l_backgroundeventtype3dots = None
                    self.l_backgroundeventtype4dots = None

                    if self.graphstyle:
                        self.ax.spines['left'].set_sketch_params(scale, length, randomness)
                        self.ax.spines['bottom'].set_sketch_params(scale, length, randomness)
                        self.ax.spines['right'].set_sketch_params(scale, length, randomness)
                        self.ax.spines['top'].set_sketch_params(scale, length, randomness)
                    # hide all spines from the delta_ax
    #                self.delta_ax.spines['left'].set_visible(False)
    #                self.delta_ax.spines['bottom'].set_visible(False)
    #                self.delta_ax.spines['right'].set_visible(False)
    #                self.delta_ax.spines['top'].set_visible(False)
                    self.delta_ax.set_frame_on(False) # hide all splines (as the four lines above)

                    if self.ygrid > 0:
                        self.ax.yaxis.set_major_locator(ticker.MultipleLocator(self.ygrid))
                        self.ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
                        for j in self.ax.get_yticklines():
                            j.set_markersize(10)
                        for m in self.ax.yaxis.get_minorticklines():
                            m.set_markersize(5)
    #                else: # hide all spines from the ax
    #                    self.ax.spines['left'].set_visible(False)
    #                    self.ax.spines['bottom'].set_visible(False)
    #                    self.ax.spines['right'].set_visible(False)
    #                    self.ax.spines['top'].set_visible(False)

                    #update X ticks, labels, and rotating_colors
                    self.xaxistosm(redraw=False)

                    for label in self.ax.get_xticklabels() :
    # labels not rendered in PDF exports on MPL 3.4 if fontproperties are set:
    #                    label.set_fontproperties(prop)
                        label.set_fontsize('small')
                    for label in self.ax.get_yticklabels() :
    # labels not rendered in PDF exports on MPL 3.4 if fontproperties are set:
    #                    label.set_fontproperties(prop)
                        label.set_fontsize('small')

                    rcParams['path.sketch'] = (0,0,0)
                    trans = transforms.blended_transform_factory(self.ax.transAxes,self.ax.transData)

                    #draw water marks for dry phase region, mid phase region, and finish phase region
                    if self.watermarksflag:
                        rect1 = patches.Rectangle((0,self.phases[0]), width=1, height=(self.phases[1]-self.phases[0]),
                                                  transform=trans, color=self.palette['rect1'],alpha=0.15)
                        rect2 = patches.Rectangle((0,self.phases[1]), width=1, height=(self.phases[2]-self.phases[1]),
                                                  transform=trans, color=self.palette['rect2'],alpha=0.15)
                        rect3 = patches.Rectangle((0,self.phases[2]), width=1, height=(self.phases[3] - self.phases[2]),
                                                  transform=trans, color=self.palette['rect3'],alpha=0.15)
                        self.ax.add_patch(rect1)
                        self.ax.add_patch(rect2)
                        self.ax.add_patch(rect3)

                    #if self.eventsGraphflag == 0 then that means don't plot event bars

                    step:float
                    if self.eventsGraphflag == 1: #plot event bars by type
                        # make blended transformations to help identify EVENT types
                        if self.mode == 'C':
                            step = 5
                            start = 20
                        else:
                            step = 10
                            start = 60
                        jump = 20.
                        for i in range(4):
                            if self.showEtypes[3-i]:
                                rectEvent = patches.Rectangle((0,self.phases[0]-start-jump), width=1, height = step, transform=trans, color=self.palette['rect5'],alpha=.15)
                                self.ax.add_patch(rectEvent)
                            if self.mode == 'C':
                                jump -= 10.
                            else:
                                jump -= 20.

                    #plot events bars by value
                    elif self.eventsGraphflag in [2,3,4]: # 2: step lines, 3: step+, 4: combo
                        # make blended transformations to help identify EVENT types
                        if self.clampEvents:
                            top = 100
                            bot = 0
                        else:
                            if self.step100temp is None:
                                top = self.phases[0]
                            else:
                                top = self.step100temp
                            bot = self.ylimit_min
                        step = (top-bot)/10
                        start = top - bot
                        small_step = step/10 # as we have 100 items
                        jump = 0.

                        for j in range(110):
                            i = int(j/10)
                            barposition = top - start - jump
                            if i == j/10.:
                                c1 = 'rect5'
                                c2 = 'background'
                                if i == 0:
                                    color = self.palette[c1] #self.palette["rect3"] # brown
                                elif i%2:
                                    color = self.palette[c2] #self.palette["rect2"] # orange # the uneven ones
                                else:
                                    color = self.palette[c1] #self.palette["rect1"] # green # the even ones
                                if i != 10: # don't draw the first and the last bar in clamp mode
                                    rectEvent = patches.Rectangle((0,barposition), width=1, height = step, transform=trans, color=color,alpha=.15)
                                    self.ax.add_patch(rectEvent)
                            self.eventpositionbars[j] = barposition
                            jump -= small_step

                    rcParams['path.sketch'] = (scale, length, randomness)

                    #check BACKGROUND flag
                    if self.background and self.backgroundprofile is not None:
                        if smooth:
                            # re-smooth background curves
                            tb = self.timeB
                            t1 = self.temp1B
                            t2 = self.temp2B
                            if tb is not None and tb:
                                tb_lin = numpy.linspace(tb[0],tb[-1],len(tb))
                            else:
                                tb_lin = None
                            self.stemp1B = self.smooth_list(tb,fill_gaps(t1),window_len=self.curvefilter,decay_smoothing=decay_smoothing_p,a_lin=tb_lin)
                            self.stemp2B = self.smooth_list(tb,fill_gaps(t2),window_len=self.curvefilter,decay_smoothing=decay_smoothing_p,a_lin=tb_lin)

                        self.l_background_annotations = []
                        #check to see if there is both a profile loaded and a background loaded
                        if self.backmoveflag != 0:
                            self.timealign(redraw=False,recompute=False)

                        bcharge_idx = 0
                        if self.timeindexB[0] > -1:
                            bcharge_idx = self.timeindexB[0]
                        bdrop_idx = len(self.timeB)-1
                        if self.timeindexB[6] > 0:
                            bdrop_idx = self.timeindexB[6]

                        #draw one extra device on background stemp1BX
                        if self.xtcurveidx > 0:
                            idx3 = self.xtcurveidx - 1
                            n3 = idx3 // 2
                            if len(self.stemp1BX) > n3 and len(self.stemp2BX) > n3 and len(self.extratimexB) > n3:
                                if smooth:
                                    # re-smooth the extra background curve
                                    tx = self.extratimexB[n3]
                                    if tx is not None and tx:
                                        tx_lin = numpy.linspace(tx[0],tx[-1],len(tx))
                                    else:
                                        tx_lin = None
                                if self.xtcurveidx % 2:
                                    if self.temp1Bdelta[n3]:
                                        trans = self.delta_ax.transData
                                    else:
                                        trans = self.ax.transData
                                    if smooth:
                                        self.stemp1BX[n3] = self.smooth_list(tx,fill_gaps(self.temp1BX[n3]),window_len=self.curvefilter,decay_smoothing=decay_smoothing_p,a_lin=tx_lin)
                                    stemp3B = self.stemp1BX[n3]
                                else:
                                    if self.temp2Bdelta[n3]:
                                        trans = self.delta_ax.transData
                                    else:
                                        trans = self.ax.transData
                                    if smooth:
                                        self.stemp2BX[n3] = self.smooth_list(tx,fill_gaps(self.temp2BX[n3]),window_len=self.curvefilter,decay_smoothing=decay_smoothing_p,a_lin=tx_lin)
                                    stemp3B = self.stemp2BX[n3]
                                if not self.backgroundShowFullflag:
                                    if not self.autotimex or self.autotimexMode == 0:
                                        stemp3B = numpy.concatenate((
                                            numpy.full(bcharge_idx, numpy.nan, dtype=numpy.double),
                                            stemp3B[bcharge_idx:bdrop_idx+1],
                                            numpy.full(len(self.timeB)-bdrop_idx-1, numpy.nan, dtype=numpy.double)))
                                    else:
                                        stemp3B = numpy.concatenate((
                                            stemp3B[0:bdrop_idx+1],
                                            numpy.full(len(self.timeB)-bdrop_idx-1, numpy.nan, dtype=numpy.double)))
                                try:
                                    if self.l_back3 is not None:
                                        self.l_back3.remove()
                                except Exception: # pylint: disable=broad-except
                                    pass
                                # don't draw -1:
                                stemp3B = numpy.array(stemp3B, dtype=numpy.double)
                                self.l_back3, = self.ax.plot(self.extratimexB[n3], stemp3B, markersize=self.XTbackmarkersize,marker=self.XTbackmarker,
                                                            sketch_params=None,path_effects=[],transform=trans,
                                                            linewidth=self.XTbacklinewidth,linestyle=self.XTbacklinestyle,drawstyle=self.XTbackdrawstyle,color=self.backgroundxtcolor,
                                                            alpha=self.backgroundalpha,label=self.aw.arabicReshape(QApplication.translate('Label', 'BackgroundXT')))
                        if self.ytcurveidx > 0:
                            idx4 = self.ytcurveidx - 1
                            n4 = idx4 // 2
                            if len(self.stemp1BX) > n4 and len(self.stemp2BX) > n4 and len(self.extratimexB) > n4:
                                if smooth:
                                    # re-smooth the extra background curve
                                    tx = self.extratimexB[n4]
                                    if tx is not None and tx:
                                        tx_lin = numpy.linspace(tx[0],tx[-1],len(tx))
                                    else:
                                        tx_lin = None
                                if self.ytcurveidx % 2:
                                    if self.temp1Bdelta[n4]:
                                        trans = self.delta_ax.transData
                                    else:
                                        trans = self.ax.transData
                                    if smooth:
                                        self.stemp1BX[n4] = self.smooth_list(tx,fill_gaps(self.temp1BX[n4]),window_len=self.curvefilter,decay_smoothing=decay_smoothing_p,a_lin=tx_lin)
                                    stemp4B = self.stemp1BX[n4]
                                else:
                                    if self.temp2Bdelta[n4]:
                                        trans = self.delta_ax.transData
                                    else:
                                        trans = self.ax.transData
                                    if smooth:
                                        self.stemp2BX[n4] = self.smooth_list(tx,fill_gaps(self.temp2BX[n4]),window_len=self.curvefilter,decay_smoothing=decay_smoothing_p,a_lin=tx_lin)
                                    stemp4B = self.stemp2BX[n4]
                                if not self.backgroundShowFullflag:
                                    if not self.autotimex or self.autotimexMode == 0:
                                        stemp4B = numpy.concatenate((
                                            numpy.full(bcharge_idx, numpy.nan, dtype=numpy.double),
                                            stemp4B[bcharge_idx:bdrop_idx+1],
                                            numpy.full(len(self.timeB)-bdrop_idx-1, numpy.nan, dtype=numpy.double)))
                                    else:
                                        stemp4B = numpy.concatenate((
                                            stemp4B[0:bdrop_idx+1],
                                            numpy.full(len(self.timeB)-bdrop_idx-1, numpy.nan, dtype=numpy.double)))
                                try:
                                    if self.l_back4 is not None:
                                        self.l_back4.remove()
                                except Exception: # pylint: disable=broad-except
                                    pass
                                # don't draw -1:
                                stemp4B = numpy.array(stemp4B, dtype=numpy.double)
                                self.l_back4, = self.ax.plot(self.extratimexB[n4], stemp4B, markersize=self.YTbackmarkersize,marker=self.YTbackmarker,
                                                            sketch_params=None,path_effects=[],transform=trans,
                                                            linewidth=self.YTbacklinewidth,linestyle=self.YTbacklinestyle,drawstyle=self.YTbackdrawstyle,color=self.backgroundytcolor,
                                                            alpha=self.backgroundalpha,label=self.aw.arabicReshape(QApplication.translate('Label', 'BackgroundYT')))


                        #draw background
                        if self.backgroundETcurve:
                            if self.backgroundShowFullflag:
                                temp_etb = self.stemp1B
                            elif not self.autotimex or self.autotimexMode == 0:
                                # only draw background curve from CHARGE to DROP
                                temp_etb = numpy.concatenate((
                                    numpy.full(bcharge_idx, numpy.nan, dtype=numpy.double),
                                    self.stemp1B[bcharge_idx:bdrop_idx+1],
                                    numpy.full(len(self.timeB)-bdrop_idx-1, numpy.nan, dtype=numpy.double)))
                            else:
                                temp_etb = numpy.concatenate((
                                    self.stemp1B[0:bdrop_idx+1],
                                    numpy.full(len(self.timeB)-bdrop_idx-1, numpy.nan, dtype=numpy.double)))
                        else:
                            temp_etb = numpy.full(len(self.timeB), numpy.nan, dtype=numpy.double)
                        try:
                            if self.l_back1 is not None:
                                self.l_back1.remove()
                        except Exception: # pylint: disable=broad-except
                            pass
                        # don't draw -1:
#                        temp_etb = [r if r !=-1 else None for r in temp_etb]
                        temp_etb = numpy.ma.masked_where(temp_etb == -1, temp_etb)
                        self.l_back1, = self.ax.plot(self.timeB,temp_etb,markersize=self.ETbackmarkersize,marker=self.ETbackmarker,
                                                    sketch_params=None,path_effects=[],
                                                    linewidth=self.ETbacklinewidth,linestyle=self.ETbacklinestyle,drawstyle=self.ETbackdrawstyle,color=self.backgroundmetcolor,
                                                    alpha=self.backgroundalpha,label=self.aw.arabicReshape(QApplication.translate('Label', 'BackgroundET')))
                        if self.backgroundBTcurve:
                            if self.backgroundShowFullflag:
                                temp_btb = self.stemp2B
                            elif not self.autotimex or self.autotimexMode == 0:
                                # only draw background curve from CHARGE to DROP
                                temp_btb = numpy.concatenate((
                                    numpy.full(bcharge_idx, numpy.nan, dtype=numpy.double),
                                    self.stemp2B[bcharge_idx:bdrop_idx+1],
                                    numpy.full(len(self.timeB)-bdrop_idx-1, numpy.nan, dtype=numpy.double)))
                            else:
                                temp_btb = numpy.concatenate((
                                    self.stemp2B[0:bdrop_idx+1],
                                    numpy.full(len(self.timeB)-bdrop_idx-1, numpy.nan, dtype=numpy.double)))

                        else:
                            temp_btb = numpy.full(len(self.timeB), numpy.nan, dtype=numpy.double)
                        try:
                            if self.l_back2 is not None:
                                self.l_back2.remove()
                        except Exception: # pylint: disable=broad-except
                            pass
                        # don't draw -1:
#                        temp_btb = [r if r !=-1 else None for r in temp_btb]
                        temp_btb = numpy.ma.masked_where(temp_btb == -1, temp_btb)
                        self.l_back2, = self.ax.plot(self.timeB, temp_btb,markersize=self.BTbackmarkersize,marker=self.BTbackmarker,
                                                    linewidth=self.BTbacklinewidth,linestyle=self.BTbacklinestyle,drawstyle=self.BTbackdrawstyle,color=self.backgroundbtcolor,
                                                    sketch_params=None,path_effects=[],
                                                    alpha=self.backgroundalpha,label=self.aw.arabicReshape(QApplication.translate('Label', 'BackgroundBT')))

                        self.smoothETBTBkgnd(recomputeAllDeltas,decay_smoothing_p)

                        #populate background delta ET (self.delta1B) and delta BT (self.delta2B)
                        ##### DeltaETB,DeltaBTB curves
                        if (self.DeltaETBflag or self.DeltaBTBflag) and self.delta_ax is not None:
                            trans = self.delta_ax.transData #=self.delta_ax.transScale + (self.delta_ax.transLimits + self.delta_ax.transAxes)
                            if self.DeltaETBflag and len(self.timeB) == len(self.delta1B):
                                try:
                                    if self.l_delta1B is not None:
                                        self.l_delta1B.remove()
                                except Exception: # pylint: disable=broad-except
                                    pass
                                self.l_delta1B, = self.ax.plot(
                                    self.timeB,
                                    self.delta1B,
                                    transform=trans,
                                    markersize=self.ETBdeltamarkersize,
                                    sketch_params=None,path_effects=[],
                                    marker=self.ETBdeltamarker,
                                    linewidth=self.ETBdeltalinewidth,
                                    linestyle=self.ETBdeltalinestyle,
                                    drawstyle=self.ETBdeltadrawstyle,
                                    color=self.backgrounddeltaetcolor,
                                    alpha=self.backgroundalpha,
                                    label=self.aw.arabicReshape(QApplication.translate('Label', 'BackgroundDeltaET')))
                            if self.DeltaBTBflag and len(self.timeB) == len(self.delta2B):
                                try:
                                    if self.l_delta2B is not None:
                                        self.l_delta2B.remove()
                                except Exception: # pylint: disable=broad-except
                                    pass
                                self.l_delta2B, = self.ax.plot(
                                    self.timeB,
                                    self.delta2B,
                                    transform=trans,
                                    markersize=self.BTBdeltamarkersize,
                                    sketch_params=None,path_effects=[],
                                    marker=self.BTBdeltamarker,
                                    linewidth=self.BTBdeltalinewidth,
                                    linestyle=self.BTBdeltalinestyle,
                                    drawstyle=self.BTBdeltadrawstyle,
                                    color=self.backgrounddeltabtcolor,
                                    alpha=self.backgroundalpha,
                                    label=self.aw.arabicReshape(QApplication.translate('Label', 'BackgroundDeltaBT')))
                        #check backgroundevents flag
                        if self.backgroundeventsflag:
                            height = 50 if self.mode == 'F' else 20

                            for p, bge in enumerate(self.backgroundEvents):
                                if self.eventsGraphflag not in [2,4] or self.backgroundEtypes[p] > 3:
                                    event_idx = bge
                                    if not self.backgroundShowFullflag and (((not self.autotimex or self.autotimexMode == 0) and event_idx < bcharge_idx) or event_idx > bdrop_idx):
                                        continue
                                    if self.backgroundEtypes[p] < 4:
                                        st1 = f'{self.Betypesf(self.backgroundEtypes[p])[0]}{self.eventsvaluesShort(self.backgroundEvalues[p])}'
                                    else:
                                        st1 = self.backgroundEStrings[p].strip()[:self.eventslabelschars]
                                        if len(st1) == 0:
                                            st1 = 'E'
                                    # plot events on BT when showeventsonbt is true
                                    if not self.showeventsonbt and self.temp1B[event_idx] > self.temp2B[event_idx]:
                                        temp = self.temp1B[event_idx]
                                    else:
                                        temp = self.temp2B[event_idx]
                                    if not self.showEtypes[self.backgroundEtypes[p]]:
                                        continue
                                    anno = self.ax.annotate(st1, xy=(self.timeB[event_idx], temp),path_effects=[],
                                                        xytext=(self.timeB[event_idx], temp+height),
                                                        va='center', ha='center',
                                                        fontsize='x-small',
                                                        color=self.palette['bgeventtext'],
                                                        arrowprops={'arrowstyle':'wedge',
                                                                        'color':self.palette['bgeventmarker'],
                                                                        'alpha':self.backgroundalpha},#relpos=(0,0)),
                                                        alpha=min(self.backgroundalpha + 0.1, 1.0))
                                    try:
                                        anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                    except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                        pass
                                    self.l_background_annotations.append(anno)
                            #background events by value
                            if self.eventsGraphflag in [2,3,4]: # 2: step, 3: step+, 4: combo
                                self.E1backgroundtimex,self.E2backgroundtimex,self.E3backgroundtimex,self.E4backgroundtimex = [],[],[],[]
                                self.E1backgroundvalues,self.E2backgroundvalues,self.E3backgroundvalues,self.E4backgroundvalues = [],[],[],[]
                                E1b_last = E2b_last = E3b_last = E4b_last = 0  #not really necessary but guarantees that Exb_last is defined
                                # remember event value @CHARGE (or last before CHARGE) to add if not self.backgroundShowFullflag
                                E1_CHARGE_B:Optional[float] = None
                                E2_CHARGE_B:Optional[float] = None
                                E3_CHARGE_B:Optional[float] = None
                                E4_CHARGE_B:Optional[float] = None
                                event_pos_offset = self.eventpositionbars[0]
                                event_pos_factor = self.eventpositionbars[1] - self.eventpositionbars[0]
                                #properties for the event annotation
                                eventannotationprop = self.aw.mpl_fontproperties.copy()
                                hoffset = 3  #relative to the event dot
                                voffset = 3  #relative to the event dot
                                eventannotationprop.set_size('x-small')
                                self.overlapList = []
                                for i, event_idx in enumerate(self.backgroundEvents):
                                    txx = self.timeB[event_idx]
                                    pos:float = max(0,int(round((self.backgroundEvalues[i]-1)*10)))
                                    skip_event = (not self.backgroundShowFullflag and (((not self.autotimex or self.autotimexMode == 0) and event_idx < bcharge_idx) or event_idx > bdrop_idx))
                                    if self.backgroundEtypes[i] == 0 and self.showEtypes[0]:
                                        if skip_event:
                                            if (self.timeindexB[0] > -1 and txx < self.timeB[self.timeindexB[0]]):
                                                E1_CHARGE_B = pos # remember event value at CHARGE
                                                if not self.clampEvents:
                                                    E1_CHARGE_B = (E1_CHARGE_B*event_pos_factor)+event_pos_offset
                                            continue
                                        self.E1backgroundtimex.append(self.timeB[event_idx])
                                        if self.clampEvents:
                                            self.E1backgroundvalues.append(pos)
                                        else:
                                            self.E1backgroundvalues.append((pos*event_pos_factor)+event_pos_offset)
                                        E1b_last = i
                                        try:
                                            if (len(self.timex)==0 or self.flagon) and self.eventsGraphflag!=4 and self.backgroundDetails and self.specialeventannovisibilities[0] != 0:
                                                E1b_annotation = self.parseSpecialeventannotation(self.specialeventannotations[0], i, applyto='background')
                                                temp = self.E1backgroundvalues[-1]
                                                anno = self.ax.annotate(E1b_annotation, xy=(hoffset + self.timeB[int(event_idx)], voffset + temp),
                                                            alpha=min(self.backgroundalpha + 0.1, 1.0),
                                                            color=self.palette['text'],
                                                            va='bottom', ha='left',
                                                            fontsize='x-small',
                                                            path_effects=[PathEffects.withStroke(linewidth=self.patheffects,foreground=self.palette['background'])],
                                                            )
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                try:
                                                    overlap = self.checkOverlap(anno)# , i, E1b_annotation)
                                                    if overlap:
                                                        anno.remove()
                                                except Exception: # pylint: disable=broad-except
                                                    pass
                                        except Exception as ex: # pylint: disable=broad-except
                                            _log.exception(ex)
                                            _, _, exc_tb = sys.exc_info()
                                            self.adderror((QApplication.translate('Error Message','Exception:') + ' redraw() anno {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
                                    elif self.backgroundEtypes[i] == 1 and self.showEtypes[1]:
                                        if skip_event:
                                            if (self.timeindexB[0] > -1 and txx < self.timeB[self.timeindexB[0]]):
                                                E2_CHARGE_B = pos # remember event value at CHARGE
                                                if not self.clampEvents:
                                                    E2_CHARGE_B = (E2_CHARGE_B*event_pos_factor)+event_pos_offset
                                            continue
                                        self.E2backgroundtimex.append(self.timeB[event_idx])
                                        if self.clampEvents:
                                            self.E2backgroundvalues.append(pos)
                                        else:
                                            self.E2backgroundvalues.append((pos*event_pos_factor)+event_pos_offset)
                                        E2b_last = i
                                        try:
                                            if (len(self.timex)==0 or self.flagon) and self.eventsGraphflag!=4 and self.backgroundDetails and self.specialeventannovisibilities[1] != 0:
                                                E2b_annotation = self.parseSpecialeventannotation(self.specialeventannotations[1], i, applyto='background')
                                                temp = self.E2backgroundvalues[-1]
                                                anno = self.ax.annotate(E2b_annotation, xy=(hoffset + self.timeB[int(event_idx)], voffset + temp),
                                                            alpha=min(self.backgroundalpha + 0.1, 1.0),
                                                            color=self.palette['text'],
                                                            va='bottom', ha='left',
                                                            fontproperties=eventannotationprop,
                                                            path_effects=[PathEffects.withStroke(linewidth=self.patheffects,foreground=self.palette['background'])],
                                                            )
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                try:
                                                    overlap = self.checkOverlap(anno) #, i, E2b_annotation)
                                                    if overlap:
                                                        anno.remove()
                                                except Exception: # pylint: disable=broad-except
                                                    pass
                                        except Exception as ex: # pylint: disable=broad-except
                                            _log.exception(ex)
                                            _, _, exc_tb = sys.exc_info()
                                            self.adderror((QApplication.translate('Error Message','Exception:') + ' redraw() anno {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
                                    elif self.backgroundEtypes[i] == 2 and self.showEtypes[2]:
                                        if skip_event:
                                            if (self.timeindexB[0] > -1 and txx < self.timeB[self.timeindexB[0]]):
                                                E3_CHARGE_B = pos # remember event value at CHARGE
                                                if not self.clampEvents:
                                                    E3_CHARGE_B = (E3_CHARGE_B*event_pos_factor)+event_pos_offset
                                            continue
                                        self.E3backgroundtimex.append(self.timeB[event_idx])
                                        if self.clampEvents:
                                            self.E3backgroundvalues.append(pos)
                                        else:
                                            self.E3backgroundvalues.append((pos*event_pos_factor)+event_pos_offset)
                                        E3b_last = i
                                        try:
                                            if (len(self.timex)==0 or self.flagon) and self.eventsGraphflag!=4 and self.backgroundDetails and self.specialeventannovisibilities[2] != 0:
                                                E3b_annotation = self.parseSpecialeventannotation(self.specialeventannotations[2], i, applyto='background')
                                                temp = self.E3backgroundvalues[-1]
                                                anno = self.ax.annotate(E3b_annotation, xy=(hoffset + self.timeB[int(event_idx)], voffset + temp),
                                                            alpha=min(self.backgroundalpha + 0.1, 1.0),
                                                            color=self.palette['text'],
                                                            va='bottom', ha='left',
                                                            fontproperties=eventannotationprop,
                                                            path_effects=[PathEffects.withStroke(linewidth=self.patheffects,foreground=self.palette['background'])],
                                                            )
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                try:
                                                    overlap = self.checkOverlap(anno) #, i, E3b_annotation)
                                                    if overlap:
                                                        anno.remove()
                                                except Exception: # pylint: disable=broad-except
                                                    pass
                                        except Exception as ex: # pylint: disable=broad-except
                                            _log.exception(ex)
                                            _, _, exc_tb = sys.exc_info()
                                            self.adderror((QApplication.translate('Error Message','Exception:') + ' redraw() anno {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
                                    elif self.backgroundEtypes[i] == 3 and self.showEtypes[3]:
                                        if skip_event:
                                            if (self.timeindexB[0] > -1 and txx < self.timeB[self.timeindexB[0]]):
                                                E4_CHARGE_B = pos # remember event value at CHARGE
                                                if not self.clampEvents:
                                                    E4_CHARGE_B = (E4_CHARGE_B*event_pos_factor)+event_pos_offset
                                            continue
                                        self.E4backgroundtimex.append(self.timeB[event_idx])
                                        if self.clampEvents:
                                            self.E4backgroundvalues.append(pos)
                                        else:
                                            self.E4backgroundvalues.append((pos*event_pos_factor)+event_pos_offset)
                                        E4b_last = i
                                        try:
                                            if (len(self.timex)==0 or self.flagon) and self.eventsGraphflag!=4 and self.backgroundDetails and self.specialeventannovisibilities[3] != 0:
                                                E4b_annotation = self.parseSpecialeventannotation(self.specialeventannotations[3], i, applyto='background')
                                                temp = self.E4backgroundvalues[-1]
                                                anno = self.ax.annotate(E4b_annotation, xy=(hoffset + self.timeB[int(event_idx)], voffset + temp),
                                                            alpha=min(self.backgroundalpha + 0.1, 1.0),
                                                            color=self.palette['text'],
                                                            va='bottom', ha='left',
                                                            fontproperties=eventannotationprop,
                                                            path_effects=[PathEffects.withStroke(linewidth=self.patheffects,foreground=self.palette['background'])],
                                                            )
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                try:
                                                    overlap = self.checkOverlap(anno) #, i, E4b_annotation)
                                                    if overlap:
                                                        anno.remove()
                                                except Exception: # pylint: disable=broad-except
                                                    pass
                                        except Exception as ex: # pylint: disable=broad-except
                                            _log.exception(ex)
                                            _, _, exc_tb = sys.exc_info()
                                            self.adderror((QApplication.translate('Error Message','Exception:') + ' redraw() anno {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
    #                            every = None
                                if len(self.E1backgroundtimex)>0 and len(self.E1backgroundtimex)==len(self.E1backgroundvalues):
                                    if (self.timeindexB[6] > 0 and self.extendevents and self.timeB[self.timeindexB[6]] > self.timeB[self.backgroundEvents[E1b_last]]):   #if drop exists and last event was earlier
                                        # repeat last value at time of DROP
                                        self.E1backgroundtimex.append(self.timeB[self.timeindexB[6]]) #time of drop
                                        pos = max(0,int(round((self.backgroundEvalues[E1b_last]-1)*10)))
                                        if self.clampEvents:
                                            self.E1backgroundvalues.append(pos)
                                        else:
                                            self.E1backgroundvalues.append((pos*event_pos_factor)+event_pos_offset)
                                    if E1_CHARGE_B is not None and len(self.E1backgroundvalues)>1 and self.E1backgroundvalues[0] != E1_CHARGE_B:
                                        E1xB = [self.timeB[self.timeindexB[0]]] + self.E1backgroundtimex
                                        E1yB = [E1_CHARGE_B] + self.E1backgroundvalues
                                    else:
                                        E1xB = self.E1backgroundtimex
                                        E1yB = self.E1backgroundvalues
                                    self.l_backgroundeventtype1dots, = self.ax.plot(E1xB, E1yB, color=self.EvalueColor[0],
                                                                                marker=(self.EvalueMarker[0] if self.eventsGraphflag != 4 else None),
                                                                                markersize = self.EvalueMarkerSize[0],
                                                                                picker=True,
                                                                                pickradius=2,
                                                                                #markevery=every,
                                                                                linestyle='-',drawstyle='steps-post',linewidth = self.Evaluelinethickness[0],alpha = min(self.backgroundalpha + 0.1, 1.0), label=self.Betypesf(0,True))
                                if len(self.E2backgroundtimex)>0 and len(self.E2backgroundtimex)==len(self.E2backgroundvalues):
                                    if (self.timeindexB[6] > 0 and self.extendevents and self.timeB[self.timeindexB[6]] > self.timeB[self.backgroundEvents[E2b_last]]):   #if drop exists and last event was earlier
                                        # repeat last value at time of DROP
                                        self.E2backgroundtimex.append(self.timeB[self.timeindexB[6]]) #time of drop
                                        pos = max(0,int(round((self.backgroundEvalues[E2b_last]-1)*10)))
                                        if self.clampEvents:
                                            self.E2backgroundvalues.append(pos)
                                        else:
                                            self.E2backgroundvalues.append((pos*event_pos_factor)+event_pos_offset)
                                    if E2_CHARGE_B is not None and len(self.E2backgroundvalues)>1 and self.E2backgroundvalues[0] != E2_CHARGE_B:
                                        E2xB = [self.timeB[self.timeindexB[0]]] + self.E2backgroundtimex
                                        E2yB = [E2_CHARGE_B] + self.E2backgroundvalues
                                    else:
                                        E2xB = self.E2backgroundtimex
                                        E2yB = self.E2backgroundvalues
                                    self.l_backgroundeventtype2dots, = self.ax.plot(E2xB, E2yB, color=self.EvalueColor[1],
                                                                                marker=(self.EvalueMarker[1] if self.eventsGraphflag != 4 else None),
                                                                                markersize = self.EvalueMarkerSize[1],
                                                                                picker=True,
                                                                                pickradius=2,
                                                                                #markevery=every,
                                                                                linestyle='-',drawstyle='steps-post',linewidth = self.Evaluelinethickness[1],alpha = min(self.backgroundalpha + 0.1, 1.0), label=self.Betypesf(1,True))
                                if len(self.E3backgroundtimex)>0 and len(self.E3backgroundtimex)==len(self.E3backgroundvalues):
                                    if (self.timeindexB[6] > 0 and self.extendevents and self.timeB[self.timeindexB[6]] > self.timeB[self.backgroundEvents[E3b_last]]):   #if drop exists and last event was earlier
                                        # repeat last value at time of DROP
                                        self.E3backgroundtimex.append(self.timeB[self.timeindexB[6]]) #time of drop
                                        pos = max(0,int(round((self.backgroundEvalues[E3b_last]-1)*10)))
                                        if self.clampEvents:
                                            self.E3backgroundvalues.append(pos)
                                        else:
                                            self.E3backgroundvalues.append((pos*event_pos_factor)+event_pos_offset)
                                    if E3_CHARGE_B is not None and len(self.E3backgroundvalues)>1 and self.E3backgroundvalues[0] != E3_CHARGE_B:
                                        E3xB = [self.timeB[self.timeindexB[0]]] + self.E3backgroundtimex
                                        E3yB = [E3_CHARGE_B] + self.E3backgroundvalues
                                    else:
                                        E3xB = self.E3backgroundtimex
                                        E3yB = self.E3backgroundvalues
                                    self.l_backgroundeventtype3dots, = self.ax.plot(E3xB, E3yB, color=self.EvalueColor[2],
                                                                                marker=(self.EvalueMarker[2] if self.eventsGraphflag != 4 else None),
                                                                                markersize = self.EvalueMarkerSize[2],
                                                                                picker=True,
                                                                                pickradius=2,
                                                                                #markevery=every,
                                                                                linestyle='-',drawstyle='steps-post',linewidth = self.Evaluelinethickness[2],alpha = min(self.backgroundalpha + 0.1, 1.0), label=self.Betypesf(2,True))
                                if len(self.E4backgroundtimex)>0 and len(self.E4backgroundtimex)==len(self.E4backgroundvalues):
                                    if (self.timeindexB[6] > 0 and self.extendevents and self.timeB[self.timeindexB[6]] > self.timeB[self.backgroundEvents[E4b_last]]):   #if drop exists and last event was earlier
                                        # repeat last value at time of DROP
                                        self.E4backgroundtimex.append(self.timeB[self.timeindexB[6]]) #time of drop
                                        pos = max(0,int(round((self.backgroundEvalues[E4b_last]-1)*10)))
                                        if self.clampEvents:
                                            self.E4backgroundvalues.append(pos)
                                        else:
                                            self.E4backgroundvalues.append((pos*event_pos_factor)+event_pos_offset)
                                    if E4_CHARGE_B is not None and len(self.E4backgroundvalues)>1 and self.E4backgroundvalues[0] != E4_CHARGE_B:
                                        E4xB = [self.timeB[self.timeindexB[0]]] + self.E4backgroundtimex
                                        E4yB = [E4_CHARGE_B] + self.E4backgroundvalues
                                    else:
                                        E4xB = self.E4backgroundtimex
                                        E4yB = self.E4backgroundvalues
                                    self.l_backgroundeventtype4dots, = self.ax.plot(E4xB, E4yB, color=self.EvalueColor[3],
                                                                                marker=(self.EvalueMarker[3] if self.eventsGraphflag != 4 else None),
                                                                                markersize = self.EvalueMarkerSize[3],
                                                                                picker=True,
                                                                                pickradius=2,
                                                                                #markevery=every,
                                                                                linestyle='-',drawstyle='steps-post',linewidth = self.Evaluelinethickness[3],alpha = min(self.backgroundalpha + 0.1, 1.0), label=self.Betypesf(3,True))

                            if len(self.backgroundEvents) > 0:
                                if self.eventsGraphflag == 4:
                                    # we prepare copies of the background Evalues
                                    Bevalues = [self.E1backgroundvalues[:],self.E2backgroundvalues[:],self.E3backgroundvalues[:],self.E4backgroundvalues[:]]
                                for i, event_idx in enumerate(self.backgroundEvents):
                                    if not self.backgroundShowFullflag and (((not self.autotimex or self.autotimexMode == 0) and event_idx < bcharge_idx) or event_idx > bdrop_idx):
                                        continue
                                    if self.backgroundEtypes[i] == 4 or self.eventsGraphflag in [0,3,4]:
                                        if self.backgroundEtypes[i] < 4 and (not self.renderEventsDescr or len(self.backgroundEStrings[i].strip()) == 0):
                                            Betype = self.Betypesf(self.backgroundEtypes[i])
                                            firstletter = str(Betype[0])
                                            secondletter = self.eventsvaluesShort(self.backgroundEvalues[i])
                                            if self.aw.eventslidertemp[self.backgroundEtypes[i]]:
                                                thirdletter = self.mode # postfix
                                            else:
                                                thirdletter = self.aw.eventsliderunits[self.backgroundEtypes[i]] # postfix
                                        else:
                                            firstletter = self.backgroundEStrings[i].strip()[:self.eventslabelschars]
                                            if firstletter == '':
                                                firstletter = 'E'
                                            secondletter = ''
                                            thirdletter = ''
                                        height = 50 if self.mode == 'F' else 20

                                        if self.eventsGraphflag == 4 and self.backgroundEtypes[i] < 4 and self.showEtypes[self.backgroundEtypes[i]] and len(Bevalues[self.backgroundEtypes[i]])>0:
                                            Btemp = Bevalues[self.backgroundEtypes[i]][0]
                                            Bevalues[self.backgroundEtypes[i]] = Bevalues[self.backgroundEtypes[i]][1:]
                                        else:
                                            Btemp = None

                                        if Btemp is not None and self.showEtypes[self.backgroundEtypes[i]]:
                                            if self.backgroundEtypes[i] == 0:
                                                boxstyle = 'roundtooth,pad=0.4'
                                                boxcolor = self.EvalueColor[0]
                                                textcolor = self.EvalueTextColor[0]
                                            elif self.backgroundEtypes[i] == 1:
                                                boxstyle = 'round,pad=0.3,rounding_size=0.8'
                                                boxcolor = self.EvalueColor[1]
                                                textcolor = self.EvalueTextColor[1]
                                            elif self.backgroundEtypes[i] == 2:
                                                boxstyle = 'sawtooth,pad=0.3,tooth_size=0.2'
                                                boxcolor = self.EvalueColor[2]
                                                textcolor = self.EvalueTextColor[2]
                                            elif self.backgroundEtypes[i] == 3:
                                                boxstyle = 'round4,pad=0.3,rounding_size=0.15'
                                                boxcolor = self.EvalueColor[3]
                                                textcolor = self.EvalueTextColor[3]
                                            elif self.backgroundEtypes[i] == 4:
                                                boxstyle = 'square,pad=0.1'
                                                boxcolor = self.palette['specialeventbox']
                                                textcolor = self.palette['specialeventtext']
                                            if self.eventsGraphflag in [0,3] or self.backgroundEtypes[i] > 3:
                                                anno = self.ax.annotate('f{firstletter}{secondletter}', xy=(self.timeB[int(event_idx)], Btemp),
                                                             xytext=(self.timeB[int(event_idx)],Btemp+height),
                                                             alpha=min(self.backgroundalpha + 0.1, 1.0),
                                                             color=self.palette['bgeventtext'],
                                                             va='center', ha='center',
                                                             arrowprops={'arrowstyle':'-','color':boxcolor,'alpha':self.backgroundalpha}, # ,relpos=(0,0)
                                                             bbox={'boxstyle':boxstyle, 'fc':boxcolor, 'ec':'none', 'alpha':self.backgroundalpha},
                                                             fontproperties=fontprop_small,
                                                             path_effects=[PathEffects.withStroke(linewidth=0.5,foreground=self.palette['background'])],
                                                             )
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                            elif self.eventsGraphflag == 4:
                                                if thirdletter != '':
                                                    firstletter = ''
                                                anno = self.ax.annotate(f'{firstletter}{secondletter}{thirdletter}', xy=(self.timeB[int(event_idx)], Btemp),
                                                             xytext=(self.timeB[int(event_idx)],Btemp),
                                                             alpha=min(self.backgroundalpha + 0.3, 1.0),
                                                             color=self.palette['bgeventtext'],
                                                             va='center', ha='center',
                                                             bbox={'boxstyle':boxstyle, 'fc':boxcolor, 'ec':'none',
                                                                'alpha':min(self.backgroundalpha, 1.0)},
                                                             fontproperties=fontprop_small,
                                                             path_effects=[PathEffects.withStroke(linewidth=0.5,foreground=self.palette['background'])],
                                                             )
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                        #check backgroundDetails flag
                        if self.backgroundDetails:
                            d:float = self.ylimit - self.ylimit_min
                            d = d - d/5
                            #if there is a profile loaded with CHARGE, then save time to get the relative time
                            if self.timeindex[0] != -1:   #verify it exists before loading it, otherwise the list could go out of index
                                startB = self.timex[self.timeindex[0]]
                            elif self.timeindexB[0] > 0:
                                startB = self.timeB[self.timeindexB[0]]
                            else:
                                startB = 0
                            try:
                                # background annotations are not draggable
                                self.l_background_annotations.extend(self.place_annotations(
                                    -1, # TP_index
                                    d,
                                    self.timeB,
                                    self.timeindexB,
                                    self.temp2B,
                                    self.stemp2B,
                                    startB,
                                    self.timeindex, # timeindex2
                                    TP_time_loaded=self.TP_time_B_loaded,
                                    draggable=True))
                            except Exception: # pylint: disable=broad-except
                                pass

                        #show the analysis results if they exist
    #                    if len(self.analysisresultsstr) > 0:
    #                        self.aw.analysisShowResults(redraw=False)

                        #END of Background

                    if self.patheffects:
                        rcParams['path.effects'] = [PathEffects.withStroke(linewidth=self.patheffects, foreground=self.palette['background'])]

                    self.handles = []
                    self.labels = []
                    self.legend_lines = []

                    self.smoothETBT(smooth,recomputeAllDeltas,sampling,decay_smoothing_p)

    ## Output Idle Noise StdDev of BT RoR
    #                        try:
    #                            start = self.timeindex[0]
    #                            end = self.timeindex[6]
    #                            if start == -1:
    #                                start = 0
    #                            start = start + 30 # avoiding the empty begin of heavy smoothed data
    #                            if end == 0:
    #                                end = min(len(self.delta2) -1,100)
    #                            print("ET RoR mean:",numpy.mean([x for x in self.delta1[start:end] if x is not None]))
    #                            print("ET RoR std:",numpy.std([x for x in self.delta1[start:end] if x is not None]))
    #                            print("BT RoR mean:",numpy.mean([x for x in self.delta2[start:end] if x is not None]))
    #                            print("BT RoR std:",numpy.std([x for x in self.delta2[start:end] if x is not None]))
    #                            print("BT mean:",numpy.mean([x for x in self.temp2[start:end] if x is not None]))
    #                            print("BT std:",numpy.std([x for x in self.temp2[start:end] if x is not None]))
    #                            max_BT = numpy.max([x for x in self.temp2[start:end] if x is not None])
    #                            min_BT = numpy.max([x for x in self.temp2[start:end] if x is not None])
    #                            mean_BT = numpy.mean([x for x in self.temp2[start:end] if x is not None])
    #                            print("BT max delta:", max(mean_BT - min_BT,max_BT - mean_BT))
    #                        except Exception as e: # pylint: disable=broad-except
    #                            _log.exception(e)

                    # CHARGE-DROP curve index limits
                    charge_idx = 0
                    if self.timeindex[0] > -1:
                        charge_idx = self.timeindex[0]
                    drop_idx = len(self.timex)-1
                    if self.timeindex[6] > 0:
                        drop_idx = self.timeindex[6]

                    if self.eventsshowflag != 0:
                        Nevents = len(self.specialevents)
                        #three modes of drawing events.
                        # the first mode just places annotations. They are text annotations.
                        # the second mode aligns the events types to a bar height so that they can be visually identified by type. They are text annotations
                        # the third mode plots the events by value. They are not annotations but actual lines.

                        if self.eventsGraphflag == 1 and Nevents:

                            char1 = self.etypes[0][0]
                            char2 = self.etypes[1][0]
                            char3 = self.etypes[2][0]
                            char4 = self.etypes[3][0]

                            if self.mode == 'F':
                                row = {char1:self.phases[0]-20,char2:self.phases[0]-40,char3:self.phases[0]-60,char4:self.phases[0]-80}
                            else:
                                row = {char1:self.phases[0]-10,char2:self.phases[0]-20,char3:self.phases[0]-30,char4:self.phases[0]-40}

                            #draw lines of color between events of the same type to help identify areas of events.
                            #count (as length of the list) and collect their times for each different type. Each type will have a different plot height
                            netypes:List[List[float]] = [[],[],[],[]]
                            for i in range(Nevents):
                                try:
                                    txx = self.timex[self.specialevents[i]]
                                    event_idx = int(self.specialevents[i])

                                    if self.flagstart or self.foregroundShowFullflag or (charge_idx <= event_idx <= drop_idx) or (self.autotimex and self.autotimexMode != 0 and event_idx < charge_idx):
                                        if self.specialeventstype[i] == 0 and self.showEtypes[0]:
                                            netypes[0].append(txx)
                                        elif self.specialeventstype[i] == 1 and self.showEtypes[1]:
                                            netypes[1].append(txx)
                                        elif self.specialeventstype[i] == 2 and self.showEtypes[2]:
                                            netypes[2].append(txx)
                                        elif self.specialeventstype[i] == 3 and self.showEtypes[3]:
                                            netypes[3].append(txx)
                                except Exception as e:  # pylint: disable=broad-except
                                    _log.debug(e)

                            letters = ''.join((char1,char2,char3,char4))   #"NPDF" first letter for each type (None, Power, Damper, Fan)
                            rotating_colors = [self.palette['rect2'],self.palette['rect3']] #rotating rotating_colors
                            for p,ltr in enumerate(letters):
                                if len(netypes[p]) > 1:
                                    for i in range(len(netypes[p])-1):
                                        #draw differentiating color bars between events and place then in a different height according with type
                                        rect = patches.Rectangle((netypes[p][i], row[ltr]), width = (netypes[p][i+1]-netypes[p][i]), height = step, color = rotating_colors[i%2],alpha=0.5)
                                        self.ax.add_patch(rect)

                            # annotate event
                            for i in range(Nevents):
                                if self.specialeventstype[i] > 3:
                                    # a special event of type "--"
                                    pass
                                elif self.showEtypes[self.specialeventstype[i]]:
                                    event_idx = int(self.specialevents[i])
                                    try:
                                        if not(self.flagstart or self.foregroundShowFullflag or (charge_idx <= event_idx <= drop_idx) or (self.autotimex and self.autotimexMode != 0 and event_idx < charge_idx)):
                                            continue

                                        firstletter = self.etypes[self.specialeventstype[i]][0]
                                        secondletter = self.eventsvaluesShort(self.specialeventsvalue[i])

                                        #some times ET is not drawn (ET = 0) when using device NONE
                                        if self.ETcurve or self.BTcurve:
                                            # plot events on BT when showeventsonbt is true
                                            if self.showeventsonbt and self.BTcurve:
                                                col = self.palette['bt']
                                                if self.flagon:
                                                    temps = self.temp2
                                                else:
                                                    temps = self.stemp2
                                            elif (self.ETcurve and self.temp1[event_idx] >= self.temp2[event_idx]) or (not self.BTcurve):
                                                col = self.palette['et']
                                                if self.flagon:
                                                    temps = self.temp1
                                                else:
                                                    temps = self.stemp1
                                            else:
                                                col = self.palette['bt']
                                                if self.flagon:
                                                    temps = self.temp2
                                                else:
                                                    temps = self.stemp2
        #                                    fcolor=self.EvalueColor[self.specialeventstype[i]]
                                            if platform.system() == 'Windows':
                                                vert_offset = 5.0
                                            else:
                                                vert_offset = 2.5
                                            anno = self.ax.annotate(f'{firstletter}{secondletter}',
                                                             xy=(self.timex[event_idx],
                                                             temps[event_idx]),
                                                             xytext=(self.timex[event_idx],row[firstletter] + vert_offset),
                                                             alpha=1.,
                                                             va='center', ha='left',
                                                             bbox={'boxstyle':'square,pad=0.1', 'fc':self.palette['specialeventbox'], 'ec':'none'},
                                                             path_effects=[PathEffects.withStroke(linewidth=0.5,foreground=self.palette['background'])],
                                                             color=self.palette['specialeventtext'],
                                                             arrowprops={'arrowstyle':'-','color':col,'alpha':0.4,'relpos':(0,0)},
                                                             fontsize='xx-small',
                                                             fontproperties=fontprop_small)
                                            try:
                                                anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                            except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                pass
                                    except Exception as e: # pylint: disable=broad-except
                                        _log.exception(e)

                        elif self.eventsGraphflag in [2,3,4]: # in this mode we have to generate the plots even if Nevents=0 to avoid redraw issues resulting from an incorrect number of plot count
                            self.E1timex,self.E2timex,self.E3timex,self.E4timex = [],[],[],[]
                            self.E1values,self.E2values,self.E3values,self.E4values = [],[],[],[]
                            E1_nonempty:bool = False
                            E2_nonempty:bool = False
                            E3_nonempty:bool = False
                            E4_nonempty:bool = False
                            #not really necessary but guarantees that Ex_last is defined
                            E1_last:int = 0
                            E2_last:int = 0
                            E3_last:int = 0
                            E4_last:int = 0
                            # remember event value @CHARGE (or last before CHARGE) to add if not self.foregroundShowFullflag
                            E1_CHARGE:Optional[float] = None
                            E2_CHARGE:Optional[float] = None
                            E3_CHARGE:Optional[float] = None
                            E4_CHARGE:Optional[float] = None
                            event_pos_offset = self.eventpositionbars[0]
                            event_pos_factor = self.eventpositionbars[1] - self.eventpositionbars[0]
                            #properties for the event annotations
                            eventannotationprop = self.aw.mpl_fontproperties.copy()
                            hoffset = 3  #relative to the event dot
                            voffset = 1  #relative to the event dot
                            self.overlapList = []
                            eventannotationprop.set_size('x-small')
                            for i in range(Nevents):
                                pos = max(0,int(round((self.specialeventsvalue[i]-1)*10)))
                                txx = self.timex[self.specialevents[i]]
                                skip_event = ((not self.foregroundShowFullflag and (not self.autotimex or self.autotimexMode == 0) and self.timeindex[0] > -1 and txx < self.timex[self.timeindex[0]]) or
                                            (not self.foregroundShowFullflag and self.timeindex[6] > 0 and txx > self.timex[self.timeindex[6]]))
                                try:
                                    if self.specialeventstype[i] == 0 and self.showEtypes[0]:
                                        if skip_event:
                                            if (self.timeindex[0] > -1 and txx < self.timex[self.timeindex[0]]):
                                                E1_CHARGE = pos # remember event value at CHARGE
                                                if not self.clampEvents:
                                                    E1_CHARGE = (E1_CHARGE*event_pos_factor)+event_pos_offset
                                            # don't draw event lines before CHARGE if foregroundShowFullflag is not set
                                            continue
                                        self.E1timex.append(txx)
                                        if self.clampEvents: # in clamp mode we render also event values higher than 100:
                                            self.E1values.append(pos)
                                        else:
                                            self.E1values.append((pos*event_pos_factor)+event_pos_offset)
                                        E1_nonempty = True
                                        E1_last = i
                                        try:
                                            if not sampling and not self.flagstart and self.eventsGraphflag!=4 and self.specialeventannovisibilities[0] != 0:
                                                E1_annotation = self.parseSpecialeventannotation(self.specialeventannotations[0], i)
                                                temp = self.E1values[-1]
                                                anno = self.ax.annotate(E1_annotation, xy=(hoffset + self.timex[int(self.specialevents[i])], voffset + temp),
                                                            alpha=.9,
                                                            color=self.palette['text'],
                                                            va='bottom', ha='left',
                                                            fontproperties=eventannotationprop,
                                                            path_effects=[PathEffects.withStroke(linewidth=self.patheffects,foreground=self.palette['background'])],
                                                            )
                                                self.l_eventtype1annos.append(anno)
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                try:
                                                    overlap = self.checkOverlap(anno) #, i, E1_annotation)
                                                    if overlap:
                                                        anno.remove()
                                                except Exception: # pylint: disable=broad-except
                                                    pass
                                        except Exception as ex: # pylint: disable=broad-except
                                            _log.exception(ex)
                                            _, _, exc_tb = sys.exc_info()
                                            self.adderror((QApplication.translate('Error Message','Exception:') + ' redraw() anno {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
                                    elif self.specialeventstype[i] == 1 and self.showEtypes[1]:
                                        txx = self.timex[self.specialevents[i]]
                                        if skip_event:
                                            if (self.timeindex[0] > -1 and txx < self.timex[self.timeindex[0]]):
                                                E2_CHARGE = pos # remember event value at CHARGE
                                                if not self.clampEvents:
                                                    E2_CHARGE = (E2_CHARGE*event_pos_factor)+event_pos_offset
                                            # don't draw event lines before CHARGE if foregroundShowFullflag is not set
                                            continue
                                        self.E2timex.append(txx)
                                        if self.clampEvents: # in clamp mode we render also event values higher than 100:
                                            self.E2values.append(pos)
                                        else:
                                            self.E2values.append((pos*event_pos_factor)+event_pos_offset)
                                        E2_nonempty = True
                                        E2_last = i
                                        try:
                                            if not sampling and not self.flagstart and self.eventsGraphflag!=4 and self.specialeventannovisibilities[1] != 0:
                                                E2_annotation = self.parseSpecialeventannotation(self.specialeventannotations[1], i)
                                                temp = self.E2values[-1]
                                                anno = self.ax.annotate(E2_annotation, xy=(hoffset + self.timex[int(self.specialevents[i])], voffset + temp),
                                                            alpha=.9,
                                                            color=self.palette['text'],
                                                            va='bottom', ha='left',
                                                            fontproperties=eventannotationprop,
                                                            path_effects=[PathEffects.withStroke(linewidth=self.patheffects,foreground=self.palette['background'])],
                                                            )
                                                self.l_eventtype2annos.append(anno)
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                try:
                                                    overlap = self.checkOverlap(anno) #, i, E2_annotation)
                                                    if overlap:
                                                        anno.remove()
                                                except Exception: # pylint: disable=broad-except
                                                    pass

                                        except Exception as ex: # pylint: disable=broad-except
                                            _log.exception(ex)
                                            _, _, exc_tb = sys.exc_info()
                                            self.adderror((QApplication.translate('Error Message','Exception:') + ' redraw() anno {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
                                    elif self.specialeventstype[i] == 2 and self.showEtypes[2]:
                                        txx = self.timex[self.specialevents[i]]
                                        if skip_event:
                                            if (self.timeindex[0] > -1 and txx < self.timex[self.timeindex[0]]):
                                                E3_CHARGE = pos # remember event value at CHARGE
                                                if not self.clampEvents:
                                                    E3_CHARGE = (E3_CHARGE*event_pos_factor)+event_pos_offset
                                            # don't draw event lines before CHARGE if foregroundShowFullflag is not set
                                            continue
                                        self.E3timex.append(txx)
                                        if self.clampEvents: # in clamp mode we render also event values higher than 100:
                                            self.E3values.append(pos)
                                        else:
                                            self.E3values.append((pos*event_pos_factor)+event_pos_offset)
                                        E3_nonempty = True
                                        E3_last = i
                                        try:
                                            if not sampling and not self.flagstart and self.eventsGraphflag!=4 and self.specialeventannovisibilities[2] != 0:
                                                E3_annotation = self.parseSpecialeventannotation(self.specialeventannotations[2], i)
                                                temp = self.E3values[-1]
                                                anno = self.ax.annotate(E3_annotation, xy=(hoffset + self.timex[int(self.specialevents[i])], voffset + temp),
                                                            alpha=.9,
                                                            color=self.palette['text'],
                                                            va='bottom', ha='left',
                                                            fontproperties=eventannotationprop,
                                                            path_effects=[PathEffects.withStroke(linewidth=self.patheffects,foreground=self.palette['background'])],
                                                            )
                                                self.l_eventtype3annos.append(anno)
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                try:
                                                    overlap = self.checkOverlap(anno) #, i, E3_annotation)
                                                    if overlap:
                                                        anno.remove()
                                                except Exception: # pylint: disable=broad-except
                                                    pass
                                        except Exception as ex: # pylint: disable=broad-except
                                            _log.exception(ex)
                                            _, _, exc_tb = sys.exc_info()
                                            self.adderror((QApplication.translate('Error Message','Exception:') + ' redraw() anno {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
                                    elif self.specialeventstype[i] == 3 and self.showEtypes[3]:
                                        txx = self.timex[self.specialevents[i]]
                                        if skip_event:
                                            if (self.timeindex[0] > -1 and txx < self.timex[self.timeindex[0]]):
                                                E4_CHARGE = pos # remember event value at CHARGE
                                                if not self.clampEvents:
                                                    E4_CHARGE = (E4_CHARGE*event_pos_factor)+event_pos_offset
                                            # don't draw event lines before CHARGE if foregroundShowFullflag is not set
                                            continue
                                        self.E4timex.append(txx)
                                        if self.clampEvents: # in clamp mode we render also event values higher than 100:
                                            self.E4values.append(pos)
                                        else:
                                            self.E4values.append((pos*event_pos_factor)+event_pos_offset)
                                        E4_nonempty = True
                                        E4_last = i
                                        try:
                                            if not sampling and not self.flagstart and self.eventsGraphflag!=4 and self.specialeventannovisibilities[3] != 0:
                                                E4_annotation = self.parseSpecialeventannotation(self.specialeventannotations[3], i)
                                                temp = self.E4values[-1]
                                                anno = self.ax.annotate(E4_annotation, xy=(hoffset + self.timex[int(self.specialevents[i])], voffset + temp),
                                                            alpha=.9,
                                                            color=self.palette['text'],
                                                            va='bottom', ha='left',
                                                            fontproperties=eventannotationprop,
                                                            path_effects=[PathEffects.withStroke(linewidth=self.patheffects,foreground=self.palette['background'])],
                                                            )
                                                self.l_eventtype4annos.append(anno)
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                try:
                                                    overlap = self.checkOverlap(anno) #, i, E4_annotation)
                                                    if overlap:
                                                        anno.remove()
                                                except Exception: # pylint: disable=broad-except
                                                    pass
                                        except Exception as ex: # pylint: disable=broad-except
                                            _log.exception(ex)
                                            _, _, exc_tb = sys.exc_info()
                                            self.adderror((QApplication.translate('Error Message','Exception:') + ' redraw() anno {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
                                except Exception as e: # pylint: disable=broad-except
                                    _log.exception(e)

                            E1x:List[Optional[float]]
                            E1y:List[Optional[float]]
                            E2x:List[Optional[float]]
                            E2y:List[Optional[float]]
                            E3x:List[Optional[float]]
                            E3y:List[Optional[float]]
                            E4x:List[Optional[float]]
                            E4y:List[Optional[float]]
                            if len(self.E1timex) > 0 and len(self.E1values) == len(self.E1timex):
                                pos = max(0,int(round((self.specialeventsvalue[E1_last]-1)*10)))
                                if not self.clampEvents: # in clamp mode we render also event values higher than 100:
                                    pos = (pos*event_pos_factor)+event_pos_offset
                                if self.foregroundShowFullflag and self.autotimex and self.autotimexMode != 0 and (self.timeindex[7] > 0 and
                                        self.extendevents and self.timex[self.timeindex[7]] > self.timex[self.specialevents[E1_last]]):   #if cool exists and last event was earlier
                                    self.E1timex.append(self.timex[self.timeindex[7]]) #time of cool
                                    self.E1values.append(pos) #repeat last event value
                                elif (self.timeindex[6] > 0 and self.extendevents and self.timex[self.timeindex[6]] > self.timex[self.specialevents[E1_last]]):   #if drop exists and last event was earlier
                                    self.E1timex.append(self.timex[self.timeindex[6]]) #time of drop
                                    self.E1values.append(pos) #repeat last event value
                                E1x = list(self.E1timex) # E1x:List(Optional[float] while E1timex:List[float], but List is invariant
                                E1y = list(self.E1values)
                                if E1_CHARGE is not None and len(E1y)>1 and E1y[0] != E1_CHARGE:
                                    E1x = list([self.timex[self.timeindex[0]]] + E1x)
                                    E1y = list([E1_CHARGE] + E1y)
                                ds = 'steps-post'
                            else:
                                E1x = [None]
                                E1y = [None]
                                ds = 'steps-post'
                            self.l_eventtype1dots, = self.ax.plot(E1x, E1y, color=self.EvalueColor[0],
                                                                marker = (self.EvalueMarker[0] if self.eventsGraphflag != 4 else None),
                                                                markersize = self.EvalueMarkerSize[0],
                                                                picker=True,
                                                                pickradius=2,#markevery=every,
                                                                linestyle='-',drawstyle=ds,linewidth = self.Evaluelinethickness[0],alpha = self.Evaluealpha[0],label=self.etypesf(0))
                            if len(self.E2timex) > 0 and len(self.E2values) == len(self.E2timex):
                                pos = max(0,int(round((self.specialeventsvalue[E2_last]-1)*10)))
                                if not self.clampEvents: # in clamp mode we render also event values higher than 100:
                                    pos = (pos*event_pos_factor)+event_pos_offset
                                if self.foregroundShowFullflag and self.autotimex and self.autotimexMode != 0 and (self.timeindex[7] > 0 and
                                        self.extendevents and self.timex[self.timeindex[7]] > self.timex[self.specialevents[E2_last]]):   #if cool exists and last event was earlier
                                    self.E2timex.append(self.timex[self.timeindex[7]]) #time of cool
                                    self.E2values.append(pos) #repeat last event value
                                elif (self.timeindex[6] > 0 and self.extendevents and self.timex[self.timeindex[6]] > self.timex[self.specialevents[E2_last]]):   #if drop exists and last event was earlier
                                    self.E2timex.append(self.timex[self.timeindex[6]]) #time of drop
                                    self.E2values.append(pos) #repeat last event value
                                E2x = list(self.E2timex)
                                E2y = list(self.E2values)
                                if E2_CHARGE is not None and len(E2y)>1 and E2y[0] != E2_CHARGE:
                                    E2x = list([self.timex[self.timeindex[0]]] + E2x)
                                    E2y = list([E2_CHARGE] + E2y)
                                ds = 'steps-post'
                            else:
                                E2x = [None]
                                E2y = [None]
                                ds = 'steps-post'
                            self.l_eventtype2dots, = self.ax.plot(E2x, E2y, color=self.EvalueColor[1],
                                                                marker = (self.EvalueMarker[1] if self.eventsGraphflag != 4 else None),
                                                                markersize = self.EvalueMarkerSize[1],
                                                                picker=True,
                                                                pickradius=2,#markevery=every,
                                                                linestyle='-',drawstyle=ds,linewidth = self.Evaluelinethickness[1],alpha = self.Evaluealpha[1],label=self.etypesf(1))
                            if len(self.E3timex) > 0 and len(self.E3values) == len(self.E3timex):
                                pos = max(0,int(round((self.specialeventsvalue[E3_last]-1)*10)))
                                if not self.clampEvents: # in clamp mode we render also event values higher than 100:
                                    pos = (pos*event_pos_factor)+event_pos_offset
                                if self.foregroundShowFullflag and self.autotimex and self.autotimexMode != 0 and (self.timeindex[7] > 0 and
                                        self.extendevents and self.timex[self.timeindex[7]] > self.timex[self.specialevents[E3_last]]):   #if cool exists and last event was earlier
                                    self.E3timex.append(self.timex[self.timeindex[7]]) #time of cool
                                    self.E3values.append(pos) #repeat last event value
                                elif (self.timeindex[6] > 0 and self.extendevents and self.timex[self.timeindex[6]] > self.timex[self.specialevents[E3_last]]):   #if drop exists and last event was earlier
                                    self.E3timex.append(self.timex[self.timeindex[6]]) #time of drop
                                    self.E3values.append(pos) #repeat last event value
                                E3x = list(self.E3timex)
                                E3y = list(self.E3values)
                                if E3_CHARGE is not None and len(E3y)>1 and E3y[0] != E3_CHARGE:
                                    E3x = list([self.timex[self.timeindex[0]]] + E3x)
                                    E3y = list([E3_CHARGE] + E3y)
                                ds = 'steps-post'
                            else:
                                E3x = [None]
                                E3y = [None]
                                ds = 'steps-post'
                            self.l_eventtype3dots, = self.ax.plot(E3x, E3y, color=self.EvalueColor[2],
                                                                marker = (self.EvalueMarker[2] if self.eventsGraphflag != 4 else None),
                                                                markersize = self.EvalueMarkerSize[2],
                                                                picker=True,
                                                                pickradius=2,#markevery=every,
                                                                linestyle='-',drawstyle=ds,linewidth = self.Evaluelinethickness[2],alpha = self.Evaluealpha[2],label=self.etypesf(2))
                            if len(self.E4timex) > 0 and len(self.E4values) == len(self.E4timex):
                                pos = max(0,int(round((self.specialeventsvalue[E4_last]-1)*10)))
                                if not self.clampEvents: # in clamp mode we render also event values higher than 100:
                                    pos = (pos*event_pos_factor)+event_pos_offset
                                if self.foregroundShowFullflag and self.autotimex and self.autotimexMode != 0 and (self.timeindex[7] > 0 and
                                        self.extendevents and self.timex[self.timeindex[7]] > self.timex[self.specialevents[E4_last]]):   #if cool exists and last event was earlier
                                    self.E4timex.append(self.timex[self.timeindex[7]]) #time of cool
                                    self.E4values.append(pos) #repeat last event value
                                elif (self.timeindex[6] > 0 and self.extendevents and self.timex[self.timeindex[6]] > self.timex[self.specialevents[E4_last]]):   #if drop exists and last event was earlier
                                    self.E4timex.append(self.timex[self.timeindex[6]]) #time of drop
                                    self.E4values.append(pos) #repeat last event value
                                E4x = list(self.E4timex)
                                E4y = list(self.E4values)
                                if E4_CHARGE is not None and len(E4y)>1 and E4y[0] != E4_CHARGE:
                                    E4x = list([self.timex[self.timeindex[0]]] + E4x)
                                    E4y = list([E4_CHARGE] + E4y)
                                ds = 'steps-post'
                            else:
                                E4x = [None]
                                E4y = [None]
                                ds = 'steps-post'
                            self.l_eventtype4dots, = self.ax.plot(E4x, E4y, color=self.EvalueColor[3],
                                                                marker = (self.EvalueMarker[3] if self.eventsGraphflag != 4 else None),
                                                                markersize = self.EvalueMarkerSize[3],
                                                                picker=True,
                                                                pickradius=2,#markevery=every,
                                                                linestyle='-',drawstyle=ds,linewidth = self.Evaluelinethickness[3],alpha = self.Evaluealpha[3],label=self.etypesf(3))
                        if Nevents:
                            if self.eventsGraphflag == 4:
                                # we prepare copies of the Evalues
                                evalues = [self.E1values[:],self.E2values[:],self.E3values[:],self.E4values[:]]
                            for i in range(Nevents):
                                event_idx = int(self.specialevents[i])
                                try:
                                    if self.specialeventstype[i] == 4 or self.eventsGraphflag in [0,3,4]:
                                        if self.specialeventstype[i] < 4 and (not self.renderEventsDescr or len(self.specialeventsStrings[i].strip()) == 0):
                                            etype = self.etypesf(self.specialeventstype[i])
                                            firstletter = str(etype[0])
                                            secondletter = self.eventsvaluesShort(self.specialeventsvalue[i])
                                            if self.aw.eventslidertemp[self.specialeventstype[i]]:
                                                thirdletter = self.mode # postfix
                                            else:
                                                thirdletter = self.aw.eventsliderunits[self.specialeventstype[i]] # postfix
                                        else:
                                            firstletter = self.specialeventsStrings[i].strip()[:self.eventslabelschars]
                                            if firstletter == '':
                                                firstletter = 'E'
                                            secondletter = ''
                                            thirdletter = ''
                                        height = 50 if self.mode == 'F' else 20

                                        #some times ET is not drawn (ET = 0) when using device NONE
                                        # plot events on BT when showeventsonbt is true
                                        tempo:Optional[float]
                                        if not self.showeventsonbt and self.temp1[event_idx] > self.temp2[event_idx] and self.ETcurve:
                                            if self.flagon:
                                                tempo = self.temp1[event_idx]
                                            else:
                                                tempo = self.stemp1[event_idx]
                                        elif self.BTcurve:
                                            if self.flagon:
                                                tempo = self.temp2[event_idx]
                                            else:
                                                tempo = self.stemp2[event_idx]
                                        else:
                                            tempo = None

                                        # plot events on BT when showeventsonbt is true
                                        if self.showeventsonbt and temp is not None and self.BTcurve:
                                            if self.flagon:
                                                tempo = self.temp2[event_idx]
                                            else:
                                                tempo = self.stemp2[event_idx]

                                        if not self.flagstart and not self.foregroundShowFullflag and (((not self.autotimex or self.autotimexMode == 0) and event_idx < charge_idx) or event_idx > drop_idx):
                                            continue

                                        # combo events
                                        if self.eventsGraphflag == 4 and self.specialeventstype[i] < 4 and self.showEtypes[self.specialeventstype[i]] and len(evalues[self.specialeventstype[i]])>0:
                                            tempo = evalues[self.specialeventstype[i]][0]
                                            evalues[self.specialeventstype[i]] = evalues[self.specialeventstype[i]][1:]

                                        if tempo is not None and self.showEtypes[self.specialeventstype[i]]:
                                            if self.specialeventstype[i] == 0:
                                                boxstyle = 'roundtooth,pad=0.4'
                                                boxcolor = self.EvalueColor[0]
                                                textcolor = self.EvalueTextColor[0]
                                            elif self.specialeventstype[i] == 1:
                                                boxstyle = 'round,pad=0.3,rounding_size=0.8'
                                                boxcolor = self.EvalueColor[1]
                                                textcolor = self.EvalueTextColor[1]
                                            elif self.specialeventstype[i] == 2:
                                                boxstyle = 'sawtooth,pad=0.3,tooth_size=0.2'
                                                boxcolor = self.EvalueColor[2]
                                                textcolor = self.EvalueTextColor[2]
                                            elif self.specialeventstype[i] == 3:
                                                boxstyle = 'round4,pad=0.3,rounding_size=0.15'
                                                boxcolor = self.EvalueColor[3]
                                                textcolor = self.EvalueTextColor[3]
                                            elif self.specialeventstype[i] == 4:
                                                boxstyle = 'square,pad=0.1'
                                                boxcolor = self.palette['specialeventbox']
                                                textcolor = self.palette['specialeventtext']
                                            if self.eventsGraphflag in [0,3] or self.specialeventstype[i] > 3:
                                                if i in self.l_event_flags_pos_dict:
                                                    xytext = self.l_event_flags_pos_dict[i]
                                                elif i in self.l_event_flags_dict:
                                                    xytext = self.l_event_flags_dict[i].xyann
                                                else:
                                                    xytext = (self.timex[event_idx],tempo+height)
                                                anno = self.ax.annotate(f'{firstletter}{secondletter}', xy=(self.timex[event_idx], tempo),
                                                             xytext=xytext,
                                                             alpha=0.9,
                                                             color=textcolor,
                                                             va='center', ha='center',
                                                             arrowprops={'arrowstyle':'-','color':boxcolor,'alpha':0.4}, # ,relpos=(0,0)
                                                             bbox={'boxstyle':boxstyle, 'fc':boxcolor, 'ec':'none'},
                                                             fontproperties=fontprop_small,
                                                             path_effects=[PathEffects.withStroke(linewidth=0.5,foreground=self.palette['background'])],
                                                             )
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                    anno.draggable(use_blit=True)
                                                    anno.set_picker(self.aw.draggable_text_box_picker)
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                                # register draggable flag annotation to be re-created after re-positioning on redraw
                                                self.l_event_flags_dict[i] = anno
                                                if not self.showeventsonbt and self.ETcurve:
                                                    self.l_eteventannos.append(anno)
                                                else:
                                                    self.l_bteventannos.append(anno)
                                            elif self.eventsGraphflag == 4:
                                                if thirdletter != '':
                                                    firstletter = ''
                                                anno = self.ax.annotate(f'{firstletter}{secondletter}{thirdletter}', xy=(self.timex[event_idx], tempo),
                                                             xytext=(self.timex[event_idx],tempo),
                                                             alpha=0.9,
                                                             color=textcolor,
                                                             va='center', ha='center',
                                                             bbox={'boxstyle':boxstyle, 'fc':boxcolor, 'ec':'none'},
                                                             fontproperties=fontprop_small,
                                                             path_effects=[PathEffects.withStroke(linewidth=0.5,foreground=self.palette['background'])],
                                                             )
                                                if self.specialeventstype[i] == 0:
                                                    self.l_eventtype1annos.append(anno)
                                                elif self.specialeventstype[i] == 1:
                                                    self.l_eventtype2annos.append(anno)
                                                elif self.specialeventstype[i] == 2:
                                                    self.l_eventtype3annos.append(anno)
                                                elif self.specialeventstype[i] == 3:
                                                    self.l_eventtype4annos.append(anno)
                                                try:
                                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                                    pass
                                except Exception as e: # pylint: disable=broad-except
                                    _log.exception(e)

                    #plot delta ET (self.delta1) and delta BT (self.delta2)
                    ##### DeltaET,DeltaBT curves
                    if (self.DeltaETflag or self.DeltaBTflag) and self.delta_ax is not None:
                        trans = self.delta_ax.transData #=self.delta_ax.transScale + (self.delta_ax.transLimits + self.delta_ax.transAxes)
                        # if not recording or if during recording CHARGE was set already
                        if ((not self.flagon or self.timeindex[0] > 1) and
                                len(self.timex) == len(self.delta1) and len(self.timex) == len(self.delta2) and len(self.timex)>charge_idx+2):
                            # to avoid drawing of RoR artifacts directly after CHARGE we skip the first few samples after CHARGE before starting to draw
                            # as well as the last two readings before DROP
                            skip = max(2,min(20,int(round(5000/self.delay))))
                            skip2 = max(2,int(round(skip/2)))
                            if self.swapdeltalcds:
                                self.drawDeltaET(trans,charge_idx+skip,drop_idx-skip2)
                                self.drawDeltaBT(trans,charge_idx+skip,drop_idx-skip2)
                            else:
                                self.drawDeltaBT(trans,charge_idx+skip,drop_idx-skip2)
                                self.drawDeltaET(trans,charge_idx+skip,drop_idx-skip2)
                        else:
                            # instead of drawing we still have to establish the self.ax artists to keep the linecount correct!
                            self.drawDeltaET(trans,0,0)
                            self.drawDeltaBT(trans,0,0)

                    if self.delta_ax is not None and two_ax_mode:
                        self.aw.autoAdjustAxis(timex=False)
                        self.delta_ax.set_ylim(self.zlimit_min,self.zlimit)
                        if self.zgrid > 0:
                            self.delta_ax.yaxis.set_major_locator(ticker.MultipleLocator(self.zgrid))
                            self.delta_ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
                            delta_major_tick_lines:List['Line2D'] = self.delta_ax.get_yticklines()
                            for ytl in delta_major_tick_lines:
                                ytl.set_markersize(10)
                            delta_minor_tick_lines:List['Line2D'] = self.delta_ax.yaxis.get_minorticklines()
                            for mtl in delta_minor_tick_lines:
                                mtl.set_markersize(5)
                            for label in self.delta_ax.get_yticklabels() :
                                label.set_fontsize('small')
                            if not self.LCDdecimalplaces:
                                self.delta_ax.minorticks_off()

                    ##### Extra devices-curves
                    for l in self.extratemp1lines + self.extratemp2lines:
                        try:
                            if l is not None:
                                l.remove()
                        except Exception: # pylint: disable=broad-except
                            pass
                    self.extratemp1lines,self.extratemp2lines = [],[]
                    for i in range(min(
                            len(self.extratimex),
                            len(self.extratemp1),
                            len(self.extradevicecolor1),
                            len(self.extraname1),
                            len(self.extratemp2),
                            len(self.extradevicecolor2),
                            len(self.extraname2))):
                        if self.extratimex[i] is not None and self.extratimex[i] and len(self.extratimex[i])>1:
                            timexi_lin = numpy.linspace(self.extratimex[i][0],self.extratimex[i][-1],len(self.extratimex[i]))
                        else:
                            timexi_lin = None
                        try:
                            if self.aw.extraCurveVisibility1[i]:
                                if not self.flagon and (smooth or len(self.extrastemp1[i]) != len(self.extratimex[i])):
                                    self.extrastemp1[i] = self.smooth_list(self.extratimex[i],fill_gaps(self.extratemp1[i]),window_len=self.curvefilter,decay_smoothing=decay_smoothing_p,a_lin=timexi_lin)
                                else: # we don't smooth, but remove the dropouts
                                    self.extrastemp1[i] = fill_gaps(self.extratemp1[i])
                                if self.aw.extraDelta1[i]:
                                    trans = self.delta_ax.transData
                                else:
                                    trans = self.ax.transData
                                visible_extratemp1 : 'npt.NDArray[numpy.floating]'
                                if not self.flagstart and not self.foregroundShowFullflag and (not self.autotimex or self.autotimexMode == 0) and len(self.extrastemp1[i]) > 0:
                                    visible_extratemp1 = numpy.concatenate((
                                        numpy.full(charge_idx, numpy.nan, dtype=numpy.double),
                                        numpy.array(self.extrastemp1[i][charge_idx:drop_idx+1]),
                                        numpy.full(len(self.extratimex[i])-drop_idx-1, numpy.nan, dtype=numpy.double)))
                                elif not self.flagstart and not self.foregroundShowFullflag and self.autotimex and self.autotimexMode != 0 and len(self.extrastemp1[i]) > 0:
                                    visible_extratemp1 = numpy.concatenate((
                                        numpy.array(self.extrastemp1[i][0:drop_idx+1]),
                                        numpy.full(len(self.extratimex[i])-drop_idx-1, numpy.nan, dtype=numpy.double)))
                                else:
                                    visible_extratemp1 = numpy.array(self.extrastemp1[i], dtype=numpy.double)
                                # first draw the fill if any, but not during recording!
                                if not self.flagstart and self.aw.extraFill1[i] > 0:
                                    self.ax.fill_between(self.extratimex[i], 0, visible_extratemp1,transform=trans,color=self.extradevicecolor1[i],alpha=self.aw.extraFill1[i]/100.,sketch_params=None)
                                self.extratemp1lines.append(self.ax.plot(self.extratimex[i],visible_extratemp1,transform=trans,color=self.extradevicecolor1[i],
                                    sketch_params=None,path_effects=[PathEffects.withStroke(linewidth=self.extralinewidths1[i]+self.patheffects,foreground=self.palette['background'])],
                                    markersize=self.extramarkersizes1[i],marker=self.extramarkers1[i],linewidth=self.extralinewidths1[i],linestyle=self.extralinestyles1[i],
                                    drawstyle=self.extradrawstyles1[i],label=extraname1_subst[i])[0])
                        except Exception as ex: # pylint: disable=broad-except
                            _log.exception(ex)
                            _, _, exc_tb = sys.exc_info()
                            self.adderror((QApplication.translate('Error Message','Exception:') + ' redraw() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
                        try:
                            if self.aw.extraCurveVisibility2[i]:
                                if not self.flagon and (smooth or len(self.extrastemp2[i]) != len(self.extratimex[i])):
                                    self.extrastemp2[i] = self.smooth_list(self.extratimex[i],fill_gaps(self.extratemp2[i]),window_len=self.curvefilter,decay_smoothing=decay_smoothing_p,a_lin=timexi_lin)
                                else:
                                    self.extrastemp2[i] = fill_gaps(self.extratemp2[i])
                                if self.aw.extraDelta2[i]:
                                    trans = self.delta_ax.transData
                                else:
                                    trans = self.ax.transData
                                visible_extratemp2 : 'npt.NDArray[numpy.floating]'
                                if not self.flagstart and not self.foregroundShowFullflag and (not self.autotimex or self.autotimexMode == 0) and len(self.extrastemp2[i]) > 0:
                                    visible_extratemp2 = numpy.concatenate((
                                        numpy.full(charge_idx, numpy.nan, dtype=numpy.double),
                                        numpy.array(self.extrastemp2[i][charge_idx:drop_idx+1]),
                                        numpy.full(len(self.extratimex[i])-drop_idx-1, numpy.nan, dtype=numpy.double)))
                                elif not self.flagstart and not self.foregroundShowFullflag and self.autotimex and self.autotimexMode != 0 and len(self.extrastemp2[i]) > 0:
                                    visible_extratemp2 = numpy.concatenate((
                                        numpy.array(self.extrastemp2[i][0:drop_idx+1]),
                                        numpy.full(len(self.extratimex[i])-drop_idx-1, numpy.nan, dtype=numpy.double)))
                                else:
                                    visible_extratemp2 = numpy.array(self.extrastemp2[i], dtype=numpy.double)
                                # first draw the fill if any
                                if not self.flagstart and self.aw.extraFill2[i] > 0:
                                    self.ax.fill_between(self.extratimex[i], 0, visible_extratemp2,transform=trans,color=self.extradevicecolor2[i],alpha=self.aw.extraFill2[i]/100.,sketch_params=None)
                                self.extratemp2lines.append(self.ax.plot(self.extratimex[i],visible_extratemp2,transform=trans,color=self.extradevicecolor2[i],
                                    sketch_params=None,path_effects=[PathEffects.withStroke(linewidth=self.extralinewidths2[i]+self.patheffects,foreground=self.palette['background'])],
                                    markersize=self.extramarkersizes2[i],marker=self.extramarkers2[i],linewidth=self.extralinewidths2[i],linestyle=self.extralinestyles2[i],drawstyle=self.extradrawstyles2[i],label= extraname2_subst[i])[0])
                        except Exception as ex: # pylint: disable=broad-except
                            _log.exception(ex)
                            _, _, exc_tb = sys.exc_info()
                            self.adderror((QApplication.translate('Error Message','Exception:') + ' redraw() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
                    ##### ET,BT curves
                    visible_et : 'npt.NDArray[numpy.floating]'
                    visible_bt : 'npt.NDArray[numpy.floating]'
                    if not self.flagstart and not self.foregroundShowFullflag and (not self.autotimex or self.autotimexMode == 0):
                        visible_et = numpy.concatenate((
                                        numpy.full(charge_idx, numpy.nan, dtype=numpy.double),
                                        numpy.array(self.stemp1[charge_idx:drop_idx+1]),
                                        numpy.full(len(self.timex)-drop_idx-1, numpy.nan, dtype=numpy.double)))
                        visible_bt = numpy.concatenate((
                                        numpy.full(charge_idx, numpy.nan, dtype=numpy.double),
                                        numpy.array(self.stemp2[charge_idx:drop_idx+1]),
                                        numpy.full(len(self.timex)-drop_idx-1, numpy.nan, dtype=numpy.double)))
                    elif not self.flagstart and not self.foregroundShowFullflag and self.autotimex and self.autotimexMode != 0:
                        visible_et = numpy.concatenate((
                                        numpy.array(self.stemp1[0:drop_idx+1]),
                                        numpy.full(len(self.timex)-drop_idx-1, numpy.nan, dtype=numpy.double)))
                        visible_bt = numpy.concatenate((
                                        numpy.array(self.stemp2[0:drop_idx+1]),
                                        numpy.full(len(self.timex)-drop_idx-1, numpy.nan, dtype=numpy.double)))
                    else:
                        visible_et = numpy.array(self.stemp1)
                        visible_bt = numpy.array(self.stemp2)

                    if self.swaplcds:
                        self.drawET(visible_et)
                        self.drawBT(visible_bt)
                    else:
                        self.drawBT(visible_bt)
                        self.drawET(visible_et)

                    if self.ETcurve:
                        self.handles.append(self.l_temp1)
                        self.labels.append(self.aw.arabicReshape(self.aw.ETname))
                    if self.BTcurve:
                        self.handles.append(self.l_temp2)
                        self.labels.append(self.aw.arabicReshape(self.aw.BTname))

                    if self.DeltaETflag:
                        self.handles.append(self.l_delta1)
                        self.labels.append(self.aw.arabicReshape(f'{deltaLabelMathPrefix}{self.aw.ETname}'))
                    if self.DeltaBTflag:
                        self.handles.append(self.l_delta2)
                        self.labels.append(self.aw.arabicReshape(f'{deltaLabelMathPrefix}{self.aw.BTname}'))

                    nrdevices = len(self.extradevices)

                    if nrdevices and not self.designerflag:
                        xtmpl1idx = 0
                        xtmpl2idx = 0
                        for i in range(nrdevices):
                            if self.aw.extraCurveVisibility1[i]:
                                idx1 = xtmpl1idx
                                xtmpl1idx = xtmpl1idx + 1
                                l1 = extraname1_subst[i]
                                if not l1.startswith('_'):
                                    self.handles.append(self.extratemp1lines[idx1])
                                    try:
                                        self.labels.append(self.aw.arabicReshape(l1.format(self.etypes[0],self.etypes[1],self.etypes[2],self.etypes[3])))
                                    except Exception: # pylint: disable=broad-except
                                        # a key error can occur triggered by the format if curley braces are used without reference
                                        self.labels.append(self.aw.arabicReshape(l1))
                            if self.aw.extraCurveVisibility2[i]:
                                idx2 = xtmpl2idx
                                xtmpl2idx = xtmpl2idx + 1
                                l2 = extraname2_subst[i]
                                if not l2.startswith('_'):
                                    self.handles.append(self.extratemp2lines[idx2])
                                    try:
                                        self.labels.append(self.aw.arabicReshape(l2.format(self.etypes[0],self.etypes[1],self.etypes[2],self.etypes[3])))
                                    except Exception: # pylint: disable=broad-except
                                        # a key error can occur triggered by the format if curley braces are used without reference
                                        self.labels.append(self.aw.arabicReshape(l2))

                    if self.eventsshowflag != 0 and self.eventsGraphflag in [2,3,4] and Nevents:
                        if E1_nonempty and self.showEtypes[0]:
                            self.handles.append(self.l_eventtype1dots)
                            self.labels.append(self.aw.arabicReshape(self.etypesf(0)))
                        if E2_nonempty and self.showEtypes[1]:
                            self.handles.append(self.l_eventtype2dots)
                            self.labels.append(self.aw.arabicReshape(self.etypesf(1)))
                        if E3_nonempty and self.showEtypes[2]:
                            self.handles.append(self.l_eventtype3dots)
                            self.labels.append(self.aw.arabicReshape(self.etypesf(2)))
                        if E4_nonempty and self.showEtypes[3]:
                            self.handles.append(self.l_eventtype4dots)
                            self.labels.append(self.aw.arabicReshape(self.etypesf(3)))

                    if not self.designerflag:
                        if self.BTcurve:
                            if self.flagstart: # no smoothed lines in this case, pass normal BT
                                self.l_annotations = self.place_annotations(
                                    self.TPalarmtimeindex,
                                    self.ylimit - self.ylimit_min,
                                    self.timex,self.timeindex,
                                    self.temp2,self.temp2)
                            else:
                                TP_index = self.aw.findTP()
                                if self.annotationsflag != 0:
                                    self.l_annotations = self.place_annotations(
                                        TP_index,self.ylimit - self.ylimit_min,
                                        self.timex,
                                        self.timeindex,
                                        self.temp2,
                                        self.stemp2)
                                if self.timeindex[6]:
                                    self.writestatistics(TP_index)
                            #add the time and temp annotations to the bt list
                            for x in self.l_annotations:
                                self.l_bteventannos.append(x)
                        elif self.timeindex[6]:
                            TP_index = self.aw.findTP()
                            self.writestatistics(TP_index)

                    if not sampling and not self.flagon and self.timeindex[6] and self.statssummary:
                        self.statsSummary()
                    else:
                        self.stats_summary_rect = None

                    if not sampling and not self.flagon and self.timeindex[6] and self.AUCshowFlag:
                        self.drawAUC()
                    #update label rotating_colors
                    for label in self.ax.xaxis.get_ticklabels():
                        label.set_color(self.palette['xlabel'])
                    for label in self.ax.yaxis.get_ticklabels():
                        label.set_color(self.palette['ylabel'])
                    if two_ax_mode and self.delta_ax is not None:
                        for label in self.delta_ax.yaxis.get_ticklabels():
                            label.set_color(self.palette['ylabel'])

                    #write legend
                    if self.legendloc and not sampling and not self.flagon and len(self.timex) > 2:
                        rcParams['path.effects'] = []
                        prop = self.aw.mpl_fontproperties.copy()
                        prop.set_size('x-small')
                        if len(self.handles) > 7:
                            ncol = int(math.ceil(len(self.handles)/4.))
                        elif len(self.handles) > 3:
                            ncol = int(math.ceil(len(self.handles)/2.))
                        else:
                            ncol = int(math.ceil(len(self.handles)))
                        if self.graphfont == 1:
                            self.labels = [self.__to_ascii(l) for l in self.labels]
                        loc:Union[int, Tuple[float,float]]
                        if self.legend is None:
                            if self.legendloc_pos is None:
                                loc = self.legendloc # a position selected in the axis dialog
                            else:
                                loc = self.legendloc_pos # a user define legend position set by drag-and-drop
                        else:
                            loc = self.legend._loc # pylint: disable=protected-access
                        try:
                            try:
                                leg = self.ax.legend(self.handles,self.labels, loc=loc,
                                    ncols=ncol,fancybox=True,prop=prop,shadow=False,frameon=True)
                            except Exception: # pylint: disable=broad-except
                                # ncol keyword argument to legend renamed to ncols in MPL 3.6, thus for older MPL versions we need to still use ncol
                                leg = self.ax.legend(self.handles,self.labels,loc=loc,ncol=ncol,fancybox=True,prop=prop,shadow=False,frameon=True)
                            try:
                                leg.set_in_layout(False) # remove legend from tight_layout calculation
                            except Exception: # pylint: disable=broad-except # set_in_layout not available in mpl<3.x
                                pass
                            self.legend = leg
                            self.legend_lines = leg.get_lines()
                            for h in leg.legendHandles:
                                h.set_picker(False) # we disable the click to hide on the handles feature
                                #h.set_picker(self.aw.draggable_text_box_picker) # as setting this picker results in non-termination
                            for l in leg.texts:
                                #l.set_picker(5)
                                l.set_picker(self.aw.draggable_text_box_picker)
                            try:
                                leg.set_draggable(state=True,use_blit=True)  #,update='bbox')
                                leg.set_picker(self.aw.draggable_text_box_picker)
                            except Exception: # pylint: disable=broad-except # not available in mpl<3.x
                                leg.draggable(state=True) # for mpl 2.x
                            frame = leg.get_frame()
                            frame.set_facecolor(self.palette['legendbg'])
                            frame.set_alpha(self.alpha['legendbg'])
                            frame.set_edgecolor(self.palette['legendborder'])
                            frame.set_linewidth(0.5)
                            for line,text in zip(leg.get_lines(), leg.get_texts()):
                                text.set_color(line.get_color())
                        except Exception: # pylint: disable=broad-except
                            pass

                        if self.patheffects:
                            rcParams['path.effects'] = [PathEffects.withStroke(linewidth=self.patheffects, foreground=self.palette['background'])]
                    else:
                        self.legend = None

                    # we create here the project line plots to have the accurate time axis after CHARGE
                    dashes_setup = [0.4,0.8,0.1,0.8] # simulating matplotlib 1.5 default on 2.0

                    #watermark image
                    self.placelogoimage()
                finally:
                    if self.updateBackgroundSemaphore.available() < 1:
                        self.updateBackgroundSemaphore.release(1)

                ############  ready to plot ############
#                with warnings.catch_warnings():
#                    warnings.simplefilter("ignore")
#                    self.fig.canvas.draw() # done also by updateBackground(), but the title on ON is not update if not called here too (might be a MPL bug in v3.1.2)!
                self.updateBackground() # update bitlblit backgrounds
                #######################################

                # add projection and AUC guide lines last as those are removed by updategraphics for optimized redrawing and not cached
                if self.projectFlag:
                    if self.BTcurve:
                        self.l_BTprojection, = self.ax.plot([], [],color = self.palette['bt'],
                                                    dashes=dashes_setup,
                                                    label=self.aw.arabicReshape(QApplication.translate('Label', 'BTprojection')),
                                                    linestyle = '-.', linewidth= 8, alpha = .3,sketch_params=None,path_effects=[])
                    if self.ETcurve:
                        self.l_ETprojection, = self.ax.plot([], [],color = self.palette['et'],
                                                    dashes=dashes_setup,
                                                    label=self.aw.arabicReshape(QApplication.translate('Label', 'ETprojection')),
                                                    linestyle = '-.', linewidth= 8, alpha = .3,sketch_params=None,path_effects=[])

                    if self.projectDeltaFlag and (self.DeltaBTflag or self.DeltaETflag):
                        trans = self.delta_ax.transData
                        if self.DeltaBTflag:
                            self.l_DeltaBTprojection, = self.ax.plot([], [],color = self.palette['deltabt'],
                                                        dashes=dashes_setup,
                                                        transform=trans,
                                                        label=self.aw.arabicReshape(QApplication.translate('Label', 'DeltaBTprojection')),
                                                        linestyle = '-.', linewidth= 8, alpha = .3,sketch_params=None,path_effects=[])
                        if self.DeltaETflag:
                            self.l_DeltaETprojection, = self.ax.plot([], [],color = self.palette['deltaet'],
                                                        dashes=dashes_setup,
                                                        transform=trans,
                                                        label=self.aw.arabicReshape(QApplication.translate('Label', 'DeltaETprojection')),
                                                        linestyle = '-.', linewidth= 8, alpha = .3,sketch_params=None,path_effects=[])

                if self.AUCguideFlag:
                    self.l_AUCguide = self.ax.axvline(0,visible=False,color = self.palette['aucguide'],
                                                label=self.aw.arabicReshape(QApplication.translate('Label', 'AUCguide')),
                                                linestyle = '-', linewidth= 1, alpha = .5,sketch_params=None,path_effects=[])

                if self.patheffects:
                    rcParams['path.effects'] = []

                # HACK
                # a bug in Qt/PyQt/mpl cause the canvas not to be repainted on load/switch/reset in fullscreen mode without this
                try:
                    if platform.system() == 'Darwin' and self.aw.app.allWindows()[0].visibility() == QWindow.Visibility.FullScreen or self.aw.full_screen_mode_active or self.aw.isFullScreen():
                        self.repaint()
                except Exception: # pylint: disable=broad-except
                    pass

            except Exception as ex: # pylint: disable=broad-except
                _log.exception(ex)
                _, _, exc_tb = sys.exc_info()
                self.adderror((QApplication.translate('Error Message','Exception:') + ' redraw() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
            finally:
                # we initialize at the end of the redraw the event and flag annotation custom position loaded from a profile as those should have been consumed by now
                self.l_annotations_pos_dict = {}
                self.l_event_flags_pos_dict = {}
                self.legendloc_pos = None
                if takelock and self.profileDataSemaphore.available() < 1:
                    self.profileDataSemaphore.release(1)

                # to allow the fit_title to work on the proper value we ping the redraw explicitly again after processing events
                # we need to use draw_idle here to allow Qt for relayout event processing
                # calling QApplication.processEvents() is not an option here as the event loop might not have been started yet
                # alternatively one could call canvas.draw() using a QTimer.singleShot(self.fig.canvas.draw())
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    self.fig.canvas.draw_idle()
                self.setProfileBackgroundTitle(titleB)

    def checkOverlap(self, anno): #, eventno, annotext) -> bool:
        if self.ax is None:
            return False
        overlapallowed = max(0,min(self.overlappct,100))/100  #the input is validated but this here to prevent any escapes
        overlap = False
        try:
            annocorners = self.annoboxCorners(anno)
            anno_x = anno.get_unitless_position()[0]
            ax_xlim = self.ax.get_xlim()
            # if annotation is off canvas, the display coordinates are not reliable thus we exclude this one from the check
            if anno_x < ax_xlim[0] or anno_x > ax_xlim[1]:
                _log.debug('Event annotation off canvas: %s, ax_xlim=%s', anno,ax_xlim)
                return False
            xl = annocorners[0]
            xr = annocorners[1]
            yl = annocorners[2]
            yu = annocorners[3]
            area = (xr - xl) * (yu - yl)
            for ol in self.overlapList:
                o_xl = ol[0]
                o_xr = ol[1]
                o_yl = ol[2]
                o_yu = ol[3]
                o_area = (o_xr - o_xl) * (o_yu - o_yl)
                dx = min(xr, o_xr) - max(xl, o_xl)
                dy = min(yu, o_yu) - max(yl, o_yl)
                if (dx>=0) and (dy>=0) and dx*dy/min(area,o_area) > overlapallowed:
                    overlap = True
                    break
            if not overlap:
                # note to self, the eventno and annotext can be removed from the list.  Only here for debug prints
                self.overlapList.append((xl,xr,yl,yu)) #,eventno,annotext))
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' checkOverlap() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
        return overlap

    def annoboxCorners(self,anno):
        if self.ax is None:
            return 0,0,0,0
        f = self.ax.get_figure()
        r = f.canvas.get_renderer() # this can fail for PDF generation with 'FigureCanvasPdf' object has no attribute 'get_renderer'
        anno.update_bbox_position_size(renderer=r)
        bb = anno.get_window_extent(renderer=r) # bounding box in display space
        bbox_data = self.ax.transData.inverted().transform(bb)
        bbox = Bbox(bbox_data) # x0, y0, width, height
        return (bbox.bounds[0],bbox.bounds[0]+bbox.bounds[2],bbox.bounds[1],bbox.bounds[1]+bbox.bounds[3])  # x0, x1, y0, y1

    def parseSpecialeventannotation(self,eventanno, eventnum, applyto='foreground', postFCs=False):
        try:
            #background curve values
            if applyto == 'background':
                e = self.backgroundEvalues[eventnum]
                y1 = str(self.aw.float2float(self.temp1B[self.backgroundEvents[eventnum]],self.LCDdecimalplaces))
                y2 = str(self.aw.float2float(self.temp2B[self.backgroundEvents[eventnum]],self.LCDdecimalplaces))
                try:
                    delta1 = str(self.aw.float2float(self.delta1B[self.backgroundEvents[eventnum]])) if self.delta1B[self.backgroundEvents[eventnum]] is not None else '--'
                except Exception: # pylint: disable=broad-except
                    delta1 = '\u03C5\u03c5'
                try:
                    delta2 = str(self.aw.float2float(self.delta2B[self.backgroundEvents[eventnum]])) if self.delta2B[self.backgroundEvents[eventnum]] is not None else '--'
                except Exception: # pylint: disable=broad-except
                    delta2 = '\u03C5\u03c5'
                descr = str(self.backgroundEStrings[eventnum])
                etype = str(self.Betypes[self.backgroundEtypes[eventnum]])
                sliderunit = str(self.aw.eventsliderunits[self.backgroundEtypes[eventnum]])

                if self.timeindexB[2] > 0 and self.timeB[self.backgroundEvents[eventnum]] > self.timeB[self.timeindexB[2]]:
                    postFCs = True
                    dtr = str(self.aw.float2float(100 * (self.timeB[self.backgroundEvents[eventnum]] - self.timeB[self.timeindexB[2]]) / (self.timeB[self.backgroundEvents[eventnum]] - self.timeB[self.timeindexB[0]]),1))
                else:
                    postFCs = False
                    dtr = '0'
                if self.timeindexB[2] > 0:
                    _dfcs = self.aw.float2float(self.timeB[self.backgroundEvents[eventnum]] - self.timeB[self.timeindexB[2]],0)
                    dfcs = str(_dfcs)
                    dfcs_ms = stringfromseconds(_dfcs,False)
                else:
                    dfcs = '*'
                    dfcs_ms = '*'
                if self.timeindexB[2] > 0 and self.timeB[self.backgroundEvents[eventnum]] < self.timeB[self.timeindexB[2]]:
                    _prefcs = self.aw.float2float(self.timeB[self.timeindexB[2]] - self.timeB[self.backgroundEvents[eventnum]],0)
                    prefcs = str(_prefcs)
                    prefcs_ms = stringfromseconds(_prefcs,False)
                else:
                    prefcs = '*'
                    prefcs_ms = '*'
                if self.timeindexB[0] > -1:
                    _dcharge = self.aw.float2float(self.timeB[self.backgroundEvents[eventnum]] - self.timeB[self.timeindexB[0]],0)
                    dcharge = str(_dcharge)
                    dcharge_ms = stringfromseconds(_dcharge,False)
                else:
                    dcharge = '*'
                    dcharge_ms = '*'
                fcsWindow = not postFCs and (self.timeB[self.timeindexB[2]] - self.timeB[self.backgroundEvents[eventnum]]) < 90

            # plug values for the previews
            elif applyto == 'preview':
                if eventnum == 1:
                    e = 8.0  #70
                if eventnum == 2:
                    e = 8.0  #70
                e = 7.0 if eventnum == 3 else 6.0
                y1 = '420' if self.mode=='F' else '210'
                y2 = '340' if self.mode=='F' else '170'
                delta1 = '18.2' if self.mode=='F' else '9.1'
                delta2 = '33.4' if self.mode=='F' else '16.2'
                descr = 'Full'
                etype = 'Air'
                sliderunit = 'kPa'
                dcharge = '340' if self.mode=='F' else '170'
                dcharge_ms = stringfromseconds(int(dcharge))
                dfcs = '47'
                dfcs_ms = stringfromseconds(int(dfcs))
                prefcs = '50'
                prefcs_ms = stringfromseconds(int(prefcs))
                dtr = '12'
                fcsWindow = not bool(postFCs)
                #postFCs supplied in the parseSpecialeventannotation() call

            # foreground curve values
            else:
                e = self.specialeventsvalue[eventnum]
                y1 = str(self.aw.float2float(self.temp1[self.specialevents[eventnum]],self.LCDdecimalplaces))
                y2 = str(self.aw.float2float(self.temp2[self.specialevents[eventnum]],self.LCDdecimalplaces))
                try:
                    delta1 = str(self.aw.float2float(self.delta1[self.specialevents[eventnum]])) if self.delta1[self.specialevents[eventnum]] is not None else '--'
                except Exception: # pylint: disable=broad-except
                    delta1 = '\u03C5\u03c5'
                try:
                    delta2 = str(self.aw.float2float(self.delta2[self.specialevents[eventnum]])) if self.delta2[self.specialevents[eventnum]] is not None else '--'
                except Exception: # pylint: disable=broad-except
                    delta2 = '\u03C5\u03c5'
                descr = str(self.specialeventsStrings[eventnum])
                etype = str(self.etypes[self.specialeventstype[eventnum]])
                sliderunit = str(self.aw.eventsliderunits[self.specialeventstype[eventnum]])

                if self.timeindex[2] > 0 and self.timex[self.specialevents[eventnum]] > self.timex[self.timeindex[2]]:
                    postFCs = True
                    dtr = str(self.aw.float2float(100 * (self.timex[self.specialevents[eventnum]] - self.timex[self.timeindex[2]]) / (self.timex[self.specialevents[eventnum]] - self.timex[self.timeindex[0]]),1))
                else:
                    postFCs = False
                    dtr = '0'
                if self.timeindex[2] > 0:
                    _dfcs = self.aw.float2float(self.timex[self.specialevents[eventnum]] - self.timex[self.timeindex[2]],0)
                    dfcs = str(_dfcs)
                    dfcs_ms = stringfromseconds(_dfcs,False)
#                    print(f'{dfcs_ms=}')
                else:
                    dfcs = '*'
                    dfcs_ms = '*'
                if self.timeindex[2] > 0 and self.timex[self.specialevents[eventnum]] < self.timex[self.timeindex[2]]:
                    _prefcs = self.aw.float2float(self.timex[self.timeindex[2]] - self.timex[self.specialevents[eventnum]],0)
                    prefcs = str(_prefcs)
                    prefcs_ms = stringfromseconds(_prefcs,False)
                else:
                    prefcs = '*'
                    prefcs_ms = '*'
                if self.timeindex[0] > -1:
                    _dcharge = self.aw.float2float(self.timex[self.specialevents[eventnum]] - self.timex[self.timeindex[0]],0)
                    dcharge = str(_dcharge)
                    dcharge_ms = stringfromseconds(_dcharge,False)
                else:
                    dcharge = '*'
                    dcharge_ms = '*'
                fcsWindow = not postFCs and self.timex[self.timeindex[2]] - self.timex[self.specialevents[eventnum]] < 90

            # Caution - the event field "E" is position dependent and must be the first entry in the fields list
            fields = [
                ('E', str(self.eventsInternal2ExternalValue(e))),
                ('Y1', y1),
                ('Y2', y2),
                ('descr', descr),
                ('type', etype),
                ('sldrunit', sliderunit),
                ('dCHARGE_ms', dcharge_ms),
                ('dFCs_ms', dfcs_ms),
                ('dCHARGE', dcharge),
                ('dFCs', dfcs),
                ('preFCs_ms', prefcs_ms),
                ('preFCs', prefcs),
                ('DTR', dtr),
                ('mode', self.mode),
                ('degmode', f'\u00b0{self.mode}'),
                ('degmin', f'\u00b0{self.mode}/min'),
                ('deg', '\u00b0'),
                ('R1degmin', f'{delta1}\u00b0{self.mode}/min'),
                ('R2degmin', f'{delta2}\u00b0{self.mode}/min'),
                ('R1', delta1),
                ('R2', delta2),
                ('squot', "'"),
                ('quot', '"'),
                ]

            fieldDelim = '~'
            #delimiter to show before FCs only
            preFCsDelim = "'"
            #delimiter to show after FCs only
            postFCsDelim = '"'
            #delimiter to show within a window before FCs only
            fcsWindowDelim = '`'
            #delimiter for explicit value substitutions
            nominalDelimopen = '{'
            nominalDelimclose = '}'
            nominalstringDelim = '|'
            _ignorecase = re.IGNORECASE  # @UndefinedVariable

            #newlines can sneak in from cut and paste from help page
            eventanno = eventanno.replace('\n', '')

            #text between single quotes ' will show only before FCs
            eventanno = re.sub(r'{pd}([^{pd}]+){pd}'.format(pd=preFCsDelim),
                r'\1',eventanno) if not postFCs else re.sub(r'{pd}([^{pd}]+){pd}'.format(pd=preFCsDelim),
                r'',eventanno)
            #text between double quotes " will show only after FCs
            eventanno = re.sub(r'{pd}([^{pd}]+){pd}'.format(pd=postFCsDelim),
                r'\1',eventanno) if postFCs else re.sub(r'{pd}([^{pd}]+){pd}'.format(pd=postFCsDelim),
                r'',eventanno)

            #text between back ticks ` will show only within 90 seconds before FCs
            eventanno = re.sub(r'{wd}([^{wd}]+){wd}'.format(wd=fcsWindowDelim),
                r'\1',eventanno) if (fcsWindow) else re.sub(r'{wd}([^{wd}]+){wd}'.format(wd=fcsWindowDelim),
                r'',eventanno)

            # substitute numeric to nominal values if in the annotationstring
            #
            # Caution - the event field "E" is position dependent and must be the first entry in the fields list
            # The event field E is implied in the Annotation string which should take the following form.  Enclosed by
            #    curly brackets, entries consist of a value followed immediately (no space) by a text string.  Entries are
            #    separated by a vertical bar '|'.
            #   {20Fresh Cut Grass|50Hay|80Baking Bread|100A Point}
            # Event values that do not match any value in the Annotation string return an empty string ''.
            #
            ##debug - things to watch out for in testing:
            # does the matchedgroup(4) always persist after the pattern.sub() above?
            # does the pattern.split always result in the same list pattern?  ex:
            #     ['', '20', 'Fresh Cut Grass', '|', '50', 'Hay', '|', '80', 'Baking Bread', '|', '100', 'A Point', '']
            pattern = re.compile(r'.*{ndo}(?P<nominalstr>[^{ndc}]+){ndc}'.format(ndo=nominalDelimopen,ndc=nominalDelimclose),_ignorecase)
            matched = pattern.match(eventanno)
            if matched is not None:
                pattern = re.compile(r'([0-9]+)([A-Za-z]+[A-Za-z 0-9]+)',_ignorecase)
                matches = pattern.split(matched.group('nominalstr'))
                #example form of the matches list ['', '20', 'Fresh Cut Grass', '|', '50', 'Hay', '|', '80', 'Baking Bread', '']
                replacestring = ''
                j = 1
                while j < len(matches):
                    if fields[0][1] == matches[j]:
                        replacestring = matches[j+1]
                        break
                    j += 3
                pattern = re.compile(r'({ndo}[^{ndc}]+{ndc})'.format(ndo=nominalDelimopen,ndc=nominalDelimclose))
                eventanno = pattern.sub(replacestring,eventanno)

            # make all the remaining substitutions
            for field in fields:
                pattern = re.compile(r'(.*{})({})(?P<mathop>[/*+-][0-9.]+)?(({}[0-9]+[A-Za-z]+[A-Za-z 0-9]+)+)?'.format( # pylint: disable=consider-using-f-string
                    fieldDelim,field[0],nominalstringDelim),_ignorecase)
                matched = pattern.match(eventanno)
                if matched is not None:

                    # get the value associated with the field
                    replacestring = str(field[1])
                    # do simple math if an operator is in the string
                    if matched.group('mathop') is not None:
                        replacestring += matched.group('mathop')
                        replacestring = str(self.aw.float2float(eval(replacestring),1)) # pylint: disable=eval-used

                    pattern = re.compile(fr'{fieldDelim}{field[0]}([/*+-][0-9.]+)?',_ignorecase)
                    eventanno = pattern.sub(replacestring,eventanno)

        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' parseSpecialeventannotation() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
            eventanno = ''

        return eventanno

    #watermark image
    def placelogoimage(self):
        if (self.flagon and self.aw.logoimgflag) or self.ax is None:  #if hide during roast
            return
        try:
            if len(self.aw.logofilename) == 0 or self.logoimg is None:
                return
            img_height_pixels, img_width_pixels, _ = self.logoimg.shape
            img_aspect = img_height_pixels / img_width_pixels
            coord_axes_middle_Display = self.ax.transAxes.transform((.5,.5))
            coord_axes_upperright_Display = self.ax.transAxes.transform((1.,1.))
            coord_axes_lowerleft_Display = self.ax.transAxes.transform((0.,0.))
            coord_axes_height_pixels = coord_axes_upperright_Display[1] - coord_axes_lowerleft_Display[1]
            coord_axes_width_pixels = coord_axes_upperright_Display[0] - coord_axes_lowerleft_Display[0]
            coord_axes_aspect = coord_axes_height_pixels / coord_axes_width_pixels
            if img_aspect >= coord_axes_aspect:
                scale = min(1., coord_axes_height_pixels / img_height_pixels)
            else:
                scale = min(1., coord_axes_width_pixels / img_width_pixels)

            corner_pixels = [0.,0.,0.,0.]
            corner_pixels[0] = coord_axes_middle_Display[0] - (scale * img_width_pixels / 2)
            corner_pixels[1] = coord_axes_middle_Display[1] - (scale * img_height_pixels / 2)
            corner_pixels[2] = corner_pixels[0] + scale * img_width_pixels
            corner_pixels[3] = corner_pixels[1] + scale * img_height_pixels
            ll_corner_axes = self.ax.transData.inverted().transform_point((corner_pixels[0],corner_pixels[1]))
            ur_corner_axes = self.ax.transData.inverted().transform_point((corner_pixels[2],corner_pixels[3]))
            extent = [ll_corner_axes[0], ur_corner_axes[0], ll_corner_axes[1], ur_corner_axes[1]]
            if self.ai is not None:
                try:
                    self.ai.remove()
                except Exception: # pylint: disable=broad-except
                    pass
            self.ai = self.ax.imshow(self.logoimg, zorder=0, extent=extent, alpha=self.aw.logoimgalpha/10, aspect='auto', resample=False)

        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' placelogoimage() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))

    # Convert QImage to numpy array
    @staticmethod
    def convertQImageToNumpyArray(img):
        img = img.convertToFormat(QImage.Format.Format_RGBA8888)
        width = img.width()
        height = img.height()
        imgsize = img.bits()
        try:
            imgsize.setsize(img.sizeInBytes())
        except Exception: # pylint: disable=broad-except
            imgsize.setsize(img.byteCount()) # byteCount() is deprecated, but kept here for compatibility with older Qt versions
        return numpy.array(imgsize).reshape((height, width, int(32/8)))

    #watermark image
    def logoloadfile(self,filename=None):
        try:
            if not filename:
                filename = self.aw.ArtisanOpenFileDialog(msg=QApplication.translate('Message','Load Image File'),ext='*.png *.jpg')
            if len(filename) == 0:
                return
            newImage = QImage()
            if newImage.load(filename):
                self.logoimg = self.convertQImageToNumpyArray(newImage)
                self.aw.logofilename = filename
                self.aw.sendmessage(QApplication.translate('Message','Loaded watermark image {0}').format(filename))
                QTimer.singleShot(500, lambda : self.redraw(recomputeAllDeltas=False)) #some time needed before the redraw on artisan start with no profile loaded.  processevents() does not work here.
            else:
                self.aw.sendmessage(QApplication.translate('Message','Unable to load watermark image {0}').format(filename))
                _log.info('Unable to load watermark image %s', filename)
                self.aw.logofilename = ''
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' logoloadfile() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
            self.aw.logofilename = ''

    #return a 'roast of the day' string with ordinals when english
    def roastOfTheDay(self,roastbatchpos):
        rotd_str = ''  #return an empty string if roastbatchpos is None
        if roastbatchpos is not None:
            #add an ordinal suffix for english
            if self.locale_str == 'en':
                prefix = ''
                suffix = f"{ {1: 'st', 2: 'nd', 3: 'rd'}.get(0 if roastbatchpos % 100 in (11,12,13) else roastbatchpos % 10, 'th')}" # noqa: E731
            else:
                prefix = '#'
                suffix = ''
            rotd_str = f'{prefix}{roastbatchpos}{suffix} {QApplication.translate("AddlInfo", "Roast of the Day")}'
        return rotd_str

    #add stats summary to graph
    def statsSummary(self):
        if self.ax is None:
            return
        import textwrap
        try:
            skipline = '\n'
            statstr_segments = []
            if self.statssummary:
                cp = self.aw.computedProfileInformation()  # get all the computed profile information

                #Admin Info Section
                if self.roastbatchnr > 0:
                    statstr_segments += [self.roastbatchprefix, str(self.roastbatchnr)]
                if self.title != QApplication.translate('Scope Title', 'Roaster Scope'):
                    if statstr_segments != []:
                        statstr_segments.append(' ')
                    statstr_segments.append(self.title)
                statstr_segments += [
                    skipline,
                    self.roastdate.date().toString(),
                    ' ',
                    self.roastdate.time().toString()]

                # build roast of the day string
                if self.roastbatchpos is not None and self.roastbatchpos != 0:
                    statstr_segments += [f'\n{self.roastOfTheDay(self.roastbatchpos)}']

                if self.ambientTemp not in [None,0] or self.ambient_humidity not in [None,0] or self.ambient_pressure not in [None,0]:
                    statstr_segments.append(skipline)
                    if self.ambientTemp not in [None,0]:
                        statstr_segments += [str(int(round(self.ambientTemp))), '\u00b0', self.mode, '  ']
                    if self.ambient_humidity not in [None,0]:
                        statstr_segments += [str(int(round(self.ambient_humidity))), '%  ']
                    if self.ambient_pressure not in [None,0]:
                        statstr_segments += [str(self.aw.float2float(self.ambient_pressure,2)), 'hPa']
                if self.roastertype or self.drumspeed:
                    statstr_segments.append(skipline)
                    if self.roastertype:
                        statstr_segments += [self.roastertype, ' ']
                    if self.drumspeed:
                        statstr_segments += ['(', self.drumspeed, QApplication.translate('Label', 'RPM'), ')']

                #Green Beans Info Section
                statstr_segments.append(skipline)
                if self.beans is not None and len(self.beans)>0:
                    statstr_segments.append(skipline)
                    beans_lines = textwrap.wrap(self.beans, width=self.statsmaxchrperline)
                    statstr_segments.append(beans_lines[0])
                    if len(beans_lines)>1:
                        statstr_segments += [skipline, ' ', beans_lines[1]]
                        if len(beans_lines)>2:
                            statstr_segments.append('..')

                if self.beansize_min or self.beansize_max:
                    statstr_segments += ['\n',  QApplication.translate('AddlInfo', 'Screen Size'), ': ']
                    if self.beansize_min:
                        statstr_segments.append(str(int(round(self.beansize_min))))
                    if self.beansize_max:
                        if self.beansize_min:
                            statstr_segments.append('/')
                        statstr_segments.append(str(int(round(self.beansize_max))))

                if self.density[0]!=0 and self.density[2] != 0:
                    statstr_segments += ['\n', QApplication.translate('AddlInfo', 'Density Green'), ': ',
                        str(self.aw.float2float(self.density[0]/self.density[2],2)), ' ', self.density[1], '/', self.density[3]]
                if self.moisture_greens:
                    statstr_segments += ['\n', QApplication.translate('AddlInfo', 'Moisture Green'), ': ', str(self.aw.float2float(self.moisture_greens,1)), '%']
                if self.weight[0] != 0:
                    if self.weight[2] == 'g':
                        w =str(self.aw.float2float(self.weight[0],0))
                    else:
                        w = str(self.aw.float2float(self.weight[0],2))
                    statstr_segments += ['\n', QApplication.translate('AddlInfo', 'Batch Size') , ': ', w, self.weight[2], ' ']
                    if self.weight[1]:
                        statstr_segments += ['(-', str(self.aw.float2float(self.aw.weight_loss(self.weight[0],self.weight[1]),1)), '%)']

                # Roast Info Section
                statstr_segments.append(skipline)
                if 'roasted_density' in cp:
                    statstr_segments += ['\n', QApplication.translate('AddlInfo', 'Density Roasted'), ': ', str(cp['roasted_density']),
                        ' ', self.density[1], '/', self.density[3]]
                if self.moisture_roasted:
                    statstr_segments += ['\n', QApplication.translate('AddlInfo', 'Moisture Roasted'), ': ', str(self.aw.float2float(self.moisture_roasted,1)), '%']
                if self.whole_color > 0:
                    statstr_segments += ['\n', QApplication.translate('AddlInfo', 'Whole Color'), ': #', str(self.whole_color), ' ',
                        str(self.color_systems[self.color_system_idx])]
                if self.ground_color > 0:
                    statstr_segments += ['\n', QApplication.translate('AddlInfo', 'Ground Color'), ': #', str(self.ground_color), ' ',
                        str(self.color_systems[self.color_system_idx])]
                if 'BTU_batch' in cp and cp['BTU_batch']:
                    statstr_segments += ['\n', QApplication.translate('AddlInfo', 'Energy'), ': ',
                        str(self.aw.float2float(self.convertHeat(cp['BTU_batch'],0,3),2)), 'kWh']
                    if 'BTU_batch_per_green_kg' in cp and cp['BTU_batch_per_green_kg']:
                        statstr_segments += [' (', str(self.aw.float2float(self.convertHeat(cp['BTU_batch_per_green_kg'], 0,3), 2)), 'kWh/kg)']
                if 'CO2_batch' in cp and cp['CO2_batch']:
                    statstr_segments += ['\n', QApplication.translate('AddlInfo', 'CO2'), ': ', str(self.aw.float2float(cp['CO2_batch'],0)),'g']
                    if 'CO2_batch_per_green_kg' in cp and cp['CO2_batch_per_green_kg']:
                        statstr_segments += [' (', str(self.aw.float2float(cp['CO2_batch_per_green_kg'],0)), 'g/kg)']
                if cp['AUC']:
                    statstr_segments += ['\n', QApplication.translate('AddlInfo', 'AUC'), ': ', str(cp['AUC']), 'C*min [', str(cp['AUCbase']), '\u00b0', self.mode, ']']

                def render_notes(notes,statstr_segments):
                    if notes is not None and len(notes)>0:
                        notes_lines = textwrap.wrap(notes, width=self.statsmaxchrperline)
                        if len(notes_lines)>0:
                            statstr_segments += [skipline, notes_lines[0]]
                            if len(notes_lines)>1:
                                statstr_segments += [skipline, '  ', notes_lines[1]]
                                if len(notes_lines)>2:
                                    statstr_segments.append('..')

                render_notes(self.roastingnotes,statstr_segments)

                cupping_score, cupping_all_default = self.aw.cuppingSum(self.flavors)
                if not cupping_all_default:
                    statstr_segments += ['\n', QApplication.translate('HTML Report Template', 'Cupping:'), ' ', str(self.aw.float2float(cupping_score))]

                render_notes(self.cuppingnotes,statstr_segments)

                # Trim the long lines
                trimmedstatstr_segments:List[str] = []
                for l in ''.join(statstr_segments).split('\n'):
                    if trimmedstatstr_segments:
                        trimmedstatstr_segments.append('\n')
                    trimmedstatstr_segments.append(l[:self.statsmaxchrperline])
                    if len(l) > self.statsmaxchrperline:
                        trimmedstatstr_segments.append('..')
                statstr = ''.join(trimmedstatstr_segments)

                #defaults appropriate for default font
                prop = self.aw.mpl_fontproperties.copy()
                prop_size = 'small'
                prop.set_size(prop_size)
                fc = self.palette['statsanalysisbkgnd']  #fill color
                tc = self.aw.labelBorW(fc)                   #text color
                a = self.alpha['statsanalysisbkgnd']     #alpha
                ls = 1.7                     #linespacing
                if self.graphfont == 9:   #Dijkstra
                    ls = 1.2
                border = 10                  #space around outside of text box (in seconds)
                margin = 4                   #text to edge of text box

                #adjust for other fonts
                if self.graphfont == 1:   #Humor
                    prop_size = 'x-small'
                    prop.set_size(prop_size)
                if self.graphfont == 2:   #Comic
                    ls = 1.2
                if self.graphfont == 9:   #Dijkstra
                    ls = 1.2

                if self.legendloc != 1:
                    # legend not in upper right
                    statsheight = self.ylimit - (0.08 * (self.ylimit - self.ylimit_min)) # standard positioning
                else:
                    # legend in upper right
                    statsheight = self.ylimit - (0.13 * (self.ylimit - self.ylimit_min))

                if self.timeindex[0] != -1:
                    start = self.timex[self.timeindex[0]]
                else:
                    start = 0

                # position the stats summary relative to the right hand edge of the graph
                # when in BBP mode the graph will end at CHARGE, so we must look for the CHARGE annotation instead of DROP.
                if not self.autotimex or self.autotimexMode != 2:
                    event_label = QApplication.translate('Scope Annotation','DROP {0}').replace(' {0}','')
                else:
                    event_label = QApplication.translate('Scope Annotation','CHARGE')
                _,_,eventtext_end = self.eventtextBounds(event_label,start,statsheight,ls,prop,fc)
                stats_textbox_bounds = self.statstextboxBounds(self.ax.get_xlim()[1]+border,statsheight,statstr,ls,prop,fc)
                stats_textbox_width = stats_textbox_bounds[2]
                stats_textbox_height = stats_textbox_bounds[3]
                pos_x = self.ax.get_xlim()[1]-stats_textbox_width-border

                if self.autotimex:
                    self.endofx = eventtext_end + stats_textbox_width + 2*border # provide room for the stats
                    self.xaxistosm(redraw=False)  # recalculate the x axis

                    prev_stats_textbox_width = 0
                    #set the maximum number of iterations
                    for _ in range(2, 20):
                        _,_,eventtext_end = self.eventtextBounds(event_label,start,statsheight,ls,prop,fc)
                        stats_textbox_bounds = self.statstextboxBounds(self.ax.get_xlim()[1]+border,statsheight,statstr,ls,prop,fc)
                        stats_textbox_width = stats_textbox_bounds[2]
                        stats_textbox_height = stats_textbox_bounds[3]

                        # position the stats summary relative to the right edge of the drop text
                        self.endofx = eventtext_end + stats_textbox_width + 2*border #provide room for the stats
                        self.xaxistosm(redraw=False)
                        #break the loop if it looks like stats_textbox_width has converged
                        if abs(prev_stats_textbox_width - stats_textbox_width) < .2:
                            break
                        prev_stats_textbox_width = stats_textbox_width

                    pos_x = eventtext_end + border + start

                pos_y = statsheight
#               self.stats_summary_rect = patches.Rectangle((pos_x-margin,pos_y+margin),stats_textbox_width+2*margin,-stats_textbox_height-2*margin,linewidth=0.5,edgecolor=self.palette["grid"],facecolor=fc,fill=True,alpha=a,zorder=10)
                self.stats_summary_rect = patches.Rectangle((pos_x-margin,pos_y - (stats_textbox_height + 2*margin)),stats_textbox_width+2*margin,stats_textbox_height+3*margin,linewidth=0.5,edgecolor=self.palette['grid'],facecolor=fc,fill=True,alpha=a,zorder=10)
                self.ax.add_patch(self.stats_summary_rect)

                text = self.ax.text(pos_x, pos_y, statstr, verticalalignment='top',linespacing=ls,
                    fontsize=prop_size,
                    color=tc,zorder=11,path_effects=[])
                text.set_in_layout(False)
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' statsSummary() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))

    def statstextboxBounds(self,x_pos,y_pos,textstr,ls,prop,fc):
        if self.ax is None:
            return 0,0,0,0

        with warnings.catch_warnings():
            # MPL will generate warnings for missing glyphs in some fonts
            warnings.simplefilter('ignore')
            t = self.ax.text(x_pos, y_pos, textstr, verticalalignment='top',linespacing=ls,fontproperties=prop,color=fc,path_effects=[])
            f = self.ax.get_figure()
            r = None
            try:
                r = f.canvas.get_renderer() # this might fail with 'FigureCanvasPdf' object has no attribute 'get_renderer' for PDF generation
            except Exception: # pylint: disable=broad-except
                pass
            if r is None:
                t.update_bbox_position_size()
            else:
                t.update_bbox_position_size(renderer=r)
            bb = t.get_window_extent(renderer=r) # bounding box in display space
            bbox_data = self.ax.transData.inverted().transform(bb)
            bbox = Bbox(bbox_data)
            t.remove()
            return bbox.bounds


    def eventtextBounds(self,event_label,x_pos,y_pos,ls,prop,fc):
        eventtext_width = 0
        eventtextstart = 0
        eventtext_end = 0
        try:
            if self.ax:
                eventtext_end = self.timex[-1] - x_pos #default for when Events Annotations is unchecked
                for child in self.ax.get_children():
                    if isinstance(child, mpl.text.Annotation):
                        eventtext = re.search(fr'.*\((.*?),.*({event_label}[ 0-9:]*)',str(child))
                        if eventtext:
                            eventtextstart = int(float(eventtext.group(1))) - x_pos
                            eventtext_width = self.statstextboxBounds(x_pos,y_pos,eventtext.group(2),ls,prop,fc)[2]
                            eventtext_end = eventtextstart + eventtext_width
        except Exception as e:  # pylint: disable=broad-except
            _log.exception(e)
        return eventtext_width,eventtextstart,eventtext_end

    # adjusts height of annotations
    #supporting function for self.redraw() used to find best height of annotations in graph to avoid annotating over previous annotations (unreadable) when close to each other
    def findtextgap(self, ystep_down, ystep_up, height1, height2, dd=0):
        d = self.ylimit - self.ylimit_min if dd <= 0 else dd
        init = int(d/12.0)
        gap = int(d/20.0)
        maxx = int(d/3.6)
        i = 0
        j = 0
        for i in range(init,maxx):
            if abs((height1 + ystep_up) - (height2+i)) > gap:
                break
        for j in range(init,maxx):
            if abs((height1 - ystep_down) - (height2 - j)) > gap:
                break
        return j,i  #return height of arm

    # adjust min/max limits of temperature sliders to the actual temperature mode
    def adjustTempSliders(self):
        if self.mode != self.mode_tempsliders:
            for i in range(4):
                if self.aw.eventslidertemp[i]:
                    if self.mode == 'C':
                        self.aw.eventslidermin[i] = int(round(fromFtoC(self.aw.eventslidermin[i])))
                        self.aw.eventslidermax[i] = int(round(fromFtoC(self.aw.eventslidermax[i])))
                    else:
                        self.aw.eventslidermin[i] = int(round(fromCtoF(self.aw.eventslidermin[i])))
                        self.aw.eventslidermax[i] = int(round(fromCtoF(self.aw.eventslidermax[i])))
            self.aw.updateSliderMinMax()
            self.mode_tempsliders = self.mode

    #sets the graph display in Fahrenheit mode
    def fahrenheitMode(self,setdefaultaxes=True):
        if setdefaultaxes:
            # just set it to the defaults to avoid strange conversion issues
            self.ylimit = self.ylimit_F_default
            self.ylimit_min = self.ylimit_min_F_default
            self.ygrid = self.ygrid_F_default
            self.zlimit = self.zlimit_F_default
            self.zlimit_min = self.zlimit_min_F_default
            self.zgrid = self.zgrid_F_default
        if self.mode == 'C':
            #change watermarks limits. dryphase1, dryphase2, midphase, and finish phase Y limits
            for i in range(4):
                self.phases[i] = int(round(fromCtoF(self.phases[i])))
            if self.step100temp is not None:
                self.step100temp = int(round(fromCtoF(self.step100temp)))
            self.AUCbase = int(round(fromCtoF(self.AUCbase)))
            self.alarmtemperature = [(fromCtoF(t) if t != 500 else t) for t in self.alarmtemperature]
            # conv Arduino mode
            if self.aw:
                self.aw.pidcontrol.conv2fahrenheit()
        if self.ax is not None:
            self.ax.set_ylabel('F',size=16,color = self.palette['ylabel']) #Write "F" on Y axis
        self.mode = 'F'
        if self.aw: # during initialization aw is still None!
            self.aw.FahrenheitAction.setDisabled(True)
            self.aw.CelsiusAction.setEnabled(True)
            self.aw.ConvertToFahrenheitAction.setDisabled(True)
            self.aw.ConvertToCelsiusAction.setEnabled(True)
            # configure dropfilter
            self.filterDropOut_tmin = self.filterDropOut_tmin_F_default
            self.filterDropOut_tmax = self.filterDropOut_tmax_F_default
            self.filterDropOut_spikeRoR_dRoR_limit = self.filterDropOut_spikeRoR_dRoR_limit_F_default
            self.adjustTempSliders()

    #sets the graph display in Celsius mode
    def celsiusMode(self,setdefaultaxes=True):
        if setdefaultaxes:
            self.ylimit = self.ylimit_C_default
            self.ylimit_min = self.ylimit_min_C_default
            self.ygrid = self.ygrid_C_default
            self.zlimit = self.zlimit_C_default
            self.zlimit_min = self.zlimit_min_C_default
            self.zgrid = self.zgrid_C_default
        if self.mode == 'F':
            #change watermarks limits. dryphase1, dryphase2, midphase, and finish phase Y limits
            for i in range(4):
                self.phases[i] = int(round(fromFtoC(self.phases[i])))
            if self.step100temp is not None:
                self.step100temp = int(round(fromFtoC(self.step100temp)))
            self.AUCbase = int(round(fromFtoC(self.AUCbase)))
            self.alarmtemperature = [(fromFtoC(t) if t != 500 else t) for t in self.alarmtemperature]
            # conv Arduino mode
            self.aw.pidcontrol.conv2celsius()
        if self.ax is not None:
            self.ax.set_ylabel('C',size=16,color = self.palette['ylabel']) #Write "C" on Y axis
        self.mode = 'C'
        if self.aw: # during initialization aw is still None
            self.aw.CelsiusAction.setDisabled(True)
            self.aw.FahrenheitAction.setEnabled(True)
            self.aw.ConvertToCelsiusAction.setDisabled(True)
            self.aw.ConvertToFahrenheitAction.setEnabled(True)
            # configure dropfilter
            self.filterDropOut_tmin = self.filterDropOut_tmin_C_default
            self.filterDropOut_tmax = self.filterDropOut_tmax_C_default
            self.filterDropOut_spikeRoR_dRoR_limit = self.filterDropOut_spikeRoR_dRoR_limit_C_default
            self.adjustTempSliders()

    @pyqtSlot()
    @pyqtSlot(bool)
    def fahrenheitModeRedraw(self,_=False):
        self.fahrenheitMode()
        self.redraw()

    @pyqtSlot()
    @pyqtSlot(bool)
    def celsiusModeRedraw(self,_=False):
        self.celsiusMode()
        self.redraw()

    @pyqtSlot()
    @pyqtSlot(bool)
    def convertTemperatureF(self,_=False):
        self.convertTemperature('F')

    @pyqtSlot()
    @pyqtSlot(bool)
    def convertTemperatureC(self,_=False):
        self.convertTemperature('C')

    #converts a loaded profile to a different temperature scale. t input is the requested mode (F or C).
    def convertTemperature(self,t,silent=False,setdefaultaxes=True):
        #verify there is a loaded profile
        profilelength = len(self.timex)
        if profilelength > 0 or self.background:
            if t == 'F':
                if silent:
                    reply = QMessageBox.StandardButton.Yes
                else:
                    string = QApplication.translate('Message', 'Convert profile data to Fahrenheit?')
                    reply = QMessageBox.question(self.aw, QApplication.translate('Message', 'Convert Profile Temperature'),string,
                            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel)
                if reply == QMessageBox.StandardButton.Cancel:
                    return
                if reply == QMessageBox.StandardButton.Yes:
                    if self.mode == 'C':
                        self.aw.CelsiusAction.setDisabled(True)
                        self.aw.FahrenheitAction.setEnabled(True)
                        self.aw.ConvertToCelsiusAction.setDisabled(True)
                        self.aw.ConvertToFahrenheitAction.setEnabled(True)
                        self.l_annotations_dict = {}
                        self.l_event_flags_dict = {}
                        for i in range(profilelength):
                            self.temp1[i] = fromCtoF(self.temp1[i])    #ET
                            self.temp2[i] = fromCtoF(self.temp2[i])    #BT
                            if self.delta1:
                                self.delta1[i] = RoRfromCtoF(self.delta1[i])  #Delta ET
                            if self.delta2:
                                self.delta2[i] = RoRfromCtoF(self.delta2[i])  #Delta BT
                            #extra devices curves
                            nextra = len(self.extratemp1)
                            if nextra:
                                for e in range(nextra):
                                    try:
                                        if not (len(self.extraNoneTempHint1) > e and self.extraNoneTempHint1[e]):
                                            self.extratemp1[e][i] = fromCtoF(self.extratemp1[e][i])
                                        if not (len(self.extraNoneTempHint2) > e and self.extraNoneTempHint2[e]):
                                            self.extratemp2[e][i] = fromCtoF(self.extratemp2[e][i])
                                    except Exception: # pylint: disable=broad-except
                                        pass
                        if self.ambientTemp is not None and self.ambientTemp != 0:
                            self.ambientTemp = fromCtoF(self.ambientTemp)  #ambient temperature
                        if self.greens_temp is not None and self.greens_temp != 0:
                            self.greens_temp = fromCtoF(self.greens_temp)

                        #prevents accidentally deleting a modified profile.
                        self.fileDirtySignal.emit()

                        #background
                        for i in range(len(self.timeB)):
                            self.temp1B[i] = fromCtoF(self.temp1B[i])
                            self.temp2B[i] = fromCtoF(self.temp2B[i])
                            self.stemp1B[i] = fromCtoF(self.stemp1B[i])
                            self.stemp2B[i] = fromCtoF(self.stemp2B[i])

                        self.fahrenheitMode(setdefaultaxes=setdefaultaxes)
                        if not silent:
                            self.aw.sendmessage(QApplication.translate('Message','Profile changed to Fahrenheit'))

                    elif not silent:
                        QMessageBox.information(self.aw, QApplication.translate('Message', 'Convert Profile Temperature'),
                                                QApplication.translate('Message', 'Unable to comply. You already are in Fahrenheit'))
                        self.aw.sendmessage(QApplication.translate('Message','Profile not changed'))
                        return

            elif t == 'C':
                if silent:
                    reply = QMessageBox.StandardButton.Yes
                else:
                    string = QApplication.translate('Message', 'Convert profile data to Celsius?')
                    reply = QMessageBox.question(self.aw, QApplication.translate('Message', 'Convert Profile Temperature'),string,
                            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel)
                if reply == QMessageBox.StandardButton.Cancel:
                    return
                if reply == QMessageBox.StandardButton.Yes:
                    if self.mode == 'F':
                        self.aw.ConvertToFahrenheitAction.setDisabled(True)
                        self.aw.ConvertToCelsiusAction.setEnabled(True)
                        self.aw.FahrenheitAction.setDisabled(True)
                        self.aw.CelsiusAction.setEnabled(True)
                        self.l_annotations_dict = {}
                        self.l_event_flags_dict = {}
                        for i in range(profilelength):
                            self.temp1[i] = fromFtoC(self.temp1[i])    #ET
                            self.temp2[i] = fromFtoC(self.temp2[i])    #BT
                            if self.device != 18 or self.aw.simulator is not None:
                                if self.delta1:
                                    self.delta1[i] = RoRfromFtoC(self.delta1[i])  #Delta ET
                                if self.delta2:
                                    self.delta2[i] = RoRfromFtoC(self.delta2[i])  #Delta BT
                            #extra devices curves
                            nextra = len(self.extratemp1)
                            if nextra:
                                for e in range(nextra):
                                    try:
                                        if not (len(self.extraNoneTempHint1) > e and self.extraNoneTempHint1[e]):
                                            self.extratemp1[e][i] = fromFtoC(self.extratemp1[e][i])
                                        if not (len(self.extraNoneTempHint2) > e and self.extraNoneTempHint2[e]):
                                            self.extratemp2[e][i] = fromFtoC(self.extratemp2[e][i])
                                    except Exception: # pylint: disable=broad-except
                                        pass

                        if self.ambientTemp is not None and self.ambientTemp != 0:
                            self.ambientTemp = fromFtoC(self.ambientTemp)  #ambient temperature
                        if self.greens_temp is not None and self.greens_temp != 0:
                            self.greens_temp = fromFtoC(self.greens_temp)

                        #prevents accidentally deleting a modified profile.
                        self.fileDirtySignal.emit()

                        #background
                        for i in range(len(self.timeB)):
                            self.temp1B[i] = fromFtoC(self.temp1B[i]) #ET B
                            self.temp2B[i] = fromFtoC(self.temp2B[i]) #BT B
                            self.stemp1B[i] = fromFtoC(self.stemp1B[i])
                            self.stemp2B[i] = fromFtoC(self.stemp2B[i])

                        self.celsiusMode(setdefaultaxes=setdefaultaxes)
                        if not silent:
                            self.aw.sendmessage(QApplication.translate('Message','Profile changed to Celsius'))

                    elif not silent:
                        QMessageBox.information(self.aw, QApplication.translate('Message', 'Convert Profile Temperature'),
                                                QApplication.translate('Message', 'Unable to comply. You already are in Celsius'))
                        self.aw.sendmessage(QApplication.translate('Message','Profile not changed'))
                        return

            if not silent:
                self.redraw(recomputeAllDeltas=True,smooth=True)

        elif not silent:
            QMessageBox.information(self.aw, QApplication.translate('Message', 'Convert Profile Scale'),
                                          QApplication.translate('Message', 'No profile data found'))

    @pyqtSlot()
    @pyqtSlot(bool)
    def changeGColor3(self,_=False):
        self.changeGColor(3)

    #selects color mode: input 1=color mode; input 2=black and white mode (printing); input 3 = customize colors
    def changeGColor(self,color):
        #load selected dictionary
        if color == 1:
            self.aw.sendmessage(QApplication.translate('Message','Colors set to defaults'))
            fname = os.path.join(getResourcePath(), 'Themes', application_name, 'Default.athm')
            if os.path.isfile(fname) and not self.flagon:
                self.aw.loadSettings_theme(fn=fname,remember=False,reset=False)
                self.aw.sendmessage(QApplication.translate('Message','Colors set to Default Theme'))
            else:
                for k in list(self.palette1.keys()):
                    self.palette[k] = self.palette1[k]
                self.backgroundmetcolor     = self.palette['et']
                self.backgroundbtcolor      = self.palette['bt']
                self.backgrounddeltaetcolor = self.palette['deltaet']
                self.backgrounddeltabtcolor = self.palette['deltabt']
                self.backgroundxtcolor      = self.palette['xt']
                self.backgroundytcolor      = self.palette['yt']
                self.EvalueColor = self.EvalueColor_default.copy()
                self.EvalueTextColor = self.EvalueTextColor_default.copy()
                self.aw.sendmessage(QApplication.translate('Message','Colors set to defaults'))
                self.aw.closeEventSettings()

        elif color == 2:
            self.aw.sendmessage(QApplication.translate('Message','Colors set to grey'))
            for k in list(self.palette.keys()):
                c = self.palette[k]
                nc = self.aw.convertToGreyscale(c)
                self.palette[k] = nc
            for i in range(len(self.extradevices)):
                c = self.extradevicecolor1[i]
                self.extradevicecolor1[i] = self.aw.convertToGreyscale(c)
                c = self.extradevicecolor2[i]
                self.extradevicecolor2[i] = self.aw.convertToGreyscale(c)
            for i,c in enumerate(self.EvalueColor):
                self.EvalueColor[i] = self.aw.convertToGreyscale(c)
            self.backgroundmetcolor     = self.aw.convertToGreyscale(self.backgroundmetcolor)
            self.backgroundbtcolor      = self.aw.convertToGreyscale(self.backgroundbtcolor)
            self.backgrounddeltaetcolor = self.aw.convertToGreyscale(self.backgrounddeltaetcolor)
            self.backgrounddeltabtcolor = self.aw.convertToGreyscale(self.backgrounddeltabtcolor)
            self.backgroundxtcolor      = self.aw.convertToGreyscale(self.backgroundxtcolor)
            self.backgroundytcolor      = self.aw.convertToGreyscale(self.backgroundytcolor)
            self.aw.setLCDsBW()
            self.aw.closeEventSettings()

        elif color == 3:
            from artisanlib.colors import graphColorDlg
            dialog = graphColorDlg(self.aw, self.aw, self.aw.graphColorDlg_activeTab)
            if dialog.exec():
                self.aw.graphColorDlg_activeTab = dialog.TabWidget.currentIndex()
                #
                self.palette['background'] = str(dialog.backgroundButton.text())
                self.palette['grid'] = str(dialog.gridButton.text())
                self.palette['ylabel'] = str(dialog.yButton.text())
                self.palette['xlabel'] = str(dialog.xButton.text())
                self.palette['title'] = str(dialog.titleButton.text())
                self.palette['rect1'] = str(dialog.rect1Button.text())
                self.palette['rect2'] = str(dialog.rect2Button.text())
                self.palette['rect3'] = str(dialog.rect3Button.text())
                self.palette['rect4'] = str(dialog.rect4Button.text())
                self.palette['rect5'] = str(dialog.rect5Button.text())
                self.palette['et'] = str(dialog.metButton.text())
                self.palette['bt'] = str(dialog.btButton.text())
                self.palette['deltaet'] = str(dialog.deltametButton.text())
                self.palette['deltabt'] = str(dialog.deltabtButton.text())
                self.palette['markers'] = str(dialog.markersButton.text())
                self.palette['text'] = str(dialog.textButton.text())
                self.palette['watermarks'] = str(dialog.watermarksButton.text())
                self.palette['timeguide'] = str(dialog.timeguideButton.text())
                self.palette['aucguide'] = str(dialog.aucguideButton.text())
                self.palette['aucarea'] = str(dialog.aucareaButton.text())
                self.palette['canvas'] = str(dialog.canvasButton.text())
                self.palette['legendbg'] = str(dialog.legendbgButton.text())
#                self.palette["legendbgalpha"] = str(dialog.legendbgalphaButton.text())
                self.palette['legendborder'] = str(dialog.legendborderButton.text())
                self.palette['specialeventbox'] = str(dialog.specialeventboxButton.text())
                self.palette['specialeventtext'] = str(dialog.specialeventtextButton.text())
                self.palette['bgeventmarker'] = str(dialog.bgeventmarkerButton.text())
                self.palette['bgeventtext'] = str(dialog.bgeventtextButton.text())
                self.palette['mettext'] = str(dialog.mettextButton.text())
                self.palette['metbox'] = str(dialog.metboxButton.text())
                self.backgroundmetcolor = str(dialog.bgmetButton.text())
                self.backgroundbtcolor  = str(dialog.bgbtButton.text())
                self.backgrounddeltaetcolor = str(dialog.bgdeltametButton.text())
                self.backgrounddeltabtcolor = str(dialog.bgdeltabtButton.text())
                self.backgroundxtcolor = str(dialog.bgextraButton.text())
                self.backgroundytcolor = str(dialog.bgextra2Button.text())
                self.aw.closeEventSettings()
            #deleteLater() will not work here as the dialog is still bound via the parent
            #dialog.deleteLater() # now we explicitly allow the dialog an its widgets to be GCed
            # the following will immediately release the memory despite this parent link
            QApplication.processEvents() # we ensure events concerning this dialog are processed before deletion
            try: # sip not supported on older PyQt versions (RPi!)
                sip.delete(dialog)
                #print(sip.isdeleted(dialog))
            except Exception:  # pylint: disable=broad-except
                pass

        #update screen with new colors
        self.aw.updateCanvasColors()
        self.aw.applyStandardButtonVisibility()
        self.aw.update_extraeventbuttons_visibility()
        self.fig.canvas.redraw()

    def clearFlavorChart(self):
        self.flavorchart_plotf = None
        self.flavorchart_angles = None
        self.flavorchart_plot = None
        self.flavorchart_fill = None
        self.flavorchart_labels = None
        self.flavorchart_total = None

    #draws a polar star graph to score cupping. It does not delete any profile data.
    def flavorchart(self):
        try:
            pi = math.pi

            # to trigger a recreation of the standard axis in redraw() we remove them completely
            self.ax = None
            self.delta_ax = None

            self.fig.clf()

            #create a new name ax1 instead of ax (ax is used when plotting profiles)

            if self.ax1 is not None:
                try:
                    self.fig.delaxes(self.ax1)
                except Exception: # pylint: disable=broad-except
                    pass
            self.ax1 = self.fig.add_subplot(111,projection='polar',facecolor='None') #) radar green facecolor='#d5de9c'

            # fixing yticks with matplotlib.ticker "FixedLocator"
            if self.ax1 is not None and self.flavorchart_angles is not None:
                try:
                    ticks_loc = self.ax1.get_yticks()
                    self.ax1.yaxis.set_major_locator(ticker.FixedLocator(ticks_loc))
                except Exception: # pylint: disable=broad-except
                    pass

                self.ax1.set_aspect(self.flavoraspect)

                self.aw.setFonts(redraw=False)

                #find number of divisions
                nflavors = len(self.flavors)      #last value of nflavors is used to close circle (same as flavors[0])


                sa = self.flavorstartangle % (360./nflavors)
                g_angle = numpy.arange(sa,(360.+sa),(360./nflavors))  #angles in degree
                self.ax1.set_thetagrids(g_angle)
                self.ax1.set_rmax(1.)
                self.ax1.set_autoscale_on(False)
                self.ax1.grid(True,linewidth=1.,color='#212121', linestyle = '-',alpha=.3)
                # hack to make flavor labels visible also on top and bottom
                xlabel_artist = self.ax1.set_xlabel(' -\n ', alpha=0.0)
                title_artist = self.ax1.set_title(' -\n ', alpha=0.0)
                try:
                    xlabel_artist.set_in_layout(False) # remove x-axis labels from tight_layout calculation
                except Exception: # pylint: disable=broad-except # set_in_layout not available in mpl<3.x
                    pass
                try:
                    title_artist.set_in_layout(False) # remove x-axis labels from tight_layout calculation
                except Exception: # pylint: disable=broad-except # set_in_layout not available in mpl<3.x
                    pass

                #create water marks 6-7 anf 8-9
                self.ax1.bar(.1, .1, width=2.*pi, bottom=.6,color='#0c6aa6',linewidth=0.,alpha = .1)
                self.ax1.bar(.1, .1, width=2.*pi, bottom=.8,color='#0c6aa6',linewidth=0.,alpha = .1)

                #delete degrees ticks to anotate flavor characteristics
                for tick in self.ax1.xaxis.get_major_ticks():
                    #tick.label1On = False
                    tick.label1.set_visible(False)

                fontprop_small = self.aw.mpl_fontproperties.copy()
                fontprop_small.set_size('x-small')

                #rename yaxis
                locs = self.ax1.get_yticks()
                labels = []
                for loc in locs:
                    stringlabel = str(int(round(loc*10)))
                    labels.append(stringlabel)
                self.ax1.set_yticklabels(labels,color=self.palette['xlabel'],fontproperties=fontprop_small)
                self.updateFlavorChartData()

                #anotate labels
                self.flavorchart_labels = []
                for i in range(len(self.flavorlabels)):
                    if self.flavorchart_angles[i] > 2.*pi or self.flavorchart_angles[i] < 0.:
                        _,self.flavorchart_angles[i] = divmod(self.flavorchart_angles[i],(2.*pi))
                    if self.flavorchart_angles[i] <= (pi/2.) or self.flavorchart_angles[i] >= (1.5*pi): #if < 90 or smaller than 270 degrees
                        ha = 'left'
                    else:
                        ha = 'right'
                    anno = self.ax1.annotate(self.flavorChartLabelText(i),xy =(self.flavorchart_angles[i],.9),
                                        fontproperties=fontprop_small,
                                        xytext=(self.flavorchart_angles[i],1.1),horizontalalignment=ha,verticalalignment='center')
                    try:
                        anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                    except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                        pass
                    self.flavorchart_labels.append(anno)

                # total score
                score = self.calcFlavorChartScore()
                txt = f'{score:.2f}'
                self.flavorchart_total = self.ax1.text(0.,0.,txt,fontsize='x-large',fontproperties=self.aw.mpl_fontproperties,color='#FFFFFF',horizontalalignment='center',bbox={'facecolor':'#212121', 'alpha':0.5, 'pad':10})

                #add background to plot if found
                if self.background and self.flavorbackgroundflag:
                    if len(self.backgroundFlavors) != len(self.flavors):
                        message = QApplication.translate('Message','Background does not match number of labels')
                        self.aw.sendmessage(message)
                        self.flavorbackgroundflag = False
                    else:
                        backgroundplotf = self.backgroundFlavors[:]
                        backgroundplotf.append(self.backgroundFlavors[0])
                        #normalize flavor values to 0-1 range
                        for i,_ in enumerate(backgroundplotf):
                            backgroundplotf[i] /= 10.

                        self.ax1.plot(self.flavorchart_angles,backgroundplotf,color='#cc0f50',marker='o',alpha=.5)
                        #needs matplotlib 1.0.0+
                        self.ax1.fill_between(self.flavorchart_angles,0,backgroundplotf, facecolor='#ff5871', alpha=0.1, interpolate=True)

                #add to plot
                self.flavorchart_plot, = self.ax1.plot(self.flavorchart_angles,self.flavorchart_plotf,color='#0c6aa6',marker='o')

                self.flavorchart_fill = self.ax1.fill_between(self.flavorchart_angles,0,self.flavorchart_plotf, facecolor='#1985ba', alpha=0.1, interpolate=True)

                #self.fig.canvas.draw()
                self.fig.canvas.draw_idle()
        except Exception as e:  # pylint: disable=broad-except
            _log.exception(e)

    def flavorChartLabelText(self,i):
        return f'{self.aw.arabicReshape(self.flavorlabels[i])}\n{self.flavors[i]:.2f}'

    #To close circle we need one more element. angle and values need same dimension in order to plot.
    def updateFlavorChartData(self):
        # update angles
        nflavors = len(self.flavors)      #last value of nflavors is used to close circle (same as flavors[0])
        step = 2.*math.pi/nflavors
        startradian = math.radians(self.flavorstartangle)
        self.flavorchart_angles = [startradian]   #angles in radians
        for _ in range(nflavors-1):
            self.flavorchart_angles.append(self.flavorchart_angles[-1] + step)
        self.flavorchart_angles.append(self.flavorchart_angles[-1]+step)
        # update values
        self.flavorchart_plotf = self.flavors[:]
        self.flavorchart_plotf.append(self.flavors[0])
        #normalize flavor values to 0-1 range
        for i,_ in enumerate(self.flavorchart_plotf):
            self.flavorchart_plotf[i] /= 10.

    def calcFlavorChartScore(self):
        score = 0.
        nflavors = len(self.flavors)
        for i in range(nflavors):
            score += self.flavors[i]
        score /= (nflavors)
        score *= 10.
        return score

    # an incremental redraw of the existing flavorchart
    def updateFlavorchartValues(self):
        # update data
        self.updateFlavorChartData()
        if self.flavorchart_plot is not None:
            self.flavorchart_plot.set_xdata(self.flavorchart_angles)
            self.flavorchart_plot.set_ydata(self.flavorchart_plotf)

        # collections need to be redrawn completely
        try:
            if self.flavorchart_fill is not None:
                self.flavorchart_fill.remove()
        except Exception: # pylint: disable=broad-except
            pass
        if self.ax1 is not None:
            self.flavorchart_fill = self.ax1.fill_between(self.flavorchart_angles,0,self.flavorchart_plotf, facecolor='#1985ba', alpha=0.1, interpolate=True)

        # total score
        score = self.calcFlavorChartScore()
        if self.flavorchart_total is not None:
            txt = f'{score:.2f}'
            self.flavorchart_total.set_text(txt)

        # update canvas
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def updateFlavorchartLabel(self,i):
        if self.flavorchart_labels is not None:
            label_anno = self.flavorchart_labels[i]
            label_anno.set_text(self.flavorChartLabelText(i))

            # update canvas
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                self.fig.canvas.draw()
            self.fig.canvas.flush_events()

    def samplingAction(self):
        _log.debug('async samplingAction()')
        try:
            ###  lock resources ##
            self.profileDataSemaphore.acquire(1)
            if self.extra_event_sampling_delay != 0:
                self.aw.eventactionx(self.extrabuttonactions[2],self.extrabuttonactionstrings[2])
        finally:
            if self.profileDataSemaphore.available() < 1:
                self.profileDataSemaphore.release(1)

    def AsyncSamplingActionTrigger(self):
        if self.extra_event_sampling_delay and self.extrabuttonactions[2]:
            if self.flagon:
                self.samplingAction()
            self.StopAsyncSamplingAction()
            self.aw.AsyncSamplingTimer = QTimer()
            self.aw.AsyncSamplingTimer.timeout.connect(self.AsyncSamplingActionTrigger)
            self.aw.AsyncSamplingTimer.setSingleShot(True)
            self.aw.AsyncSamplingTimer.start(int(round(self.extra_event_sampling_delay)))

    def StartAsyncSamplingAction(self):
        if self.aw.AsyncSamplingTimer is None and self.flagon and self.extra_event_sampling_delay != 0:
            self.AsyncSamplingActionTrigger()

    def StopAsyncSamplingAction(self):
        if self.aw.AsyncSamplingTimer is not None:
            self.aw.AsyncSamplingTimer.stop() # kill the running timer
            self.aw.AsyncSamplingTimer.deleteLater()
            try: # sip not supported on older PyQt versions (RPi!)
                sip.delete(self.aw.AsyncSamplingTimer)
                #print(sip.isdeleted(dialog))
            except Exception:  # pylint: disable=broad-except
                pass
            self.aw.AsyncSamplingTimer = None


    # fill the self.extraNoneTempHint1 and self.extraNoneTempHint2 lists
    # indicating which curves should not be temperature converted
    # True indicates a non-temperature device (data should not be converted)
    # False indicates a temperature device (data should be converted if temperature unit changes)
    def generateNoneTempHints(self):
        self.extraNoneTempHint1 = []
        self.extraNoneTempHint2 = []
        for d in self.extradevices:
            if d in self.nonTempDevices:
                self.extraNoneTempHint1.append(True)
                self.extraNoneTempHint2.append(True)
            elif d == 29: # MODBUS
                self.extraNoneTempHint1.append(self.aw.modbus.inputModes[0] == '')
                self.extraNoneTempHint2.append(self.aw.modbus.inputModes[1] == '')
            elif d == 33: # +MODBUS 34
                self.extraNoneTempHint1.append(self.aw.modbus.inputModes[2] == '')
                self.extraNoneTempHint2.append(self.aw.modbus.inputModes[3] == '')
            elif d == 55: # +MODBUS 56
                self.extraNoneTempHint1.append(self.aw.modbus.inputModes[4] == '')
                self.extraNoneTempHint2.append(self.aw.modbus.inputModes[5] == '')
            elif d == 109: # +MODBUS 78
                self.extraNoneTempHint1.append(self.aw.modbus.inputModes[6] == '')
                self.extraNoneTempHint2.append(self.aw.modbus.inputModes[7] == '')
            elif d == 79: # S7
                self.extraNoneTempHint1.append(not bool(self.aw.s7.mode[0]))
                self.extraNoneTempHint2.append(not bool(self.aw.s7.mode[1]))
            elif d == 80: # +S7 34
                self.extraNoneTempHint1.append(not bool(self.aw.s7.mode[2]))
                self.extraNoneTempHint2.append(not bool(self.aw.s7.mode[3]))
            elif d == 81: # +S7 56
                self.extraNoneTempHint1.append(not bool(self.aw.s7.mode[4]))
                self.extraNoneTempHint2.append(not bool(self.aw.s7.mode[5]))
            elif d == 82: # +S7 78
                self.extraNoneTempHint1.append(not bool(self.aw.s7.mode[6]))
                self.extraNoneTempHint2.append(not bool(self.aw.s7.mode[7]))
            elif d == 110: # +S7 910
                self.extraNoneTempHint1.append(not bool(self.aw.s7.mode[8]))
                self.extraNoneTempHint2.append(not bool(self.aw.s7.mode[9]))
            elif d == 111: # WebSocket
                self.extraNoneTempHint1.append(not bool(self.aw.ws.channel_modes[0]))
                self.extraNoneTempHint2.append(not bool(self.aw.ws.channel_modes[1]))
            elif d == 112: # +S7 34
                self.extraNoneTempHint1.append(not bool(self.aw.ws.channel_modes[2]))
                self.extraNoneTempHint2.append(not bool(self.aw.ws.channel_modes[3]))
            elif d == 113: # +S7 56
                self.extraNoneTempHint1.append(not bool(self.aw.ws.channel_modes[4]))
                self.extraNoneTempHint2.append(not bool(self.aw.ws.channel_modes[5]))
            elif d == 118: # +S7 78
                self.extraNoneTempHint1.append(not bool(self.aw.ws.channel_modes[6]))
                self.extraNoneTempHint2.append(not bool(self.aw.ws.channel_modes[7]))
            elif d == 119: # +S7 910
                self.extraNoneTempHint1.append(not bool(self.aw.ws.channel_modes[8]))
                self.extraNoneTempHint2.append(not bool(self.aw.ws.channel_modes[9]))
            else:
                self.extraNoneTempHint1.append(False)
                self.extraNoneTempHint2.append(False)

    def addPhidgetServer(self):
        if not self.phidgetServerAdded:
            from Phidget22.Net import Net as PhidgetNetwork # type: ignore
            if self.phidgetServerID == '' and not self.phidgetServiceDiscoveryStarted:
                try:
                    # we enable the automatic service discovery if no server host is given
                    from Phidget22.PhidgetServerType import PhidgetServerType # type: ignore
                    PhidgetNetwork.enableServerDiscovery(PhidgetServerType.PHIDGETSERVER_DEVICEREMOTE)
                    self.phidgetServiceDiscoveryStarted = True
                    self.aw.sendmessage(QApplication.translate('Message','Phidget service discovery started...'))
                except Exception as e:  # pylint: disable=broad-except
                    _log.exception(e)
            else:
                PhidgetNetwork.addServer('PhidgetServer',self.phidgetServerID,self.phidgetPort,self.phidgetPassword,0)
                self.phidgetServerAdded = True

    def removePhidgetServer(self):
        if self.phidgetServerAdded:
            from Phidget22.Net import Net as PhidgetNetwork # type: ignore
            try:
                PhidgetNetwork.removeServer('PhidgetServer')
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            self.phidgetServerAdded = False
            if self.phidgetServiceDiscoveryStarted:
                try:
                    from Phidget22.PhidgetServerType import PhidgetServerType # type: ignore
                    PhidgetNetwork.disableServerDiscovery(PhidgetServerType.PHIDGETSERVER_DEVICEREMOTE)
                    self.phidgetServiceDiscoveryStarted = False
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)

    @staticmethod
    def deviceLogDEBUG():
        from Phidget22.Devices.Log import Log as PhidgetLog # type: ignore
        from Phidget22.LogLevel import LogLevel as PhidgetLogLevel # type: ignore
        PhidgetLog.setLevel(PhidgetLogLevel.PHIDGET_LOG_VERBOSE)

    @staticmethod
    def deviceLLogINFO():
        from Phidget22.Devices.Log import Log as PhidgetLog # type: ignore
        from Phidget22.LogLevel import LogLevel as PhidgetLogLevel # type: ignore
        PhidgetLog.setLevel(PhidgetLogLevel.PHIDGET_LOG_INFO)

    # returns True if any device (main or extra) is a Phidget, ambient sensor or button/slider actions contain Phidget commands
    # the PhidgetManager which makes Phidgets accessible is only started if PhdigetsConfigured returns True
    def PhidgetsConfigured(self):

        # searching sets is faster than lists
        phidget_device_ids = set(self.phidgetDevices)

        # collecting all device ids in use (from main or extra)
        device_ids_in_use = self.extradevices[:]
        device_ids_in_use.append(self.device)

        # collecting ambient device ids in use (ids 1 and 3 indicate Phidgets modules)
        ambient_device_ids = [
            self.ambient_temperature_device,
            self.ambient_humidity_device,
            self.ambient_pressure_device]

        # IO Command, PWM Command, VOUT Command, RC Command
        # Note that those commands could also trigger Yoctopuce actions
        main_button_phidget_action_ids = { 5, 11, 12, 19 }

        # Note that the ids for the same Command types are different here:
        custom_button_phidget_action_ids = { 6, 13, 14, 21 }

        # Note that the ids for the same Command types are different here:
        slider_phidget_action_ids = { 9, 10, 11, 17 }

        return (
            any(i in phidget_device_ids for i in device_ids_in_use) or                    # phidget main/extra device
            any(i in [1, 3] for i in ambient_device_ids) or                               # phidget ambient device
            any(i in main_button_phidget_action_ids for i in self.buttonactions) or       # phidget actions in event button commands (CHARGE, .., COOL)
            any(i in main_button_phidget_action_ids for i in self.extrabuttonactions) or  # phidget actions in main event button commandss (ON, OFF, SAMPLE)
            any(i in main_button_phidget_action_ids for i in self.xextrabuttonactions) or # phidget actions in special event commands (RESET, START)
            any(i in custom_button_phidget_action_ids for i in self.aw.extraeventsactions) or  # phidget actions in custom event buttons commands
            any(i in slider_phidget_action_ids for i in self.aw.eventslideractions))           # phidget actions in slider commands


    # the PhidgetManager needs to run to allow Phidgets to attach
    # the PhidgetManager is only started if self.PhidgetsConfigured() returns True signaling
    # that Phidget modules are configured as main/extra devices, ambient devices, or in button/slider actions
    def startPhidgetManager(self):
        # this is needed to suppress the message on the ignored Exception
        #                            # Phidget that is raised on starting the PhidgetManager without installed
        #                            # Phidget driver (artisanlib/suppress_error.py fails to suppress this)
#        _stderr = sys.stderr
#        sys.stderr = object
#        try:
        if not self.aw.app.artisanviewerMode and self.PhidgetsConfigured():
            # Phidget server is only started if any device or action addressing Phidgets is configured
            if self.phidgetManager is None:
                try:
                    from Phidget22.Devices.Log import Log as PhidgetLog # type: ignore
                    from Phidget22.LogLevel import LogLevel as PhidgetLogLevel # type: ignore
                    PhidgetLog.enable(PhidgetLogLevel.PHIDGET_LOG_DEBUG, self.device_log_file)
                    PhidgetLog.enableRotating()
                    _log.info('phidgetLog started')
                except Exception: # pylint: disable=broad-except
                    pass # logging might already be enabled
            if self.phidgetRemoteFlag:
                try:
                    self.addPhidgetServer()
                    _log.info('phidgetServer started')
                except Exception: # pylint: disable=broad-except
                    if self.device in self.phidgetDevices:
                        self.adderror(QApplication.translate('Error Message',"Exception: PhidgetManager couldn't be started. Verify that the Phidget driver is correctly installed!"))
            if self.phidgetManager is None:
                try:
                    self.phidgetManager = PhidgetManager()
                    _log.info('phidgetManager started')
                except Exception: # pylint: disable=broad-except
                    if self.device in self.phidgetDevices:
                        self.adderror(QApplication.translate('Error Message',"Exception: PhidgetManager couldn't be started. Verify that the Phidget driver is correctly installed!"))
#        finally:
#            sys.stderr = _stderr

    def stopPhidgetManager(self):
        if self.phidgetManager is not None:
            self.phidgetManager.close()
            self.phidgetManager = None
        self.removePhidgetServer()
        try:
            from Phidget22.Devices.Log import Log as PhidgetLog # type: ignore
            PhidgetLog.disable()
        except Exception: # pylint: disable=broad-except
            pass

    def restartPhidgetManager(self):
        self.stopPhidgetManager()
        self.startPhidgetManager()

    # this one is protected by the sampleSemaphore not to mess up with the timex during sampling
    def resetTimer(self):
        try:
            self.samplingSemaphore.acquire(1)
            self.timeclock.start()
        finally:
            if self.samplingSemaphore.available() < 1:
                self.samplingSemaphore.release(1)

    def OnMonitor(self):
        try:
            if self.aw.simulator is None:
                self.startPhidgetManager()
                # collect ambient data if any
                if self.ambient_pressure_device or self.ambient_humidity_device or self.ambient_temperature_device:
                    self.ambiThread = QThread()
                    self.ambiWorker = AmbientWorker(self.aw)
                    self.ambiWorker.moveToThread(self.ambiThread)
                    self.ambiThread.started.connect(self.ambiWorker.run)
                    self.ambiWorker.finished.connect(self.ambiThread.quit)
                    self.ambiWorker.finished.connect(self.ambiWorker.deleteLater)
                    self.ambiThread.finished.connect(self.ambiThread.deleteLater)
                    self.ambiThread.start()

            # warm up software PID (write current p-i-d settings,..)
            self.aw.pidcontrol.confSoftwarePID()

            self.generateNoneTempHints()
            self.block_update = True # block the updating of the bitblit canvas (unblocked at the end of this function to avoid multiple redraws)
            res = self.reset(False,False,sampling=True,keepProperties=True)
            if not res: # reset canceled
                self.OffMonitor()
                return

            if not bool(self.aw.simulator):
                if self.device == 53:
                    # connect HOTTOP
                    from artisanlib.hottop import startHottop
                    startHottop(0.6,self.aw.ser.comport,self.aw.ser.baudrate,self.aw.ser.bytesize,self.aw.ser.parity,self.aw.ser.stopbits,self.aw.ser.timeout)
                elif self.device == 134:
                    # connect Santoker
                    from artisanlib.santoker import SantokerNetwork
                    self.aw.santoker = SantokerNetwork()
                    self.aw.santoker.setLogging(self.device_logging)
                    self.aw.santoker.start(self.aw.santokerHost, self.aw.santokerPort,
                        connected_handler=lambda : self.aw.sendmessageSignal.emit(QApplication.translate('Message', 'Santoker connected'),True,None),
                        disconnected_handler=lambda : self.aw.sendmessageSignal.emit(QApplication.translate('Message', 'Santoker disconnected'),True,None),
                        charge_handler=lambda : (self.markChargeSignal.emit() if (self.timeindex[0] == -1) else None),
                        dry_handler=lambda : (self.markDRYSignal.emit() if (self.timeindex[2] == 0) else None),
                        fcs_handler=lambda : (self.markFCsSignal.emit() if (self.timeindex[1] == 0) else None),
                        scs_handler=lambda : (self.markSCsSignal.emit() if (self.timeindex[4] == 0) else None),
                        drop_handler=lambda : (self.markDropSignal.emit() if (self.timeindex[6] == 0) else None))
            self.aw.initializedMonitoringExtraDeviceStructures()

            #reset alarms
            self.silent_alarms = False
            self.temporaryalarmflag = -3
            self.alarmstate = [-1]*len(self.alarmflag)  #1- = not triggered; any other value = triggered; value indicates the index in self.timex at which the alarm was triggered
            #reset TPalarmtimeindex to trigger a new TP recognition during alarm processing
            self.TPalarmtimeindex = None

            self.flagon = True
            self.redraw(True,sampling=True,smooth=self.optimalSmoothing) # we need to re-smooth with standard smoothing if ON and optimal-smoothing is ticked

            if self.designerflag:
                return
            self.aw.sendmessage(QApplication.translate('Message','Scope monitoring...'))
            #disable RESET button:
            self.aw.buttonRESET.setEnabled(False)
            self.aw.buttonRESET.setVisible(False)

            # disable "green flag" menu:
            try:
                self.aw.ntb.disable_edit_curve_parameters()
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            QApplication.processEvents()
            if self.aw.simulator:
                self.aw.buttonONOFF.setStyleSheet(self.aw.pushbuttonstyles_simulator['ON'])
            else:
                self.aw.buttonONOFF.setStyleSheet(self.aw.pushbuttonstyles['ON'])
#            QApplication.processEvents()

            self.aw.buttonONOFF.setText(QApplication.translate('Button', 'OFF')) # text means click to turn OFF (it is ON)
            self.aw.buttonONOFF.setToolTip(QApplication.translate('Tooltip', 'Stop monitoring'))
            self.aw.buttonSTARTSTOP.setEnabled(True) # ensure that the START button is enabled
            self.aw.disableEditMenus()
            self.aw.update_extraeventbuttons_visibility()
            self.aw.updateExtraButtonsVisibility()
            self.aw.updateSlidersVisibility() # update visibility of sliders based on the users preference
            self.aw.update_minieventline_visibility()
            self.aw.pidcontrol.activateONOFFeasySV(self.aw.pidcontrol.svButtons and self.aw.buttonONOFF.isVisible())
            self.aw.pidcontrol.activateSVSlider(self.aw.pidcontrol.svSlider and self.aw.buttonONOFF.isVisible())
            self.block_update = False # unblock the updating of the bitblit canvas
            self.aw.updateReadingsLCDsVisibility() # this one triggers the resize and the recreation of the bitblit canvas
            self.threadserver.createSampleThread()
            try:
                self.aw.eventactionx(self.extrabuttonactions[0],self.extrabuttonactionstrings[0])
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            if not bool(self.aw.simulator):
                QTimer.singleShot(300,self.StartAsyncSamplingAction)
            _log.info('ON MONITOR (sampling @%ss)', self.aw.float2float(self.delay/1000))
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' OnMonitor() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))

    def OffMonitor(self):
        _log.info('OFF MONITOR')
        try:
            # first activate "Stopping Mode" to ensure that sample() is not resetting the timer now (independent of the flagstart state)

            # stop Recorder if still running
            recording = self.flagstart
            if recording:
                self.OffRecorder(autosave=False) # we autosave after the monitor is turned off to get all the data in the generated PDF!

            self.flagon = False
            # stop async sampling action before stopping sampling
            self.StopAsyncSamplingAction()

            try:
                # trigger event action before disconnecting from devices
                if self.extrabuttonactions[1] != 18: # Artisan Commands are executed after the OFFMonitor action is fully executued as they might trigger another buttons
                    self.aw.eventactionx(self.extrabuttonactions[1],self.extrabuttonactionstrings[1])
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            # now wait until the current sampling round is done
            while self.flagsampling:
                libtime.sleep(0.05)
                QApplication.processEvents()
            if len(self.timex) < 3:
                # clear data from monitoring-only mode
                self.clearMeasurements()
            else:
                # we only reset the LCDs, but keep the readings
                self.clearLCDs()

            self.aw.pidcontrol.pidOff()
#            if self.device == 53:
#                self.aw.HottopControlOff()

            # disconnect Santoker
            if not bool(self.aw.simulator) and self.device == 134 and self.aw.santoker is not None:
                self.aw.santoker.stop()
                self.aw.santoker = None

            # at OFF we stop the follow-background on FujiPIDs and set the SV to 0
            if self.device == 0 and self.aw.fujipid.followBackground and self.aw.fujipid.sv and self.aw.fujipid.sv > 0:
                try:
                    self.aw.fujipid.setsv(0,silent=True)
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
                self.aw.fujipid.sv = 0
            QTimer.singleShot(5,self.disconnectProbes)
            # reset the canvas color when it was set by an alarm but never reset
            if 'canvas_alt' in self.palette:
                self.palette['canvas'] = self.palette['canvas_alt']
                self.aw.updateCanvasColors(checkColors=False)
            #enable RESET button:
            self.aw.buttonRESET.setStyleSheet(self.aw.pushbuttonstyles['RESET'])
            self.aw.buttonRESET.setEnabled(True)
            self.aw.buttonRESET.setVisible(True)

            # reset a stopped simulator
            self.aw.sample_loop_running = True
            self.aw.time_stopped = 0

            # enable "green flag" menu:
            try:
                self.aw.ntb.enable_edit_curve_parameters()
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            if self.aw.simulator:
                self.aw.buttonONOFF.setStyleSheet(self.aw.pushbuttonstyles_simulator['OFF'])
            else:
                self.aw.buttonONOFF.setStyleSheet(self.aw.pushbuttonstyles['OFF'])
            self.aw.buttonONOFF.setToolTip(QApplication.translate('Tooltip', 'Start monitoring'))
            self.aw.sendmessage(QApplication.translate('Message','Scope stopped'))
            self.aw.buttonONOFF.setText(QApplication.translate('Button', 'ON')) # text means click to turn OFF (it is ON)
            # reset time LCD color to the default (might have been changed to red due to long cooling!)
            self.aw.updateReadingsLCDsVisibility()
            # reset WebLCDs
            resLCD = '-.-' if self.LCDdecimalplaces else '--'
            if self.aw.WebLCDs:
                self.updateWebLCDs(bt=resLCD,et=resLCD)
            if not self.aw.HottopControlActive:
                self.aw.hideExtraButtons(changeDefault=False)
            self.aw.updateSlidersVisibility() # update visibility of sliders based on the users preference
            self.aw.update_minieventline_visibility()
            self.aw.updateExtraButtonsVisibility()
            self.aw.pidcontrol.activateONOFFeasySV(False)
            self.aw.enableEditMenus()

            self.aw.autoAdjustAxis()
            self.redraw(recomputeAllDeltas=True,smooth=True)
            # HACK:
            # with visible (draggable) legend a click (or several) on the canvas makes the extra lines disappear
            # this happens after real recordings or simlator runs and also if signals onclick/onpick/ondraw are disconnected
            # solutions are to run an updateBackground() or another redraw() about in 100s using a QTimer
            # also a call  to self.fig.canvas.flush_events() or QApplication.processEvents() here resolves it. A libtime.sleep(1) does not solve the issue
#            QTimer.singleShot(100,self.updateBackground) # solves the issue
#            self.fig.canvas.flush_events() # solves the issue
            QApplication.processEvents()  # solves the issue

            # we autosave after full redraw after OFF to have the optional generated PDF containing all information
            if len(self.timex) > 2 and self.autosaveflag != 0 and self.autosavepath:
                try:
                    self.aw.automaticsave()
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)

            # update error dlg
            if self.aw.error_dlg:
                self.aw.error_dlg.update()
            #update serial_dlg
            if self.aw.serial_dlg:
                try:
                    self.aw.serial_dlg.update()
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)

            try:
                # trigger event action before disconnecting from devices
                if self.extrabuttonactions[1] == 18: # Artisan Commands are executed after the OFFMonitor action is fully executued as they might trigger other buttons
                    self.aw.eventactionx(self.extrabuttonactions[1],self.extrabuttonactionstrings[1])
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            if recording and self.flagKeepON and len(self.timex) > 10:
                QTimer.singleShot(300,self.OnMonitor)

        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' OffMonitor() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))

    def getAmbientData(self):
        _log.debug('getAmbientData()')
        # this is needed to suppress the message on the ignored Exception
        #                            # Phidget that is raised on starting the PhidgetManager without installed
        #                            # Phidget driver (artisanlib/suppresss_error.py fails to suppress this)
#        _stderr = sys.stderr
#        sys.stderr = object
        try:
            humidity = None
            temp = None # assumed to be gathered in C (not F!)
            pressure = None

            #--- humidity
            if self.ambient_humidity_device == 1: # Phidget HUM1000
                humidity = self.aw.ser.PhidgetHUM1000humidity()
            elif self.ambient_humidity_device == 2: # Yocto Meteo
                humidity = self.aw.ser.YoctoMeteoHUM()

            #--- temperature
            if self.ambient_temperature_device == 1: # Phidget HUM1000
                temp = self.aw.ser.PhidgetHUM1000temperature()
            elif self.ambient_temperature_device == 2: # Yocto Meteo
                temp = self.aw.ser.YoctoMeteoTEMP()
            elif self.ambient_temperature_device == 3: # Phidget TMP1000
                temp = self.aw.ser.PhidgetTMP1000temperature()

            #--- pressure
            if self.ambient_pressure_device == 1: # Phidget PRE1000
                pressure = self.aw.ser.PhidgetPRE1000pressure()
                if pressure is not None:
                    pressure = pressure * 10 # convert to hPa/mbar
            elif self.ambient_pressure_device == 2: # Yocto Meteo
                pressure = self.aw.ser.YoctoMeteoPRESS()

            # calc final values
            if pressure is not None:
                # we just assume 23C room temperature if no ambient temperature is given or ambient temperature is out of range
                t = 23 if temp is None or temp < -20 or temp > 40 else temp
                pressure = self.barometricPressure(pressure,t,self.elevation)

            # set and report
            if humidity is not None:
                self.ambient_humidity = self.aw.float2float(humidity,1)
                self.ambient_humidity_sampled = self.ambient_humidity
                self.aw.sendmessage(QApplication.translate('Message','Humidity: {}%').format(self.ambient_humidity))
                libtime.sleep(1)

            if temp is not None:
                if self.mode == 'F':
                    temp = fromCtoF(temp)
                self.ambientTemp = self.aw.float2float(temp,1)
                self.ambientTemp_sampled = self.ambientTemp
                self.aw.sendmessage(QApplication.translate('Message','Temperature: {}{}').format(self.ambientTemp,self.mode))
                libtime.sleep(1)

            if pressure is not None:
                self.ambient_pressure = self.aw.float2float(pressure,1)
                self.ambient_pressure_sampled = self.ambient_pressure
                self.aw.sendmessage(QApplication.translate('Message','Pressure: {}hPa').format(self.ambient_pressure))
        except Exception as e:  # pylint: disable=broad-except
            _log.exception(e)
#        finally:
#            sys.stderr = _stderr

    # computes the barometric pressure from
    #   aap:  atmospheric pressure in hPa
    #   atc:  temperature in Celsius
    #   hasl: height above sea level in m
    # see https://www.wmo.int/pages/prog/www/IMOP/meetings/SI/ET-Stand-1/Doc-10_Pressure-red.pdf
    @staticmethod
    def barometricPressure(aap, atc, hasl):
        return aap * pow((1 - ((0.0065*hasl) / (atc + (0.0065*hasl) + 273.15))),-5.257)

    # close serial port, Phidgets and Yocto ports
    def disconnectProbesFromSerialDevice(self, ser):
        try:
            self.samplingSemaphore.acquire(1)
            # close main serial port
            try:
                ser.closeport()
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            # disconnect phidgets
            if ser.PhidgetTemperatureSensor is not None:
                try:
                    if ser.PhidgetTemperatureSensor[0].getAttached():
                        serial = ser.PhidgetTemperatureSensor[0].getDeviceSerialNumber()
                        port = ser.PhidgetTemperatureSensor[0].getHubPort()  # returns 0 for USB Phidgets!
                        deviceType = ser.PhidgetTemperatureSensor[0].getDeviceID()
                        ser.PhidgetTemperatureSensor[0].close()
                        ser.phidget1048detached(serial,port,deviceType,0) # call detach handler to release from PhidgetManager
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
                try:
                    if len(ser.PhidgetTemperatureSensor) > 1 and ser.PhidgetTemperatureSensor[1].getAttached():
                        serial = ser.PhidgetTemperatureSensor[1].getDeviceSerialNumber()
                        port = ser.PhidgetTemperatureSensor[1].getHubPort()  # returns 0 for USB Phidgets!
                        deviceType = ser.PhidgetTemperatureSensor[1].getDeviceID()
                        ser.PhidgetTemperatureSensor[1].close()
                        ser.phidget1048detached(serial,port,deviceType,1) # call detach handler to release from PhidgetManager
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
                ser.Phidget1048values = [[],[],[],[]]
                ser.Phidget1048lastvalues = [-1]*4
                ser.PhidgetTemperatureSensor = None
            if ser.PhidgetIRSensor is not None:
                try:
                    if ser.PhidgetIRSensor.getAttached():
                        serial = ser.PhidgetIRSensor.getDeviceSerialNumber()
                        port = ser.PhidgetIRSensor.getHubPort() # returns 0 for USB Phidgets!
                        deviceType = ser.PhidgetIRSensor.getDeviceID()
                        ser.PhidgetIRSensor.close()
                        ser.phidget1045detached(serial,port,deviceType) # call detach handler to release from PhidgetManager
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
                try:
                    if ser.PhidgetIRSensorIC is not None and ser.PhidgetIRSensorIC.getAttached():
                        ser.PhidgetIRSensorIC.close()
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
                ser.PhidgetIRSensor = None
                ser.Phidget1045values = [] # async values of the one channel
                ser.Phidget1045lastvalue = -1
                ser.Phidget1045tempIRavg = None
                ser.PhidgetIRSensorIC = None
            if ser.PhidgetBridgeSensor is not None:
                try:
                    if ser.PhidgetBridgeSensor[0].getAttached():
                        serial = ser.PhidgetBridgeSensor[0].getDeviceSerialNumber()
                        port = ser.PhidgetBridgeSensor[0].getHubPort()   # returns 0 for USB Phidgets!
                        deviceType = ser.PhidgetBridgeSensor[0].getDeviceID()
                        ser.PhidgetBridgeSensor[0].close()
                        ser.phidget1046detached(serial,port,deviceType,0) # call detach handler to release from PhidgetManager
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
                try:
                    if len(ser.PhidgetBridgeSensor) > 1 and ser.PhidgetBridgeSensor[1].getAttached():
                        serial = ser.PhidgetBridgeSensor[1].getDeviceSerialNumber()
                        port = ser.PhidgetBridgeSensor[1].getHubPort()   # returns 0 for USB Phidgets!
                        deviceType = ser.PhidgetBridgeSensor[1].getDeviceID()
                        ser.PhidgetBridgeSensor[1].close()
                        ser.phidget1046detached(serial,port,deviceType,1) # call detach handler to release from PhidgetManager
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
                ser.Phidget1046values = [[],[],[],[]]
                ser.Phidget1046lastvalues = [-1]*4
                ser.PhidgetBridgeSensor = None
            if ser.PhidgetIO is not None:
                try:
                    if ser.PhidgetIO[0].getAttached():
                        serial = ser.PhidgetIO[0].getDeviceSerialNumber()
                        port = ser.PhidgetIO[0].getHubPort()   # returns 0 for USB Phidgets!
                        className = ser.PhidgetIO[0].getChannelClassName()
                        deviceType = ser.PhidgetIO[0].getDeviceID()
                        ser.PhidgetIO[0].close()
                        ser.phidget1018detached(serial,port,className,deviceType,0)
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
                try:
                    if len(ser.PhidgetIO) > 1 and ser.PhidgetIO[1].getAttached():
                        serial = ser.PhidgetIO[1].getDeviceSerialNumber()
                        port = ser.PhidgetIO[1].getHubPort()   # returns 0 for USB Phidgets!
                        className = ser.PhidgetIO[1].getChannelClassName()
                        deviceType = ser.PhidgetIO[1].getDeviceID()
                        ser.PhidgetIO[1].close()
                        ser.phidget1018detached(serial,port,className,deviceType,1)
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
                ser.PhidgetIO = None
                ser.PhidgetIOvalues = [[],[],[],[],[],[],[],[]]
                ser.PhidgetIOlastvalues = [-1]*8
            if ser.YOCTOsensor is not None:
                try:
                    ser.YOCTOsensor = None
                    ser.YOCTOchan1 = None
                    ser.YOCTOchan2 = None
                    ser.YOCTOtempIRavg = None
                    if ser.YOCTOthread is not None:
                        ser.YOCTOthread.join()
                        ser.YOCTOthread = None
                    ser.YOCTOvalues = [[],[]]
                    ser.YOCTOlastvalues = [-1]*2
                    YAPI.FreeAPI()
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
        finally:
            if self.samplingSemaphore.available() < 1:
                self.samplingSemaphore.release(1)

    # close Phidget and and Yocto outputs
    def closePhidgetOUTPUTs(self):
        # close Phidget Digital Outputs
        self.aw.ser.phidgetOUTclose()
        # close Phidget Digital Outputs on Hub
        self.aw.ser.phidgetOUTcloseHub()
        # close Phidget IO Outputs
        self.aw.ser.phidgetBinaryOUTclose()
        # close Phidget Analog Outputs
        self.aw.ser.phidgetVOUTclose()
        # close Phidget DCMotors
        self.aw.ser.phidgetDCMotorClose()
        # close Phidget RC Servos
        self.aw.ser.phidgetRCclose()
        # close Yocto Voltage Outputs
        self.aw.ser.yoctoVOUTclose()
        # close Yocto Current Outputs
        self.aw.ser.yoctoCOUTclose()
        # close Yocto Relay Outputs
        self.aw.ser.yoctoRELclose()
        # close Yocto Servo Outputs
        self.aw.ser.yoctoSERVOclose()
        # close Yocto PWM Outputs
        self.aw.ser.yoctoPWMclose()

    def closePhidgetAMBIENTs(self):
        # note that we do not unregister this detach in the self.phidgetManager as we only support one of those devices
        try:
            if self.aw.ser.TMP1000temp is not None and self.aw.ser.TMP1000temp.getAttached():
                self.aw.ser.TMP1000temp.close()
                _log.debug('Phidget TMP1000 temperature channel closed')
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
        try:
            if self.aw.ser.PhidgetHUMtemp is not None and self.aw.ser.PhidgetHUMtemp.getAttached():
                self.aw.ser.PhidgetHUMtemp.close()
                _log.debug('Phidget HUM100x temperature channel closed')
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
        try:
            if self.aw.ser.PhidgetHUMhum is not None and self.aw.ser.PhidgetHUMhum.getAttached():
                self.aw.ser.PhidgetHUMhum.close()
                _log.debug('Phidget HUM100x humidity channel closed')
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
        try:
            if self.aw.ser.PhidgetPREpre is not None and self.aw.ser.PhidgetPREpre.getAttached():
                self.aw.ser.PhidgetPREpre.close()
                _log.debug('Phidget PRE1000 pressure channel closed')
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)


    def disconnectProbes(self):
        # close ports of main device
        self.disconnectProbesFromSerialDevice(self.aw.ser)
        # close (serial) port of Modbus device
        self.aw.modbus.disconnect()
        # close port of S7 device
        self.aw.s7.disconnect()
        # close WebSocket connection
        self.aw.ws.disconnect()
        # close ports of extra devices
        for xs in self.aw.extraser:
            self.disconnectProbesFromSerialDevice(xs)

    @pyqtSlot()
    def toggleMonitorTigger(self):
        self.ToggleMonitor()

    #Turns ON/OFF flag self.flagon to read and print values. Called from push buttonONOFF.
    @pyqtSlot(bool)
    def ToggleMonitor(self,_=False):
        #turn ON
        if not self.flagon:
            QApplication.processEvents()
            # the sample thread might still run, but should terminate soon. We do nothing and ignore this click on ON
            if not self.flagsamplingthreadrunning:
                if not self.checkSaved():
                    return
                self.aw.soundpopSignal.emit()
                self.OnMonitor()
        #turn OFF
        else:
            try:
                self.aw.soundpopSignal.emit()
            except Exception: # pylint: disable=broad-except
                pass
            self.OffMonitor()

    def fireChargeTimer(self): #profileDataSemaphore
        #### lock shared resources #####
        try:
            self.profileDataSemaphore.acquire(1)
            self.autoChargeIdx = max(1,len(self.timex))
        finally:
            if self.profileDataSemaphore.available() < 1:
                self.profileDataSemaphore.release(1)


    def OnRecorder(self):
        try:

            # if on turn mouse crosslines off
            if self.crossmarker:
                self.togglecrosslines()
            self.set_xlabel('')
            if self.ax is not None:
                self.ax.set_ylabel('')
            if not self.title_show_always:
                self.setProfileTitle('')

            self.aw.cacheCurveVisibilities()

            # disable "green flag" menu:
            try:
                self.aw.ntb.disable_edit_curve_parameters()
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            # reset LCD timer color that might have been reset by the RS PID in monitoring mode:
            self.aw.setTimerColor('timer')
            if self.delta_ax is not None:
                y_label = self.delta_ax.set_ylabel('')
                try:
                    y_label.set_in_layout(False) # remove y-axis labels from tight_layout calculation
                except Exception: # pylint: disable=broad-except # set_in_layout not available in mpl<3.x
                    pass

            self.resetTimer() #reset time, otherwise the recorded timestamps append to the time on START after ON!

            self.flagstart = True

            self.timealign(redraw=True)

            # start Monitor if not yet running
            if not self.flagon:
                self.OnMonitor()
            try:
                self.aw.eventactionx(self.xextrabuttonactions[1],self.xextrabuttonactionstrings[1])
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)

            # update the roasts start time
            self.roastdate = QDateTime.currentDateTime()
            self.roastepoch = self.roastdate.toSecsSinceEpoch()
            self.roasttzoffset = libtime.timezone

            self.roastbatchnr = 0 # initialized to 0, set to increased batchcounter on DROP
            self.roastbatchpos = 1 # initialized to 1, set to increased batchsequence on DROP
            if not self.title_show_always:
                self.fig.suptitle('')
            self.profile_sampling_interval = self.delay / 1000.
            self.updateDeltaSamples()
            self.aw.disableSaveActions()
            self.aw.sendmessage(QApplication.translate('Message','Scope recording...'))
            self.aw.buttonSTARTSTOP.setEnabled(False)
            ge:Optional[QGraphicsEffect] = self.aw.buttonSTARTSTOP.graphicsEffect()
            if ge is not None:
                ge.setEnabled(False)
#            self.aw.buttonSTARTSTOP.setGraphicsEffect(None) # not type correct as setGraphicsEffect expects a QGraphicsEffect
            self.aw.buttonONOFF.setText(QApplication.translate('Button', 'OFF')) # text means click to turn OFF (it is ON)
            self.aw.buttonONOFF.setToolTip(QApplication.translate('Tooltip', 'Stop recording'))
            self.aw.buttonONOFF.setEnabled(True) # ensure that the OFF button is enabled
            #disable RESET button:
            self.aw.buttonRESET.setEnabled(False)
            self.updateLCDtime()
            self.aw.lowerbuttondialog.setVisible(True)
            self.aw.applyStandardButtonVisibility()
            if self.aw.keyboardmoveflag:
                self.aw.keyboardmoveflag = 0
                self.aw.moveKbutton('enter', force=True)

            self.aw.update_extraeventbuttons_visibility()
            self.aw.updateExtraButtonsVisibility()

            if self.buttonvisibility[0]: # if CHARGE button is visible we let it blink on START
                self.aw.buttonCHARGE.startAnimation()

            self.aw.updateSlidersVisibility() # update visibility of sliders based on the users preference
            self.aw.update_minieventline_visibility()
            self.aw.updateReadingsLCDsVisibility() # update visibility of reading LCDs based on the user preference
            if self.phasesLCDflag:
                self.aw.phasesLCDs.show()
                self.aw.TP2DRYlabel.setStyleSheet("background-color:'transparent'; color: " + self.palette['messages'] + ';')
                self.aw.DRY2FCslabel.setStyleSheet("background-color:'transparent'; color: " + self.palette['messages'] + ';')
            if self.AUClcdFlag:
                self.aw.AUCLCD.show()

            self.phasesLCDmode = self.phasesLCDmode_l[0]

            self.aw.update_minieventline_visibility()

            # set CHARGEtimer
            if self.chargeTimerFlag:
                if self.chargeTimerPeriod > 0:
                    self.aw.setTimerColor('slowcoolingtimer')
                QTimer.singleShot(self.chargeTimerPeriod*1000, self.fireChargeTimer)

            _log.info('START RECORDING')
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' OnRecorder() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))

    def OffRecorder(self, autosave=True):
        _log.info('STOP RECORDING')
        try:
            # mark DROP if not yet set, at least 7min roast time and CHARGE is set and either autoDROP is active or DROP button is hidden
            if self.timeindex[6] == 0 and self.timeindex[0] != -1 and (self.autoDropFlag or not self.buttonvisibility[6]):
                start = self.timex[self.timeindex[0]]
                if (len(self.timex)>0 and self.timex[-1] - start) > 7*60: # only after 7min into the roast
                    self.markDrop()
            self.aw.enableSaveActions()
            self.aw.resetCurveVisibilities()
            self.flagstart = False
            if self.aw.simulator:
                self.aw.buttonSTARTSTOP.setStyleSheet(self.aw.pushbuttonstyles_simulator['STOP'])
            else:
                self.aw.buttonSTARTSTOP.setStyleSheet(self.aw.pushbuttonstyles['STOP'])
            self.aw.buttonSTARTSTOP.setEnabled(True)
            self.aw.buttonSTARTSTOP.setGraphicsEffect(self.aw.makeShadow())
            #enable RESET button:
            self.aw.buttonRESET.setStyleSheet(self.aw.pushbuttonstyles['RESET'])
            self.aw.buttonRESET.setEnabled(True)
            self.updateLCDtime()
            #prevents accidentally deleting a modified profile:
            if len(self.timex) > 2:
                self.fileDirtySignal.emit()
                self.aw.autoAdjustAxis() # automatic adjust axis after roast if auto axis is enabled
                try:
                    self.aw.ntb.update() # reset the MPL navigation history
                except Exception as e: # pylint: disable=broad-except
                    _log.error(e)
            try:
                if self.aw.clusterEventsFlag:
                    self.aw.clusterEvents()
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            if autosave and self.autosaveflag != 0 and self.autosavepath:
                try:
                    self.aw.automaticsave()
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
            self.aw.sendmessage(QApplication.translate('Message','Scope recording stopped'))
            self.aw.buttonSTARTSTOP.setText(QApplication.translate('Button', 'START'))
            self.aw.lowerbuttondialog.setVisible(False)
            self.aw.messagelabel.setVisible(True)
            self.aw.phasesLCDs.hide()
            self.aw.AUCLCD.hide()
            self.aw.hideEventsMinieditor()

            # enable "green flag" menu:
            try:
                self.aw.ntb.enable_edit_curve_parameters()
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' OffRecorder() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))

    @pyqtSlot()
    def toggleRecorderTigger(self):
        if self.flagstart:
            self.ToggleMonitor()
        else:
            self.ToggleRecorder()

    #Turns START/STOP flag self.flagon to read and plot. Called from push buttonSTARTSTOP.
    @pyqtSlot(bool)
    def ToggleRecorder(self,_=False):
        #turn START
        if not self.flagstart:
            if not self.checkSaved():
                return
            self.aw.soundpopSignal.emit()
            if self.flagon and len(self.timex) == 1:
                # we are already in monitoring mode, we just clear this first measurement and go
                self.clearMeasurements(andLCDs=False)
            elif self.timex != []: # there is a profile loaded, we have to reset
                self.reset(True,False,keepProperties=True)
            try:
                settings = QSettings()
                starts = 0
                if settings.contains('starts'):
                    starts = toInt(settings.value('starts'))
                settings.setValue('starts',starts+1)
                settings.sync()
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            self.OnRecorder()
        #turn STOP
        else:
            self.aw.soundpopSignal.emit()
            self.OffRecorder()

    # trigger to be called by the markChargeSignal
    # if delay is not 0, the markCharge is issues after n milliseconds
    @pyqtSlot(int)
    def markChargeDelay(self,delay):
        if delay == 0:
            self.markCharge()
        else:
            QTimer.singleShot(delay,self.markChargeTrigger)

    def markChargeTrigger(self):
        self.markCharge()

    #Records charge (put beans in) marker. called from push button 'Charge'
    @pyqtSlot(bool)
    def markCharge(self,_=False):
        removed = False
        try:
            self.profileDataSemaphore.acquire(1)
            if self.flagstart:
                try:
                    self.aw.soundpopSignal.emit()
                    #prevents accidentally deleting a modified profile.
                    self.fileDirtySignal.emit()
                    if self.aw.buttonCHARGE.isFlat() and self.timeindex[0] > -1:
                        # undo wrongly set CHARGE
                        ## deactivate autoCHARGE
                        ##self.autoCHARGEenabled = False
                        st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation', 'CHARGE'))
                        if len(self.l_annotations) > 1 and self.l_annotations[-1].get_text() == st1:
                            try:
                                self.l_annotations[-1].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            try:
                                self.l_annotations[-2].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            self.l_annotations = self.l_annotations[:-2]
                            if 0 in self.l_annotations_dict:
                                del self.l_annotations_dict[0]
                            self.timeindex[0] = -1
                            removed = True
                            self.xaxistosm(redraw=False)
                    elif not self.aw.buttonCHARGE.isFlat():
                        if self.device == 18 and self.aw.simulator is None: #manual mode
                            tx,et,bt = self.aw.ser.NONE()
                            if bt != 1 and et != -1:  #cancel
                                self.drawmanual(et,bt,tx)
                                self.timeindex[0] = len(self.timex)-1
                            else:
                                return
                        else:
                            if self.autoChargeIdx:
                                # prevent CHARGE outofindex:
                                if len(self.timex) > self.autoChargeIdx:
                                    self.timeindex[0] = self.autoChargeIdx
                                elif len(self.timex) > self.autoChargeIdx - 1:
                                    # not yet enough readings
                                    self.timeindex[0] = self.autoChargeIdx - 1
                                else:
                                    return
                            elif len(self.timex) > 0:
                                self.timeindex[0] = len(self.timex)-1
                            else:
                                self.autoChargeIdx = 1 # set CHARGE on next (first) reading
                                message = QApplication.translate('Message','Not enough data collected yet. Try again in a few seconds')
                                self.aw.sendmessage(message)
                                return
                            if self.aw.pidcontrol.pidOnCHARGE and not self.aw.pidcontrol.pidActive: # Arduino/TC4, Hottop, MODBUS
                                self.aw.pidcontrol.pidOn()
                        if self.chargeTimerPeriod > 0:
                            self.aw.setTimerColor('timer')
                        try:
                            # adjust startofx to the new timeindex[0] as it depends on timeindex[0]
                            if self.locktimex:
                                self.startofx = self.locktimex_start + self.timex[self.timeindex[0]]
                            else:
                                self.startofx = self.chargemintime + self.timex[self.timeindex[0]] # we set the min x-axis limit to the CHARGE Min time
                        except Exception: # pylint: disable=broad-except
                            pass

                        try:
                            # adjust endofx back to resetmaxtime (it might have been extended if "Expand" is ticked beyond the resetmaxtime at START)
                            if not self.locktimex and not self.fixmaxtime and self.endofx != self.resetmaxtime:
                                self.endofx = self.resetmaxtime
                        except Exception: # pylint: disable=broad-except
                            pass
                        self.xaxistosm(redraw=False) # need to fix uneven x-axis labels like -0:13

                        if self.BTcurve:
                            # only if BT is shown we place the annotation:
                            d = self.ylimit - self.ylimit_min
                            st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation', 'CHARGE'))
                            t2 = self.temp2[self.timeindex[0]]
                            tx = self.timex[self.timeindex[0]]
                            self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,t2,t2,d)
                            time_temp_annos = self.annotate(t2,st1,tx,t2,self.ystep_up,self.ystep_down,draggable_anno_key=0)
                            if time_temp_annos is not None:
                                self.l_annotations += time_temp_annos

                        # mark active slider values that are not zero
                        for slidernr in range(4):
                            if self.aw.eventslidervisibilities[slidernr]:
                                # we record also for inactive sliders as some button press actions might have changed the event values also for those
                                slidervalue = 0
                                if slidernr == 0:
                                    slidervalue = self.aw.slider1.value()
                                elif slidernr == 1:
                                    slidervalue = self.aw.slider2.value()
                                elif slidernr == 2:
                                    slidervalue = self.aw.slider3.value()
                                elif slidernr == 3:
                                    slidervalue = self.aw.slider4.value()
                                # only mark events that are non-zero # and have not been marked before not to duplicate the event values
                                if slidervalue != 0: #  and slidernr not in self.specialeventstype:
                                    value = self.aw.float2float((slidervalue + 10.0) / 10.0)
                                    # note that EventRecordAction avoids to generate events were type and value matches to the previously recorded one
                                    self.EventRecordAction(extraevent = 1,eventtype=slidernr,eventvalue=value,takeLock=False,doupdategraphics=False)
                                    # we don't take another lock in EventRecordAction as we already hold that lock!
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
            else:
                message = QApplication.translate('Message','CHARGE: Scope is not recording')
                self.aw.sendmessage(message)
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' markCharge() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
        finally:
            if self.profileDataSemaphore.available() < 1:
                self.profileDataSemaphore.release(1)
        if self.flagstart:
            # redraw (within timealign) should not be called if semaphore is hold!
            # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
            self.timealign(redraw=True,recompute=False,force=True) # redraws at least the canvas if redraw=True, so no need here for doing another canvas.draw()
            if self.aw.buttonCHARGE.isFlat():
                if removed:
                    self.aw.buttonCHARGE.setFlat(False)
                    self.aw.buttonCHARGE.startAnimation()
                    self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
            else:
                self.aw.eventactionx(self.buttonactions[0],self.buttonactionstrings[0])
                self.aw.buttonCHARGE.setFlat(True)
                self.aw.buttonCHARGE.stopAnimation()
                try:
                    fmt = '%.1f' if self.LCDdecimalplaces else '%.0f'
                    bt = fmt%self.temp2[self.timeindex[0]] + self.mode
                    message = QApplication.translate('Message','Roast time starts now 00:00 BT = {0}').format(bt)
                    self.aw.sendmessage(message)
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)
                if self.roastpropertiesAutoOpenFlag:
                    self.aw.openPropertiesSignal.emit()
                if not(self.autoChargeIdx and self.timeindex[0] < 0):
                    self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
            self.aw.onMarkMoveToNext(self.aw.buttonCHARGE)


    # called from sample() and marks the autodetected TP visually on the graph
    def markTP(self):
        try:
            self.profileDataSemaphore.acquire(1)
            if self.flagstart and self.markTPflag and self.TPalarmtimeindex and self.timeindex[0] != -1 and len(self.timex) > self.TPalarmtimeindex:
                st = stringfromseconds(self.timex[self.TPalarmtimeindex]-self.timex[self.timeindex[0]],False)
                st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','TP {0}').format(st))
                #anotate temperature
                d = self.ylimit - self.ylimit_min
                self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[0]],self.temp2[self.TPalarmtimeindex],d)
                time_temp_annos = self.annotate(self.temp2[self.TPalarmtimeindex],st1,self.timex[self.TPalarmtimeindex],self.temp2[self.TPalarmtimeindex],self.ystep_up,self.ystep_down,0,1.,draggable_anno_key=-1)
                if time_temp_annos is not None:
                    self.l_annotations += time_temp_annos
                #self.fig.canvas.draw() # not needed as self.annotate does the (partial) redraw
                self.updateBackground() # but we need to update the background cache with the new annotation
                st2 = f'{self.temp2[self.TPalarmtimeindex]:.1f} {self.mode}'
                message = QApplication.translate('Message','[TP] recorded at {0} BT = {1}').format(st,st2)
                #set message at bottom
                self.aw.sendmessage(message)
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' markTP() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
        finally:
            if self.profileDataSemaphore.available() < 1:
                self.profileDataSemaphore.release(1)
        self.autoTPIdx = 0 # avoid a loop on auto marking

    # trigger to be called by the markDRYSignal
    @pyqtSlot()
    def markDRYTrigger(self):
        self.markDryEnd()

    @pyqtSlot(bool)
    def markDryEnd(self,_=False):
        if len(self.timex) > 1:
            removed = False
            try:
                self.profileDataSemaphore.acquire(1)
                if self.flagstart:
                    self.aw.soundpopSignal.emit()
                    #prevents accidentally deleting a modified profile.
                    self.fileDirtySignal.emit()

                    if self.timeindex[0] > -1:
                        start = self.timex[self.timeindex[0]]
                    else:
                        start = 0
                    if self.aw.buttonDRY.isFlat() and self.timeindex[1] > 0:
                        # undo wrongly set DRY
                        # deactivate autoDRY
                        self.autoDRYenabled = False
                        st = stringfromseconds(self.timex[self.timeindex[1]]-start,False)
                        DE_str = self.aw.arabicReshape(QApplication.translate('Scope Annotation','DE {0}').format(st))
                        if len(self.l_annotations) > 1 and self.l_annotations[-1].get_text() == DE_str:
                            try:
                                self.l_annotations[-1].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            try:
                                self.l_annotations[-2].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            self.l_annotations = self.l_annotations[:-2]
                            if 1 in self.l_annotations_dict:
                                del self.l_annotations_dict[1]
                            self.timeindex[1] = 0
                            removed = True
                    elif not self.aw.buttonDRY.isFlat():
                        if self.device != 18 or self.aw.simulator is not None:
                            self.timeindex[1] = max(0,len(self.timex)-1)
                        else:
                            tx,et,bt = self.aw.ser.NONE()
                            if et != -1 and bt != -1:
                                self.drawmanual(et,bt,tx)
                                self.timeindex[1] = max(0,len(self.timex)-1)
                            else:
                                return
                        if self.phasesbuttonflag:
                            self.phases[1] = int(round(self.temp2[self.timeindex[1]]))
                        if self.BTcurve:
                            # only if BT is shown we place the annotation:
                            #calculate time elapsed since charge time
                            st = stringfromseconds(self.timex[self.timeindex[1]]-start,False)
                            st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','DE {0}').format(st))
                            #anotate temperature
                            d = self.ylimit - self.ylimit_min
                            self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[0]],self.temp2[self.timeindex[1]],d)
                            time_temp_annos = self.annotate(self.temp2[self.timeindex[1]],st1,self.timex[self.timeindex[1]],self.temp2[self.timeindex[1]],self.ystep_up,self.ystep_down,draggable_anno_key=1)
                            if time_temp_annos is not None:
                                self.l_annotations += time_temp_annos
                            #self.fig.canvas.draw() # not needed as self.annotate does the (partial) redraw
                            self.updateBackground() # but we need

                        self.phasesLCDmode = self.phasesLCDmode_l[1]

                else:
                    message = QApplication.translate('Message','DRY END: Scope is not recording')
                    self.aw.sendmessage(message)
            except Exception as ex: # pylint: disable=broad-except
                _log.exception(ex)
                _, _, exc_tb = sys.exc_info()
                self.adderror((QApplication.translate('Error Message', 'Exception:') + ' markDryEnd() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
            finally:
                if self.profileDataSemaphore.available() < 1:
                    self.profileDataSemaphore.release(1)
            if self.flagstart:
                # redraw (within timealign) should not be called if semaphore is hold!
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                if self.alignEvent in [1,7]:
                    self.timealign(redraw=True,recompute=False) # redraws at least the canvas if redraw=True, so no need here for doing another canvas.draw()
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                if self.aw.buttonDRY.isFlat():
                    if removed:
                        self.updateBackground()
                        self.aw.buttonDRY.setFlat(False)
                        if self.timeindex[0] == -1: # reactivate the CHARGE button if not yet set
                            self.aw.buttonCHARGE.setFlat(False)
                            if self.buttonvisibility[0]:
                                self.aw.buttonCHARGE.startAnimation()
                        self.updategraphicsSignal.emit()
                else:
                    self.aw.buttonDRY.setFlat(True) # deactivate DRY button
                    self.aw.buttonCHARGE.setFlat(True) # also deactivate CHARGE button
                    self.aw.buttonCHARGE.stopAnimation()
                    try:
                        self.aw.eventactionx(self.buttonactions[1],self.buttonactionstrings[1])
                        if self.timeindex[0] > -1:
                            start = self.timex[self.timeindex[0]]
                        else:
                            start = 0
                        st = stringfromseconds(self.timex[self.timeindex[1]]-start)
                        st2 = f'{self.temp2[self.timeindex[1]]:.1f} {self.mode}'
                        message = QApplication.translate('Message','[DRY END] recorded at {0} BT = {1}').format(st,st2)
                        #set message at bottom
                        self.aw.sendmessage(message)
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                    if self.autoDryIdx == 0:
                        # only if markDryEnd() is not anyhow triggered within updategraphics()
                        self.updategraphicsSignal.emit()
                self.aw.onMarkMoveToNext(self.aw.buttonDRY)

    # trigger to be called by the markFCsSignal
    @pyqtSlot()
    def markFCsTrigger(self):
        self.mark1Cstart()

    #record 1C start markers of BT. called from push buttonFCs of application window
    @pyqtSlot(bool)
    def mark1Cstart(self,_=False):
        if len(self.timex) > 1:
            removed = False
            try:
                self.profileDataSemaphore.acquire(1)
                if self.flagstart:
                    self.aw.soundpopSignal.emit()
                    #prevents accidentally deleting a modified profile.
                    self.fileDirtySignal.emit()

                    if self.timeindex[0] > -1:
                        start = self.timex[self.timeindex[0]]
                    else:
                        start = 0
                    if self.aw.buttonFCs.isFlat() and self.timeindex[2] > 0:
                        # undo wrongly set FCs
                        # deactivate autoFCs
                        self.autoFCsenabled = False
                        st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','FCs {0}').format(stringfromseconds(self.timex[self.timeindex[2]]-start,False)))
                        if len(self.l_annotations) > 1 and self.l_annotations[-1].get_text() == st1:
                            try:
                                self.l_annotations[-1].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            try:
                                self.l_annotations[-2].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            self.l_annotations = self.l_annotations[:-2]
                            if 2 in self.l_annotations_dict:
                                del self.l_annotations_dict[2]
                            self.timeindex[2] = 0
                            removed = True
                    elif not self.aw.buttonFCs.isFlat():
                        # record 1Cs only if Charge mark has been done
                        if self.device != 18 or self.aw.simulator is not None:
                            self.timeindex[2] = max(0,len(self.timex)-1)
                        else:
                            tx,et,bt = self.aw.ser.NONE()
                            if et != -1 and bt != -1:
                                self.drawmanual(et,bt,tx)
                                self.timeindex[2] = max(0,len(self.timex)-1)
                            else:
                                return
                        if self.phasesbuttonflag:
                            self.phases[2] = int(round(self.temp2[self.timeindex[2]]))
                        if self.BTcurve:
                            # only if BT is shown we place the annotation:
                            #calculate time elapsed since charge time
                            st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','FCs {0}').format(stringfromseconds(self.timex[self.timeindex[2]]-start,False)))
                            d = self.ylimit - self.ylimit_min
                            if self.timeindex[1]:
                                self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[1]],self.temp2[self.timeindex[2]],d)
                            else:
                                self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[0]],self.temp2[self.timeindex[2]],d)
                            time_temp_annos = self.annotate(self.temp2[self.timeindex[2]],st1,self.timex[self.timeindex[2]],self.temp2[self.timeindex[2]],self.ystep_up,self.ystep_down,draggable_anno_key=2)
                            if time_temp_annos is not None:
                                self.l_annotations += time_temp_annos
                            #self.fig.canvas.draw() # not needed as self.annotate does the (partial) redraw
                            self.updateBackground() # but we need

                        self.phasesLCDmode = self.phasesLCDmode_l[2]
                else:
                    message = QApplication.translate('Message','FC START: Scope is not recording')
                    self.aw.sendmessage(message)
            except Exception as ex: # pylint: disable=broad-except
                _log.exception(ex)
                _, _, exc_tb = sys.exc_info()
                self.adderror((QApplication.translate('Error Message', 'Exception:') + ' mark1Cstart() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
            finally:
                if self.profileDataSemaphore.available() < 1:
                    self.profileDataSemaphore.release(1)
            if self.flagstart:
                # redraw (within timealign) should not be called if semaphore is hold!
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                if self.alignEvent in [2,7]:
                    self.timealign(redraw=True,recompute=False) # redraws at least the canvas if redraw=True, so no need here for doing another canvas.draw()
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                if self.aw.buttonFCs.isFlat():
                    if removed:
                        self.updateBackground()
                        self.aw.buttonFCs.setFlat(False)
                        if self.timeindex[1] == 0: # reactivate the DRY button if not yet set
                            self.aw.buttonDRY.setFlat(False)
                            if self.timeindex[0] == -1: # reactivate the CHARGE button if not yet set
                                self.aw.buttonCHARGE.setFlat(False)
                                if self.buttonvisibility[0]:
                                    self.aw.buttonCHARGE.startAnimation()
                        self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
                else:
                    self.aw.buttonFCs.setFlat(True)
                    self.aw.buttonCHARGE.setFlat(True)
                    self.aw.buttonCHARGE.stopAnimation()
                    self.aw.buttonDRY.setFlat(True)
                    self.aw.eventactionx(self.buttonactions[2],self.buttonactionstrings[2])
                    if self.timeindex[0] > -1:
                        start = self.timex[self.timeindex[0]]
                    else:
                        start = 0
                    st1 = stringfromseconds(self.timex[self.timeindex[2]]-start)
                    st2 = f'{self.temp2[self.timeindex[2]]:.1f} {self.mode}'
                    message = QApplication.translate('Message','[FC START] recorded at {0} BT = {1}').format(st1,st2)
                    self.aw.sendmessage(message)
                    if self.autoFCsIdx == 0:
                        # only if mark1Cstart() is not triggered from within updategraphics() and the canvas is anyhow updated
                        self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
                self.aw.onMarkMoveToNext(self.aw.buttonFCs)

    # trigger to be called by the markFCeSignal
    @pyqtSlot()
    def markFCeTrigger(self):
        self.mark1Cend()

    #record 1C end markers of BT. called from buttonFCe of application window
    @pyqtSlot(bool)
    def mark1Cend(self,_=False):
        if len(self.timex) > 1:
            removed = False
            try:
                self.profileDataSemaphore.acquire(1)
                if self.flagstart:
                    self.aw.soundpopSignal.emit()
                    #prevents accidentally deleting a modified profile.
                    self.fileDirtySignal.emit()

                    if self.timeindex[0] > -1:
                        start = self.timex[self.timeindex[0]]
                    else:
                        start = 0
                    if self.aw.buttonFCe.isFlat() and self.timeindex[3] > 0:
                        # undo wrongly set FCe
                        st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','FCe {0}').format(stringfromseconds(self.timex[self.timeindex[3]]-start,False)))
                        if len(self.l_annotations) > 1 and self.l_annotations[-1].get_text() == st1:
                            try:
                                self.l_annotations[-1].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            try:
                                self.l_annotations[-2].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            self.l_annotations = self.l_annotations[:-2]
                            if 3 in self.l_annotations_dict:
                                del self.l_annotations_dict[3]
                            self.timeindex[3] = 0
                            removed = True
                    elif not self.aw.buttonFCe.isFlat():
                        if self.device != 18 or self.aw.simulator is not None:
                            self.timeindex[3] = max(0,len(self.timex)-1)
                        else:
                            tx,et,bt = self.aw.ser.NONE()
                            if et != -1 and bt != -1:
                                self.drawmanual(et,bt,tx)
                                self.timeindex[3] = max(0,len(self.timex)-1)
                            else:
                                return
                        if self.BTcurve:
                            # only if BT is shown we place the annotation:
                            #calculate time elapsed since charge time
                            st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','FCe {0}').format(stringfromseconds(self.timex[self.timeindex[3]]-start,False)))
                            d = self.ylimit - self.ylimit_min
                            self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[2]],self.temp2[self.timeindex[3]],d)
                            time_temp_annos = self.annotate(self.temp2[self.timeindex[3]],st1,self.timex[self.timeindex[3]],self.temp2[self.timeindex[3]],self.ystep_up,self.ystep_down,draggable_anno_key=3)
                            if time_temp_annos is not None:
                                self.l_annotations += time_temp_annos
                            #self.fig.canvas.draw() # not needed as self.annotate does the (partial) redraw
                            self.updateBackground() # but we need
                else:
                    message = QApplication.translate('Message','FC END: Scope is not recording')
                    self.aw.sendmessage(message)
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
                _, _, exc_tb = sys.exc_info()
                self.adderror((QApplication.translate('Error Message', 'Exception:') + ' mark1Cend() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
            finally:
                if self.profileDataSemaphore.available() < 1:
                    self.profileDataSemaphore.release(1)
            if self.flagstart:
                # redraw (within timealign) should not be called if semaphore is hold!
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                if self.alignEvent in [3,7]:
                    self.timealign(redraw=True,recompute=False) # redraws at least the canvas if redraw=True, so no need here for doing another canvas.draw()
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                if self.aw.buttonFCe.isFlat():
                    if removed:
                        self.updateBackground()
                        self.aw.buttonFCe.setFlat(False)
                        if self.timeindex[2] == 0: # reactivate the FCs button if not yet set
                            self.aw.buttonFCs.setFlat(False)
                            if self.timeindex[1] == 0: # reactivate the DRY button if not yet set
                                self.aw.buttonDRY.setFlat(False)
                                if self.timeindex[0] == -1: # reactivate the CHARGE button if not yet set
                                    self.aw.buttonCHARGE.setFlat(False)
                                    if self.buttonvisibility[0]:
                                        self.aw.buttonCHARGE.startAnimation()
                        self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
                else:
                    self.aw.buttonFCe.setFlat(True)
                    self.aw.buttonCHARGE.setFlat(True)
                    self.aw.buttonCHARGE.stopAnimation()
                    self.aw.buttonDRY.setFlat(True)
                    self.aw.buttonFCs.setFlat(True)
                    self.aw.eventactionx(self.buttonactions[3],self.buttonactionstrings[3])
                    if self.timeindex[0] > -1:
                        start = self.timex[self.timeindex[0]]
                    else:
                        start = 0
                    st1 = stringfromseconds(self.timex[self.timeindex[3]]-start)
                    st2 = f'{self.temp2[self.timeindex[3]]:.1f} {self.mode}'
                    message = QApplication.translate('Message','[FC END] recorded at {0} BT = {1}').format(st1,st2)
                    self.aw.sendmessage(message)
                    self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
                self.aw.onMarkMoveToNext(self.aw.buttonFCe)


    # trigger to be called by the markSCsSignal
    @pyqtSlot()
    def markSCsTrigger(self):
        self.mark2Cstart()

    #record 2C start markers of BT. Called from buttonSCs of application window
    @pyqtSlot(bool)
    def mark2Cstart(self,_=False):
        if len(self.timex) > 1:
            st1 = ''
            st2 = ''
            removed = False
            try:
                self.profileDataSemaphore.acquire(1)
                if self.flagstart:
                    self.aw.soundpopSignal.emit()
                    #prevents accidentally deleting a modified profile.
                    self.fileDirtySignal.emit()

                    if self.timeindex[0] > -1:
                        start = self.timex[self.timeindex[0]]
                    else:
                        start = 0
                    if self.aw.buttonSCs.isFlat() and self.timeindex[4] > 0:
                        # undo wrongly set FCs
                        st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','SCs {0}').format(stringfromseconds(self.timex[self.timeindex[4]]-start,False)))
                        if len(self.l_annotations) > 1 and self.l_annotations[-1].get_text() == st1:
                            try:
                                self.l_annotations[-1].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            try:
                                self.l_annotations[-2].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            self.l_annotations = self.l_annotations[:-2]
                            if 4 in self.l_annotations_dict:
                                del self.l_annotations_dict[4]
                            self.timeindex[4] = 0
                            removed = True
                    elif not self.aw.buttonSCs.isFlat():
                        if self.device != 18 or self.aw.simulator is not None:
                            self.timeindex[4] = max(0,len(self.timex)-1)
                        else:
                            tx,et,bt = self.aw.ser.NONE()
                            if et != -1 and bt != -1:
                                self.drawmanual(et,bt,tx)
                                self.timeindex[4] = max(0,len(self.timex)-1)
                            else:
                                return
                        if self.BTcurve:
                            # only if BT is shown we place the annotation:
                            st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','SCs {0}').format(stringfromseconds(self.timex[self.timeindex[4]]-start,False)))
                            d = self.ylimit - self.ylimit_min
                            if self.timeindex[3]:
                                self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[3]],self.temp2[self.timeindex[4]],d)
                            else:
                                self.ystep_down,self.ystep_up = self.findtextgap(0,0,self.temp2[self.timeindex[4]],self.temp2[self.timeindex[4]],d)
                            time_temp_annos = self.annotate(self.temp2[self.timeindex[4]],st1,self.timex[self.timeindex[4]],self.temp2[self.timeindex[4]],self.ystep_up,self.ystep_down,draggable_anno_key=4)
                            if time_temp_annos is not None:
                                self.l_annotations += time_temp_annos
                            #self.fig.canvas.draw() # not needed as self.annotate does the (partial) redraw
                            self.updateBackground() # but we need
                else:
                    message = QApplication.translate('Message','SC START: Scope is not recording')
                    self.aw.sendmessage(message)
            except Exception as ex: # pylint: disable=broad-except
                _log.exception(ex)
                _, _, exc_tb = sys.exc_info()
                self.adderror((QApplication.translate('Error Message', 'Exception:') + ' mark2Cstart() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
            finally:
                if self.profileDataSemaphore.available() < 1:
                    self.profileDataSemaphore.release(1)
            if self.flagstart:
                # redraw (within timealign) should not be called if semaphore is hold!
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                if self.alignEvent in [4,7]:
                    self.timealign(redraw=True,recompute=False) # redraws at least the canvas if redraw=True, so no need here for doing another canvas.draw()
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                if self.aw.buttonSCs.isFlat():
                    if removed:
                        self.updateBackground()
                        self.aw.buttonSCs.setFlat(False)
                        if self.timeindex[3] == 0: # reactivate the FCe button if not yet set
                            self.aw.buttonFCe.setFlat(False)
                            if self.timeindex[2] == 0: # reactivate the FCs button if not yet set
                                self.aw.buttonFCs.setFlat(False)
                                if self.timeindex[1] == 0: # reactivate the DRY button if not yet set
                                    self.aw.buttonDRY.setFlat(False)
                                    if self.timeindex[0] == -1: # reactivate the CHARGE button if not yet set
                                        self.aw.buttonCHARGE.setFlat(False)
                                        if self.buttonvisibility[0]:
                                            self.aw.buttonCHARGE.startAnimation()
                        self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
                else:
                    self.aw.buttonSCs.setFlat(True)
                    self.aw.buttonCHARGE.setFlat(True)
                    self.aw.buttonCHARGE.stopAnimation()
                    self.aw.buttonDRY.setFlat(True)
                    self.aw.buttonFCs.setFlat(True)
                    self.aw.buttonFCe.setFlat(True)
                    try:
                        self.aw.eventactionx(self.buttonactions[4],self.buttonactionstrings[4])
                        if self.timeindex[0] > -1:
                            start = self.timex[self.timeindex[0]]
                        else:
                            start = 0
                        try:
                            st1 = stringfromseconds(self.timex[self.timeindex[4]]-start)
                            st2 = f'{self.temp2[self.timeindex[4]]:.1f} {self.mode}'
                        except Exception: # pylint: disable=broad-except
                            pass
                        message = QApplication.translate('Message','[SC START] recorded at {0} BT = {1}').format(st1,st2)
                        self.aw.sendmessage(message)
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)
                    self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
                self.aw.onMarkMoveToNext(self.aw.buttonSCs)

    # trigger to be called by the markSCeSignal
    @pyqtSlot()
    def markSCeTrigger(self):
        self.mark2Cend()

    #record 2C end markers of BT. Called from buttonSCe of application window
    @pyqtSlot(bool)
    def mark2Cend(self,_=False):
        if len(self.timex) > 1:
            removed = False
            try:
                self.profileDataSemaphore.acquire(1)
                if self.flagstart:
                    self.aw.soundpopSignal.emit()
                    #prevents accidentally deleting a modified profile.
                    self.fileDirtySignal.emit()

                    if self.timeindex[0] > -1:
                        start = self.timex[self.timeindex[0]]
                    else:
                        start = 0
                    if self.aw.buttonSCe.isFlat() and self.timeindex[5] > 0:
                        # undo wrongly set FCs
                        st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','SCe {0}').format(stringfromseconds(self.timex[self.timeindex[5]]-start,False)))
                        if len(self.l_annotations) > 1 and self.l_annotations[-1].get_text() == st1:
                            try:
                                self.l_annotations[-1].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            try:
                                self.l_annotations[-2].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            self.l_annotations = self.l_annotations[:-2]
                            if 5 in self.l_annotations_dict:
                                del self.l_annotations_dict[5]
                            self.timeindex[5] = 0
                            removed = True
                    elif not self.aw.buttonSCe.isFlat():
                        if self.device != 18 or self.aw.simulator is not None:
                            self.timeindex[5] = max(0,len(self.timex)-1)
                        else:
                            tx,et,bt = self.aw.ser.NONE()
                            if et != -1 and bt != -1:
                                self.drawmanual(et,bt,tx)
                                self.timeindex[5] = max(0,len(self.timex)-1)
                            else:
                                return
                        if self.BTcurve:
                            # only if BT is shown we place the annotation:
                            st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','SCe {0}').format(stringfromseconds(self.timex[self.timeindex[5]]-start,False)))
                            d = self.ylimit - self.ylimit_min
                            self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[4]],self.temp2[self.timeindex[5]],d)
                            time_temp_annos = self.annotate(self.temp2[self.timeindex[5]],st1,self.timex[self.timeindex[5]],self.temp2[self.timeindex[5]],self.ystep_up,self.ystep_down,draggable_anno_key=5)
                            if time_temp_annos is not None:
                                self.l_annotations += time_temp_annos
                            #self.fig.canvas.draw() # not needed as self.annotate does the (partial) redraw
                            self.updateBackground() # but we need
                else:
                    message = QApplication.translate('Message','SC END: Scope is not recording')
                    self.aw.sendmessage(message)
            except Exception as ex: # pylint: disable=broad-except
                _log.exception(ex)
                _, _, exc_tb = sys.exc_info()
                self.adderror((QApplication.translate('Error Message', 'Exception:') + ' mark2Cend() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
            finally:
                if self.profileDataSemaphore.available() < 1:
                    self.profileDataSemaphore.release(1)
            if self.flagstart and len(self.timex) > 0:
                # redraw (within timealign) should not be called if semaphore is hold!
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                if self.alignEvent in [5,7]:
                    self.timealign(redraw=True,recompute=False) # redraws at least the canvas if redraw=True, so no need here for doing another canvas.draw()
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                if self.aw.buttonSCe.isFlat():
                    if removed:
                        self.updateBackground()
                        self.aw.buttonSCe.setFlat(False)
                        if self.timeindex[4] == 0: # reactivate the SCs button if not yet set
                            self.aw.buttonSCs.setFlat(False)
                            if self.timeindex[3] == 0: # reactivate the FCe button if not yet set
                                self.aw.buttonFCe.setFlat(False)
                                if self.timeindex[2] == 0: # reactivate the FCs button if not yet set
                                    self.aw.buttonFCs.setFlat(False)
                                    if self.timeindex[1] == 0: # reactivate the DRY button if not yet set
                                        self.aw.buttonDRY.setFlat(False)
                                        if self.timeindex[0] == -1: # reactivate the CHARGE button if not yet set
                                            self.aw.buttonCHARGE.setFlat(False)
                                            if self.buttonvisibility[0]:
                                                self.aw.buttonCHARGE.startAnimation()
                        self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
                else:
                    self.aw.buttonSCe.setFlat(True)
                    self.aw.buttonCHARGE.setFlat(True)
                    self.aw.buttonCHARGE.stopAnimation()
                    self.aw.buttonDRY.setFlat(True)
                    self.aw.buttonFCs.setFlat(True)
                    self.aw.buttonFCe.setFlat(True)
                    self.aw.buttonSCs.setFlat(True)
                    self.aw.eventactionx(self.buttonactions[5],self.buttonactionstrings[5])
                    if self.timeindex[0] > -1:
                        start = self.timex[self.timeindex[0]]
                    else:
                        start = 0
                    st1 = stringfromseconds(self.timex[self.timeindex[5]]-start)
                    st2 = f'{self.temp2[self.timeindex[5]]:.1f} {self.mode}'
                    message = QApplication.translate('Message','[SC END] recorded at {0} BT = {1}').format(st1,st2)
                    self.aw.sendmessage(message)
                    self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
                self.aw.onMarkMoveToNext(self.aw.buttonSCe)

    # trigger to be called by the markDropSignal
    @pyqtSlot()
    def markDropTrigger(self):
        self.markDrop()

    #record end of roast (drop of beans). Called from push button 'Drop'
    @pyqtSlot(bool)
    def markDrop(self,_=False):
        if len(self.timex) > 1:
            removed = False
            try:
                self.profileDataSemaphore.acquire(1)
                if self.flagstart:
                    self.aw.soundpopSignal.emit()
                    #prevents accidentally deleting a modified profile.
                    self.fileDirtySignal.emit()

                    if self.timeindex[0] > -1:
                        start = self.timex[self.timeindex[0]]
                    else:
                        start = 0
                    # we check if this is the first DROP mark on this roast
                    firstDROP = self.timeindex[6] == 0 # on UNDO DROP we do not send the record to plus
                    if self.aw.buttonDROP.isFlat() and self.timeindex[6] > 0:
                        # undo wrongly set FCs
                        # deactivate autoDROP
                        self.autoDROPenabled = False
                        st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','DROP {0}').format(stringfromseconds(self.timex[self.timeindex[6]]-start,False)))
                        if len(self.l_annotations) > 1 and self.l_annotations[-1].get_text() == st1:
                            try:
                                self.l_annotations[-1].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            try:
                                self.l_annotations[-2].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            self.l_annotations = self.l_annotations[:-2]
                            if 6 in self.l_annotations_dict:
                                del self.l_annotations_dict[6]
                            self.timeindex[6] = 0
                            #decrease BatchCounter again
                            self.decBatchCounter()
                            removed = True
                    elif not self.aw.buttonDROP.isFlat():
                        self.incBatchCounter()
                        # generate UUID
                        if self.roastUUID is None: # there might be already one assigned by undo and redo the markDROP!
                            import uuid
                            self.roastUUID = uuid.uuid4().hex
                        if self.device != 18 or self.aw.simulator is not None:
                            if self.autoDropIdx:
                                self.timeindex[6] = max(0,self.autoDropIdx)
                            else:
                                self.timeindex[6] = max(0,len(self.timex)-1)
                        else:
                            tx,et,bt = self.aw.ser.NONE()
                            if et != -1 and bt != -1:
                                self.drawmanual(et,bt,tx)
                                self.timeindex[6] = max(0,len(self.timex)-1)
                            else:
                                return
                        if self.BTcurve:
                            # only if BT is shown we place the annotation:
                            st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','DROP {0}').format(stringfromseconds(self.timex[self.timeindex[6]]-start,False)))
                            d = self.ylimit - self.ylimit_min
                            if self.timeindex[5]:
                                self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[5]],self.temp2[self.timeindex[6]],d)
                            elif self.timeindex[4]:
                                self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[4]],self.temp2[self.timeindex[6]],d)
                            elif self.timeindex[3]:
                                self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[3]],self.temp2[self.timeindex[6]],d)
                            elif self.timeindex[2]:
                                self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[2]],self.temp2[self.timeindex[6]],d)
                            elif self.timeindex[1]:
                                self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[1]],self.temp2[self.timeindex[6]],d)
                            time_temp_annos = self.annotate(self.temp2[self.timeindex[6]],st1,self.timex[self.timeindex[6]],self.temp2[self.timeindex[6]],19,19,draggable_anno_key=6)
                            if time_temp_annos is not None:
                                self.l_annotations += time_temp_annos
                            #self.fig.canvas.draw() # not needed as self.annotate does the (partial) redraw
                            self.updateBackground() # but we need

                        try:
                            # update ambient temperature if a ambient temperature source is configured and no value yet established
                            self.updateAmbientTempFromPhidgetModulesOrCurve()
                        except Exception as e: # pylint: disable=broad-except
                            _log.exception(e)
    #PLUS
                        # only on first setting the DROP event (not set yet and no previous DROP undone) and if not in simulator modus, we upload to PLUS
                        if firstDROP and self.autoDROPenabled and self.aw.plus_account is not None and not bool(self.aw.simulator):
                            try:
                                self.aw.updatePlusStatus()
                            except Exception as e: # pylint: disable=broad-except
                                _log.exception(e)
                                # add to out-queue
                            try:
                                addRoast()
                            except Exception as e: # pylint: disable=broad-except
                                _log.exception(e)
                else:
                    message = QApplication.translate('Message','DROP: Scope is not recording')
                    self.aw.sendmessage(message)
            except Exception as ex: # pylint: disable=broad-except
                _log.exception(ex)
                _, _, exc_tb = sys.exc_info()
                self.adderror((QApplication.translate('Error Message', 'Exception:') + ' markDrop() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
            finally:
                if self.profileDataSemaphore.available() < 1:
                    self.profileDataSemaphore.release(1)
            if self.flagstart:
                # redraw (within timealign) should not be called if semaphore is hold!
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                if self.alignEvent in [6,7]:
                    self.timealign(redraw=True,recompute=False) # redraws at least the canvas if redraw=True, so no need here for doing another canvas.draw()
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                try:
                    if self.aw.buttonDROP.isFlat():
                        if removed:
                            self.updateBackground()
                            self.aw.buttonDROP.setFlat(False)
                            if self.timeindex[5] == 0: # reactivate the SCe button if not yet set
                                self.aw.buttonSCe.setFlat(False)
                                if self.timeindex[4] == 0: # reactivate the SCs button if not yet set
                                    self.aw.buttonSCs.setFlat(False)
                                    if self.timeindex[3] == 0: # reactivate the FCe button if not yet set
                                        self.aw.buttonFCe.setFlat(False)
                                        if self.timeindex[2] == 0: # reactivate the FCs button if not yet set
                                            self.aw.buttonFCs.setFlat(False)
                                            if self.timeindex[1] == 0: # reactivate the DRY button if not yet set
                                                self.aw.buttonDRY.setFlat(False)
                                                if self.timeindex[0] == -1: # reactivate the CHARGE button if not yet set
                                                    self.aw.buttonCHARGE.setFlat(False)
                                                    if self.buttonvisibility[0]:
                                                        self.aw.buttonCHARGE.startAnimation()
                            self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
                    else:
                        self.aw.buttonDROP.setFlat(True)
                        self.aw.buttonCHARGE.setFlat(True)
                        self.aw.buttonCHARGE.stopAnimation()
                        self.aw.buttonDRY.setFlat(True)
                        self.aw.buttonFCs.setFlat(True)
                        self.aw.buttonFCe.setFlat(True)
                        self.aw.buttonSCs.setFlat(True)
                        self.aw.buttonSCe.setFlat(True)

                        try:
                            self.aw.eventactionx(self.buttonactions[6],self.buttonactionstrings[6])
                            if self.timeindex[0] > -1:
                                start = self.timex[self.timeindex[0]]
                            else:
                                start = 0
                            st1 = stringfromseconds(self.timex[self.timeindex[6]]-start)
                            st2 = f'{self.temp2[self.timeindex[6]]:.1f} {self.mode}'
                            message = QApplication.translate('Message','Roast ended at {0} BT = {1}').format(st1,st2)
                            self.aw.sendmessage(message)
                        except Exception as e: # pylint: disable=broad-except
                            _log.exception(e)
                        # at DROP we stop the follow background on FujiPIDs and set the SV to 0
                        if self.device == 0 and self.aw.fujipid.followBackground and self.aw.fujipid.sv and self.aw.fujipid.sv > 0:
                            try:
                                self.aw.fujipid.setsv(0,silent=True)
                                self.aw.fujipid.sv = 0
                            except Exception as e: # pylint: disable=broad-except
                                _log.exception(e)
                        if self.roastpropertiesAutoOpenDropFlag:
                            self.aw.openPropertiesSignal.emit()
                        if not (self.autoDropIdx > 0 and self.timeindex[0] > -1 and not self.timeindex[6]):
                            # only if not anyhow markDrop() is triggered from within updategraphic() which guarantees an immediate redraw
                            self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
                    self.aw.onMarkMoveToNext(self.aw.buttonDROP)
                except Exception as e: # pylint: disable=broad-except
                    _log.exception(e)

    # trigger to be called by the markCoolSignal
    @pyqtSlot()
    def markCoolTrigger(self):
        self.markCoolEnd()

    @pyqtSlot(bool)
    def markCoolEnd(self,_=False):
        if len(self.timex) > 1:
            removed = False
            try:
                self.profileDataSemaphore.acquire(1)
                if self.flagstart:
                    self.aw.soundpopSignal.emit()
                    #prevents accidentally deleting a modified profile.
                    self.fileDirtySignal.emit()

                    if self.timeindex[0] > -1:
                        start = self.timex[self.timeindex[0]]
                    else:
                        start = 0
                    if self.aw.buttonCOOL.isFlat() and self.timeindex[7] > 0:
                        # undo wrongly set COOL

                        st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','CE {0}').format(stringfromseconds(self.timex[self.timeindex[7]] - start)))

                        if len(self.l_annotations) > 1 and self.l_annotations[-1].get_text() == st1:
                            try:
                                self.l_annotations[-1].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            try:
                                self.l_annotations[-2].remove()
                            except Exception: # pylint: disable=broad-except
                                pass
                            self.l_annotations = self.l_annotations[:-2]
                            if 7 in self.l_annotations_dict:
                                del self.l_annotations_dict[7]
                            self.timeindex[7] = 0
                            removed = True

                    elif not self.aw.buttonCOOL.isFlat():
                        if self.device != 18 or self.aw.simulator is not None:
                            self.timeindex[7] = max(0,len(self.timex)-1)
                        else:
                            tx,et,bt = self.aw.ser.NONE()
                            if et != -1 and bt != -1:
                                self.drawmanual(et,bt,tx)
                                self.timeindex[7] = max(0,len(self.timex)-1)
                            else:
                                return
                        if self.BTcurve:
                            # only if BT is shown we place the annotation:
                            #calculate time elapsed since charge time
                            st1 = self.aw.arabicReshape(QApplication.translate('Scope Annotation','CE {0}').format(stringfromseconds(self.timex[self.timeindex[7]] - start)))
                            #anotate temperature
                            d = self.ylimit - self.ylimit_min
                            self.ystep_down,self.ystep_up = self.findtextgap(self.ystep_down,self.ystep_up,self.temp2[self.timeindex[6]],self.temp2[self.timeindex[7]],d)
                            time_temp_annos = self.annotate(self.temp2[self.timeindex[7]],st1,self.timex[self.timeindex[7]],self.temp2[self.timeindex[7]],self.ystep_up,self.ystep_down,draggable_anno_key=7)
                            if time_temp_annos is not None:
                                self.l_annotations += time_temp_annos
                            #self.fig.canvas.draw() # not needed as self.annotate does the (partial) redraw
                            self.updateBackground() # but we need
                else:
                    message = QApplication.translate('Message','COOL: Scope is not recording')
                    self.aw.sendmessage(message)
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
                _, _, exc_tb = sys.exc_info()
                self.adderror((QApplication.translate('Error Message', 'Exception:') + ' markCoolEnd() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
            finally:
                if self.profileDataSemaphore.available() < 1:
                    self.profileDataSemaphore.release(1)
            if self.flagstart:
                # NOTE: the following self.aw.eventaction might do serial communication that acquires a lock, so release it here
                if self.aw.buttonCOOL.isFlat():
                    if removed:
                        self.updateBackground()
                        self.aw.buttonCOOL.setFlat(False)
                        if self.timeindex[6] == 0: # reactivate the DROP button if not yet set
                            self.aw.buttonDROP.setFlat(False)
                            if self.timeindex[5] == 0: # reactivate the SCe button if not yet set
                                self.aw.buttonSCe.setFlat(False)
                                if self.timeindex[4] == 0: # reactivate the SCs button if not yet set
                                    self.aw.buttonSCs.setFlat(False)
                                    if self.timeindex[3] == 0: # reactivate the FCe button if not yet set
                                        self.aw.buttonFCe.setFlat(False)
                                        if self.timeindex[2] == 0: # reactivate the FCs button if not yet set
                                            self.aw.buttonFCs.setFlat(False)
                                            if self.timeindex[1] == 0: # reactivate the DRY button if not yet set
                                                self.aw.buttonDRY.setFlat(False)
                                                if self.timeindex[0] == -1: # reactivate the CHARGE button if not yet set
                                                    self.aw.buttonCHARGE.setFlat(False)
                                                    if self.buttonvisibility[0]:
                                                        self.aw.buttonCHARGE.startAnimation()
                        self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
                else:
                    self.aw.buttonCOOL.setFlat(True)
                    self.aw.buttonCHARGE.setFlat(True)
                    self.aw.buttonCHARGE.stopAnimation()
                    self.aw.buttonDRY.setFlat(True)
                    self.aw.buttonFCs.setFlat(True)
                    self.aw.buttonFCe.setFlat(True)
                    self.aw.buttonSCs.setFlat(True)
                    self.aw.buttonSCe.setFlat(True)
                    self.aw.buttonDROP.setFlat(True)
                    self.aw.eventactionx(self.buttonactions[7],self.buttonactionstrings[7])
                    if self.timeindex[0] > -1:
                        start = self.timex[self.timeindex[0]]
                    else:
                        start = 0
                    st1 = stringfromseconds(self.timex[self.timeindex[7]]-start)
                    st2 = f'{self.temp2[self.timeindex[7]]:.1f} {self.mode}'
                    message = QApplication.translate('Message','[COOL END] recorded at {0} BT = {1}').format(st1,st2)
                    #set message at bottom
                    self.aw.sendmessage(message)
                    self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately
                self.aw.onMarkMoveToNext(self.aw.buttonCOOL)

    def decBatchCounter(self):
        if not bool(self.aw.simulator):
            if self.lastroastepoch + 5400 < self.roastepoch:
                # reset the sequence counter
                self.batchsequence = 1
            elif self.batchsequence > 1:
                self.batchsequence -= 1
            self.roastbatchpos = self.batchsequence
        if self.batchcounter > -1 and not bool(self.aw.simulator):
            self.batchcounter -= 1 # we decrease the batch counter
            # set the batchcounter of the current profile
            self.roastbatchnr = 0
            # store updated batchcounter immediately in the app settings
            try:
                app_settings = QSettings()
                app_settings.beginGroup('Batch')
                app_settings.setValue('batchcounter',self.batchcounter)
                app_settings.setValue('batchsequence',self.batchsequence)
                app_settings.endGroup()
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            # decr. the batchcounter of the loaded app settings
            if self.aw.settingspath and self.aw.settingspath != '':
                try:
                    settings = QSettings(self.aw.settingspath,QSettings.Format.IniFormat)
                    settings.beginGroup('Batch')
                    if settings.contains('batchcounter'):
                        bc = toInt(settings.value('batchcounter',self.batchcounter))
                        bprefix = toString(settings.value('batchprefix',self.batchprefix))
                        if bc > -1 and bc == self.batchcounter+1 and self.batchprefix == bprefix:
                            settings.setValue('batchcounter',bc - 1)
                            settings.setValue('batchsequence',self.batchsequence)
                    settings.endGroup()
                except Exception: # pylint: disable=broad-except
                    self.aw.settingspath = ''

    def incBatchCounter(self):
        if not bool(self.aw.simulator):
            # update batchsequence by estimating batch sequence (roastbatchpos) from lastroastepoch and roastepoch
            # if this roasts DROP is more than 1.5h after the last registered DROP, we assume a new session starts
            if self.lastroastepoch + 5400 < self.roastepoch:
                # reset the sequence counter
                self.batchsequence = 1
            else:
                self.batchsequence += 1
            self.roastbatchpos = self.batchsequence
        # update lastroastepoch to time of roastdate
        self.lastroastepoch = self.roastepoch
        # set roastbatchpos
        if self.batchcounter > -1 and not bool(self.aw.simulator):
            self.batchcounter += 1 # we increase the batch counter
            # set the batchcounter of the current profile
            self.roastbatchnr = self.batchcounter
            # set the batchprefix of the current profile
            self.roastbatchprefix = self.batchprefix
            # store updated batchcounter immediately in the app settings
            try:
                app_settings = QSettings()
                app_settings.beginGroup('Batch')
                app_settings.setValue('batchcounter',self.batchcounter)
                app_settings.setValue('batchsequence',self.batchsequence)
                app_settings.setValue('lastroastepoch',self.lastroastepoch)
                app_settings.endGroup()
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            # incr. the batchcounter of the loaded app settings
            if self.aw.settingspath and self.aw.settingspath != '':
                try:
                    settings = QSettings(self.aw.settingspath,QSettings.Format.IniFormat)
                    settings.beginGroup('Batch')
                    if settings.contains('batchcounter'):
                        bc = toInt(settings.value('batchcounter',self.batchcounter))
                        bprefix = toString(settings.value('batchprefix',self.batchprefix))
                        if bc > -1 and self.batchprefix == bprefix:
                            settings.setValue('batchcounter',self.batchcounter)
                            settings.setValue('batchsequence',self.batchsequence)
                            settings.setValue('lastroastepoch',self.lastroastepoch)
                    settings.endGroup()
                except Exception: # pylint: disable=broad-except
                    self.aw.settingspath = ''
        else: # batch counter system inactive
            # set the batchcounter of the current profiles
            self.roastbatchnr = 0

    # action of the EVENT button
    @pyqtSlot(bool)
    def EventRecord_action(self,_=False):
        self.EventRecord()

    @pyqtSlot(int)
    def EventRecordSlot(self,ee):
        self.EventRecord(ee)

    def EventRecord(self,extraevent=None,takeLock=True,doupdategraphics=True,doupdatebackground=True):
        try:
            if extraevent is not None:
                if self.aw.extraeventstypes[extraevent] <= 4:
                    self.EventRecordAction(
                        extraevent=extraevent,
                        eventtype=self.aw.extraeventstypes[extraevent],
                        eventvalue=self.aw.extraeventsvalues[extraevent],
                        eventdescription=self.aw.extraeventsdescriptions[extraevent],takeLock=takeLock,
                        doupdategraphics=doupdategraphics,doupdatebackground=doupdatebackground)
                elif self.aw.extraeventstypes[extraevent] == 9:
                    self.EventRecordAction(
                        extraevent=extraevent,
                        eventtype=4,  # we map back to the untyped event type
                        eventvalue=self.aw.extraeventsvalues[extraevent],
                        eventdescription=self.aw.extraeventsdescriptions[extraevent],takeLock=takeLock,
                        doupdategraphics=doupdategraphics,doupdatebackground=doupdatebackground)
                else: # on "relative" event values, we take the last value set per event via the recordextraevent call before
                    self.EventRecordAction(
                        extraevent=extraevent,
                        eventtype=self.aw.extraeventstypes[extraevent]-5,
                        eventvalue=self.eventsExternal2InternalValue(self.aw.extraeventsactionslastvalue[self.aw.extraeventstypes[extraevent]-5]),
                        eventdescription=self.aw.extraeventsdescriptions[extraevent],takeLock=takeLock,
                        doupdategraphics=doupdategraphics,doupdatebackground=doupdatebackground)
            else:
                self.EventRecordAction(extraevent=extraevent,takeLock=takeLock,
                doupdategraphics=doupdategraphics,doupdatebackground=doupdatebackground)
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' EventRecord() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))

    #Marks location in graph of special events. For example change a fan setting.
    #Uses the position of the time index (variable self.timex) as location in time
    # extraevent is given when called from self.aw.recordextraevent() from an extra Event Button
    def EventRecordAction(self,extraevent=None,eventtype=None,eventvalue=None,eventdescription='',takeLock=True,doupdategraphics=True,doupdatebackground=True):
        try:
            if takeLock:
                self.profileDataSemaphore.acquire(1)
            if self.flagstart:
                if len(self.timex) > 0 or (self.device == 18 and self.aw.simulator is None):
                    self.aw.soundpopSignal.emit()
                    #prevents accidentally deleting a modified profile.
                    self.fileDirtySignal.emit()
                    Nevents = len(self.specialevents)
                    #if in manual mode record first the last point in self.timex[]
                    if self.device == 18 and self.aw.simulator is None:
                        if not doupdategraphics and not doupdatebackground: # a call from a multiple event action
                            tx,et,bt = self.timeclock.elapsed()/1000.,-1,-1
                        else:
                            tx,et,bt = self.aw.ser.NONE()
                        if bt != -1 or et != -1:
                            self.drawmanual(et,bt,tx)
                        elif bt==-1 and et==-1:
                            return
                    #i = index number of the event (current length of the time list)
                    i = len(self.timex)-1
                    # if Description, Type and Value of the new event equals the last recorded one, we do not record this again!
                    if not(self.specialeventstype) or not(self.specialeventsvalue) or not(self.specialeventsStrings) or not(eventtype != 4 and self.specialeventstype[-1] == eventtype and self.specialeventsvalue[-1] == eventvalue and self.specialeventsStrings[-1] == eventdescription):
                        fontprop_small = self.aw.mpl_fontproperties.copy()
                        fontsize = 'xx-small'
                        fontprop_small.set_size(fontsize)
                        self.specialevents.append(i)
                        self.specialeventstype.append(4)
                        self.specialeventsStrings.append(str(Nevents+1))
                        self.specialeventsvalue.append(0)
                        #if event was initiated by an Extra Event Button then change the type,value,and string
                        if extraevent is not None and eventtype is not None and eventvalue is not None:
                            self.specialeventstype[-1] = eventtype
                            self.specialeventsvalue[-1] = eventvalue
                            self.specialeventsStrings[-1] = eventdescription
                        etype = cast(int, self.specialeventstype[-1])
                        tx = self.timex[self.specialevents[-1]]
                        sevalue = cast(float, self.specialeventsvalue[-1])
                        if self.clampEvents: # in clamp mode we render also event values higher than 100:
                            val = int(round((sevalue-1)*10))
                        else:
                            event_pos_offset = self.eventpositionbars[0]
                            event_pos_factor = self.eventpositionbars[1] - self.eventpositionbars[0]
                            pos = max(0,int(round((sevalue-1)*10)))
                            val = int((pos*event_pos_factor)+event_pos_offset)
                        if etype == 0:
                            self.E1timex.append(tx)
                            self.E1values.append(val)
                        elif etype == 1:
                            self.E2timex.append(tx)
                            self.E2values.append(val)
                        elif etype == 2:
                            self.E3timex.append(tx)
                            self.E3values.append(val)
                        elif etype == 3:
                            self.E4timex.append(tx)
                            self.E4values.append(val)
                        #if Event show flag
                        if self.eventsshowflag != 0 and self.showEtypes[etype] and self.ax is not None:
                            index = self.specialevents[-1]
                            if etype < 4  and (not self.renderEventsDescr or len(self.specialeventsStrings[-1].strip()) == 0):
                                firstletter = self.etypesf(etype)[0]
                                secondletter = self.eventsvaluesShort(float(etype))
                                if self.aw.eventslidertemp[etype]:
                                    thirdletter = self.mode # postfix
                                else:
                                    thirdletter = self.aw.eventsliderunits[etype] # postfix
                            else:
                                firstletter = self.specialeventsStrings[-1].strip()[:self.eventslabelschars]
                                if firstletter == '':
                                    firstletter = 'E'
                                secondletter = ''
                                thirdletter = ''
                            #if Event Type-Bars flag
                            if self.eventsGraphflag == 1 and etype < 4:
                                if self.mode == 'F':
                                    row = {0:self.phases[0]-20,1:self.phases[0]-40,2:self.phases[0]-60,3:self.phases[0]-80}
                                else:
                                    row = {0:self.phases[0]-10,1:self.phases[0]-20,2:self.phases[0]-30,3:self.phases[0]-40}
                                #some times ET is not drawn (ET = 0) when using device NONE
                                # plot events on BT when showeventsonbt is true
                                anno = None
                                if self.ETcurve and not self.showeventsonbt and self.temp1[index] >= self.temp2[index]:
                                    anno = self.ax.annotate(f'{firstletter}{secondletter}',
                                        xy=(self.timex[index],
                                        self.temp1[index]),
                                        xytext=(self.timex[index],row[etype]),
                                        alpha=1.,
                                        bbox={'boxstyle':'square,pad=0.1', 'fc':self.EvalueColor[etype], 'ec':'none'},
                                        path_effects=[PathEffects.withStroke(linewidth=0.5,foreground=self.palette['background'])],
                                        color=self.EvalueTextColor[etype],
                                        arrowprops={'arrowstyle':'-','color':self.palette['et'],'alpha':0.4,'relpos':(0,0)},
                                        fontsize=fontsize,
                                        fontproperties=fontprop_small)
                                elif self.BTcurve:
                                    anno = self.ax.annotate(f'{firstletter}{secondletter}',
                                            xy=(self.timex[index],
                                            self.temp2[index]),
                                            xytext=(self.timex[index],row[etype]),
                                            alpha=1.,
                                            bbox={'boxstyle':'square,pad=0.1', 'fc':self.EvalueColor[etype], 'ec':'none'},
                                            path_effects=[PathEffects.withStroke(linewidth=0.5,foreground=self.palette['background'])],
                                            color=self.EvalueTextColor[etype],
                                            arrowprops={'arrowstyle':'-','color':self.palette['bt'],'alpha':0.4,'relpos':(0,0)},
                                            fontsize=fontsize,
                                            fontproperties=fontprop_small)
                                try:
                                    if anno is not None:
                                        anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                    pass
                            elif self.eventsGraphflag in [2,3,4] and etype < 4:
                                # update lines data using the lists with new data
                                if etype == 0 and self.showEtypes[0] and self.l_eventtype1dots is not None:
                                    self.l_eventtype1dots.set_data(self.E1timex, self.E1values)
                                elif etype == 1 and self.showEtypes[1] and self.l_eventtype2dots is not None:
                                    self.l_eventtype2dots.set_data(self.E2timex, self.E2values)
                                elif etype == 2 and self.showEtypes[2] and self.l_eventtype3dots is not None:
                                    self.l_eventtype3dots.set_data(self.E3timex, self.E3values)
                                elif etype == 3 and self.showEtypes[3] and self.l_eventtype4dots is not None:
                                    self.l_eventtype4dots.set_data(self.E4timex, self.E4values)
                            if etype == 4 or (self.eventsGraphflag in [0,3,4] and len(self.showEtypes) > etype and self.showEtypes[etype]):
                                height = 50 if self.mode == 'F' else 20
                                #some times ET is not drawn (ET = 0) when using device NONE
                                # plot events on BT when showeventsonbt is true
                                if self.ETcurve and not self.showeventsonbt and self.temp1[index] > self.temp2[index]:
                                    temp = self.temp1[index]
                                elif self.BTcurve:
                                    temp = self.temp2[index]
                                else:
                                    temp = None

                                if self.eventsGraphflag == 4:
                                    if etype == 0:
                                        temp = self.E1values[-1]
                                    elif etype == 1:
                                        temp = self.E2values[-1]
                                    elif etype == 2:
                                        temp = self.E3values[-1]
                                    elif etype == 3:
                                        temp = self.E4values[-1]

                                if temp is not None and self.ax is not None:
                                    if etype == 0:
                                        boxstyle = 'roundtooth,pad=0.4'
                                        boxcolor = self.EvalueColor[0]
                                        textcolor = self.EvalueTextColor[0]
                                    elif etype == 1:
                                        boxstyle = 'round,pad=0.3,rounding_size=0.8'
                                        boxcolor = self.EvalueColor[1]
                                        textcolor = self.EvalueTextColor[1]
                                    elif etype == 2:
                                        boxstyle = 'sawtooth,pad=0.3,tooth_size=0.2'
                                        boxcolor = self.EvalueColor[2]
                                        textcolor = self.EvalueTextColor[2]
                                    elif etype == 3:
                                        boxstyle = 'round4,pad=0.3,rounding_size=0.15'
                                        boxcolor = self.EvalueColor[3]
                                        textcolor = self.EvalueTextColor[3]
                                    else: # etype == 4:
                                        boxstyle = 'square,pad=0.1'
                                        boxcolor = self.palette['specialeventbox']
                                        textcolor = self.palette['specialeventtext']
                                    anno = None
                                    if self.eventsGraphflag in [0,3] or etype > 3:
                                        anno = self.ax.annotate(f'{firstletter}{secondletter}', xy=(self.timex[index], temp),xytext=(self.timex[index],temp+height),alpha=0.9,
                                                         color=textcolor,
                                                         va='center', ha='center',
                                                         arrowprops={'arrowstyle':'-','color':boxcolor,'alpha':0.4}, #,relpos=(0,0)),
                                                         bbox={'boxstyle':boxstyle, 'fc':boxcolor, 'ec':'none'},
                                                         fontsize=fontsize,
                                                         fontproperties=fontprop_small,
                                                         path_effects=[PathEffects.withStroke(linewidth=0.5,foreground=self.palette['background'])],
                                                         backgroundcolor=boxcolor)
                                    elif self.eventsGraphflag == 4:
                                        if thirdletter != '':
                                            firstletter = ''
                                        anno = self.ax.annotate(f'{firstletter}{secondletter}{thirdletter}', xy=(self.timex[index], temp),xytext=(self.timex[index],temp),alpha=0.9,
                                                         color=textcolor,
                                                         va='center', ha='center',
                                                         bbox={'boxstyle':boxstyle, 'fc':boxcolor, 'ec':'none'},
                                                         fontsize=fontsize,
                                                         fontproperties=fontprop_small,
                                                         path_effects=[PathEffects.withStroke(linewidth=0.5,foreground=self.palette['background'])],
                                                         backgroundcolor=boxcolor)

                                    try:
                                        if anno is not None:
                                            anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                                    except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                        pass
                        if doupdatebackground:
                            self.updateBackground() # call to canvas.draw() not needed as self.annotate does the (partial) redraw, but updateBackground() is needed
                        temp2 = f'{self.temp2[i]:.1f} {self.mode}'
                        if self.timeindex[0] != -1:
                            start = self.timex[self.timeindex[0]]
                        else:
                            start = 0
                        timed = stringfromseconds(self.timex[i] - start)
                        message = QApplication.translate('Message','Event # {0} recorded at BT = {1} Time = {2}').format(str(Nevents+1),temp2,timed)
                        self.aw.sendmessage(message)
                        #write label in mini recorder if flag checked
                        self.aw.eventlabel.setText(QApplication.translate('Label', 'Event #<b>{0} </b>').format(Nevents+1))
                        self.aw.eNumberSpinBox.blockSignals(True)
                        try:
                            self.aw.eNumberSpinBox.setValue(Nevents+1)
                        except Exception: # pylint: disable=broad-except
                            pass
                        finally:
                            self.aw.eNumberSpinBox.blockSignals(False)
                        if self.timeindex[0] > -1:
                            timez = stringfromseconds(self.timex[self.specialevents[Nevents]]-self.timex[self.timeindex[0]])
                        else:
                            timez = stringfromseconds(self.timex[self.specialevents[Nevents]])
                        self.aw.etimeline.setText(timez)
                        self.aw.etypeComboBox.setCurrentIndex(self.specialeventstype[Nevents])
                        self.aw.valueEdit.setText(self.eventsvalues(self.specialeventsvalue[Nevents]))
                        self.aw.lineEvent.setText(self.specialeventsStrings[Nevents])
            else:
                self.aw.sendmessage(QApplication.translate('Message','Timer is OFF'))
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' EventRecordAction() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
        finally:
            if takeLock and self.profileDataSemaphore.available() < 1:
                self.profileDataSemaphore.release(1)
        if self.flagstart and doupdategraphics:
            self.updategraphicsSignal.emit() # we need this to have the projections redrawn immediately

    #called from controlling devices when roasting to record steps (commands) and produce a profile later
    def DeviceEventRecord(self,command):
        try:
            self.profileDataSemaphore.acquire(1)
            if self.flagstart:
                #prevents accidentally deleting a modified profile.
                self.fileDirtySignal.emit()
                #number of events
                Nevents = len(self.specialevents)
                #index number
                i = len(self.timex)-1
                if i > 0:
                    self.specialevents.append(i)                                     # store absolute time index
                    self.specialeventstype.append(0)                                 # set type (to the first index 0)
                    self.specialeventsStrings.append(command)                        # store the command in the string section of events (not a binary string)
                    self.specialeventsvalue.append(0)                                # empty
                    temp_str = str(self.temp2[i])
                    if self.timeindex[0] != -1:
                        start = self.timex[self.timeindex[0]]
                    else:
                        start = 0
                    timed = stringfromseconds(self.timex[i]-start)
                    message = QApplication.translate('Message','Computer Event # {0} recorded at BT = {1} Time = {2}').format(str(Nevents+1),temp_str,timed)
                    self.aw.sendmessage(message)
                    #write label in mini recorder if flag checked
                    self.aw.eNumberSpinBox.setValue(Nevents+1)
                    self.aw.etypeComboBox.setCurrentIndex(self.specialeventstype[Nevents-1])
                    self.aw.valueEdit.setText(self.eventsvalues(self.specialeventsvalue[Nevents-1]))
                    self.aw.lineEvent.setText(self.specialeventsStrings[Nevents])
                #if Event show flag
                if self.eventsshowflag != 0 and self.ax is not None:
                    index = self.specialevents[-1]
                    if self.specialeventstype[-1] < 4 and self.showEtypes[self.specialeventstype[-1]]:
                        fontprop_small = self.aw.mpl_fontproperties.copy()
                        fontsize = 'xx-small'
                        fontprop_small.set_size(fontsize)
                        firstletter = self.etypesf(self.specialeventstype[-1])[0]
                        secondletter = self.eventsvaluesShort(self.specialeventsvalue[-1])

                        if self.eventsGraphflag == 0:
                            anno = None
                            height = 50 if self.mode == 'F' else 20
                            #some times ET is not drawn (ET = 0) when using device NONE
                            # plot events on BT when showeventsonbt is true
                            if self.ETcurve and not self.showeventsonbt and self.temp1[index] > self.temp2[index]:
                                temp = self.temp1[index]
                            else:
                                temp = self.temp2[index]
                            anno = self.ax.annotate(f'{firstletter}{secondletter}', xy=(self.timex[index], temp),xytext=(self.timex[index],temp+height),alpha=0.9,
                                            color=self.palette['specialeventtext'],arrowprops={'arrowstyle':'-','color':self.palette['bt'],'alpha':0.4,'relpos':(0,0)},
                                             fontsize=fontsize,fontproperties=fontprop_small,backgroundcolor=self.palette['specialeventbox'])
                            try:
                                anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                            except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                pass
                        #if Event Type-Bars flag
                        if self.eventsGraphflag == 1:
                            anno = None
                            if self.mode == 'F':
                                row = {0:self.phases[0]-20,1:self.phases[0]-40,2:self.phases[0]-60,3:self.phases[0]-80}
                            else:
                                row = {0:self.phases[0]-10,1:self.phases[0]-20,2:self.phases[0]-30,3:self.phases[0]-40}
                            #some times ET is not drawn (ET = 0) when using device NONE
                            # plot events on BT when showeventsonbt is true
                            if self.ETcurve and not self.showeventsonbt and self.temp1[index] >= self.temp2[index]:
                                anno = self.ax.annotate(f'{firstletter}{secondletter}', xy=(self.timex[index], self.temp1[index]),xytext=(self.timex[index],row[self.specialeventstype[-1]]),alpha=1.,
                                                 color=self.palette['specialeventtext'],arrowprops={'arrowstyle':'-',
                                                    'color':self.palette['et'],'alpha':0.4,'relpos':(0,0)},fontsize=fontsize,
                                                 fontproperties=fontprop_small,backgroundcolor=self.palette['specialeventbox'])
                            elif self.BTcurve:
                                anno = self.ax.annotate(f'{firstletter}{secondletter}', xy=(self.timex[index], self.temp2[index]),xytext=(self.timex[index],row[self.specialeventstype[-1]]),alpha=1.,
                                                 color=self.palette['specialeventtext'],arrowprops={'arrowstyle':'-',
                                                    'color':self.palette['et'],'alpha':0.4,'relpos':(0,0)}, fontsize=fontsize,
                                                 fontproperties=fontprop_small,backgroundcolor=self.palette['specialeventbox'])
                            try:
                                if anno is not None:
                                    anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                            except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                                pass
                        if self.eventsGraphflag in [2,3,4]:
                            # update lines data using the lists with new data
                            etype = self.specialeventstype[-1]
                            if etype == 0 and self.l_eventtype1dots is not None:
                                self.l_eventtype1dots.set_data(self.E1timex, self.E1values)
                            elif etype == 1 and self.l_eventtype2dots is not None:
                                self.l_eventtype2dots.set_data(self.E2timex, self.E2values)
                            elif etype == 2 and self.l_eventtype3dots is not None:
                                self.l_eventtype3dots.set_data(self.E3timex, self.E3values)
                            elif etype == 3 and self.l_eventtype4dots is not None:
                                self.l_eventtype4dots.set_data(self.E4timex, self.E4values)
                    #self.fig.canvas.draw() # not needed as self.annotate does the (partial) redraw
                    self.updateBackground() # but we need
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' DeviceEventRecord() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
        finally:
            if self.profileDataSemaphore.available() < 1:
                self.profileDataSemaphore.release(1)

    def writecharacteristics(self,TP_index=None,LP=None):
        try:
            # Display MET marker
            if self.showmet and self.ETcurve and self.timeindex[0] > -1 and self.timeindex[6] > 0:
                if TP_index is None:
                    TP_index = self.aw.findTP()
                met_temp = max(self.temp1[TP_index:self.timeindex[6]])
                self.idx_met = TP_index + self.temp1[TP_index:self.timeindex[6]].index(met_temp)
                if self.idx_met is not None:
                    if self.timeindex[2] != 0:
                        # time between MET and FCs
                        met_delta = self.aw.float2float(self.timex[self.timeindex[2]] - self.timex[self.idx_met],0)
                    else:
                        met_delta = None
                    self.met_timex_temp1_delta = ((self.timex[self.idx_met]-self.timex[self.timeindex[0]]), met_temp, met_delta) #used in onpick() to display the MET temp and time
                    # plot a MET marker
                    if self.ax is not None and self.showmet and self.ETcurve:
                        height = 0 if self.mode == 'F' else 0
                        boxstyle = 'round4,pad=0.3,rounding_size=0.15'
                        boxcolor = self.palette['metbox'] #match the ET color
                        textcolor = self.palette['mettext']
                        fontprop_small = self.aw.mpl_fontproperties.copy()
                        fontprop_small.set_size('xx-small')
                        self.met_annotate = self.ax.annotate('MET', xy=(self.timex[self.idx_met], met_temp),
                                     xytext=(self.timex[self.idx_met], met_temp + height),
                                     ha = 'center',
                                     alpha=0.9,
                                     color=textcolor,
                                     bbox={'boxstyle':boxstyle, 'fc':boxcolor, 'ec':'none'},
                                     fontproperties=fontprop_small,
                                     path_effects=[PathEffects.withStroke(linewidth=0.5,foreground=self.palette['background'])],
                                     picker=True,
                                     zorder=2,
                                     )
                        try:
                            if self.met_annotate is not None:
                                self.met_annotate.set_in_layout(False) # remove suptitle from tight_layout calculation
                        except Exception: # pylint: disable=broad-except # set_in_layout not available in mpl<3.x
                            pass

            if self.statisticsflags[3] and self.timeindex[0]>-1:
                statsprop = self.aw.mpl_fontproperties.copy()
                statsprop.set_size('small')
                if self.statisticsmode == 0:
                    if TP_index is None:
                        TP_index = self.aw.findTP()
                    if LP is None:
                        #find Lowest Point in BT
                        LP = 1000
                        if TP_index >= 0:
                            LP = self.temp2[TP_index]
                    # compute max ET between TP and DROP
                    ETmax = '--'
                    temp1_values_max = 0.
                    try:
                        if TP_index is not None:
                            if self.timeindex[6] > 0 and TP_index<self.timeindex[6]:
                                temp1_values = self.temp1[TP_index:self.timeindex[6]]
                            else:
                                temp1_values = self.temp1[TP_index:]
                            if self.LCDdecimalplaces:
                                lcdformat = '%.1f'
                            else:
                                lcdformat = '%.0f'
                            temp1_values_max = max(temp1_values)
                            ETmax = lcdformat%temp1_values_max + self.mode
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)

                    FCperiod = None
                    try:
                        if self.timeindex[2] > 0 and self.timeindex[3] > 0:
                            FCperiod = stringfromseconds(self.timex[self.timeindex[3]] - self.timex[self.timeindex[2]])[1:]
                        elif self.timeindex[2] > 0 and self.timeindex[6] > 0:
                            FCperiod = stringfromseconds(self.timex[self.timeindex[6]] - self.timex[self.timeindex[2]])[1:]
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)

                    ror = f'{((self.temp2[self.timeindex[6]]-LP)/(self.timex[self.timeindex[6]]-self.timex[self.timeindex[0]]))*60.:.1f}'
                    _,_,tsb,_ = self.aw.ts(tp=TP_index)

                    #curveSimilarity
                    det,dbt = self.aw.curveSimilarity() # we analyze from DRY-END as specified in the phases dialog to DROP

                    #end temperature
                    if det is None or det == -1 or numpy.isnan(det):
                        det_txt = '––'
                    else:
                        det_txt = f'{det:.1f}'
                    if dbt is None or dbt == -1 or numpy.isnan(dbt):
                        dbt_txt = '––'
                    else:
                        dbt_txt = f'{dbt:.1f}'
                    if self.locale_str == 'ar':
                        strline = (
                                    f'C*min{int(tsb)}={self.aw.arabicReshape(QApplication.translate("Label", "AUC"))}   '
                                    f'{self.aw.arabicReshape(self.mode + "/min")}'
                                    f'{ror}=self.aw.arabicReshape(QApplication.translate("Label", "RoR"))   '
                                    f'{ETmax}=self.aw.arabicReshape(QApplication.translate("Label", "MET"))'
                                   )
                        if det is not None:
                            strline = f"{det_txt}/{dbt_txt}{self.mode}={QApplication.translate('Label', 'CM')} {strline}"
                        if FCperiod is not None:
                            strline = f"min{FCperiod + QApplication.translate('Label', 'FC')}=   {strline}"
                    else:
                        strline = ''
                        if temp1_values_max and temp1_values_max > 0:
                            strline = f"{QApplication.translate('Label', 'MET')}={ETmax}   "
                        strline += f"{QApplication.translate('Label', 'RoR')}={ror}{self.mode}/min   {QApplication.translate('Label', 'AUC')}={int(tsb)}C*min"
                        if det is not None or dbt is not None:
                            strline = f"{strline}   {QApplication.translate('Label', 'CM')}={det_txt}/{dbt_txt}{self.mode}"
                        if FCperiod is not None:
                            strline = f"{strline}   {QApplication.translate('Label', 'FC')}={FCperiod}min"
                    self.set_xlabel(strline)
                elif self.statisticsmode == 1:
                    sep = '   '
                    msg = self.roastdate.date().toString(QLocale().dateFormat(QLocale.FormatType.ShortFormat))
                    tm = self.roastdate.time().toString()[:-3]
                    if tm != '00:00':
                        msg = f'{msg}, {tm}'
                    if self.beans and self.beans != '':
                        msg = f'{msg} {abbrevString(self.beans,25)}'
                    if self.weight[0]:
                        if self.weight[2] in ['g','oz']:
                            msg += f'{sep}{self.aw.float2float(self.weight[0],0)}{self.weight[2]}'
                        else:
                            msg += f'{sep}{self.aw.float2float(self.weight[0],1)}{self.weight[2]}'
                        if self.weight[1]:
                            msg += f'{sep}{-1*self.aw.float2float(self.aw.weight_loss(self.weight[0],self.weight[1]),1)}%'
                    if self.volume[0] and self.volume[1]:
                        msg += f'{sep}{self.aw.float2float(self.aw.volume_increase(self.volume[0],self.volume[1]),1)}%'
                    if self.whole_color and self.ground_color:
                        msg += f'{sep}#{self.whole_color}/{self.ground_color}'
                    elif self.ground_color:
                        msg += f'{sep}#{self.ground_color}'
                    self.set_xlabel(msg)
                elif self.statisticsmode == 2:
                    # total energy/CO2
                    energy_label = QApplication.translate('GroupBox','Energy')
                    CO2_label = QApplication.translate('GroupBox','CO2')
                    if not (platform.system() == 'Windows' and int(platform.release()) < 10):
                        # no subscript for legacy Windows
                        CO2_label = CO2_label.replace('CO2','CO₂')
                    energy_unit = self.energyunits[self.energyresultunit_setup]
                    energymetrics,_ = self.calcEnergyuse()
                    KWH_per_green = energymetrics['KWH_batch_per_green_kg']
                    CO2_per_green = energymetrics['CO2_batch_per_green_kg']

                    # energy per kg
                    if KWH_per_green > 0:
                        if KWH_per_green < 1:
                            scaled_energy_kwh = scaleFloat2String(KWH_per_green*1000.) + ' Wh/kg'
                        else:
                            scaled_energy_kwh = scaleFloat2String(KWH_per_green) + ' kWh/kg'
                        energyPerKgCoffeeLabel = f'  ({scaled_energy_kwh})'
                    # no weight is available
                    else:
                        energyPerKgCoffeeLabel = ''

                    # CO2 per kg
                    if CO2_per_green > 0:
                        if CO2_per_green < 1000:
                            scaled_co2_kg = scaleFloat2String(CO2_per_green) + 'g/kh'
                        else:
                            scaled_co2_kg = scaleFloat2String(CO2_per_green/1000.) + 'kg/kh'
                        CO2perKgCoffeeLabel = f'  ({scaled_co2_kg})'
                    # no weight is available
                    else:
                        CO2perKgCoffeeLabel = ''

                    total_energy = scaleFloat2String(self.convertHeat(energymetrics['BTU_batch'],0,self.energyresultunit_setup))
                    scaled_co2_batch = str(scaleFloat2String(energymetrics['CO2_batch']))+'g' if energymetrics['CO2_batch']<1000 else str(scaleFloat2String(energymetrics['CO2_batch']/1000.)) +'kg'


                    msg = f'{energy_label}: {total_energy}{energy_unit}{energyPerKgCoffeeLabel}   {CO2_label}: {scaled_co2_batch}{CO2perKgCoffeeLabel}'
                    self.set_xlabel(msg)
                elif self.statisticsmode == 3:
                    # just roast energy/CO2
                    energy_label = QApplication.translate('GroupBox','Energy')
                    CO2_label = QApplication.translate('GroupBox','CO2')
                    if not (platform.system() == 'Windows' and int(platform.release()) < 10):
                        # no subscript for legacy Windows
                        CO2_label = CO2_label.replace('CO2','CO₂')
                    energy_unit = self.energyunits[self.energyresultunit_setup]
                    roast_label = QApplication.translate('Label','Roast')
                    energymetrics,_ = self.calcEnergyuse()
                    KWH_per_green_roast = energymetrics['KWH_roast_per_green_kg']
                    CO2_per_green_roast = energymetrics['CO2_roast_per_green_kg']

                    # energy per kg
                    if KWH_per_green_roast > 0:
                        if KWH_per_green_roast < 1:
                            scaled_energy_kwh = scaleFloat2String(KWH_per_green_roast*1000.) + ' Wh/kg'
                        else:
                            scaled_energy_kwh = scaleFloat2String(KWH_per_green_roast) + ' kWh/kg'
                        energyPerKgCoffeeLabel = f'  ({scaled_energy_kwh})'
                    # no weight is available
                    else:
                        energyPerKgCoffeeLabel = ''

                    # CO2 per kg
                    if CO2_per_green_roast > 0:
                        if CO2_per_green_roast < 1000:
                            scaled_co2_kg = scaleFloat2String(CO2_per_green_roast) + 'g/kh'
                        else:
                            scaled_co2_kg = scaleFloat2String(CO2_per_green_roast/1000.) + 'kg/kh'
                        CO2perKgCoffeeLabel = f'  ({scaled_co2_kg})'
                    # no weight is available
                    else:
                        CO2perKgCoffeeLabel = ''

                    total_energy = scaleFloat2String(self.convertHeat(energymetrics['BTU_roast'],0,self.energyresultunit_setup))
                    scaled_co2_batch = str(scaleFloat2String(energymetrics['CO2_roast']))+'g' if energymetrics['CO2_roast']<1000 else str(scaleFloat2String(energymetrics['CO2_roast']/1000.)) +'kg'

                    msg = f'{roast_label} {energy_label}: {total_energy}{energy_unit}{energyPerKgCoffeeLabel}   {roast_label} {CO2_label}: {scaled_co2_batch}{CO2perKgCoffeeLabel}'
                    self.set_xlabel(msg)
                else:
                    self.set_xlabel('')
            elif self.flagstart or self.xgrid == 0:
                self.set_xlabel('')
            else:
                self.set_xlabel(self.aw.arabicReshape(QApplication.translate('Label', 'min','abbrev. of minutes')))
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' writecharacteristics() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))

    # calculates self.statisticstimes values and returns dryEndIndex as well as the calculated statisticstimes array of length 5
    def calcStatistics(self,TP_index):
        statisticstimes:List[float] = [0,0,0,0,0]
        try:
            if self.timeindex[1]:
                #manual dryend available
                dryEndIndex = self.timeindex[1]
            else:
                #find when dry phase ends
                dryEndIndex = self.aw.findDryEnd(TP_index)
            if len(self.timex) > dryEndIndex:
                dryEndTime = self.timex[dryEndIndex]

                #if DROP
                if self.timeindex[6] and self.timeindex[2]:
                    totaltime = self.timex[self.timeindex[6]]-self.timex[self.timeindex[0]]
                    if totaltime == 0:
                        return dryEndIndex, statisticstimes

                    statisticstimes[0] = totaltime
                    dryphasetime = dryEndTime - self.timex[self.timeindex[0]] # self.aw.float2float(dryEndTime - self.timex[self.timeindex[0]])
                    midphasetime = self.timex[self.timeindex[2]] - dryEndTime # self.aw.float2float(self.timex[self.timeindex[2]] - dryEndTime)
                    finishphasetime = self.timex[self.timeindex[6]] - self.timex[self.timeindex[2]] # self.aw.float2float(self.timex[self.timeindex[6]] - self.timex[self.timeindex[2]])

                    if self.timeindex[7]:
                        coolphasetime = self.timex[self.timeindex[7]] - self.timex[self.timeindex[6]] # int(round(self.timex[self.timeindex[7]] - self.timex[self.timeindex[6]]))
                    else:
                        coolphasetime = 0

                    statisticstimes[1] = dryphasetime
                    statisticstimes[2] = midphasetime
                    statisticstimes[3] = finishphasetime
                    statisticstimes[4] = coolphasetime
                return dryEndIndex, statisticstimes
            return self.timeindex[1], statisticstimes
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            return self.timeindex[1], statisticstimes

    # Writes information about the finished profile in the graph
    # TP_index is the TP index calculated by findTP and might be -1 if no TP could be detected
    def writestatistics(self,TP_index):
        try:
            if self.ax is None:
                return

            LP = None

            dryEndIndex, statisticstimes = self.calcStatistics(TP_index)

            if statisticstimes[0] == 0:
                self.writecharacteristics(TP_index,LP)
                return
            self.statisticstimes = statisticstimes

            #if DROP
            if self.timeindex[6] and self.timeindex[2]:

                #dry time string
                st1 = stringfromseconds(self.statisticstimes[1],False)

                #mid time string
                st2 = stringfromseconds(self.statisticstimes[2],False)

                #finish time string
                st3 = stringfromseconds(self.statisticstimes[3],False)

                if self.statisticstimes[4]:
                    st4 = stringfromseconds(self.statisticstimes[4],False)
                else:
                    st4 = ''

                #calculate the positions for the statistics elements
                ydist = self.ylimit - self.ylimit_min
                statisticsbarheight = ydist/70

                if self.legendloc in [1,2,9]:
                    # legend on top
                    statisticsheight = self.ylimit - (0.13 * ydist) # standard positioning
                else:
                    # legend not on top
                    statisticsheight = self.ylimit - (0.08 * ydist)

                if self.mode == 'C':
                    statisticsupper = statisticsheight + statisticsbarheight + 4
                    statisticslower = statisticsheight - 3.5*statisticsbarheight
                else:
                    statisticsupper = statisticsheight + statisticsbarheight + 10
                    statisticslower = statisticsheight - 2.5*statisticsbarheight

                if self.statisticsflags[1]:

                    #Draw cool phase rectangle
                    if self.timeindex[7]:
                        rect = patches.Rectangle((self.timex[self.timeindex[6]], statisticsheight), width = self.statisticstimes[4], height = statisticsbarheight,
                                                color = self.palette['rect4'],alpha=0.5)
                        self.ax.add_patch(rect)

                    if self.timeindex[2]: # only if FCs exists
                        #Draw finish phase rectangle
                        #check to see if end of 1C exists. If so, use half between start of 1C and end of 1C. Otherwise use only the start of 1C
                        rect = patches.Rectangle((self.timex[self.timeindex[2]], statisticsheight), width = self.statisticstimes[3], height = statisticsbarheight,
                                                color = self.palette['rect3'],alpha=0.5)
                        self.ax.add_patch(rect)

                        # Draw mid phase rectangle
                        rect = patches.Rectangle((self.timex[self.timeindex[0]]+self.statisticstimes[1], statisticsheight), width = self.statisticstimes[2], height = statisticsbarheight,
                                              color = self.palette['rect2'],alpha=0.5)
                        self.ax.add_patch(rect)

                    # Draw dry phase rectangle
                    rect = patches.Rectangle((self.timex[self.timeindex[0]], statisticsheight), width = self.statisticstimes[1], height = statisticsbarheight,
                                              color = self.palette['rect1'],alpha=0.5)
                    self.ax.add_patch(rect)

                fmtstr = '{0:.1f}' if self.LCDdecimalplaces else '{0:.0f}'
                if self.statisticstimes[0]:
                    dryphaseP = fmtstr.format(self.statisticstimes[1]*100./self.statisticstimes[0])
                    midphaseP = fmtstr.format(self.statisticstimes[2]*100./self.statisticstimes[0])
                    finishphaseP = fmtstr.format(self.statisticstimes[3]*100./self.statisticstimes[0])
                else:
                    dryphaseP = ' --- '
                    midphaseP = ' --- '
                    finishphaseP = ' --- '

                #find Lowest Point in BT
                LP = 1000
                if TP_index >= 0:
                    LP = self.temp2[TP_index]

                if self.statisticsflags[0]:
                    text = self.ax.text(self.timex[self.timeindex[0]]+ self.statisticstimes[1]/2.,statisticsupper,st1 + '  '+ dryphaseP+'%',color=self.palette['text'],ha='center',
                        fontsize='medium'
                        )
                    try:
                        text.set_in_layout(False)
                    except Exception: # pylint: disable=broad-except
                        pass
                    if self.timeindex[2]: # only if FCs exists
                        text = self.ax.text(self.timex[self.timeindex[0]]+ self.statisticstimes[1]+self.statisticstimes[2]/2.,statisticsupper,st2+ '  ' + midphaseP+'%',color=self.palette['text'],ha='center',
                            fontsize='medium'
                            )
                        try:
                            text.set_in_layout(False)
                        except Exception: # pylint: disable=broad-except
                            pass
                        text = self.ax.text(self.timex[self.timeindex[0]]+ self.statisticstimes[1]+self.statisticstimes[2]+self.statisticstimes[3]/2.,statisticsupper,st3 + '  ' + finishphaseP+ '%',color=self.palette['text'],ha='center',
                            fontsize='medium'
                            )
                        try:
                            text.set_in_layout(False)
                        except Exception:  # pylint: disable=broad-except
                            pass
                    if self.timeindex[7]: # only if COOL exists
                        text = self.ax.text(self.timex[self.timeindex[0]]+ self.statisticstimes[1]+self.statisticstimes[2]+self.statisticstimes[3]+self.statisticstimes[4]/2.,statisticsupper,st4,color=self.palette['text'],ha='center',
                            fontsize='medium'
                            )
                        try:
                            text.set_in_layout(False)
                        except Exception: # pylint: disable=broad-except
                            pass

                st1 = st2 = st3 = st4 = ''

                if self.statisticsflags[4] or self.statisticsflags[6]:
                    rates_of_changes = self.aw.RoR(TP_index,dryEndIndex)
                    d = str(self.LCDdecimalplaces)
                    if self.statisticsflags[6]:
                        fmtstr = '{0:.' + d + 'f}{1}'
                        if self.statisticsflags[4]:
                            fmtstr += '  {2:.' + d + 'f}{3}'
                    else:
                        fmtstr = '{2:.' + d + 'f}{3}'

                    unit = self.aw.arabicReshape(self.mode + '/min')
                    st1 = st1 + fmtstr.format(rates_of_changes[3], self.mode, rates_of_changes[0], unit)
                    st2 = st2 + fmtstr.format(rates_of_changes[4], self.mode, rates_of_changes[1], unit)
                    st3 = st3 + fmtstr.format(rates_of_changes[5], self.mode, rates_of_changes[2], unit)

                    text = self.ax.text(self.timex[self.timeindex[0]] + self.statisticstimes[1]/2.,statisticslower,st1,
                        color=self.palette['text'],
                        ha='center',
                        fontsize='medium')
                    try:
                        text.set_in_layout(False)
                    except Exception: # pylint: disable=broad-except
                        pass
                    if self.timeindex[2]: # only if FCs exists
                        text = self.ax.text(self.timex[self.timeindex[0]] + self.statisticstimes[1]+self.statisticstimes[2]/2.,statisticslower,st2,color=self.palette['text'],ha='center',
                            #fontproperties=statsprop # fails be rendered in PDF exports on MPL v3.4.x
                            fontsize='medium'
                            )
                        try:
                            text.set_in_layout(False)
                        except Exception: # pylint: disable=broad-except
                            pass
                        text = self.ax.text(self.timex[self.timeindex[0]] + self.statisticstimes[1]+self.statisticstimes[2]+self.statisticstimes[3]/2.,statisticslower,st3,color=self.palette['text'],ha='center',
                            #fontproperties=statsprop # fails be rendered in PDF exports on MPL v3.4.x
                            fontsize='medium'
                            )
                        try:
                            text.set_in_layout(False)
                        except Exception: # pylint: disable=broad-except
                            pass
                    if self.timeindex[7]: # only if COOL exists
                        text = self.ax.text(self.timex[self.timeindex[0]]+ self.statisticstimes[1]+self.statisticstimes[2]+self.statisticstimes[3]+max(self.statisticstimes[4]/2.,self.statisticstimes[4]/3.),statisticslower,st4,color=self.palette['text'],ha='center',
                            #fontproperties=statsprop # fails be rendered in PDF exports on MPL v3.4.x
                            fontsize='medium'
                            )
                        try:
                            text.set_in_layout(False)
                        except Exception: # pylint: disable=broad-except
                            pass
            self.writecharacteristics(TP_index,LP)
        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' writestatistics() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))

    @staticmethod
    def convertHeat(value, fromUnit, toUnit=0):
        if value in [-1,None]:
            return value
        conversion = {#     BTU            kJ             kCal           kWh            hph
                       0:{0:1.,          1:1.0551E+00,  2:2.5200E-01,  3:2.9307E-04,  4:3.9301E-04 }, # = 1 btu
                       1:{0:9.4782E-01,  1:1.,          2:2.3885E-01,  3:2.7778E-04,  4:3.7251E-04 }, # = 1 kj
                       2:{0:3.9683E+00,  1:4.1868E+00,  2:1.,          3:1.1630E-03,  4:1.5596E-03 }, # = 1 kcal
                       3:{0:3.4121E+03,  1:3.6000E+03,  2:8.5985E+02,  3:1.,          4:1.3410E+00 }, # = 1 kwh
                       4:{0:2.5444E+03,  1:2.6845E+03,  2:6.4119E+02,  3:7.4570E-01,  4:1.         }} # = 1 hph

        return value * conversion[fromUnit][toUnit]

    def calcEnergyuse(self,beanweightstr='') -> Tuple['EnergyMetrics', List['BTU']]:
        energymetrics:EnergyMetrics = {}
        btu_list:List[BTU] = []
        try:
            if len(self.timex) == 0:
                #self.aw.sendmessage(QApplication.translate("Message","No profile data"),append=False)
                return energymetrics, btu_list

            # helping function
            def formatLoadLabel(i):
                if len(self.loadlabels[i]) > 0:
                    return  self.loadlabels[i]
                return chr(ord('A')+i)

            # get the valid green weight
            if beanweightstr != '':
                w = toFloat(beanweightstr)
            else:
                w = self.weight[0]
            bean_weight = self.aw.convertWeight(w,self.weight_units.index(self.weight[2]),1) # to kg

            #reference: https://www.eia.gov/environment/emissions/co2_vol_mass.php (dated Nov-18-2021, accessed Jan-02-2022)
            #           https://www.eia.gov/tools/faqs/faq.php?id=74&t=11 (referencing data from 2020, accessed Jan-02-2022)
            # entries must match those in self.sourcenames
            CO2kg_per_BTU = {0:6.288e-05, 1:5.291e-05, 2:2.964e-04}  # "LPG", "NG", "Elec"

            eTypes = [''] + self.etypes[:][:4]

            # init the prev_loadtime to drop if it exists or to the end of profile time
            if self.timeindex[6] > 0:
                prev_loadtime = [self.timex[self.timeindex[6]]]*4
            else:
                prev_loadtime = [self.timex[-1]]*4
                #self.aw.sendmessage(QApplication.translate("Message","Profile has no DROP event"),append=False)

            for i in range(0,4):
                # iterate specialevents in reverse from DROP to the first event
                for j in range(len(self.specialevents) - 1, -1, -1):
                    if self.load_etypes[i] != 0 and self.specialeventstype[j] == self.load_etypes[i]-1:
                        # skip if loadrating is zero
                        if self.loadratings[i] == 0:
                            break
                        loadtime = self.timex[self.specialevents[j]]
                        # exclude heat before charge event
                        if self.timeindex[0] > -1 and loadtime <= self.timex[self.timeindex[0]]:
                            if prev_loadtime[i] <= self.timex[self.timeindex[0]]:
                                break
                            loadtime = self.timex[self.timeindex[0]]
                        duration = prev_loadtime[i] - loadtime

                        # exclude heat after drop event
                        if duration < 0:
                            continue
                        prev_loadtime[i] = loadtime
                        # scale the burner setting for 0-100%
                        val = (self.specialeventsvalue[j] - 1) * 10
                        emin = toInt(self.loadevent_zeropcts[i])
                        emax = toInt(self.loadevent_hundpcts[i])
                        scaled = (val - emin) / (emax - emin)  #emax > emin enforced by energy.py
                        load_pct = min(1,max(0,scaled)) * 100
                        if self.presssure_percents[i] and self.sourcetypes[i] in [0,1]:   # gas loads only
                            # convert pressure to heat
                            factor = math.sqrt(load_pct / 100)
                        else:
                            factor = load_pct / 100

                        BTUs = self.loadratings[i] * factor * (duration / 3600) * self.convertHeat(1,self.ratingunits[i],0)
                        if BTUs > 0:
                            loadlabel = f'{formatLoadLabel(i)}-{eTypes[self.load_etypes[i]]}'
                            kind = 7  #Roast Event
                            sortorder = (2000 * (i + 1)) + j
                            CO2g = BTUs * CO2kg_per_BTU[self.sourcetypes[i]] * 1000
                            if self.sourcetypes[i] in [2]:  #electicity
                                CO2g = CO2g * (1 - self.electricEnergyMix/100)
                            btu_list.append({'load_pct':load_pct,'duration':duration,'BTUs':BTUs,'CO2g':CO2g,'LoadLabel':loadlabel,'Kind':kind,'SourceType':self.sourcetypes[i],'SortOrder':sortorder})
                ### end of loop: for j in range(len(self.specialevents) - 1, -1, -1)

                # calculate Continuous event type
                if self.load_etypes[i] == 0:
                    if self.timeindex[0] > -1 and self.timeindex[6] > 0:
                        duration = self.timex[self.timeindex[6]] - self.timex[self.timeindex[0]]
                    else:
                        duration = 0
                        #self.aw.sendmessage(QApplication.translate("Message","Missing CHARGE or DROP event"),append=False)
                    load_pct = toInt(self.loadevent_hundpcts[i])  #needed only for the btu_list and outmsg
                    if self.presssure_percents[i] and self.sourcetypes[i] in [0,1]:   # gas loads only
                        # convert pressure to heat
                        factor = math.sqrt(load_pct / 100)
                    else:
                        factor = load_pct / 100

                    loadlabel = formatLoadLabel(i)
                    kind = 6  #Roast Continuous
                    fueltype = self.sourcetypes[i]
                    sortorder = 2000 - i
                    BTUs = self.loadratings[i] * factor * (duration / 3600) * self.convertHeat(1,self.ratingunits[i],0)
                    CO2g = BTUs * CO2kg_per_BTU[fueltype] * 1000
                    if self.sourcetypes[i] in [2]:  #electicity
                        CO2g = CO2g * (1 - self.electricEnergyMix/100)
                    if BTUs > 0:
                        btu_list.append({'load_pct':load_pct,'duration':duration,'BTUs':BTUs,'CO2g':CO2g,'LoadLabel':loadlabel,'Kind':kind,'SourceType':self.sourcetypes[i],'SortOrder':sortorder})

                # calculate preheat
                if self.preheatenergies[i] != 0 and self.roastbatchpos == 1:
                    if self.preheatenergies[i] < 0 < self.preheatDuration:
                        # percent load multiplied by duration
                        load_pct = abs(self.preheatenergies[i] * 1000./10)
                        if self.presssure_percents[i] and self.sourcetypes[i] in [0,1]:   # gas loads only
                            # convert pressure to heat
                            factor = math.sqrt(load_pct / 100)
                        else:
                            factor = load_pct / 100
                        duration = self.preheatDuration
                        BTUs = self.loadratings[i] * factor * (duration / 3600) * self.convertHeat(1,self.ratingunits[i],0)
                        kind = 1  #Preheat Percent
                    else:
                        # measured value
                        load_pct = 0
                        duration = 0
                        BTUs = self.preheatenergies[i] * self.convertHeat(1,self.ratingunits[i],0)
                        kind = 0  #Preheat Measured

                    loadlabel = formatLoadLabel(i)
                    sortorder = 100 + i
                    CO2g = BTUs * CO2kg_per_BTU[self.sourcetypes[i]] * 1000
                    if self.sourcetypes[i] in [2]:  #electicity
                        CO2g = CO2g * (1 - self.electricEnergyMix/100)
                    if BTUs > 0:
                        btu_list.append({'load_pct':load_pct,'duration':duration,'BTUs':BTUs,'CO2g':CO2g,'LoadLabel':loadlabel,'Kind':kind,'SourceType':self.sourcetypes[i],'SortOrder':sortorder})

                # calculate betweenbatch
                if self.betweenbatchenergies[i] != 0 and (self.roastbatchpos > 1 or self.betweenbatch_after_preheat or self.roastbatchpos==0):
                    if self.betweenbatchenergies[i] < 0 < self.betweenbatchDuration:
                        # percent load multiplied by duration
                        load_pct = abs(self.betweenbatchenergies[i] * 1000./10)
                        if self.presssure_percents[i] and self.sourcetypes[i] in [0,1]:   # gas loads only
                            # convert pressure to heat
                            factor = math.sqrt(load_pct / 100)
                        else:
                            factor = load_pct / 100
                        duration = self.betweenbatchDuration
                        BTUs = self.loadratings[i] * factor * (duration / 3600) * self.convertHeat(1,self.ratingunits[i],0)
                        kind = 3  #BBP Percent
                    else:
                        # measured value
                        load_pct = 0
                        duration = 0
                        BTUs = self.betweenbatchenergies[i] * self.convertHeat(1,self.ratingunits[i],0)
                        kind = 2  #BBP Measured

                    loadlabel = formatLoadLabel(i)
                    sortorder = 400 + i
                    CO2g = BTUs * CO2kg_per_BTU[self.sourcetypes[i]] * 1000
                    if self.sourcetypes[i] in [2]:  #electicity
                        CO2g = CO2g * (1 - self.electricEnergyMix/100)
                    if BTUs > 0:
                        btu_list.append({'load_pct':load_pct,'duration':duration,'BTUs':BTUs,'CO2g':CO2g,'LoadLabel':loadlabel,'Kind':kind,'SourceType':self.sourcetypes[i],'SortOrder':sortorder})

                # calculate cooling
                if self.coolingenergies[i] != 0 and self.roastbatchpos == 1:
                    if self.coolingenergies[i] < 0 < self.coolingDuration:
                        # percent load multiplied by duration
                        load_pct = abs(self.coolingenergies[i] * 1000./10)
                        if self.presssure_percents[i] and self.sourcetypes[i] in [0,1]:   # gas loads only
                            # convert pressure to heat
                            factor = math.sqrt(load_pct / 100)
                        else:
                            factor = load_pct / 100
                        duration = self.coolingDuration
                        BTUs = self.loadratings[i] * factor * (duration / 3600) * self.convertHeat(1,self.ratingunits[i],0)
                        kind = 5  #Cooling Percent
                    else:
                        # measured value
                        load_pct = 0
                        duration = 0
                        BTUs = self.coolingenergies[i] * self.convertHeat(1,self.ratingunits[i],0)
                        kind = 4  #Cooling Measured

                    loadlabel = formatLoadLabel(i)
                    sortorder = 800 + i
                    CO2g = BTUs * CO2kg_per_BTU[self.sourcetypes[i]] * 1000
                    if self.sourcetypes[i] in [2]:  #electicity
                        CO2g = CO2g * (1 - self.electricEnergyMix/100)
                    if BTUs > 0:
                        btu_list.append({'load_pct':load_pct,'duration':duration,'BTUs':BTUs,'CO2g':CO2g,'LoadLabel':loadlabel,'Kind':kind,'SourceType':self.sourcetypes[i],'SortOrder':sortorder})
            #### end of loop: for i in range(0,4)

            btu_list.sort(key=lambda k : k['SortOrder'] )

            # summarize the batch metrics
            btu_batch = btu_preheat = btu_bbp = btu_cooling = btu_roast = 0.
            co2_batch = co2_preheat = co2_bbp = co2_cooling = co2_roast = 0.
            btu_elec = btu_lpg = btu_ng = 0.
            for item in btu_list:
                btu_batch += item['BTUs']
                btu_preheat += item['BTUs'] if item['Kind'] in [0,1] else 0
                btu_bbp += item['BTUs'] if item['Kind'] in [2,3] else 0
                btu_cooling += item['BTUs'] if item['Kind'] in [4,5] else 0
                btu_roast += item['BTUs'] if item['Kind'] in [6,7] else 0
                co2_batch += item['CO2g']
                co2_preheat += item['CO2g'] if item['Kind'] in [0,1] else 0
                co2_bbp += item['CO2g'] if item['Kind'] in [2,3] else 0
                co2_cooling += item['CO2g'] if item['Kind'] in [4,5] else 0
                co2_roast += item['CO2g'] if item['Kind'] in [6,7] else 0
                btu_lpg += item['BTUs'] if item['SourceType'] in [0] else 0
                btu_ng += item['BTUs'] if item['SourceType'] in [1] else 0
                btu_elec += item['BTUs'] if item['SourceType'] in [2] else 0
            btu_batch = self.aw.float2float(btu_batch,3)
            btu_preheat = self.aw.float2float(btu_preheat,3)
            btu_bbp = self.aw.float2float(btu_bbp,3)
            btu_cooling = self.aw.float2float(btu_cooling,3)
            btu_roast = self.aw.float2float(btu_roast,3)
            co2_batch = self.aw.float2float(co2_batch,3)
            co2_preheat = self.aw.float2float(co2_preheat,3)
            co2_bbp = self.aw.float2float(co2_bbp,3)
            co2_cooling = self.aw.float2float(co2_cooling,3)
            co2_roast = self.aw.float2float(co2_roast,3)
            btu_lpg = self.aw.float2float(btu_lpg,3)
            btu_ng = self.aw.float2float(btu_ng,3)
            btu_elec = self.aw.float2float(btu_elec,3)
            if bean_weight > 0:
                co2_batch_per_green_kg = co2_batch / bean_weight
                co2_roast_per_green_kg = co2_roast / bean_weight
                btu_batch_per_green_kg = btu_batch / bean_weight
                btu_roast_per_green_kg = btu_roast / bean_weight
            else:
                co2_batch_per_green_kg = 0
                co2_roast_per_green_kg = 0
                btu_batch_per_green_kg = 0
                btu_roast_per_green_kg = 0
            co2_batch_per_green_kg = self.aw.float2float(co2_batch_per_green_kg,3)
            co2_roast_per_green_kg = self.aw.float2float(co2_roast_per_green_kg,3)
            btu_batch_per_green_kg = self.aw.float2float(btu_batch_per_green_kg,3)
            btu_roast_per_green_kg = self.aw.float2float(btu_roast_per_green_kg,3)
            kwh_batch_per_green_kg = self.aw.float2float(self.convertHeat(btu_batch_per_green_kg,0,3),3)
            kwh_roast_per_green_kg = self.aw.float2float(self.convertHeat(btu_roast_per_green_kg,0,3),3)


            # energymetrics
            energymetrics['BTU_batch'] = btu_batch
            energymetrics['BTU_batch_per_green_kg'] = btu_batch_per_green_kg
            energymetrics['CO2_batch'] = co2_batch
            energymetrics['BTU_preheat'] = btu_preheat
            energymetrics['CO2_preheat'] = co2_preheat
            energymetrics['BTU_bbp'] = btu_bbp
            energymetrics['CO2_bbp'] = co2_bbp
            energymetrics['BTU_cooling'] = btu_cooling
            energymetrics['CO2_cooling'] = co2_cooling
            energymetrics['BTU_roast'] = btu_roast
            energymetrics['BTU_roast_per_green_kg'] = btu_roast_per_green_kg
            energymetrics['CO2_roast'] = co2_roast
            energymetrics['CO2_batch_per_green_kg'] = co2_batch_per_green_kg
            energymetrics['CO2_roast_per_green_kg'] = co2_roast_per_green_kg
            energymetrics['BTU_LPG'] = btu_lpg
            energymetrics['BTU_NG'] = btu_ng
            energymetrics['BTU_ELEC'] = btu_elec
            energymetrics['KWH_batch_per_green_kg'] = kwh_batch_per_green_kg
            energymetrics['KWH_roast_per_green_kg'] = kwh_roast_per_green_kg

        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' calcEnergyuse() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
        return energymetrics,btu_list

    def measureFromprofile(self):
        coolEnergy = [0.]*4
        heatEnergy = [0.]*4
        heatDuration = 0.
        coolDuration = 0.
        try:
            if len(self.timex) == 0:
                #self.aw.sendmessage(QApplication.translate("Message","No profile data"),append=False)
                return [-1]*4, [-1]*4, 0, 0

            def getEnergy(i,j,duration):
                try:
                    # scale the burner setting for 0-100%
                    val = (self.specialeventsvalue[j] - 1) * 10
                    emin = toInt(self.loadevent_zeropcts[i])
                    emax = toInt(self.loadevent_hundpcts[i])
                    scaled = (val - emin) / (emax - emin)  #emax > emin enforced by energy.py
                    load_pct = min(1,max(0,scaled)) * 100
                    if self.presssure_percents[i] and self.sourcetypes[i] in [0,1]:   # gas loads only
                        # convert pressure to heat
                        factor = math.sqrt(load_pct / 100)
                    else:
                        factor = load_pct / 100
                    energy = self.loadratings[i] * factor * (duration / 3600) #* self.convertHeat(1,self.ratingunits[i],0)
                    return energy
                except Exception as ex: # pylint: disable=broad-except
                    _log.exception(ex)
                    _, _, exc_tb = sys.exc_info()
                    self.adderror((QApplication.translate('Error Message','Exception:') + ' measureFromprofile() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
                return 0

            # if there is a DROP event use that for coolstart
            if self.timeindex[6] > 0:
                coolstart = self.timex[self.timeindex[6]]
            # else if there is a CHARGE event use that for coolstart
            elif self.timeindex[0] > -1:
                coolstart = self.timex[self.timeindex[0]]
            # else use the start of time for coolstart
            else:
                coolstart = self.timex[0]

            # if there is a CHARGE event use that for heatend
            if self.timeindex[0] > -1:
                heatend = self.timex[self.timeindex[0]]
            # else use the end of time for heatend
            else:
                heatend = self.timex[-1]

            prev_loadtime = [self.timex[-1]]*4

            for i in range(0,4):
                # iterate specialevents in reverse from end of profile to start
                if self.load_etypes[i] == 0:
                    heatEnergy[i] = -1
                    coolEnergy[i] = -1
                elif self.loadratings[i] > 0:
                    for j in range(len(self.specialevents) - 1, -1, -1):
                        if self.specialeventstype[j] == self.load_etypes[i]-1:
                            loadtime = self.timex[self.specialevents[j]]

                            if coolstart <= loadtime < prev_loadtime[i]:
                                duration = prev_loadtime[i] - loadtime
                                coolEnergy[i] += getEnergy(i,j,duration)
                            elif loadtime < coolstart <= prev_loadtime[i]:
                                duration = prev_loadtime[i] - coolstart
                                coolEnergy[i] += getEnergy(i,j,duration)

                            if loadtime < heatend <= prev_loadtime[i]:
                                duration = heatend - loadtime
                                heatEnergy[i] += getEnergy(i,j,duration)
                            elif loadtime < heatend and prev_loadtime[i] < heatend:
                                duration = prev_loadtime[i] - loadtime
                                heatEnergy[i] += getEnergy(i,j,duration)

                            prev_loadtime[i] = loadtime

                    ### end of loop: for j in range(len(self.specialevents) - 1, -1, -1)
            #### end of loop: for i in range(0,4)

            heatDuration = self.timex[self.timeindex[0]]
            coolDuration = self.timex[-1] - self.timex[self.timeindex[6]]

        except Exception as ex: # pylint: disable=broad-except
            _log.exception(ex)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' measureFromprofile() {0}').format(str(ex)),getattr(exc_tb, 'tb_lineno', '?'))
        return heatEnergy, coolEnergy, heatDuration, coolDuration

    #called from markdryend(), markcharge(), mark1Cstart(),  etc when using device 18 (manual mode)
    def drawmanual(self,et,bt,tx):
        self.timex.append(tx)
        self.temp1.append(et)
        if self.ETcurve and self.l_temp1 is not None:
            self.l_temp1.set_data(self.timex, self.temp1)
        self.temp2.append(bt)
        if self.BTcurve and self.l_temp2 is not None:
            self.l_temp2.set_data(self.timex, self.temp2)

    def movebackground(self,direction,step):
        lt = len(self.timeB)
        le = len(self.temp1B)
        lb = len(self.temp2B)
        #all background curves must have same dimension in order to plot. Check just in case.
        if lt > 1 and lt == le and lb == le:
            if  direction == 'up':
                for i in range(lt):
                    self.temp1B[i] += step
                    self.temp2B[i] += step
                    self.stemp1B[i] += step
                    self.stemp2B[i] += step
                for i,xtB in enumerate(self.extratimexB):
                    for j,_ in enumerate(xtB):
                        self.temp1BX[i][j] += step
                        self.temp2BX[i][j] += step
                        self.stemp1BX[i][j] += step
                        self.stemp2BX[i][j] += step
                self.backgroundprofile_moved_y += step
                self.moveBackgroundAnnoPositionsY(step)

            elif direction == 'left':
                for i in range(lt):
                    self.timeB[i] -= step
                for xtB in self.extratimexB:
                    for j,_ in enumerate(xtB):
                        xtB[j] -= step
                self.backgroundprofile_moved_x -= step
                self.moveBackgroundAnnoPositionsX(-step)

            elif direction == 'right':
                for i in range(lt):
                    self.timeB[i] += step
                for xtB in self.extratimexB:
                    for j,_ in enumerate(xtB):
                        xtB[j] += step
                self.backgroundprofile_moved_x += step
                self.moveBackgroundAnnoPositionsX(step)

            elif direction == 'down':
                for i in range(lt):
                    self.temp1B[i] -= step
                    self.temp2B[i] -= step
                    self.stemp1B[i] -= step
                    self.stemp2B[i] -= step

                for i,xtB in enumerate(self.extratimexB):
                    for j,_ in enumerate(xtB):
                        self.temp1BX[i][j] -= step
                        self.temp2BX[i][j] -= step
                        self.stemp1BX[i][j] -= step
                        self.stemp2BX[i][j] -= step
                self.backgroundprofile_moved_y -= step
                self.moveBackgroundAnnoPositionsY(-step)
        else:
            self.aw.sendmessage(QApplication.translate('Message','Unable to move background'))
            return

    #points are used to draw interpolation
    def findpoints(self):
        #if profile found
        if self.timeindex[0] != -1:
            Xpoints = []                        #make temporary lists to hold the values to return
            Ypoints = []

            #start point from beginning of time
            Xpoints.append(self.timex[0])
            Ypoints.append(self.temp2[0])
            #input beans (CHARGE)
            Xpoints.append(self.timex[self.timeindex[0]])
            Ypoints.append(self.temp2[self.timeindex[0]])

            #find indexes of lowest point and dryend
            LPind = self.aw.findTP()
            DE = self.aw.findDryEnd()

            if LPind < DE:
                Xpoints.append(self.timex[LPind])
                Ypoints.append(self.temp2[LPind])
                Xpoints.append(self.timex[DE])
                Ypoints.append(self.temp2[DE])
            else:
                Xpoints.append(self.timex[DE])
                Ypoints.append(self.temp2[DE])
                Xpoints.append(self.timex[LPind])
                Ypoints.append(self.temp2[LPind])

            if self.temp2[self.timeindex[1]] > self.timex[DE] and self.temp2[self.timeindex[1]] > self.timex[LPind]:
                Xpoints.append(self.timex[self.timeindex[1]])
                Ypoints.append(self.temp2[self.timeindex[1]])
            if self.timeindex[2]:
                Xpoints.append(self.timex[self.timeindex[2]])
                Ypoints.append(self.temp2[self.timeindex[2]])
            if self.timeindex[3]:
                Xpoints.append(self.timex[self.timeindex[3]])
                Ypoints.append(self.temp2[self.timeindex[3]])
            if self.timeindex[4]:
                Xpoints.append(self.timex[self.timeindex[4]])
                Ypoints.append(self.temp2[self.timeindex[4]])
            if self.timeindex[5]:
                Xpoints.append(self.timex[self.timeindex[5]])
                Ypoints.append(self.temp2[self.timeindex[5]])
            if self.timeindex[6]:
                Xpoints.append(self.timex[self.timeindex[6]])
                Ypoints.append(self.temp2[self.timeindex[6]])

            #end point
            if self.timex[self.timeindex[6]] != self.timex[-1]:
                Xpoints.append(self.timex[-1])
                Ypoints.append(self.temp2[-1])

            return Xpoints,Ypoints

        self.aw.sendmessage(QApplication.translate('Message','No finished profile found'))
        return [],[]

    #collects info about the univariate interpolation
    def univariateinfo(self):
        try:
            from scipy.interpolate import UnivariateSpline # type: ignore
            #pylint: disable=E0611
            Xpoints,Ypoints = self.findpoints()  #from lowest point to avoid many coefficients
            equ = UnivariateSpline(Xpoints, Ypoints)
            coeffs = equ.get_coeffs().tolist()
            knots = equ.get_knots().tolist()
            resid = equ.get_residual()
            roots = equ.roots().tolist()

            #interpretation of coefficients: http://www.sagenb.org/home/pub/1708/

            string = '<b>' + QApplication.translate('Message','Polynomial coefficients (Horner form):') + '</b><br><br>'
            string += str(coeffs) + '<br><br>'
            string += '<b>' + QApplication.translate('Message','Knots:') + '</b><br><br>'
            string += str(knots) + '<br><br>'
            string += '<b>' + QApplication.translate('Message','Residual:') + '</b><br><br>'
            string += str(resid) + '<br><br>'
            string += '<b>' + QApplication.translate('Message','Roots:') + '</b><br><br>'
            string += str(roots)

            QMessageBox.information(self.aw, QApplication.translate('Message','Profile information'),string)

        except ValueError as e:
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Value Error:') + ' univariateinfo() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
            return

        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' univariateinfo() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
            return

#    def test(self):
##        p = 120 # period in seconds
##        k = int(round(p / self.delay * 1000)) # number of past readings to consider
#        k = 70
#        if len(self.timex)>k:
#            try:
#                ET = numpy.array([numpy.nan if x == -1 else x for x in self.temp1[-k:]], dtype='float64')
#                BT = numpy.array([numpy.nan if x == -1 else x for x in self.temp2[-k:]], dtype='float64')
#                ET_BT = ET - BT
##                delta = numpy.array([numpy.nan if x == -1 else x for x in self.delta2[-k:]], dtype='float64')
#                delta = numpy.array([numpy.nan if x == -1 else x for x in self.unfiltereddelta2[-k:]], dtype='float64')
#                idx = numpy.isfinite(ET_BT) & numpy.isfinite(delta)
#                z, residuals, _, _, _ = numpy.polyfit(ET_BT[idx],delta[idx], 2, full=True)
#                print("z",z)
#                f = numpy.poly1d(z)
#                v = f(ET_BT[-1])
##                v = (f(ET_BT[-2]) + f(ET_BT[-1])) / 2 # this smoothing seems to delay too much
#                print("res",residuals, f(0), abs(delta[-1] - v))
#                if abs(delta[-1] - v) > 10:
#                    return -1, -1
#                else:
#                    return f(0), v
##                    return residuals, v
#
##                    if residuals > 280:
##                        return -1, -1
##                    elif residuals > 50:
##                        return v, -1
##                    else:
##                        return -1, v
#            except Exception as e: # pylint: disable=broad-except
#                print(e)
#                _log.exception(e)
#                return -1, -1
#        else:
#            return -1, -1

    def polyfit(self,xarray,yarray,deg,startindex,endindex,_=False,onDeltaAxis=False):
        xa = xarray[startindex:endindex]
        ya = yarray[startindex:endindex]
        if len(xa) > 0 and len(xa) == len(ya) and not all(x == 0 for x in xa) and not all(x == 0 for x in ya):
            try:
                # polyfit only over proper values (not -1, infinite or NaN)
                c1 = numpy.array([numpy.nan if x == -1 else x for x in xa], dtype='float64')
                c2 = numpy.array([numpy.nan if x == -1 else x for x in ya], dtype='float64')
                idx = numpy.isfinite(c1) & numpy.isfinite(c2)
                z = numpy.polyfit(c1[idx],c2[idx],deg)
                p = numpy.poly1d(z)
                x = p(xarray[startindex:endindex])
                pad = max(0,len(self.timex) - startindex - len(x))
                xx = numpy.concatenate((numpy.full((max(0,startindex)), None),x, numpy.full((pad,), None)))
                trans = None
                if onDeltaAxis and self.delta_ax is not None:
                    trans = self.delta_ax.transData
                elif self.ax is not None:
                    trans = self.ax.transData
                if trans is not None and self.ax is not None:
                    self.ax.plot(self.timex, xx, linestyle = '--', linewidth=3,transform=trans)
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        self.fig.canvas.draw()
                    return z
                return None
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
                return None
        else:
            return None

    #ln() regression. ln() will be used when power does not equal 2 (quadratic) or 3 (cubic).
    def lnRegression(self,power:int=0, curvefit_starttime:float=0, curvefit_endtime:float=0, plot:bool=True):
        res = ''
        try:
            from scipy.optimize import curve_fit # type: ignore
            if self.timeindex[0] > -1 and self.timeindex[6] > -1:  #CHARGE and DROP events exist
                charge = self.timex[self.timeindex[0]]
                if curvefit_starttime is not None and curvefit_starttime > charge:
                    begin = self.time2index(curvefit_starttime)
                    time_l = []
                    temp_l = []
                else:
                    #a = [charge] # not used!?
                    # find the DRY END point
                    if self.timeindex[1]: # take DRY if available
                        begin = self.timeindex[1]
                    else: # take DRY as specified in phases
                        pi = self.aw.findDryEnd(phasesindex=1)
                        begin = self.time2index(self.timex[pi])
                    # initial bean temp set to greens_temp or ambient or a fixed temp
                    if self.greens_temp > 0:
                        time_l = [charge]
                        temp_l = [self.greens_temp]
                    elif self.ambientTemp is not None and self.ambientTemp > 0:
                        time_l = [charge]
                        temp_l = [self.ambientTemp]
                    else:
                        time_l = [charge]
                        roomTemp = 70.0 if self.mode == 'F' else 21.0
                        temp_l = [roomTemp]
                if curvefit_endtime > 0:
                    end = self.time2index(curvefit_endtime)
                else:
                    end = self.timeindex[6]
                time_l = time_l + self.timex[begin:end]
                temp_l = temp_l + self.temp2[begin:end]

                xa = numpy.array(time_l) - charge
                yn = numpy.array(temp_l)
                func:Callable
                if power == 2:
                    func = lambda x,a,b,c: a*x*x + b*x + c # noqa: E731 # pylint: disable=unnecessary-lambda-assignment
                elif power == 3:
                    func = lambda x,a,b,c,d: a*x*x*x + b*x*x + c*x + d # noqa: E731 # pylint: disable=unnecessary-lambda-assignment
                else:
                    func = lambda x,a,b,c: a * numpy.log(b*x+c) # noqa: E731 # pylint: disable=unnecessary-lambda-assignment
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    hint = [0.01,0.01,1]
                    if power == 2:
                        hint = [-0.001, 0.5, 10]
                    elif power == 3:
                        hint =     [-0.00001, -0.0001, 0.5, 10]
                    popt,_ = curve_fit(func, xa, yn, p0=hint, maxfev=3000) # pylint: disable=unbalanced-tuple-unpacking
                #perr = numpy.sqrt(numpy.diag(pcov))
                if plot and self.ax is not None:
                    xb = numpy.array(self.timex)
                    xxb = xb + charge
                    xxa = xa + charge
                    self.ax.plot(xxb, func(xb, *popt),  color='black', linestyle = '-.', linewidth=3)
                    self.ax.plot(xxa, yn, 'ro')
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        self.fig.canvas.draw()
                if len(popt)>2:
                    if power == 2:
                        res = f"{popt[0]:.8f} * t*t {('+' if popt[1] > 0 else '')} {popt[1]:.8f} * t {('+' if popt[2] > 0 else '')} {popt[2]:.8f}"
                    elif power ==3:
                        res = f"{popt[0]:.8f} * t*t*t {('+' if popt[1] > 0 else '')} {popt[1]:.8f} * t*t {('+' if popt[2] > 0 else '')} {popt[2]:.8f} * t {('+' if popt[3] > 0 else '')} {popt[3]:.8f}"
                    else:
                        res = f"{popt[0]:.8f} * log({popt[1]:.8f} * t {('+' if popt[2] > 0 else '')} {popt[2]:.8f}, e)"
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror(QApplication.translate('Error Message','Error in lnRegression:') + ' lnRegression() ' + str(e),getattr(exc_tb, 'tb_lineno', '?'))
            if power == 2:
                fit = 'x\u00b2'
            elif power == 3:
                fit = 'x\u00b3'
            else:
                fit = QApplication.translate('Label','ln()')
            msg = QApplication.translate('Message','Cannot fit this curve to ' + fit)
            QApplication.processEvents() #this is here to be sure the adderror gets wrtten to the log before the sendmessage
            self.aw.sendmessage(msg)
            #QMessageBox.warning(aw,QApplication.translate("Message","Curve fit problem"), msg)

        return res

    #interpolation type
    def univariate(self):
        try:
            if self.ax is not None:
                from scipy.interpolate import UnivariateSpline # type: ignore
                #pylint: disable=E0611
                Xpoints,Ypoints = self.findpoints()

                func = UnivariateSpline(Xpoints, Ypoints)

                xa = numpy.array(self.timex)
                newX = func(xa).tolist()

                self.ax.plot(self.timex, newX, color='black', linestyle = '-.', linewidth=3)
                self.ax.plot(Xpoints, Ypoints, 'ro')

                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    self.fig.canvas.draw()

        except ValueError:
            self.adderror(QApplication.translate('Error Message','Value Error:') + ' univariate()')

        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror(QApplication.translate('Error Message','Exception:') + ' univariate() ' + str(e),getattr(exc_tb, 'tb_lineno', '?'))

    def drawinterp(self,mode):
        try:
            if self.ax is not None:
                #pylint: disable=E1101
                from scipy import interpolate as inter # type: ignore
                Xpoints,Ypoints = self.findpoints() #from 0 origin
                func = inter.interp1d(Xpoints, Ypoints, kind=mode)
                newY = func(self.timex)
                self.ax.plot(self.timex, newY, color='black', linestyle = '-.', linewidth=3)
                self.ax.plot(Xpoints, Ypoints, 'ro')

                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    self.fig.canvas.draw()

        except ValueError as e:
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Value Error:') + ' drawinterp() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))

        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' drawinterp() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))

    # calculates the (interpolated) temperature from the given time/temp arrays at timepoint "seconds"
    @staticmethod
    def timetemparray2temp(timearray, temparray, seconds):
        if timearray is not None and temparray is not None and len(timearray) and len(temparray) and len(timearray) == len(temparray):
            if seconds > timearray[-1] or seconds < timearray[0]:
                # requested timepoint out of bonds
                return -1
            # compute the closest index (left sided)
            i = numpy.searchsorted(timearray,seconds,side='left')
            ti = timearray[i]
            tempi = temparray[i]
            if i < len(timearray) - 1:
                j = i - 1
                tj = timearray[j]
                tempj = temparray[j]
                s = (tempi - tempj) / (ti - tj)
                return tempj + s*(seconds - tj)
            # should not be reached (guarded by the outer if)
            return tempi
        return -1

    # if smoothed=True, the smoothed data is taken if available
    # if relative=True, the given time in seconds is interpreted relative to CHARGE, otherwise absolute from the first mesasurement
    def BTat(self,seconds,smoothed=True,relative=False):
        if smoothed and self.stemp2 is not None and len(self.stemp2) != 0:
            temp = self.stemp2
        else:
            temp = self.temp2
        if self.timeindex[0] > -1 and relative:
            offset = self.timex[self.timeindex[0]]
        else:
            offset = 0
        return self.timetemparray2temp(self.timex,temp,seconds + offset)

    def ETat(self,seconds,smoothed=True,relative=False):
        if smoothed and self.stemp1 is not None and len(self.stemp1) != 0:
            temp = self.stemp1
        else:
            temp = self.temp1
        if self.timeindex[0] > -1 and relative:
            offset = self.timex[self.timeindex[0]]
        else:
            offset = 0
        return self.timetemparray2temp(self.timex,temp,seconds + offset)

    def backgroundBTat(self,seconds, relative=False):
        if self.timeindexB[0] > -1 and relative:
            offset = self.timeB[self.timeindexB[0]]
        else:
            offset = 0
        return self.timetemparray2temp(self.timeB,self.temp2B,seconds + offset)

    def backgroundSmoothedBTat(self,seconds, relative=False):
        if self.timeindexB[0] > -1 and relative:
            offset = self.timeB[self.timeindexB[0]]
        else:
            offset = 0
        return self.timetemparray2temp(self.timeB,self.stemp2B,seconds + offset)

    def backgroundETat(self,seconds,relative=False):
        if self.timeindexB[0] > -1 and relative:
            offset = self.timeB[self.timeindexB[0]]
        else:
            offset = 0
        return self.timetemparray2temp(self.timeB,self.temp1B,seconds + offset)

    def backgroundSmoothedETat(self,seconds,relative=False):
        if self.timeindexB[0] > -1 and relative:
            offset = self.timeB[self.timeindexB[0]]
        else:
            offset = 0
        return self.timetemparray2temp(self.timeB,self.stemp1B,seconds + offset)

    # returns the background temperature of extra curve n
    # with n=0 => extra device 1, curve 1; n=1 => extra device 1, curve 2; n=2 => extra device 2, curve 1,....
    # if the selected extra curve does not exists, the error value -1 is returned
    # if smoothed is True, the value of the corresponding smoothed extra line is returned
    def backgroundXTat(self, n, seconds, relative=False, smoothed=False):
        if self.timeindexB[0] > -1 and relative:
            offset = self.timeB[self.timeindexB[0]]
        else:
            offset = 0
        if n % 2 == 0:
            # even
            tempBX = self.stemp1BX if smoothed else self.temp1BX
        # odd
        elif smoothed:
            tempBX = self.stemp2BX
        else:
            tempBX = self.temp2BX
        c = n // 2
        if len(tempBX)>c:
            temp = tempBX[c]
        else:
            # no such extra device curve
            return -1
        return self.timetemparray2temp(self.timeB,temp,seconds + offset)

    def backgroundDBTat(self,seconds, relative=False):
        if self.timeindexB[0] > -1 and relative:
            offset = self.timeB[self.timeindexB[0]]
        else:
            offset = 0
        return self.timetemparray2temp(self.timeB,self.delta2B,seconds + offset)

    def backgroundDETat(self,seconds,relative=False):
        if self.timeindexB[0] > -1 and relative:
            offset = self.timeB[self.timeindexB[0]]
        else:
            offset = 0
        return self.timetemparray2temp(self.timeB,self.delta1B,seconds + offset)

    # fast variant based on binary search on lists using bisect (using numpy.searchsorted is slower)
    # side-condition: values in self.qmc.timex in linear order
    # time: time in seconds
    # nearest: if nearest is True the closest index is returned (slower), otherwise the previous (faster)
    # returns
    #   -1 on empty timex
    #    0 if time smaller than first entry of timex
    #  len(timex)-1 if time larger than last entry of timex (last index)
    @staticmethod
    def timearray2index(timearray, time, nearest:bool=True):
        i = bisect_right(timearray, time)
        if i:
            if nearest and i>0 and (i == len(timearray) or abs(time - timearray[i]) > abs(time - timearray[i-1])):
                return i-1
            return i
        return -1

    #selects closest time INDEX in self.timex from a given input float seconds
    def time2index(self,seconds, nearest:bool=True):
        #find where given seconds crosses self.timex
        return self.timearray2index(self.timex, seconds, nearest)

    #selects closest time INDEX in self.timeB from a given input float seconds
    def backgroundtime2index(self,seconds, nearest:bool=True):
        #find where given seconds crosses self.timeB
        return self.timearray2index(self.timeB, seconds, nearest)

    #updates list self.timeindex when found an _OLD_ profile without self.timeindex (new version)
    def timeindexupdate(self,times):
##        #          START            DRYEND          FCs             FCe         SCs         SCe         DROP
##        times = [self.startend[0],self.dryend[0],self.varC[0],self.varC[2],self.varC[4],self.varC[6],self.startend[2]]
        for i,tms in enumerate(times):
            if times[i]:
                self.timeindex[i] = max(0,self.time2index(tms))
            else:
                self.timeindex[i] = 0

    #updates list self.timeindexB when found an _OLD_ profile without self.timeindexB
    def timebackgroundindexupdate(self,times):
##        #          STARTB            DRYENDB          FCsB       FCeB         SCsB         SCeB               DROPB
##        times = [self.startendB[0],self.dryendB[0],self.varCB[0],self.varCB[2],self.varCB[4],self.varCB[6],self.startendB[2]]
        for i,tms in enumerate(times):
            if times[i]:
                self.timeindexB[i] = max(0,self.backgroundtime2index(tms))
            else:
                self.timeindexB[i] = 0


    #adds errors (can be called also outside the GUI thread, eg. from the sampling thread as actual message is written by updategraphics in the GUI thread)
    def adderror(self,error,line=None):
        try:
            #### lock shared resources #####
            self.errorsemaphore.acquire(1)
            timez = str(QDateTime.currentDateTime().toString('hh:mm:ss.zzz'))    #zzz = milliseconds
            #keep a max of 500 errors
            if len(self.errorlog) > 499:
                self.errorlog = self.errorlog[1:]
            if line:
                error = error + '@line ' + str(line)
            self.errorlog.append(timez + ' ' + error)
            # truncate to first line for window message line
            try:
                # only show first line in
                error = error.splitlines()[0]
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            if self.flagon: # don't send message here, but cache it and send it from updategraphics from within the GUI thread
                self.temporary_error = error
            else:
                self.aw.sendmessage(error)
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
        finally:
            if self.errorsemaphore.available() < 1:
                self.errorsemaphore.release(1)

    ####################  PROFILE DESIGNER   ###################################################################################
    #launches designer
    def designer(self):
        #disconnect mouse cross if ON
        if self.crossmarker:
            self.togglecrosslines()
        #clear background if it came from analysis
        if len(self.analysisresultsstr) > 0:
            self.aw.deleteBackground()

        if self.timex:
            reply = QMessageBox.question(self.aw, QApplication.translate('Message','Designer Start'),
                                         QApplication.translate('Message','Importing a profile in to Designer will decimate all data except the main [points].\nContinue?'),
                                         QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Yes:
                res = self.initfromprofile()
                if res:
                    self.connect_designer()
                    self.aw.disableEditMenus(designer=True)
                    self.redraw()
                else:
                    self.aw.designerAction.setChecked(False)
            elif reply == QMessageBox.StandardButton.Cancel:
                self.aw.designerAction.setChecked(False)
        else:
            #if no profile found
            #
            # reset also the special event copy held for the designer
            self.eventtimecopy = []
            self.specialeventsStringscopy = []
            self.specialeventsvaluecopy = []
            self.specialeventstypecopy = []
            #
            self.reset(redraw=False,soundOn=False)
            self.connect_designer()
            self.aw.disableEditMenus(designer=True)
            self.designerinit()

    @pyqtSlot()
    @pyqtSlot(bool)
    def savepoints(self,_=False):
        try:
            filename = self.aw.ArtisanSaveFileDialog(msg=QApplication.translate('Message', 'Save Points'),ext='*.adsg')
            if filename:
                obj:Dict[str, Union[List[float],List[int]]] = {}
                obj['timex'] = self.timex # List[float]
                obj['temp1'] = self.temp1 # List[float]
                obj['temp2'] = self.temp2 # List[float]
                obj['timeindex'] = self.timeindex # List[int]
                import codecs # @Reimport
                with codecs.open(filename, 'w+', encoding='utf-8') as f:
                    f.write(repr(obj))
                self.aw.sendmessage(QApplication.translate('Message','Points saved'))
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' savepoints() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))

    @pyqtSlot()
    @pyqtSlot(bool)
    def loadpoints(self,_=False):
        try:
            filename = self.aw.ArtisanOpenFileDialog(msg=QApplication.translate('Message', 'Load Points'),ext='*.adsg')
            obj = None
            if os.path.exists(filename):
                import codecs # @Reimport
                with codecs.open(filename, 'rb', encoding='utf-8') as f:
                    obj=ast.literal_eval(f.read())
            if obj and 'timex' in obj and 'temp1' in obj and 'temp2' in obj:
                self.timex = obj['timex']
                self.temp1 = obj['temp1']
                self.temp2 = obj['temp2']
                self.timeindex = obj['timeindex']
                self.xaxistosm(redraw=False)
                self.redrawdesigner(force=True)
                self.aw.sendmessage(QApplication.translate('Message','Points loaded'))
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message','Exception:') + ' loadpoints() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))


    #used to start designer from scratch (not from a loaded profile)
    def designerinit(self):
        #init start vars        #CH, DE,      FCs,      FCe,       SCs,         SCe,         Drop,      COOL
        self.designertimeinit = [0,(4*60),(9*60),(11*60),(12*60),(12.5*60),(13*60),(17*60)]
        if self.mode == 'C':
            self.designertemp1init = [230.,230.,230.,230.,225.,220.,215.,150.]   #CHARGE,DE,FCs,FCe,SCs,SCe,DROP,COOL
            self.designertemp2init = [210.,150.,198.,207.,212.,213.,215.,150.]   #CHARGE,DE,FCs,FCe,SCs,SCe,DROP,COOL
        elif self.mode == 'F':
            self.designertemp1init = [446.,446.,446.,446.,437.,428.,419.,302.]
            self.designertemp2init = [410.,300.,388.,404.,413.,415.5,419.,302.]

        idx = 0
        self.timex,self.temp1,self.temp2 = [],[],[]
        for i,_ in enumerate(self.timeindex):
            # add SCe and COOL END only if corresponding button is enabled
            if (i != 5 or self.buttonvisibility[5]) and (i != 7 or self.buttonvisibility[7]):
                self.timex.append(self.designertimeinit[i])
                self.temp1.append(self.designertemp1init[i])
                self.temp2.append(self.designertemp2init[i])
                self.timeindex[i] = idx
                idx += 1
        # add TP
        if self.mode == 'C':
            self.timex.insert(1,1.5*60)
            self.temp1.insert(1,230)
            self.temp2.insert(1,110)
            # add one intermediate point between DRY and FCs
            self.timex.insert(3,6*60)
            self.temp1.insert(3,230)
            self.temp2.insert(3,174)
        elif self.mode == 'F':
            self.timex.insert(1,1.5*60)
            self.temp1.insert(1,446)
            self.temp2.insert(1,230)
            # add one intermediate point between DRY and FCs
            self.timex.insert(3,6*60)
            self.temp1.insert(3,446)
            self.temp2.insert(3,345)
        for x,_ in enumerate(self.timeindex):
            if self.timeindex[x] >= 2:
                self.timeindex[x] += 2
            elif self.timeindex[x] >= 1:
                self.timeindex[x] += 1

        if not self.locktimex:
            self.xaxistosm(redraw=False)

#        # import UnivariateSpline needed to draw the curve in designer
#        from scipy.interpolate import UnivariateSpline # @UnusedImport # pylint: disable=import-error
#        global UnivariateSpline # pylint: disable=global-statement
        # init designer timez
        self.designer_timez = list(numpy.arange(self.timex[0],self.timex[-1],self.time_step_size))
        # set initial RoR z-axis limits
        self.setDesignerDeltaAxisLimits(self.DeltaETflag, self.DeltaBTflag)
        self.redrawdesigner(force=True)

    #loads main points from a profile so that they can be edited
    def initfromprofile(self):
        if self.timeindex[0] == -1 or self.timeindex[6] == 0:
            QMessageBox.information(self.aw, QApplication.translate('Message','Designer Init'),
                                    QApplication.translate('Message','Unable to start designer.\nProfile missing [CHARGE] or [DROP]'))
            self.disconnect_designer()
            return False

        #save events. They will be deleted on qmc.reset()
        self.specialeventsStringscopy = self.specialeventsStrings[:]
        self.specialeventsvaluecopy = self.specialeventsvalue[:]
        self.specialeventstypecopy = self.specialeventstype[:]
        self.eventtimecopy = []
        for spe in self.specialevents:
            #save relative time of events
            self.eventtimecopy.append(self.timex[spe]-self.timex[self.timeindex[0]])

        #find lowest point from profile to be converted
        lpindex = self.aw.findTP()
        if lpindex != -1 and lpindex not in self.timeindex:
            lptime = self.timex[lpindex]
            lptemp2 = self.temp2[lpindex]
            # we only consider TP if its BT is at least 20 degrees lower than the CHARGE temperature
            if self.temp2[self.timeindex[0]] < (lptemp2 + 20):
                lpindex = -1
        else:
            lpindex = -1
            lptime = -1
            lptemp2 = -1

        timeindexhold = [self.timex[self.timeindex[0]],0,0,0,0,0,0,0]
        timez,t1,t2 = [self.timex[self.timeindex[0]]],[self.temp1[self.timeindex[0]]],[self.temp2[self.timeindex[0]]]    #first CHARGE point
        for i in range(1,len(self.timeindex)):
            if self.timeindex[i]:                           # fill up empty lists with main points (FCs, etc). match from timeindex
                timez.append(self.timex[self.timeindex[i]])  #add time
                t1.append(self.temp1[self.timeindex[i]])    #add temp1
                t2.append(self.temp2[self.timeindex[i]])    #add temp2
                timeindexhold[i] =  self.timex[self.timeindex[i]]

        res = self.reset()  #erase screen
        if not res:
            return False

        self.timex,self.temp1,self.temp2 = timez[:],t1[:],t2[:]  #copy lists back after reset() with the main points

        self.timeindexupdate(timeindexhold) #create new timeindex[]

        #add lowest point as extra point
        if lpindex != -1:
            self.currentx = lptime
            self.currenty = lptemp2
            self.addpoint(manual=False)
            # reset cursor coordinates
            self.currentx = 0
            self.currenty = 0

        if not self.locktimex:
            self.xaxistosm(redraw=False)
#        # import UnivariateSpline needed to draw the curve in designer
#        from scipy.interpolate import UnivariateSpline # @UnusedImport # pylint: disable=import-error
#        global UnivariateSpline # pylint: disable=global-statement
        # init designer timez
        self.designer_timez = list(numpy.arange(self.timex[0],self.timex[-1],self.time_step_size))
        # set initial RoR z-axis limits
        self.setDesignerDeltaAxisLimits(self.DeltaETflag, self.DeltaBTflag)
        self.redrawdesigner(force=True)                                   #redraw the designer screen
        return True


    def setDesignerDeltaAxisLimits(self, setET:bool, setBT:bool):
        if setET or setBT:
            from scipy.interpolate import UnivariateSpline # type: ignore
            delta1_max = 0
            delta2_max = 0
            # we have first to calculate the delta data
            # returns the max ET/BT RoR between CHARGE and DROP
            if setET:
                func1 = UnivariateSpline(self.timex,self.temp1, k = self.ETsplinedegree)
                funcDelta1 = func1.derivative()
                delta1_max = max(funcDelta1(self.designer_timez) * 60)
            if setBT:
                func2 = UnivariateSpline(self.timex,self.temp2, k = self.BTsplinedegree)
                funcDelta2 = func2.derivative()
                delta2_max = max(funcDelta2(self.designer_timez) * 60)
            dmax = max(delta1_max, delta2_max)
            # we only adjust the upper limit automatically
            assert self.aw is not None
            zlimit_org = self.zlimit
            if dmax > self.zlimit_min:
                self.zlimit = int(dmax) + 1
            else:
                self.zlimit = self.zlimit_min + 1
            if self.delta_ax is not None:
                if zlimit_org != self.zlimit:
                    self.delta_ax.set_ylim(self.zlimit_min,self.zlimit)
                if self.zgrid != 0:
                    d = self.zlimit - self.zlimit_min
                    steps = int(round(d/5))
                    if steps > 50:
                        steps = int(round(steps/10))*10
                    elif steps > 10:
                        steps = int(round(steps/5))*5
                    elif steps > 5:
                        steps = 5
                    else:
                        steps = int(round(steps/2))*2
                    auto_grid = max(2,steps)
                    if auto_grid != self.zgrid:
                        self.zgrid = auto_grid
                        if self.zgrid > 0:
                            self.delta_ax.yaxis.set_major_locator(ticker.MultipleLocator(self.zgrid))
                            self.delta_ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
                            for i in self.delta_ax.get_yticklines():
                                i.set_markersize(10)
                            for i in self.delta_ax.yaxis.get_minorticklines():
                                i.set_markersize(5)
                            for label in self.delta_ax.get_yticklabels() :
                                label.set_fontsize('small')
                            if not self.LCDdecimalplaces:
                                self.delta_ax.minorticks_off()


    #redraws designer
    def redrawdesigner(self,force=False): #if force is set the bitblit cache is ignored and a full redraw is triggered
        from scipy.interpolate import UnivariateSpline # type: ignore
        if self.designerflag and self.ax is not None:

            if self.ax_background_designer is None or force:
                # we first initialize the background canvas and the bitblit cache
                self.designer_timez = list(numpy.arange(self.timex[0],self.timex[-1],self.time_step_size))

                #pylint: disable=E0611
                #reset (clear) plot
                self.ax_lines_clear()
                self.ax_annotations_clear() # remove background profiles annotations

                # remove logo image while in Designer
                if self.ai is not None:
                    try:
                        self.ai.remove()
                    except Exception: # pylint: disable=broad-except
                        pass
                fontprop_medium = self.aw.mpl_fontproperties.copy()
                fontprop_medium.set_size('medium')
                self.set_xlabel(self.aw.arabicReshape(QApplication.translate('Label', 'Designer')))

                # update z-axis limits if autoDelta is enabled
                self.setDesignerDeltaAxisLimits(self.DeltaETflag and self.autodeltaxET, self.DeltaBTflag and self.autodeltaxBT)

                if not self.locktimex and self.timex[-1] > self.endofx:
                    self.endofx = self.timex[-1] + 120
                    self.xaxistosm()

                # init artists
                rcParams['path.sketch'] = (0,0,0)


                #draw background
                if self.background:
                    if self.backgroundShowFullflag:
                        btime = self.timeB
                        b1temp = self.stemp1B
                        b2temp = self.stemp2B
                    else:
                        bcharge_idx = 0
                        if self.timeindexB[0] > -1:
                            bcharge_idx = self.timeindexB[0]
                        bdrop_idx = len(self.timeB)-1
                        if self.timeindexB[6] > 0:
                            bdrop_idx = self.timeindexB[6]
                        btime = self.timeB[bcharge_idx:bdrop_idx]
                        b1temp = self.stemp1B[bcharge_idx:bdrop_idx]
                        b2temp = self.stemp2B[bcharge_idx:bdrop_idx]

                    self.ax.plot(btime,b1temp,markersize=self.ETbackmarkersize,marker=self.ETbackmarker,
                                                    sketch_params=None,path_effects=[],
                                                    linewidth=self.ETbacklinewidth,linestyle=self.ETbacklinestyle,drawstyle=self.ETbackdrawstyle,color=self.backgroundmetcolor,
                                                    alpha=self.backgroundalpha,label=self.aw.arabicReshape(QApplication.translate('Label', 'BackgroundET')))
                    self.ax.plot(btime,b2temp,markersize=self.BTbackmarkersize,marker=self.BTbackmarker,
                                                    linewidth=self.BTbacklinewidth,linestyle=self.BTbacklinestyle,drawstyle=self.BTbackdrawstyle,color=self.backgroundbtcolor,
                                                    sketch_params=None,path_effects=[],
                                                    alpha=self.backgroundalpha,label=self.aw.arabicReshape(QApplication.translate('Label', 'BackgroundBT')))

                self.l_stat1, = self.ax.plot([],[],color = self.palette['rect1'],alpha=.5,linewidth=5)
                self.l_stat2, = self.ax.plot([],[],color = self.palette['rect2'],alpha=.5,linewidth=5)
                self.l_stat3, = self.ax.plot([],[],color = self.palette['rect3'],alpha=.5,linewidth=5)

                self.l_div1, = self.ax.plot([],[],color = self.palette['grid'],alpha=.3,linewidth=3,linestyle='--')
                self.l_div2, = self.ax.plot([],[],color = self.palette['grid'],alpha=.3,linewidth=3,linestyle='--')
                self.l_div3, = self.ax.plot([],[],color = self.palette['grid'],alpha=.3,linewidth=3,linestyle='--')
                self.l_div4, = self.ax.plot([],[],color = self.palette['grid'],alpha=.3,linewidth=3,linestyle='--')

                if (self.DeltaBTflag or self.DeltaETflag) and self.delta_ax is not None:
                    trans = self.delta_ax.transData #=self.delta_ax.transScale + (self.delta_ax.transLimits + self.delta_ax.transAxes)

                    self.l_delta1, = self.ax.plot([],[],transform=trans,markersize=self.ETdeltamarkersize,marker=self.ETdeltamarker,
                        sketch_params=None,path_effects=[PathEffects.withStroke(linewidth=self.ETdeltalinewidth+self.patheffects,foreground=self.palette['background'])],
                        linewidth=self.ETdeltalinewidth,linestyle=self.ETdeltalinestyle,drawstyle=self.ETdeltadrawstyle,color=self.palette['deltaet'],
                        label=self.aw.arabicReshape(deltaLabelPrefix + QApplication.translate('Label', 'ET')))
                    self.l_delta2, = self.ax.plot([],[],transform=trans,markersize=self.BTdeltamarkersize,marker=self.BTdeltamarker,
                        sketch_params=None,path_effects=[PathEffects.withStroke(linewidth=self.BTdeltalinewidth+self.patheffects,foreground=self.palette['background'])],
                        linewidth=self.BTdeltalinewidth,linestyle=self.BTdeltalinestyle,drawstyle=self.BTdeltadrawstyle,color=self.palette['deltabt'],
                        label=self.aw.arabicReshape(deltaLabelPrefix + QApplication.translate('Label', 'BT')))
                else:
                    self.l_delta1 = None
                    self.l_delta2 = None

                self.l_temp1, = self.ax.plot([], [],markersize=self.ETmarkersize,marker=self.ETmarker,linewidth=self.ETlinewidth,
                    linestyle=self.ETlinestyle,drawstyle=self.ETdrawstyle,color=self.palette['et'],
                        label=QApplication.translate('Label', 'ET'))
                self.l_temp2, = self.ax.plot([], [], markersize=self.BTmarkersize,marker=self.BTmarker,linewidth=self.BTlinewidth,
                    linestyle=self.BTlinestyle,drawstyle=self.BTdrawstyle,color=self.palette['bt'],
                        label=QApplication.translate('Label', 'BT'))

                self.l_temp1_markers, = self.ax.plot([],[],color = self.palette['et'],marker = 'o',picker=True, pickradius=10,linestyle='',markersize=8)
                self.l_temp2_markers, = self.ax.plot([],[],color = self.palette['bt'],marker = 'o',picker=True, pickradius=10,linestyle='',markersize=8)

                self._designer_orange_mark, = self.ax.plot([],[],color = 'orange',marker = 'o',alpha = .3,markersize=30)
                self._designer_blue_mark, = self.ax.plot([],[],color = 'blue',marker = 'o',alpha = .3,markersize=30)

                #plot
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    self.fig.canvas.draw() # NOTE: this needs to be done NOW and not via draw_idle() at any time later, to avoid ghost lines

                # initialize bitblit background
                self.ax_background_designer = self.fig.canvas.copy_from_bbox(self.ax.get_figure().bbox)



            # restore background
            self.fig.canvas.restore_region(self.ax_background_designer)


            #create statistics bar
            #calculate the positions for the statistics elements
            ydist = self.ylimit - self.ylimit_min
            statisticsheight = self.ylimit - (0.13 * ydist)
            stats_ys = [statisticsheight,statisticsheight]

            #add statistics bar

            if self.l_stat1 is not None:
                self.l_stat1.set_data([self.timex[self.timeindex[0]],self.timex[self.timeindex[1]]],stats_ys)
                self.ax.draw_artist(self.l_stat1)
            if self.l_stat2 is not None:
                self.l_stat2.set_data([self.timex[self.timeindex[1]],self.timex[self.timeindex[2]]],stats_ys)
                self.ax.draw_artist(self.l_stat2)
            if self.l_stat3 is not None:
                self.l_stat3.set_data([self.timex[self.timeindex[2]],self.timex[self.timeindex[6]]],stats_ys)
                self.ax.draw_artist(self.l_stat3)

            #add phase division lines

            ylist = [self.ylimit,0]
            if self.l_div1 is not None:
                self.l_div1.set_data([self.timex[self.timeindex[0]],self.timex[self.timeindex[0]]],ylist)
                self.ax.draw_artist(self.l_div1)
            if self.l_div2 is not None:
                self.l_div2.set_data([self.timex[self.timeindex[1]],self.timex[self.timeindex[1]]],ylist)
                self.ax.draw_artist(self.l_div2)
            if self.l_div3 is not None:
                self.l_div3.set_data([self.timex[self.timeindex[2]],self.timex[self.timeindex[2]]],ylist)
                self.ax.draw_artist(self.l_div3)
            if self.l_div4 is not None:
                self.l_div4.set_data([self.timex[self.timeindex[6]],self.timex[self.timeindex[6]]],ylist)
                self.ax.draw_artist(self.l_div4)

            if self.BTsplinedegree >= len(self.timex):  #max 5 or less. Cannot biger than points
                self.BTsplinedegree = len(self.timex)-1

            if self.ETsplinedegree >= len(self.timex):  #max 5 or less. Cannot biger than points
                self.ETsplinedegree = len(self.timex)-1

            try:
                func2 = UnivariateSpline(self.timex,self.temp2, k = self.BTsplinedegree)
                btvals = func2(self.designer_timez)
                func1 = UnivariateSpline(self.timex,self.temp1, k = self.ETsplinedegree)
                etvals = func1(self.designer_timez)
            except Exception: # pylint: disable=broad-except
                self.adderror(QApplication.translate('Error Message', 'Exception: redrawdesigner() Roast events may be out of order. Restting Designer.'))
                self.reset_designer()
                return

            #convert all time values to temperature

            if self.DeltaBTflag and self.l_delta2 is not None:
                funcDelta2 = func2.derivative()
                deltabtvals = funcDelta2(self.designer_timez) * 60
                self.l_delta2.set_data(self.designer_timez,deltabtvals)
                self.ax.draw_artist(self.l_delta2)

            if self.DeltaETflag and self.l_delta1 is not None:
                funcDelta1 = func1.derivative()
                deltaetvals = funcDelta1(self.designer_timez) * 60
                self.l_delta1.set_data(self.designer_timez,deltaetvals)
                self.ax.draw_artist(self.l_delta1)

            #add curves
            if self.ETcurve and self.l_temp1 is not None:
                self.l_temp1.set_data(self.designer_timez, etvals)
                self.ax.draw_artist(self.l_temp1)
            if self.BTcurve and self.l_temp2 is not None:
                self.l_temp2.set_data(self.designer_timez, btvals)
                self.ax.draw_artist(self.l_temp2)

            #add markers (big circles) '0'
            if self.ETcurve and self.l_temp1_markers is not None:
                self.l_temp1_markers.set_data(self.timex,self.temp1)
                self.ax.draw_artist(self.l_temp1_markers)
            if self.BTcurve and self.l_temp2_markers is not None:
                self.l_temp2_markers.set_data(self.timex,self.temp2)
                self.ax.draw_artist(self.l_temp2_markers)

            if self._designer_orange_mark_shown and self._designer_orange_mark is not None:
                self.ax.draw_artist(self._designer_orange_mark)
            if self._designer_blue_mark_shown and self._designer_blue_mark is not None:
                self.ax.draw_artist(self._designer_blue_mark)

            self.fig.canvas.blit(self.ax.get_figure().bbox)
            self.fig.canvas.flush_events()

    #CONTEXT MENU  = Right click
    def on_press(self,event):
        try:
            if event.inaxes != self.ax or event.button != 3:
                return #select right click only

            self.releaseMouse()
            self.mousepress = False
            # reset the zoom rectangles
            self.aw.ntb.release_pan(event)
            self.aw.ntb.release_zoom(event)
            # set cursor
            self.setCursor(Qt.CursorShape.PointingHandCursor)

            self.currentx = event.xdata
            self.currenty = event.ydata

            designermenu = QMenu(self.aw)  # if we bind this to self, we inherit the background-color: transparent from self.fig

            designermenu.addSeparator()

            addpointAction = QAction(QApplication.translate('Contextual Menu', 'Add point'),self)
            addpointAction.triggered.connect(self.addpoint_action)
            designermenu.addAction(addpointAction)

            removepointAction = QAction(QApplication.translate('Contextual Menu', 'Remove point'),self)
            removepointAction.triggered.connect(self.removepoint)
            designermenu.addAction(removepointAction)

            designermenu.addSeparator()

            loadpointsAction = QAction(QApplication.translate('Contextual Menu', 'Load points'),self)
            loadpointsAction.triggered.connect(self.loadpoints)
            designermenu.addAction(loadpointsAction)

            savepointsAction = QAction(QApplication.translate('Contextual Menu', 'Save points'),self)
            savepointsAction.triggered.connect(self.savepoints)
            designermenu.addAction(savepointsAction)

            designermenu.addSeparator()

            resetAction = QAction(QApplication.translate('Contextual Menu', 'Reset Designer'),self)
            resetAction.triggered.connect(self.reset_designer)
            designermenu.addAction(resetAction)

            configAction = QAction(QApplication.translate('Contextual Menu', 'Config...'),self)
            configAction.triggered.connect(self.desconfig)
            designermenu.addAction(configAction)

            designermenu.exec(QCursor.pos())
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)

    def on_pick(self,event):
        if self.currentx or self.currenty:
            self.currentx = 0
            self.currenty = 0
            return

        self.setCursor(Qt.CursorShape.ClosedHandCursor)

        if hasattr(event, 'ind'):
            if isinstance(event.ind, (int)):
                self.indexpoint = event.ind
            else:
                N = len(event.ind)
                if not N:
                    return
                self.indexpoint = event.ind[0]
        else:
            return

        self.mousepress = True

        line = event.artist
        #identify which line is being edited
        ydata = line.get_ydata()
        if ydata[1] == self.temp1[1]:
            self.workingline = 1
        else:
            self.workingline = 2

    #handles when releasing mouse
    def on_release(self,_):
        self.mousepress = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.redrawdesigner(force=True)

    def phases_to_messageline(self):
        totaltime = self.timex[self.timeindex[6]] - self.timex[self.timeindex[0]]
        dryphasetime = self.timex[self.timeindex[1]] - self.timex[self.timeindex[0]]
        midphasetime = self.timex[self.timeindex[2]] - self.timex[self.timeindex[1]]
        finishphasetime = self.timex[self.timeindex[6]] - self.timex[self.timeindex[2]]

        if totaltime:
            dryphaseP = int(round(dryphasetime*100./totaltime))
            midphaseP = int(round(midphasetime*100./totaltime))
            finishphaseP = int(round(finishphasetime*100./totaltime))
        else:
            return

        midramp = self.temp2[self.timeindex[2]] - self.temp2[self.timeindex[1]]
        finishramp = self.temp2[self.timeindex[6]] - self.temp2[self.timeindex[2]]

        min_bt,time_min_bt = self.findTPdes()
        if min_bt is not None and time_min_bt is not None:
            dryrampTP = self.temp2[self.timeindex[1]] - min_bt
            dryphasetimeTP = self.timex[self.timeindex[1]] - time_min_bt

            if dryphasetimeTP:
                dryroc = f' {((dryrampTP/dryphasetimeTP)*60.):.1f} {self.mode}/min'
            else:
                dryroc = f' 0 {self.mode}/min'

            if midphasetime:
                midroc = f' {((midramp/midphasetime)*60.):.1f} {self.mode}/min'
            else:
                midroc = '/min' f' 0 {self.mode}/min'

            if finishphasetime:
                finishroc = f' {((finishramp/finishphasetime)*60.):.1f} {self.mode}/min'
            else:
                finishroc = f'/min' f' 0 {self.mode}/min'

            margin = '&nbsp;&nbsp;&nbsp;'
            text_color_rect1 = 'white' if self.aw.QColorBrightness(QColor(self.palette['rect1'])) < 128 else 'black'
            string1 = f" <font color = \"{text_color_rect1}\" style=\"BACKGROUND-COLOR: {self.palette['rect1']}\">{margin}{stringfromseconds(dryphasetime)}{margin}{dryphaseP}%{margin}{dryroc}{margin}</font>"
            text_color_rect2 = 'white' if self.aw.QColorBrightness(QColor(self.palette['rect2'])) < 128 else 'black'
            string2 = f" <font color = \"{text_color_rect2}\" style=\"BACKGROUND-COLOR: {self.palette['rect2']}\">{margin} {stringfromseconds(midphasetime)} {margin} {midphaseP}% {margin} {midroc} {margin}</font>"
            text_color_rect3 = 'white' if self.aw.QColorBrightness(QColor(self.palette['rect3'])) < 128 else 'black'
            string3 = f" <font color = \"{text_color_rect3}\" style=\"BACKGROUND-COLOR: {self.palette['rect3']}\">{margin} {stringfromseconds(finishphasetime)} {margin} {finishphaseP}% {margin} {finishroc} {margin}</font>"
            self.aw.sendmessage(f'{string1}{string2}{string3}',append=False)

    #handler for moving point
    def on_motion(self,event):
        if not event.inaxes:
            return

        ydata = event.ydata

        try:
            if self.mousepress:                                 #if mouse clicked

                self.timex[self.indexpoint] = event.xdata
                if self.workingline == 1:
                    self.temp1[self.indexpoint] = ydata
                else:
                    self.temp2[self.indexpoint] = ydata

                if self._designer_orange_mark_shown and self._designer_orange_mark is not None:
                    self._designer_orange_mark.set_data([event.xdata], [ydata])
                elif self._designer_blue_mark_shown and self._designer_blue_mark is not None:
                    self._designer_blue_mark.set_data([event.xdata], [ydata])

                #check point going over point
                #check to the left
                if self.indexpoint > 0 and abs(self.timex[self.indexpoint] - self.timex[self.indexpoint - 1]) < 10.:
                    self.unrarefy_designer()
                    return
                #check to the right
                if self.indexpoint <= len(self.timex)-2 and abs(self.timex[self.indexpoint] - self.timex[self.indexpoint + 1]) < 10.:
                    self.unrarefy_designer()
                    return

                #check for possible CHARGE time moving
                if self.indexpoint == self.timeindex[0]:
                    self.designer_timez = numpy.arange(self.timex[0],self.timex[-1],1).tolist()
                    self.xaxistosm(redraw=False)

                #check for possible DROP/COOL time moving
                if (self.timeindex[7] and self.indexpoint == self.timeindex[7]) or (not self.timeindex[7] and self.indexpoint == self.timeindex[6]):
                    self.designer_timez = list(numpy.arange(self.timex[0],self.timex[-1],self.time_step_size))

                #redraw
                self.redrawdesigner()

                if self.indexpoint in self.timeindex:
                    #report phases to messageline on moving event points
                    self.phases_to_messageline()
                else:
                    #report time of the additional point in blue
                    timez = stringfromseconds(self.timex[self.indexpoint] - self.timex[self.timeindex[0]])
                    self.aw.sendmessage(timez,style="background-color:'lightblue';",append=False)
                return

            orange_hit = False
            blue_hit = False
            if self.ax is not None and type(event.xdata):                       #outside graph type is None
                for i,_ in enumerate(self.timex):
                    if abs(event.xdata - self.timex[i]) < 7.:
                        if i in self.timeindex:
                            if self.BTcurve and abs(self.temp2[i] - ydata) < 10:
                                orange_hit = True
                                if not self._designer_orange_mark_shown and self._designer_orange_mark is not None:
                                    self._designer_orange_mark_shown = True
                                    self._designer_orange_mark.set_data(self.timex[i],self.temp2[i])
                                    self.ax.draw_artist(self._designer_orange_mark)
                                    self.fig.canvas.blit(self.ax.get_figure().bbox)
                                    self.fig.canvas.flush_events()
                            elif self.ETcurve and abs(self.temp1[i] - ydata) < 10:
                                orange_hit = True
                                if not self._designer_orange_mark_shown and self._designer_orange_mark is not None:
                                    self._designer_orange_mark_shown = True
                                    self._designer_orange_mark.set_data(self.timex[i],self.temp1[i])
                                    self.ax.draw_artist(self._designer_orange_mark)
                                    self.fig.canvas.blit(self.ax.get_figure().bbox)
                                    self.fig.canvas.flush_events()
                            index = self.timeindex.index(i)
                            if index == 0:
                                timez = stringfromseconds(0)
                                self.aw.sendmessage(QApplication.translate('Message', '[ CHARGE ]') + ' ' + timez, style="background-color:'#f07800';",append=False)
                            elif index == 1:
                                timez = stringfromseconds(self.timex[self.timeindex[1]] - self.timex[self.timeindex[0]])
                                self.aw.sendmessage(QApplication.translate('Message', '[ DRY END ]') + ' ' + timez, style="background-color:'orange';",append=False)
                            elif index == 2:
                                timez = stringfromseconds(self.timex[self.timeindex[2]] - self.timex[self.timeindex[0]])
                                self.aw.sendmessage(QApplication.translate('Message', '[ FC START ]') + ' ' + timez, style="background-color:'orange';",append=False)
                            elif index == 3:
                                timez = stringfromseconds(self.timex[self.timeindex[3]] - self.timex[self.timeindex[0]])
                                self.aw.sendmessage(QApplication.translate('Message', '[ FC END ]') + ' ' + timez, style="background-color:'orange';",append=False)
                            elif index == 4:
                                timez = stringfromseconds(self.timex[self.timeindex[4]] - self.timex[self.timeindex[0]])
                                self.aw.sendmessage(QApplication.translate('Message', '[ SC START ]') + ' ' + timez, style="background-color:'orange';",append=False)
                            elif index == 5:
                                timez = stringfromseconds(self.timex[self.timeindex[5]] - self.timex[self.timeindex[0]])
                                self.aw.sendmessage(QApplication.translate('Message', '[ SC END ]') + ' ' + timez, style="background-color:'orange';",append=False)
                            elif index == 6:
                                timez = stringfromseconds(self.timex[self.timeindex[6]] - self.timex[self.timeindex[0]])
                                self.aw.sendmessage(QApplication.translate('Message', '[ DROP ]') + ' ' + timez, style="background-color:'#f07800';",append=False)
                            elif index == 7:
                                timez = stringfromseconds(self.timex[self.timeindex[7]] - self.timex[self.timeindex[0]])
                                self.aw.sendmessage(QApplication.translate('Message', '[ COOL ]') + ' ' + timez, style="background-color:'#6FB5D1';",append=False)
                            break
                        if self.BTcurve and abs(self.temp2[i] - ydata) < 10:
                            blue_hit = True
                            if not self._designer_blue_mark_shown and self._designer_blue_mark is not None:
                                self._designer_blue_mark_shown = True
                                self._designer_blue_mark.set_data(self.timex[i],self.temp2[i])
                                self.ax.draw_artist(self._designer_blue_mark)
                                self.fig.canvas.blit(self.ax.get_figure().bbox)
                                self.fig.canvas.flush_events()
                        elif self.ETcurve and abs(self.temp1[i] - ydata) < 10:
                            blue_hit = True
                            if not self._designer_blue_mark_shown and self._designer_blue_mark is not None:
                                self._designer_blue_mark_shown = True
                                self._designer_blue_mark.set_data(self.timex[i],self.temp1[i])
                                self.ax.draw_artist(self._designer_blue_mark)
                                self.fig.canvas.blit(self.ax.get_figure().bbox)
                                self.fig.canvas.flush_events()
                        timez = stringfromseconds(self.timex[i] - self.timex[self.timeindex[0]])
                        self.aw.sendmessage(timez,style="background-color:'lightblue';",append=False)
                        break
                draw_idle = False
                if not orange_hit and self._designer_orange_mark_shown and self._designer_orange_mark is not None:
                    # clear mark
                    self._designer_orange_mark_shown = False
                    self._designer_orange_mark.set_data([], [])
                    draw_idle = True
                if not blue_hit and self._designer_blue_mark_shown and self._designer_blue_mark is not None:
                    # clear mark
                    self._designer_blue_mark_shown = False
                    self._designer_blue_mark.set_data([], [])
                    draw_idle = True
                if draw_idle:
                    self.redrawdesigner(force=True)

                if orange_hit or blue_hit:
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                else:
                    self.setCursor(Qt.CursorShape.PointingHandCursor) # Qt.CursorShape.PointingHandCursor or Qt.CursorShape.ArrowCursor
                    self.phases_to_messageline()


        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' on_motion() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
            self.unrarefy_designer()
            return

    def findTPdes(self):
        try:
            from scipy.interpolate import UnivariateSpline # type: ignore
            funcBT = UnivariateSpline(self.timex,self.temp2, k = self.BTsplinedegree)
            timez = numpy.arange(self.timex[0],self.timex[-1],1).tolist()
            btvals = funcBT(timez).tolist()
            min_bt = min(btvals)
            idx_min_bt = btvals.index(min_bt)
            time_min_bt = timez[idx_min_bt]
            return min_bt, time_min_bt

        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' findTPdes() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
            return None, None

    #this is used in on_motion() to try to prevent points crossing over points
    def unrarefy_designer(self):
        for i in range(len(self.timex)-1):
            if abs(self.timex[i]-self.timex[i+1]) < 20:
                self.timex[i+1] = self.timex[i] + 20
            self.disconnect_designer()
            self.connect_designer()

    @pyqtSlot()
    @pyqtSlot(bool)
    def addpoint_action(self,_=False):
        self.addpoint()

    def addpoint(self,manual=True):
        try:
            #current x, and y is obtained when doing right click in mouse: on_press()
            if manual:
                # open a dialog to let the user correct the input
                offset:float = 0.
                if self.timeindex[0] > -1:
                    offset = self.timex[self.timeindex[0]]
                values = [self.currentx-offset, self.currenty]
                from artisanlib.designer import pointDlg
                dlg = pointDlg(parent=self.aw, aw=self.aw, values=values)
                if dlg.exec():
                    self.currentx = values[0] + offset
                    self.currenty = values[1]
                else:
                    return


            if self.currentx > self.timex[-1]:       #if point is beyond max timex (all the way to the right)

                #find closest line
                d1 = abs(self.temp1[-1] - self.currenty)
                d2 = abs(self.temp2[-1] - self.currenty)
                if d2 < d1:
                    self.temp2.append(self.currenty)
                    self.temp1.append(self.temp1[-1])
                else:
                    self.temp2.append(self.temp2[-1])
                    self.temp1.append(self.currenty)

                self.timex.append(self.currentx)
                #no need to update time index

                self.redrawdesigner(force=True)
                return # 0

            if self.currentx < self.timex[0]:         #if point is below min timex (all the way to the left)
                #find closest line
                d1 = abs(self.temp1[0] - self.currenty)
                d2 = abs(self.temp2[0] - self.currenty)
                if d2 < d1:
                    self.temp2.insert(0,self.currenty)
                    self.temp1.insert(0,self.temp1[0])
                else:
                    self.temp2.insert(0,self.temp2[0])
                    self.temp1.insert(0,self.currenty)

                self.timex.insert(0,self.currentx)

                #update timeindex
                if self.timeindex[0] != -1:   #we update timeindex[0] different
                    self.timeindex[0] += 1
                for u in range(1,len(self.timeindex)):
                    if self.timeindex[u]:
                        self.timeindex[u] += 1

                self.redrawdesigner(force=True)
                return # len(self.timex)-1   #return index received from Designer Dialog Config to assign index to timeindex)

            #mid range
            #find index
            i = next((x for x, val in enumerate(self.timex) if val > self.currentx), None) # returns None if no index exists with "self.timex[i] > self.currentx"

            if i is None:
                return

            #find closest line
            d1 = abs(self.temp1[i] - self.currenty)
            d2 = abs(self.temp2[i] - self.currenty)
            if (d2 < d1 or self.temp1[i] == -1) and self.temp2[i] != -1:
                self.temp2.insert(i,self.currenty)
                self.temp1.insert(i,self.temp1[i])
            elif self.temp1[i] != -1:
                self.temp2.insert(i,self.temp2[i])
                self.temp1.insert(i,self.currenty)
            if not (self.temp1[i] == -1 and self.temp2[i] == -1):
                self.timex.insert(i,self.currentx)

                #update timeindex
                for x,_ in enumerate(self.timeindex):
                    if self.timeindex[x] >= i:
                        self.timeindex[x] += 1

            self.redrawdesigner(force=True)
            return # i

        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' addpoint() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))

    #removes point
    @pyqtSlot()
    @pyqtSlot(bool)
    def removepoint(self,_=False):
        try:
            #current x, and y is obtained when doing right click in mouse: on_press()
            #find index

            i = next((x for x, val in enumerate(self.timex) if val > self.currentx), None) # returns None if no index exists with "self.timex[i] > self.currentx"

            if i is None:
                return

            #find closest point
            if abs(self.timex[i]- self.currentx) < abs(self.timex[i-1] - self.currentx):
                index = i
            else:
                index = i-1

            #check if if it is a landmark point
            if index in self.timeindex:
                whichone = self.timeindex.index(index)
                if whichone in [0, 6]:  #if charge or drop
                    return
                self.timeindex[whichone] = 0

            self.timex.pop(index)
            self.temp1.pop(index)
            self.temp2.pop(index)

            for x,_ in enumerate(self.timeindex):
                if self.timeindex[x] > index: #decrease time index by one when above the index taken out
                    self.timeindex[x] = max(0,self.timeindex[x] - 1)

            self.redrawdesigner(force=True)

        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' removepoint() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))

    def clear_designer(self):
        # removes all generated artists and cleans the bitblit cache
        self.ax_background_designer = None
        self.ax_lines_clear()
        # clear references
        self._designer_orange_mark = None
        self._designer_orange_mark_shown = False
        self._designer_blue_mark = None
        self._designer_blue_mark_shown = False
        self.l_temp1_markers = None
        self.l_temp2_markers = None
        self.l_stat1 = None
        self.l_stat2 = None
        self.l_stat3 = None
        self.l_div1 = None
        self.l_div2 = None
        self.l_div3 = None
        self.l_div4 = None


    #converts from a designer profile to a normal profile
    def convert_designer(self):
        try:
            self.disconnect_designer()

            from scipy.interpolate import UnivariateSpline # type: ignore
            #pylint: disable=E0611
            #prevents accidentally deleting a modified profile.
            self.fileDirtySignal.emit()
            #create functions
            funcBT = UnivariateSpline(self.timex,self.temp2, k = self.BTsplinedegree)
            funcET = UnivariateSpline(self.timex,self.temp1, k = self.ETsplinedegree)

            #create longer list of time values
            timez = numpy.arange(self.timex[0],self.timex[-1],1).tolist()

            #convert all time values to temperature
            btvals = funcBT(timez).tolist()
            etvals = funcET(timez).tolist()

            #find new indexes for events
            for i,_ in enumerate(self.specialevents):
                for p, tp in enumerate(timez):
                    if tp > self.timex[self.specialevents[i]]:
                        self.specialevents[i] = p
                        break

            #save landmarks
            maintimes = []
            for txi in self.timeindex:
                maintimes.append(self.timex[txi])

            self.timex = timez[:]
            self.temp1 = etvals[:]
            self.temp2 = btvals[:]

            self.timeindexupdate(maintimes)

            #check and restore carried over events
            if self.eventtimecopy:
                for etc in self.eventtimecopy:
                    self.specialevents.append(self.time2index(etc + self.timex[self.timeindex[0]]))
                self.specialeventsStrings = self.specialeventsStringscopy[:]
                self.specialeventsvalue = self.specialeventsvaluecopy[:]
                self.specialeventstype = self.specialeventstypecopy[:]

            #check for extra devices
            num = len(self.timex)
            for i in range(len(self.extradevices)):
                self.extratemp1[i] = [-1.]*num
                self.extratemp2[i] = [-1.]*num
                self.extratimex[i] = self.timex[:]

            if self.profile_sampling_interval is None:
                self.profile_sampling_interval = self.delay / 1000.

            #create playback events
            if self.reproducedesigner == 1:
                self.designer_create_BT_rateofchange()
            elif self.reproducedesigner == 2:
                self.designer_create_ET_rateofchange()
            elif self.reproducedesigner == 3:
                self.designer_create_sv_command()
            elif self.reproducedesigner == 4:
                self.designer_create_ramp_command()

            self.redraw()
            self.aw.sendmessage(QApplication.translate('Message', 'New profile created'))

        except ValueError:
            _, _, exc_tb = sys.exc_info()
            self.adderror(QApplication.translate('Error Message', 'Value Error:') + ' createFromDesigner()',getattr(exc_tb, 'tb_lineno', '?'))
            return

        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' createFromDesigner() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
            return

    #activates mouse events
    def connect_designer(self):
        if not self.designerflag:
            self.designerflag = True
            self.aw.designerAction.setChecked(True)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.mousepress = False
            #create mouse events. Note: keeping the ids inside a list helps protect against extrange python behaviour.
            self.designerconnections = [None,None,None,None]
            self.designerconnections[0] = self.fig.canvas.mpl_connect('pick_event', self.on_pick)
            self.designerconnections[1] = self.fig.canvas.mpl_connect('button_release_event', self.on_release)
            self.designerconnections[2] = self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
            self.designerconnections[3] = self.fig.canvas.mpl_connect('button_press_event', self.on_press) #right click
            #this is needed to prevent complaints from UnivariateSpline() -used in redraw()- in extreme cases of difficulty
            warnings.simplefilter('ignore', UserWarning)

    #deactivates mouse events
    def disconnect_designer(self):
        self.designerflag = False
        self.aw.designerAction.setChecked(False)
        for dc in self.designerconnections:
            if dc is not None:
                self.fig.canvas.mpl_disconnect(dc)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        warnings.simplefilter('default', UserWarning)

    #launches designer config Window
    @pyqtSlot()
    @pyqtSlot(bool)
    def desconfig(self, _=False): # pylint: disable=no-self-use # used as slot
        from artisanlib.designer import designerconfigDlg
        dialog = designerconfigDlg(self.aw, self.aw)
        dialog.show()

    @pyqtSlot()
    @pyqtSlot(bool)
    def reset_designer(self,_=False):
        #self.disconnect_designer() # done in reset() !
        self.reset()
        self.connect_designer()
        self.designerinit()

    #saves next BT rate of change till next landmark as an event (example idea for arduino TC4)
    def designer_create_BT_rateofchange(self):
        self.deleteEvents()
        lastindexused = 0
        for i in range(1,len(self.timeindex)):
            if self.timeindex[i]:
                difftemp = self.temp2[self.timeindex[i]] - self.temp2[self.timeindex[lastindexused]]
                difftime = (self.timex[self.timeindex[i]] - self.timex[self.timeindex[lastindexused]])/60.
                if difftime:
                    string = QApplication.translate('Label', 'BT {0} {1}/min for {2}').format(f'{difftemp/difftime:.1f}',self.mode,stringfromseconds(self.timex[self.timeindex[i]]-self.timex[self.timeindex[lastindexused]])) # pylint: disable=consider-using-f-string
                    self.specialevents.append(self.timeindex[lastindexused])
                    self.specialeventstype.append(0)
                    self.specialeventsStrings.append(string)
                    self.specialeventsvalue.append(0)
                    lastindexused = i

    #saves next BT rate of change till next landmark as an event (example idea for arduino TC4)
    def designer_create_ET_rateofchange(self):
        self.deleteEvents()
        lastindexused = 0
        for i in range(1,len(self.timeindex)):
            if self.timeindex[i]:
                difftemp = self.temp1[self.timeindex[i]] - self.temp1[self.timeindex[lastindexused]]
                difftime = (self.timex[self.timeindex[i]] - self.timex[self.timeindex[lastindexused]])/60.
                if difftime:
                    string = QApplication.translate('Label', 'ET {0} {1}/min for {2}').format(f'{difftemp/difftime:.1f}',self.mode,stringfromseconds(self.timex[self.timeindex[i]]-self.timex[self.timeindex[lastindexused]])) # pylint: disable=consider-using-f-string
                    self.specialevents.append(self.timeindex[lastindexused])
                    self.specialeventstype.append(0)
                    self.specialeventsStrings.append(string)
                    self.specialeventsvalue.append(0)
                    lastindexused = i

    def deleteEvents(self):
        self.specialevents = []
        self.specialeventstype = []
        self.specialeventsStrings = []
        self.specialeventsvalue = []

    #this is used to create a string in pid language to reproduce the profile from Designer
    #NOTE: pid runs ET (temp1)
    def designer_create_ramp_command(self):
        tempinits = []
        minutes_segments = []

        #ramp times in minutes
        minsDryPhase = str(int(abs(self.timex[self.timeindex[0]] - self.timex[self.timeindex[1]])/60))
        minsMidPhase = str(int(abs(self.timex[self.timeindex[1]] - self.timex[self.timeindex[2]])/60))
        minsFinishPhase = str(int(abs(self.timex[self.timeindex[2]] - self.timex[self.timeindex[6]])/60))

        #target temps for ET
        tempinits.append(f'{self.temp1[self.timeindex[1]]:.1f}')
        tempinits.append(f'{self.temp1[self.timeindex[2]]:.1f}')
        tempinits.append(f'{self.temp1[self.timeindex[6]]:.1f}')

        minutes_segments.append(minsDryPhase)
        minutes_segments.append(minsMidPhase)
        minutes_segments.append(minsFinishPhase)

        command = ''
        for i in range(3):
            command += 'SETRS::' + tempinits[i] + '::' + minutes_segments[i] + '::0::'
        command += 'SETRS::' + tempinits[-1] + '::0::0'

        self.clean_old_pid_commands()

        #do only one event but with all segments
        self.specialevents.append(0)
        self.specialeventstype.append(0)
        self.specialeventsStrings.append(command)
        self.specialeventsvalue.append(0)

    #this is used to create a string in ET temp language to reproduce the profile from Designer
    def designer_create_sv_command(self):
        self.clean_old_pid_commands()
        for i in range(len(self.timeindex)-1):
            command = 'SETSV::{self.temp1[self.timeindex[i+1]]:.1f}'
            if i > 0 and self.timeindex[i]:
                self.specialevents.append(self.timeindex[i])
                self.specialeventstype.append(0)
                self.specialeventsStrings.append(command)
                self.specialeventsvalue.append(0)

    #verifies there are no previous machine commands on events
    def clean_old_pid_commands(self):
        #check for possible preloaded machine commands
        target = 0
        if self.specialevents:
            for i in range(len(self.specialevents)):
                if '::' in self.specialeventsStrings[i]:
                    self.specialevents.pop(i)
                    self.specialeventstype.pop(i)
                    self.specialeventsStrings.pop(i)
                    self.specialeventsvalue.pop(i)
                    target = 1
                    break     #break or the index i can become larger than the new shorted length of specialevents
        if target:
            self.clean_old_pid_commands()

    ###################################      WHEEL GRAPH  ####################################################

    @staticmethod
    def findCenterWheelTextAngle(t):
        if t > 360. or t < 0.:
            _,t = divmod(t,360.)
        if t in [0.,360.]:
            return 270.
        #check cuadrants
        if 0. < t < 90 or t > 360:        #quadrant 1
            return 270.+t
        if 90 <= t <= 180:                #quadrant 2
            return t - 90.
        if 180 < t < 270:                 #quadrant 3
            return t + 90
        return t - 270                    #quadrant 4

    @staticmethod
    def findRadialWheelTextAngle(t):
        if t > 360. or t < 0.:
            _,t = divmod(t,360.)
        if 0 < t <= 90 or t > 270:
            return t
        return 180 + t

    def loadselectorwheel(self,path):
        s = 'Wheels' + '\\' + path
        direct = QDir()
        pathDir = direct.toNativeSeparators(s)
        filename = self.aw.ArtisanOpenFileDialog(msg=QApplication.translate('Message','Open Wheel Graph'),path=pathDir,ext='*.wg')
        if filename:
            self.connectWheel()
            self.aw.loadWheel(filename)
            self.drawWheel()

    @pyqtSlot()
    @pyqtSlot(bool)
    def addTocuppingnotes(self,_=False):
        descriptor = str(self.wheelnames[self.wheelx][self.wheelz])
        if self.cuppingnotes == '':
            self.cuppingnotes = descriptor
        else:
            self.cuppingnotes += '\n' + descriptor
        s = QApplication.translate('Message', ' added to cupping notes')
        self.aw.sendmessage(descriptor + s)

    @pyqtSlot()
    @pyqtSlot(bool)
    def addToroastingnotes(self,_=False):
        descriptor =  str(self.wheelnames[self.wheelx][self.wheelz]) + ' '
        if self.roastingnotes == '':
            self.roastingnotes = descriptor
        else:
            self.roastingnotes +=  '\n' + descriptor
        string = QApplication.translate('Message', ' added to roasting notes')
        self.aw.sendmessage(descriptor + string)

    def wheel_pick(self,event):
        rect =  event.artist
        loc = rect.get_url().split('-')
        x = int(loc[0])
        z = int(loc[1])
        self.aw.sendmessage(self.wheelnames[x][z])
        self.wheelx = x
        self.wheelz = z

    def wheel_release(self,event):
        newlocz = event.xdata
        if newlocz and newlocz != self.wheellocationz:
            diff = math.degrees(self.wheellocationx - newlocz)
            for i,_ in enumerate(self.startangle):
                self.startangle[i] -= diff
            self.drawWheel()

    def wheel_menu(self,event):
        if str(event.inaxes) != str(self.ax2):
            return
        if event.button == 1:
            self.wheellocationx = event.xdata
            self.wheellocationz = event.ydata

        elif event.button == 3:
            designermenu = QMenu(self.aw) # if we bind this to self, we inherit the background-color: transparent from self.fig
            cuppingAction = QAction(QApplication.translate('Contextual Menu', 'Add to Cupping Notes'),self)
            cuppingAction.triggered.connect(self.addTocuppingnotes)
            designermenu.addAction(cuppingAction)

            roastingAction = QAction(QApplication.translate('Contextual Menu', 'Add to Roasting Notes'),self)
            roastingAction.triggered.connect(self.addToroastingnotes)
            designermenu.addAction(roastingAction)

            designermenu.addSeparator()

            editAction = QAction(QApplication.translate('Contextual Menu', 'Edit'),self)
            editAction.triggered.connect(self.editmode)
            designermenu.addAction(editAction)

            designermenu.exec(QCursor.pos())

    @pyqtSlot()
    @pyqtSlot(bool)
    def editmode(self,_=False):
        self.disconnectWheel()
        if self.aw.wheeldialog is not None:
            self.aw.wheeldialog.show()

    def exitviewmode(self):
        self.disconnectWheel()
        if self.ax2 is not None:
            try:
                self.fig.delaxes(self.ax2)
            except Exception: # pylint: disable=broad-except
                pass
        self.redraw(recomputeAllDeltas=False,forceRenewAxis=True)

    def connectWheel(self):
        self.wheelflag = True
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.wheelconnections[0] = self.fig.canvas.mpl_connect('pick_event', self.wheel_pick)
        self.wheelconnections[1] = self.fig.canvas.mpl_connect('button_press_event', self.wheel_menu)           #right click menu context
        self.wheelconnections[2] = self.fig.canvas.mpl_connect('button_release_event', self.wheel_release)

    def disconnectWheel(self):
        self.wheelflag = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.fig.canvas.mpl_disconnect(self.wheelconnections[0])
        self.fig.canvas.mpl_disconnect(self.wheelconnections[1])
        self.fig.canvas.mpl_disconnect(self.wheelconnections[2])

    def drawWheel(self):
        try:
            ### var constants  #####
            pi = numpy.pi
            threesixty = 2.*pi
            div = threesixty/100.
            rad = 360./threesixty
            ########################
            # same as redraw but using different axes
            self.fig.clf()
            #create a new name ax1 instead of ax
            if self.ax2 is not None:
                try:
                    self.fig.delaxes(self.ax2)
                except Exception: # pylint: disable=broad-except
                    pass
            self.ax2 = self.fig.add_subplot(111, projection='polar',facecolor='None')


            if self.ax2 is not None:

                # fixing yticks with matplotlib.ticker "FixedLocator"
                try:
                    ticks_loc = self.ax2.get_yticks()
                    self.ax2.yaxis.set_major_locator(ticker.FixedLocator(ticks_loc))
                except Exception: # pylint: disable=broad-except
                    pass

                self.ax2.set_rmax(1.)
                self.ax2.set_aspect(self.wheelaspect)
                self.ax2.grid(False)

                #delete degrees ticks
                for tick in self.ax2.xaxis.get_major_ticks():
                    #tick.label1On = False
                    tick.label1.set_visible(False)
                #delete yaxis
                locs = self.ax2.get_yticks()
                labels = ['']*len(locs)
                self.ax2.set_yticklabels(labels)

                names = self.wheelnames[:]
                Wradii = self.wradii[:]
                startangle = self.startangle[:]
                projection = self.projection[:]

                #calculate text orientation
                wheels = len(names)

                if not wheels:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        self.fig.canvas.draw()
                    return

                n,textangles,textloc = [],[],[] # nr of names, text angles, text locations
                for i in range(wheels):
                    l,tloc = [],[]
                    count = self.startangle[i]
                    #calculate text orientation
                    for p in range(len(names[i])):
                        if projection[i] == 0:
                            l.append(0)
                        elif projection[i] == 1:
                            l.append(self.findCenterWheelTextAngle(3.6*self.segmentlengths[i][p]/2. + count))
                        elif projection[i] == 2:
                            l.append(self.findRadialWheelTextAngle(3.6*self.segmentlengths[i][p]/2. + count))
                        tloc.append((3.6*self.segmentlengths[i][p]/2. + count)/rad)
                        count += self.segmentlengths[i][p]*3.6

                    textloc.append(tloc)
                    textangles.append(l)
                    Wradii[i] = float(Wradii[i])/100.                   #convert radii to float between 0-1 range
                    startangle[i] = startangle[i]/rad                   #convert angles to radians
                    n.append(len(names[i]))                             #store the number of names for each wheel

                #store the absolute len-radius origin of each circle
                lbottom = [0.]
                count = 0.
                for i in range(wheels-1):
                    count += Wradii[i]
                    lbottom.append(count)

                Wradiitext = [Wradii[0]/2.]
                for i in range(wheels-1):
                    Wradiitext.append(lbottom[i+1] + Wradii[i+1]/2.)     #store absolute len-radius for text in each circle
                    Wradii[i] += self.wheeledge                          #create extra color edge between wheels by overlapping wheels
                #Generate Wheel graph
                barwheel = []                                                 #holds bar-graphs (wheels)

                for z, nz in enumerate(n):
                    #create wheel
                    theta,segmentwidth,radii = [],[],[]
                    count = startangle[z]
                    for i in range(nz):
                        #negative number affect eventpicker
                        if count > threesixty:
                            count %= threesixty
                        elif count < 0.:
                            count += threesixty
                        theta.append(count + div*self.segmentlengths[z][i] / 2.)
                        count += div*self.segmentlengths[z][i]
                        segmentwidth.append(div*self.segmentlengths[z][i])
                        radii.append(Wradii[z])

                    barwheel.append(self.ax2.bar(theta, radii, width=segmentwidth, bottom=lbottom[z],edgecolor=self.wheellinecolor,
                                            linewidth=self.wheellinewidth,picker=3))
                    count = 0
                    #set color, alpha, and text
                    for _,barwheel[z] in zip(radii, barwheel[z]): # noqa: B020
                        barwheel[z].set_facecolor(self.wheelcolor[z][count])
                        barwheel[z].set_alpha(max(min(self.segmentsalpha[z][count],1),0))
                        barwheel[z].set_url(str(z) + '-' + str(count))
                        fontprop = self.aw.mpl_fontproperties.copy()
                        fontprop.set_size(self.wheeltextsize[z])
                        anno = self.ax2.annotate(names[z][count],xy=(textloc[z][count],Wradiitext[z]),xytext=(textloc[z][count],Wradiitext[z]),
                            rotation=textangles[z][count],
                            horizontalalignment='center',
                            verticalalignment='center',
                            color=self.wheeltextcolor,
                            fontproperties=fontprop)
                        try:
                            anno.set_in_layout(False)  # remove text annotations from tight_layout calculation
                        except Exception: # pylint: disable=broad-except # mpl before v3.0 do not have this set_in_layout() function
                            pass
                        count += 1
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    self.fig.canvas.draw()

        except ValueError as e:
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Value Error:') + ' drawWheel() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
            return

        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            _, _, exc_tb = sys.exc_info()
            self.adderror((QApplication.translate('Error Message', 'Exception:') + ' drawWheel() {0}').format(str(e)),getattr(exc_tb, 'tb_lineno', '?'))
            return

    def makewheelcolorpattern(self):
        for wc in self.wheelcolor:
            wlen = len(wc)
            for i in range(wlen):
                color = QColor()
                color.setHsv(int(round((360/wlen)*i*self.wheelcolorpattern)),255,255,255)
                wc[i] = str(color.name())

    # sets parent and corrects segment lengths so that child fits inside parent (multiple children can be set to same parent)
    # input: z = index of parent in previous wheel    # wn = wheel number    # idx = index of element in wheel x
    def setwheelchild(self,z,wn,idx):
        #set same start angle
        self.startangle[wn] = self.startangle[wn-1]
        self.wheellabelparent[wn][idx] = z

        #adjust lengths
        for x in range(1,len(self.segmentlengths)):
            nsegments = len(self.segmentlengths[x])
            parentanglecount:float = 0
            for i in range(nsegments):
                if self.wheellabelparent[x][i]:                                                   #if parent selected (otherwise 0)
                    parentindex = self.wheellabelparent[x][i]                                     #parent index
                    if self.wheellabelparent[x][i] == parentindex:                                #if match
                        parentangle = self.segmentlengths[x-1][self.wheellabelparent[x][i]-1]     #find parent angle (in %)
                        #find number of labels with same parent
                        count = self.wheellabelparent[x].count(parentindex)                       #count number of labels with same parent
                        self.segmentlengths[x][i] = parentangle/count                             #divide parent angle between children

                        #calculate last total angle
                        if i < nsegments-1:
                            parentanglecount += self.segmentlengths[x][i]

                        #adjust rest of angles to get 100 % coverage
                        for a in range(i+1,nsegments):
                            self.segmentlengths[x][a] = (100-parentanglecount)/(nsegments-(i+1))

#############################     MOUSE CROSS     #############################

    def togglecrosslines(self):
        if not self.crossmarker and not self.designerflag and not self.flagstart:  #if not projection flag
            #turn ON
            self.l_horizontalcrossline = None
            self.l_verticalcrossline = None
            self.updateBackground() # update bitlblit backgrounds
            self.crossmarker = True
            message = QApplication.translate('Message', 'Mouse Cross ON: move mouse around')
            self.aw.sendmessage(message)
            self.crossmouseid = self.fig.canvas.mpl_connect('motion_notify_event', self.drawcross)
            self.onreleaseid = self.fig.canvas.mpl_connect('button_release_event', self.onrelease)  #mouse cross lines measurement
        else:
            #turn OFF
            self.crossmarker = False
            if self.crossmouseid is not None:
                try:
                    self.fig.canvas.mpl_disconnect(self.crossmouseid)
                except Exception: # pylint: disable=broad-except
                    pass
            if self.onreleaseid is not None:
                try:
                    self.fig.canvas.mpl_disconnect(self.onreleaseid)  #mouse cross lines measurement
                except Exception: # pylint: disable=broad-except
                    pass
            try:
                if self.ax is not None:
                    self.ax.lines.remove(self.l_horizontalcrossline)
            except Exception: # pylint: disable=broad-except
                pass
            self.l_horizontalcrossline = None
            try:
                if self.ax is not None:
                    self.ax.lines.remove(self.l_verticalcrossline)
            except Exception: # pylint: disable=broad-except
                pass
            self.l_verticalcrossline = None
            self.resetlines()
            message = QApplication.translate('Message', 'Mouse cross OFF')
            self.aw.sendmessage(message)
            self.updateBackground() # update bitlblit backgrounds

    def drawcross(self,event):
        # do not interleave with redraw()
        gotlock = self.profileDataSemaphore.tryAcquire(1,0)
        if not gotlock:
            _log.info('drawcross(): failed to get profileDataSemaphore lock')
        else:
            try:
                if self.ax is not None and event.inaxes == self.ax:
                    x = event.xdata
                    y = event.ydata
                    if self.delta_ax is not None and self.baseX and self.baseY:
                        deltaX = stringfromseconds(event.xdata - self.baseX)
                        deltaY = str(self.aw.float2float(event.ydata - self.baseY,1))
                        RoR = str(self.aw.float2float(60 * (event.ydata - self.baseY) / (event.xdata - self.baseX),1))
                        deltaRoR = (self.delta_ax.transData.inverted().transform((0,self.ax.transData.transform((0,event.ydata))[1]))[1]
                                    - self.delta_ax.transData.inverted().transform((0,self.ax.transData.transform((0,self.baseY))[1]))[1])
                        #RoRoR is always in C/min/min
                        if self.mode == 'F':
                            deltaRoR = RoRfromFtoC(deltaRoR)
                        RoRoR = str(self.aw.float2float(60 * (deltaRoR)/(event.xdata - self.baseX),1))
                        message = f'delta Time= {deltaX},    delta Temp= {deltaY} {self.mode},    RoR= {RoR} {self.mode}/min,    RoRoR= {RoRoR} C/min/min'
                        self.aw.sendmessage(message)
                        self.base_messagevisible = True
                    elif self.base_messagevisible:
                        self.aw.clearMessageLine()
                        self.base_messagevisible = False
                    if x and y:
                        if self.l_horizontalcrossline is None:
                            self.l_horizontalcrossline = self.ax.axhline(y,color = self.palette['text'], linestyle = '-', linewidth= .5, alpha = 1.0,sketch_params=None,path_effects=[])
                        else:
                            self.l_horizontalcrossline.set_ydata(y)
                        if self.l_verticalcrossline is None:
                            self.l_verticalcrossline = self.ax.axvline(x,color = self.palette['text'], linestyle = '-', linewidth= .5, alpha = 1.0,sketch_params=None,path_effects=[])
                        else:
                            self.l_verticalcrossline.set_xdata(x)
                        if self.ax_background:
                            self.fig.canvas.restore_region(self.ax_background)
                            self.ax.draw_artist(self.l_horizontalcrossline)
                            self.ax.draw_artist(self.l_verticalcrossline)
                            if self.base_horizontalcrossline and self.base_verticalcrossline:
                                self.ax.draw_artist(self.base_horizontalcrossline)
                                self.ax.draw_artist(self.base_verticalcrossline)
                            try:
                                self.fig.canvas.blit(self.ax.get_tightbbox(self.fig.canvas.get_renderer()))
                            except Exception: # pylint: disable=broad-except
                                pass
                        else:
                            self.updateBackground()
            finally:
                if self.profileDataSemaphore.available() < 1:
                    self.profileDataSemaphore.release(1)

    def __to_ascii(self, s:str) -> str:
        utf8_string = str(s)
        if self.locale_str.startswith('de'):
            for k, uml in self.umlaute_dict.items():
                utf8_string = utf8_string.replace(k, uml)
        from unidecode import unidecode
        return unidecode(utf8_string)



########################################################################################
###     Sample thread
########################################################################################

class SampleThread(QThread): # pyright: ignore # Argument to class must be a base class (reportGeneralTypeIssues)
    sample_processingSignal = pyqtSignal(bool,list,list,list)

    def __init__(self, aw:'ApplicationWindow') -> None:
        super().__init__()

        self.aw = aw

        if str(platform.system()).startswith('Windows'):
            self.accurate_delay_cutoff = 10e-3
        else:
            self.accurate_delay_cutoff = 5e-3

    def sample_main_device(self):
        #read time, ET (t1) and BT (t2) TEMPERATURE
        try:
            if self.aw.simulator is None:
                tx,t1,t2 = self.aw.ser.devicefunctionlist[self.aw.qmc.device]() # Note that not all device functions feature the force parameter!!
                if self.aw.qmc.swapETBT:
                    return tx,float(t2),float(t1)
                return tx,float(t1),float(t2)
            tx = self.aw.qmc.timeclock.elapsedMilli()
            t1,t2 = self.aw.simulator.read(tx if self.aw.qmc.flagstart else 0)
            return tx,float(t1),float(t2)
        except Exception as e: # pylint: disable=broad-except
            _log.exception(e)
            tx = self.aw.qmc.timeclock.elapsedMilli()
            return tx,-1.0,-1.0

    def sample_extra_device(self, i):
        try:
            if self.aw.simulator is None or self.aw.qmc.extradevices[i] == 22: # the PID SV/DUTY we show from the computed readings
                tx,t1,t2 = self.aw.extraser[i].devicefunctionlist[self.aw.qmc.extradevices[i]]()
            else:
                tx = self.aw.qmc.timeclock.elapsedMilli()
                t1,t2 = self.aw.simulator.readextra(i,(tx if self.aw.qmc.flagstart else 0))
            return tx,float(t1),float(t2)
        except Exception: # pylint: disable=broad-except
#            _log.exception(e)
            tx = self.aw.qmc.timeclock.elapsedMilli()
            return tx,-1.0,-1.0

    # fetch the raw samples from the main and all extra devices once per interval
    def sample(self):
        gotlock = self.aw.qmc.samplingSemaphore.tryAcquire(1,0) # we try to catch a lock if available but we do not wait, if we fail we just skip this sampling round (prevents stacking of waiting calls)
        if not gotlock:
            _log.info('sample(): failed to get samplingSemaphore lock')
        else:
            temp1_readings = []
            temp2_readings = []
            timex_readings = []
            try:
                if self.aw.qmc.device != 18 or self.aw.simulator is not None: # not NONE device
                    ##### send sampling action if any interval is set to "sync" (extra_event_sampling_delay = 0)
                    try:
                        if self.aw.qmc.extra_event_sampling_delay == 0 and self.aw.qmc.extrabuttonactions[2]:
                            _log.debug('sync samplingAction()')
                            self.aw.eventactionx(self.aw.qmc.extrabuttonactions[2],self.aw.qmc.extrabuttonactionstrings[2])
                    except Exception as e: # pylint: disable=broad-except
                        _log.exception(e)

                    #### first retrieve readings from the main device
#                    timeBeforeETBT = libtime.perf_counter() # the time before sending the request to the main device
#                    #read time, ET (t1) and BT (t2) TEMPERATURE
#                    tx_org,t1,t2 = self.sample_main_device()
#                    etbt_time = libtime.perf_counter() - timeBeforeETBT
#                    tx = tx_org + (etbt_time / 2.0) # we take the average between before and after
# instead of estimating the real time of the sample, let the device implementation decide (mostly, the time the request was send should be accurate enough)
                    tx,t1,t2 = self.sample_main_device()
                    #etbt_time = libtime.perf_counter() - timeBeforeETBT
                    temp1_readings.append(t1)
                    temp2_readings.append(t2)
                    timex_readings.append(tx)

                    ##############  if using Extra devices
                    for i in range(len(self.aw.qmc.extradevices)):
                        extratx, extrat2, extrat1 = self.sample_extra_device(i)
                        temp1_readings.append(extrat1)
                        temp2_readings.append(extrat2)
                        timex_readings.append(extratx)
#                    total_time = libtime.perf_counter() - timeBeforeETBT

#                    _log.debug("sample(): ET/BT time => %.4f", etbt_time)
#                    _log.debug("sample(): total time => %.4f", total_time)
            except Exception as e: # pylint: disable=broad-except
                _log.exception(e)
            finally:
                local_flagstart = self.aw.qmc.flagstart # this need to be caught within the samplingSemaphore and forwarded to the sample_processing()
                if self.aw.qmc.samplingSemaphore.available() < 1:
                    self.aw.qmc.samplingSemaphore.release(1)
                self.sample_processingSignal.emit(local_flagstart, temp1_readings, temp2_readings, timex_readings)


    # libtime.sleep is accurate only up to 0-5ms
    # using a hyprid approach using sleep() and busy-wait based on the time.perf_counter()
    def accurate_delay(self, delay):
        ''' Function to provide accurate time delay in seconds
        '''
        _ = libtime.perf_counter() + delay
        # use the standard sleep until one 5ms before the timeout (Windows <10 might need a limit of 5.5ms)
        if delay > self.accurate_delay_cutoff:
            libtime.sleep(delay - self.accurate_delay_cutoff)
        # continuous with a busy sleep
        while libtime.perf_counter() < _:
            pass # this raises CPU to 100%
#            libtime.sleep(1/100000) # this is a compromise with increased accuracy vs time.sleep() avoiding a 100% CPU load

    def run(self):
        pool = None
        try:
            self.aw.qmc.flagsamplingthreadrunning = True
            if sys.platform.startswith('darwin'):
                from Foundation import NSAutoreleasePool # type: ignore # @UnresolvedImport  # pylint: disable=import-error,no-name-in-module
                pool = NSAutoreleasePool.alloc().init()  # @UndefinedVariable # pylint: disable=maybe-no-member # noqa: F841
            self.aw.qmc.afterTP = False
            if not self.aw.qmc.flagon:
                return

            # initialize digitizer
            self.aw.lastdigitizedvalue = [None,None,None,None] # last digitized value per quantifier
            self.aw.lastdigitizedtemp = [None,None,None,None] # last digitized temp value per quantifier

            interval = self.aw.qmc.delay/self.aw.qmc.timeclock.getBase()
            next_time:Optional[float] = None
            while True:
                if self.aw.qmc.flagon:
                    if next_time is None:
                        next_time = libtime.perf_counter() + interval
                    else:
                        #libtime.sleep(max(0, next_time - libtime.time())) # sleep is not very accurate
                        self.accurate_delay(max(0, next_time - libtime.perf_counter())) # more accurate, but keeps the CPU busy

                    #_log.info(datetime.datetime.now()) # use this to check for drifts

                    #collect information
                    if self.aw.sample_loop_running and self.aw.qmc.flagon:
                        try:
                            self.aw.qmc.flagsampling = True # we signal that we are sampling
                            self.sample()
                        finally:
                            self.aw.qmc.flagsampling = False # we signal that we are done with sampling
                else:
                    self.aw.qmc.flagsampling = False # type: ignore # mypy: Statement is unreachable  [unreachable] # we signal that we are done with sampling
                    try:
                        if self.aw.ser.SP.is_open:
                            self.aw.ser.closeport()
                        QApplication.processEvents()
                    except Exception: # pylint: disable=broad-except
                        pass
                    self.quit()
                    break  #thread ends
                # skip tasks if we are behind schedule:
                next_time += (libtime.perf_counter() - next_time) // interval * interval + interval
        finally:
            self.aw.qmc.flagsampling = False # we signal that we are done with sampling
            self.aw.qmc.flagsamplingthreadrunning = False
            if sys.platform.startswith('darwin'):
                # disable undefined variable warning:
                del pool # pylint: disable=E0602


#########################################################################################################
###     Artisan thread Server
#########################################################################################################

class Athreadserver(QWidget): # pylint: disable=too-few-public-methods # pyright: ignore # Argument to class must be a base class (reportGeneralTypeIssues)
    def __init__(self, aw:'ApplicationWindow') -> None:
        super().__init__()
        self.aw = aw

    def createSampleThread(self):
        if self.aw is not None and not self.aw.qmc.flagsamplingthreadrunning: # we only start a new sampling thread if none is running yet
            sthread = SampleThread(self.aw)

            #connect graphics to GUI thread
            sthread.sample_processingSignal.connect(self.aw.qmc.sample_processing)
            sthread.start(QThread.Priority.TimeCriticalPriority) # TimeCriticalPriority > HighestPriority > HighPriority > NormalPriority > LowPriority
            sthread.wait(300)    #needed in some Win OS
