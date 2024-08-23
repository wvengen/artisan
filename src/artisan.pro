# The project file for the Artisan application.
#
# LICENSE
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 2 of the License, or
# version 3 of the License, or (at your option) any later version. It is
# provided for educational purposes and is distributed in the hope that
# it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
# the GNU General Public License for more details.
#
# This file is part of Artisan.

# not sure if the following is strictly needed (might be needed for accent characters in source of translations)
CODECFORSRC = UTF-8
CODECFORTR = UTF-8

SOURCES = \
    artisanlib/alarms.py \
    artisanlib/autosave.py \
    artisanlib/axis.py \
    artisanlib/background.py \
    artisanlib/batches.py \
    artisanlib/calculator.py \
    artisanlib/canvas.py \
    artisanlib/colors.py \
    artisanlib/comm.py \
    artisanlib/comparator.py \
    artisanlib/cropster.py \
    artisanlib/cup_profile.py \
    artisanlib/curves.py \
    artisanlib/designer.py \
    artisanlib/devices.py \
    artisanlib/dialogs.py \
    artisanlib/events.py \
    artisanlib/giesen.py \
    artisanlib/ikawa.py \
    artisanlib/large_lcds.py \
    artisanlib/logs.py \
    artisanlib/loring.py \
    artisanlib/main.py \
    artisanlib/modbusport.py \
    artisanlib/petroncini.py \
    artisanlib/phases.py \
    artisanlib/phases_canvas.py \
    artisanlib/pid_control.py \
    artisanlib/pid_dialogs.py \
    artisanlib/platformdlg.py \
    artisanlib/ports.py \
    artisanlib/roast_properties.py \
    artisanlib/rubasse.py \
    artisanlib/s7port.py \
    artisanlib/sampling.py \
    artisanlib/statistics.py \
    artisanlib/transposer.py \
    artisanlib/wheels.py \
    artisanlib/wsport.py \
    artisanlib/help/alarms_help.py \
    artisanlib/help/autosave_help.py \
    artisanlib/help/energy_help.py \
    artisanlib/help/eventannotations_help.py \
    artisanlib/help/eventbuttons_help.py \
    artisanlib/help/eventsliders_help.py \
    artisanlib/help/keyboardshortcuts_help.py \
    artisanlib/help/modbus_help.py \
    artisanlib/help/programs_help.py \
    artisanlib/help/s7_help.py \
    artisanlib/help/symbolic_help.py \
    artisanlib/help/transposer_help.py \
    artisanlib/plus/blend.py \
    artisanlib/plus/controller.py \
    artisanlib/plus/countries.py \
    artisanlib/plus/login.py \
    artisanlib/plus/queue.py \
    artisanlib/plus/schedule.py \
    artisanlib/plus/stock.py \
    artisanlib/plus/sync.py

# the list of translation has to be synced with the script pylupdate6pro (for pylupdate6)
TRANSLATIONS = \
	translations/artisan_ar.ts \
	translations/artisan_da.ts \
	translations/artisan_de.ts \
	translations/artisan_el.ts \
	translations/artisan_es.ts \
	translations/artisan_fa.ts \
	translations/artisan_fi.ts \
	translations/artisan_fr.ts \
	translations/artisan_gd.ts \
	translations/artisan_he.ts \
	translations/artisan_hu.ts \
	translations/artisan_id.ts \
	translations/artisan_it.ts \
	translations/artisan_ja.ts \
	translations/artisan_ko.ts \
	translations/artisan_lv.ts \
	translations/artisan_nl.ts \
	translations/artisan_no.ts \
	translations/artisan_pl.ts \
	translations/artisan_pt_BR.ts \
	translations/artisan_pt.ts \
	translations/artisan_ru.ts \
	translations/artisan_sk.ts \
	translations/artisan_sv.ts \
	translations/artisan_th.ts \
	translations/artisan_tr.ts \
	translations/artisan_uk.ts \
	translations/artisan_vi.ts \
	translations/artisan_zh_CN.ts \
	translations/artisan_zh_TW.ts
