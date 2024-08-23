#!/bin/bash
# ABOUT
# Generate translation, ui, and help files derived from repository sources
# for Artisan Linux and macOS builds
#
# LICENSE
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 2 of the License, or
# version 3 of the License, or (at your option) any later versison. It is
# provided for educational purposes and is distributed in the hope that
# it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
# the GNU General Public License for more details.
#
# AUTHOR
# Dave Baxter, Marko Luther 2023

echo "build-derived.sh"

# required environment variables...
PYUIC="${PYUIC:-pyuic6}"
PYLUPDATE="${PYLUPDATE:-./pylupdate6pro.py}"
QTTOOLS=qt6-tools;

# Check if an argument was passed
if [ $# != 0 ]; then
    # Check if the argument matches one of the accepted strings
    case "$1" in
        macos|linux)
            # the argument is valid
            ;;
        *)
            echo "Error: invalid argument \"$arg\""
            echo "Argument is invalid: $1. Must be 'macos' or 'linux'"
            exit 1
            ;;
    esac
fi

#
# Generate translation, ui, and help files derived from repository sources
#

# convert help files from .xlsx to .py
echo "************* help files **************"
python3 ../doc/help_dialogs/Script/xlsx_to_artisan_help.py all
if [ $? -ne 0 ]; then exit $?; else echo "** Success"; fi

# ui / uix
echo "************* ui/uic **************"
find ui -iname "*.ui" | while read f
do
    fullfilename=$(basename $f)
    fn=${fullfilename%.*}
    $PYUIC -o uic/${fn}.py -x ui/${fn}.ui
    if [ $? -ne 0 ]; then exit $?; fi
done
echo "** Success"

# translations
echo "************* pylupdate **************"
python3 $PYLUPDATE
if [ $? -ne 0 ]; then exit $?; else echo "** Success"; fi

echo "************* lrelease **************"
echo "*** compiling translations"
if [ -f "$QT_SRC_PATH/bin/lrelease" ]; then
    echo "*** using env QT_SRC_PATH: $QT_SRC_PATH/bin/lrelease"
    $QT_SRC_PATH/bin/lrelease -verbose translations/*.ts
    if [ $? -ne 0 ]; then exit $?; else echo "** Success"; fi
elif [[ $(type -P "$QTTOOLS") ]]; then
    echo "*** using env QTTOOLS: $QTTOOLS"
    $QTTOOLS lrelease -verbose translations/*.ts
    if [ $? -ne 0 ]; then exit $?; else echo "** Success"; fi
else
    echo "Error: $QT_SRC_PATH/bin/lrelease does not exist"
    echo "Error: $QTTOOLS does not exist on the path"
    echo $PATH
    exit 1
fi

if [ $# != 0 ]; then
    # create a zip with the generated files
    echo "************* zip generated files **************"
    echo "** Argument supplied: $1"
    zip -rq ../generated-$1.zip ../doc/help_dialogs/Output_html/ help/ translations/ uic/
    if [ $? -ne 0 ]; then exit $?; else echo "** Success"; fi
fi
#
#  End of generating derived files
#
