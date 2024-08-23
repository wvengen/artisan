@echo off
:: ABOUT
:: Windows CI build file for Artisan
::
:: LICENSE
:: This program or module is free software: you can redistribute it and/or
:: modify it under the terms of the GNU General Public License as published
:: by the Free Software Foundation, either version 2 of the License, or
:: version 3 of the License, or (at your option) any later versison. It is
:: provided for educational purposes and is distributed in the hope that
:: it will be useful, but WITHOUT ANY WARRANTY; without even the implied
:: warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
:: the GNU General Public License for more details.
::
:: AUTHOR
:: Dave Baxter, Marko Luther 2023

:: on entry to this script the current path must be the src folder
::

:: ----------------------------------------------------------------------
setlocal enabledelayedexpansion
if /i "%APPVEYOR%" NEQ "True" (
    echo This file is for use on Appveyor CI only.
    exit /b 1
)
if /i "%ARTISAN_LEGACY%" NEQ "True" (
    set ARTISAN_SPEC=win
) else (
    set ARTISAN_SPEC=win-legacy
)
:: ----------------------------------------------------------------------

python -V

::
:: build derived files
::
echo ""************* build derived files **************"

call build-derived-win.bat
if ERRORLEVEL 1 (echo ** Failed in build-derived-win.bat & exit /b 1) else (echo ** Finished build-dependant-win.bat)

::
:: run pyinstaller and NSIS to generate the install .exe
::
:: set environment variables for version and build
for /f "usebackq delims==" %%a IN (`python -c "import artisanlib; print(artisanlib.__version__)"`) DO (set ARTISAN_VERSION=%%~a)
for /f "usebackq delims==" %%a IN (`python -c "import artisanlib; print(artisanlib.__build__)"`) DO (set ARTISAN_BUILD=%%~a)
::
:: create a version file for pyinstaller
create-version-file version-metadata.yml --outfile version_info-win.txt --version %ARTISAN_VERSION%.%ARTISAN_BUILD%

::
:: run pyinstaller
:: Choose log-level from 'TRACE', 'DEBUG', 'INFO', 'WARN', 'DEPRECATION', 'ERROR', 'FATAL'
echo **** Running pyinstaller
pyinstaller --noconfirm --log-level=WARN artisan-win.spec
if ERRORLEVEL 1 (echo ** Failed in pyinstaller & exit /b 1) else (echo ** Success)

::
:: Don't make assumptions as to where the 'makensis.exe' is - look in the obvious places
if exist "/Program Files (x86)/NSIS/makensis.exe"   set NSIS_EXE="/Program Files (x86)/NSIS/makensis.exe"
if exist "/Program Files/NSIS/makensis.exe"         set NSIS_EXE="/Program Files/NSIS/makensis.exe"
if exist "%ProgramFiles%/NSIS/makensis.exe"         set NSIS_EXE="%ProgramFiles%/NSIS/makensis.exe"
if exist "%ProgramFiles(x86)%/NSIS/makensis.exe"    set NSIS_EXE="%ProgramFiles(x86)%/NSIS/makensis.exe"
::
:: echo the file date since makensis does not have a version command
for %%x in (%NSIS_EXE%) do set NSIS_DATE=%%~tx
echo **** Running NSIS makensis.exe file date %NSIS_DATE%

::
:: run NSIS to build the install .exe file
%NSIS_EXE% /DPRODUCT_VERSION=%ARTISAN_VERSION%.%ARTISAN_BUILD% /DLEGACY=%ARTISAN_LEGACY% setup-install3-pi.nsi
if ERRORLEVEL 1 (echo ** Failed in NSIS & exit /b 1) else (echo ** Success)

::
:: package the installation zip file
::
if /i "%APPVEYOR%" == "True" (
    copy "..\LICENSE" "LICENSE.txt"
    7z a artisan-%ARTISAN_SPEC%-%ARTISAN_VERSION%.zip Setup*.exe LICENSE.txt README.txt
    if ERRORLEVEL 1 (echo ** Failed in 7z zipping the setup files & exit /b 1)
)

::
:: check that the packaged files are above an expected size
::
set file=artisan-%ARTISAN_SPEC%-%ARTISAN_VERSION%.zip
set min_size=170000000
for %%A in (%file%) do set size=%%~zA
if %size% LSS %min_size% (
    echo *** Zip file is smaller than expected
    exit /b 1
) else (
    echo **** Success: %file% is larger than minimum %min_size% bytes
)
