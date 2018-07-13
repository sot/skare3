#!/bin/bash
./configure --prefix=${PREFIX} --with-ssl-dir=${PREFIX}/lib
make
make install

