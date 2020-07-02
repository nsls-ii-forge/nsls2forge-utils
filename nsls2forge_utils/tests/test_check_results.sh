#!/bin/bash

echo "BEGINNING check-results TESTS"

# set conda source
source ~/mc/etc/profile.d/conda.sh

# test for default behavior (no packages installed)
conda create --name df -y
conda activate df
conda install -c defaults pip -y
pip install .
conda list --show-channel-url
check-results -t channels
EXIT="$?"
if [ "$EXIT" -gt "0" ]; then
  echo "ERROR: default behavior test failed with exit code $EXIT"
  exit 1
fi

# test for default channel behavior
conda install -c defaults numpy -y
conda list --show-channel-url
check-results -t channels -f conda-forge
EXIT="$?"
if [ "$EXIT" -gt "0" ]; then
  echo "ERROR: default channel test failed with exit code $EXIT"
  exit 1
fi
conda deactivate

# tests for conda-forge channel + ignore
conda create --name cf -y
conda activate cf
FORBIDDEN_NAME="conda-forge"
conda install -c $FORBIDDEN_NAME --override-channels pip -y
pip install .
conda list --show-channel-url
check-results -t channels -f $FORBIDDEN_NAME
EXIT="$?"
if [ "$EXIT" -eq "0" ]; then
  echo "ERROR: forbidden channel $FORBIDDEN_NAME raise error test failed with exit code $EXIT"
  exit 1
fi

check-results -t channels -f $FORBIDDEN_NAME -i
EXIT="$?"
if [ "$EXIT" -gt "0" ]; then
  echo "ERROR: ignore forbidden channel $FORBIDDEN_NAME test failed with exit code $EXIT"
  exit 1
fi

echo "SUCCESS: ALL TESTS PASSED"
conda deactivate
