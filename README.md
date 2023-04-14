# Mapping the global wildland-urban interface



## 1. System requirements

This code was developed for use on Ubuntu 20.04.5 LTS.
The code was developed using Python 3.8.10 and imports the following external packages: numpy (v. 1.21.6), gdal (v. 3.4.1).
The code was not tested using any other configuration.

## 2. Installation guide

The code can be downloaded and immediately used on any machine that satisfies the system requirements. There is no install time.

## 3. Demo

This repository provides a demo inlcuding all required datasets. 

Run `python3 /directory/map_wui.py NA X0062_Y0061` from the demo directorty to execute the script with the demo tile. The resulting wildland-urban interface map will be saved to the `wui` directory.

The expected runtime is ca. 9 seconds per tile (single-core tested, 2.6 GHz CPU speed).


## 4. Instructions for use
