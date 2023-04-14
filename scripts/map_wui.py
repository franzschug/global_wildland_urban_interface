import os
import sys
import numpy as np
from osgeo import gdal

#
# Developed under: Python 3.8.10

# Author: Franz Schug (fschug@wisc.edu)
# Date:   March 2023
# Corresponding publication: in review
# 
# Description:  This script creates a Wildland-Urban Interface (WUI) map based on a set of building density and land cover data using threshold criteria.
#               See Schug et al. (in reveiw) for details.
#               This code uses data organized in an EQUI7 grid and tiling scheme (Bauer-Maschallinger et al. 2014).
#
# Parameters :  region  String              - region according to the EQUI7 grid (AF, AS, EU, NA, OC, SA)
#               tile    String              - tile (X0xxx_Y0xxx) according to the EQUI7 tiling scheme
# Output     :  raster  Byte / GeoTiff      - map of nine WUI and non-WUI classes:
#                                               0 - water
#                                               1 - WUI Intermix (dominant forest/shrubland/wetland)
#                                               2 - WUI Interface (dominant forest/shrubland/wetland)
#                                               3 - WUI Intermix (dominant grassland)
#                                               4 - WUI Interface (dominant grassland)
#                                               5 - non-WUI, wildland vegetation (forest/shrubland/wetland)
#                                               6 - non-WUI, wildland vegetation (grassland)
#                                               7 - non-WUI, dense built-up / urban
#                                               8 - non-WUI, other land cover (e.g., dominant agriculture)
                                                
# Example of Usage: python3 /directory/map_wui.py NA X0062_Y0061
#

### Read region and tile parameter
region = str(sys.argv[1]).split(" ")[0]
tile = str(sys.argv[2]).split(" ")[0]

### Set paths to all input data

# mean building density in a 500 m radius
bldDensityPath = "/dir/bldDensity/" + region + "/" + tile + "/bldDensity_500.tif"

# mean wildland vegetation cover (all classes) in a 500 m radius
wildVegPath = "/dir/landcover/" + region + "/" + tile + "/allWildVeg_500.tif"

# mean wildland vegetation cover (forest/shrubland/wetland only) in a 500 m radius
fswVegPath = "/dir/landcover/" + region + "/" + tile + "/fswWildVeg_500.tif"

# water mask
waterPath = "/dir/water/" + region + "/" + tile + "/water.tif"
wcPath = "data/landcover/" + region + "/" + tile + "/worldcover.tif"

# buffered large vegetation patches
bufferedPath = "/dir/landcover/" + region + "/" + tile + "/bufferedVeg_2400.tif"

# buffered large vegetation patches (only forest/shrubland/grassland)
bufferedFSWPath = "/dir/landcover/" + region + "/" + tile + "/bufferedFSWVeg_2400.tif"


### Set out directory and path
outDir = "/dir/wui/" + region + "/" + tile
outPath = outDir + "/WUI.tif"


### Load datasets
driver = gdal.GetDriverByName("GTiff")

bldDensityRaster = gdal.Open(bldDensityPath)
bldDensity = bldDensityRaster.ReadAsArray()

wildVegetation = gdal.Open(wildVegPath).ReadAsArray()
fswWildVegetation = gdal.Open(fswVegPath).ReadAsArray()

grassWildVegetation = wildVegetation - fswWildVegetation

bufferedVegPath = gdal.Open(bufferedPath).ReadAsArray()

fswVegetationBuffer = gdal.Open(bufferedFSWPath).ReadAsArray()


### Workflow
# pixel qualifies as WUI because building density > 0.5% 
bldThreshold = (bldDensity > 0.5)

# pixel qualifies as WUI intermix because wildland vegetation cover > 50% (3922 = 0.5 * sum(area) when area = 7845 pixels in 500 m radius, pixel resolution 10 m)
# vegetation cannot be > 50% when building density is > 50%
wildVegTreshold = (wildVegetation > 3922) * (bldDensity < 50)

# pixel potentially qualifies as WUI interface when wildland vegetation cover < 50%
invWildVegTreshold = (wildVegetation <= 3922)

# pixel potentially qualifies as WUI interface when buffered wildland patch rater is 1 (i.e., pixel is within the 2.4 km buffer of a large wildland patch)
proximityToWildPatch = (bufferedVegPath == 1)

# identify araes where the proximity to forest/shrubland/wetland patches alone is not given (i.e., cannot form interface)
proximityToWildPatchThroughGrass = (fswVegetationBuffer == 0)

# pixel is intermix when building density > 0.5% and wildland vegetation cover > 50%
intermix = bldThreshold * wildVegTreshold

# pixel is interface when building density > 0.5%, wildland vegetation cover < 50%, and pixel close to a large wild vegetation patch
interface = bldThreshold * invWildVegTreshold * proximityToWildPatch

# pixel is grassland interface if the distance to large vegetation patch criterium is only met because of a grassland patch
grassInterfaceThroughGrass = bldThreshold * invWildVegTreshold * proximityToWildPatchThroughGrass * proximityToWildPatch

# if a pixel is densely built-up, it has an urban structure and cannot be intermix
urbanIntermix = (intermix > 0) * (bldDensity > 15)

# if an urban intermix pixel meets the criteria for interface, it is overwritten with interface
urbanInterface = bldThreshold * urbanIntermix * proximityToWildPatch

# it is a grassland interface if the distance to large vegetation patch criterium is only met because of a grassland patch
urbanInterfaceThroughGrass = bldThreshold * urbanIntermix * proximityToWildPatchThroughGrass * proximityToWildPatch


# Classify
dominantFSW = (grassWildVegetation <= fswWildVegetation)
dominantGrass = (grassWildVegetation > fswWildVegetation)

outArray = np.zeros([10000, 10000])
outArray[intermix * dominantFSW] = 1        # forest/shrubland/wetland-dominated intermix
outArray[interface] = 2                     # interface
outArray[intermix * dominantGrass] = 3      # grassland-dominated intermix
outArray[grassInterfaceThroughGrass] = 4    # interface that only forms because of a grassland patch
outArray[urbanIntermix] = 7                 # built-up-dominated area that meets all intermix criteria (eventuall non-WUI)
outArray[urbanInterface] = 2                # built-up-dominated area that meets all intermix criteria and meets interface criteria
outArray[urbanInterfaceThroughGrass] = 4    # built-up-dominated area that meets all intermix criteria and meets interface criteria because of a grassland patch

# Where WUI criteria are met, classify non-WUI classes
isGreen = (outArray == 0) * wildVegTreshold * dominantFSW                   # forest/shrubland/wetland-dominated non-WUI
isYellow = (outArray == 0) * wildVegTreshold * dominantGrass                # grassland-dominated non-WUI
isRed = (outArray == 0) * (bldDensity > 15)                                 # built-up-dominated non-WUI
isGrey = (outArray == 0) * (isGreen == 0) * (isYellow == 0) * (isRed == 0)  # other non-WUI

outArray[isGreen] = 5       # forest/shrubland/wetland-dominated non-WUI
outArray[isYellow] = 6      # grassland-dominated non-WUI
outArray[isRed] = 7         # built-up-dominated non-WUI
outArray[isGrey] = 8        # other non-WUI


### Apply final water mask
waterMask = gdal.Open(waterPath).ReadAsArray()
outArray[waterMask > 20] = 0

wcMask = gdal.Open(wcPath).ReadAsArray()
outArray[wcMask == 80] = 0
outArray[wcMask == 255] = 0

### Write output
if not os.path.exists(outDir):
    os.makedirs(outDir)
	
dimensions = [1, 10000, 10000]
createoptions = ['COMPRESS=LZW']
outRasterWUI = driver.Create(outPath, dimensions[1], dimensions[2], dimensions[0], gdal.GDT_Byte, options = createoptions)
outRasterWUI.SetGeoTransform(bldDensityRaster.GetGeoTransform())
outRasterWUI.SetProjection(bldDensityRaster.GetProjection())

outband = outRasterWUI.GetRasterBand(1)
outband.SetNoDataValue(255)
outband.WriteArray(outArray)
outband.FlushCache()