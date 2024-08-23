#!/bin/sh

set -ex

export LD_LIBRARY_PATH=$LD_LIBTRARY_PATH:/usr/local/lib
export PATH=$PATH:$HOME/.local/bin

if [ ! -z $TRAVIS ]; then
    # Travis environment
    export PYTHON_PATH=/home/travis/virtualenv/python3.8/lib/python3.8/site-packages
    export QT_PATH=$PYTHON_PATH/PyQt5/Qt
elif [ -d /usr/lib/python3/dist-packages/PyQt5 ]; then
    # ARM builds
    export PYTHON_PATH=`python3 -m site --user-site`
    export QT_PATH=/usr/share/qt5
else
    # Other builds
    export PYTHON_PATH=`python3 -m site --user-site`
    export QT_PATH=$PYTHON_PATH/PyQt5/Qt
fi

rm -rf build
rm -rf dist

rm -f libusb-1.0.so.0
if [ -f /lib/x86_64-linux-gnu/libusb-1.0.so.0 ]; then
    ln -s /lib/x86_64-linux-gnu/libusb-1.0.so.0
elif [ -f /lib/arm-linux-gnueabihf/libusb-1.0.so.0 ]; then
    ln -s /lib/arm-linux-gnueabihf/libusb-1.0.so.0
else
    ln -s /usr/lib/libusb-1.0.so.0
fi

# update UI
find ui -iname "*.ui" | while read f
do
    fullfilename=$(basename $f)
    fn=${fullfilename%.*}
    python3 -m PyQt5.uic.pyuic -o uic/${fn}.py --from-imports ui/${fn}.ui
done


pyinstaller -y --log-level=INFO artisan-linux.spec

mv dist/artisan dist/artisan.d
mv dist/artisan.d/* dist
rm -rf dist/artisan.d

# copy translations
mkdir dist/translations


for lan in ar, da, de, en, el, es, fa, fi, fr, gd, he, hu, id, it, ja, ko, lv, nl, no, pl, pt_BR, pt, ru, sk, sv, th, tr, vi, zh_CN, zh_TW;
do
     QTBASE_FILE=$QT_PATH/translations/qtbase_${lan}.qm
     QT_FILE=$QT_PATH/translations/qt_${lan}.qm
     if [ -e ${QTBASE_FILE} ]
          then cp ${QTBASE_FILE} dist/translations
     fi
     if [ -e ${QT_FILE} ]
          then cp ${QT_FILE} dist/translations
     fi
done

cp translations/*.qm dist/translations

# copy data
#cp -R $PYTHON_PATH/matplotlib/mpl-data dist
#rm -rf dist/mpl-data/sample_data
rm -rf dist/matplotlib/sample_data

rm -f dist/libphidget22.so.0

mkdir dist/yoctopuce
mkdir dist/yoctopuce/cdll
cp $PYTHON_PATH/yoctopuce/cdll/*.so dist/yoctopuce/cdll

# copy file icon and other includes
cp artisan-alog.xml dist
cp artisan-alrm.xml dist
cp artisan-apal.xml dist
cp artisan-athm.xml dist
cp artisan-aset.xml dist
cp artisan-wg.xml dist
cp includes/Humor-Sans.ttf dist
cp includes/WenQuanYiZenHei-01.ttf dist
cp includes/WenQuanYiZenHeiMonoMedium.ttf dist
cp includes/SourceHanSansCN-Regular.otf dist
cp includes/SourceHanSansHK-Regular.otf dist
cp includes/SourceHanSansJP-Regular.otf dist
cp includes/SourceHanSansKR-Regular.otf dist
cp includes/SourceHanSansTW-Regular.otf dist
cp includes/dijkstra.ttf dist
cp includes/alarmclock.eot dist
cp includes/alarmclock.svg dist
cp includes/alarmclock.ttf dist
cp includes/alarmclock.woff dist
cp includes/android-chrome-192x192.png dist
cp includes/android-chrome-512x512.png dist
cp includes/apple-touch-icon.png dist
cp includes/browserconfig.xml dist
cp includes/favicon-16x16.png dist
cp includes/favicon-32x32.png dist
cp includes/favicon.ico dist
cp includes/mstile-150x150.png dist
cp includes/safari-pinned-tab.svg dist
cp includes/site.webmanifest dist
cp includes/artisan.tpl dist
cp includes/bigtext.js dist
cp includes/sorttable.js dist
cp includes/report-template.htm dist
cp includes/roast-template.htm dist
cp includes/ranking-template.htm dist
cp includes/jquery-1.11.1.min.js dist
cp includes/logging.yaml dist
cp -R icons dist
cp -R Wheels dist
cp README.txt dist
cp ../LICENSE dist/LICENSE.txt

mkdir dist/Machines
find includes/Machines -name '.*.aset' -exec rm -r {} \;
cp -R includes/Machines/* dist/Machines

mkdir dist/Themes
find includes/Themes -name '.*.athm' -exec rm -r {} \;
cp -R includes/Themes/* dist/Themes

mkdir dist/Icons
find includes/Icons -name '.*.aset' -exec rm -r {} \;
cp -R includes/Icons/* dist/Icons

cp $PYTHON_PATH/yoctopuce/cdll/* dist

cp /usr/lib/libsnap7.so dist

cp README.txt dist
cp ../LICENSE dist/LICENSE.txt

# remove automatically collected libs that might break things on some installations (eg. Ubuntu 16.04)
# so it is better to rely on the system installed once
# see https://github.com/gridsync/gridsync/issues/47 and https://github.com/gridsync/gridsync/issues/43
#   and https://askubuntu.com/questions/575505/glibcxx-3-4-20-not-found-how-to-fix-this-error
#rm -f dist/libdrm.so.2 # https://github.com/gridsync/gridsync/issues/47
#rm -f dist/libX11.so.6 # https://github.com/gridsync/gridsync/issues/43
#rm -f dist/libstdc++.so.6 # https://github.com/gridsync/gridsync/issues/189
# the following libs might not need to be removed
#rm -f dist/libgio-2.0.so.0
#rm -f dist/libz.so.1 # removing this lib seems to break the build on some RPi Buster version
#rm -f dist/libglib-2.0.so.0 # removed for v1.6 and later

#rm -f dist/libusb-1.0.so.0
