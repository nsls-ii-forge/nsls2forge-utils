#!/bin/bash

# get and install miniconda
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
chmod +x miniconda.sh
./miniconda.sh -b -p ~/mc
source ~/mc/etc/profile.d/conda.sh

# test for defaults channel
conda create --name df
conda activate df
check-results -t channels
if [ $? != 0 ]; then
  echo "ERROR: default channel test failed"
  exit 1
fi

# tests for conda-forge channel + ignore
conda deactivate
conda create --name cf
conda activate cf
conda config --env --add channels conda-forge
conda install -c conda-forge --override-channels pip
check-results -t channels
if [ $? == 0 ]; then
  echo "ERROR: forbidden channel raise error test failed"
  exit 1
fi
check-results -t channels -i
if [ $? != 0 ]; then
  echo "ERROR: ignore forbidden channel test failed"
  exit 1
fi