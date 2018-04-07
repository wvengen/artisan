#!/bin/sh

set -ex
sudo apt-get update
sudo apt-get install p7zip-full libglib2.0-dev zlib1g-dev

curl -L -O https://download.qemu.org/qemu-2.11.1.tar.xz
tar xvJf qemu-2.11.1.tar.xz
cd qemu-2.11.1
./configure
make
sudo make install
cd ..
