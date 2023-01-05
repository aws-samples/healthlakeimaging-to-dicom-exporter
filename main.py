"""
HLI-to-DICOM application entrypoint. Contains the business logic to iterate through all the instances of the DICOM study to be exported.

SPDX-License-Identifier: MIT-0
"""

import array
import pydicom
from pydicom.sequence import Sequence
from pydicom import Dataset , DataElement 
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import UID
import json
import logging
import boto3
from openjpeg import decode
import io
import sys
import time
import os
import collections
from threading import Thread
from time import sleep
from HLIFrameFetcher import *
from HLIDataDICOMizer import *
import getopt, sys
import PIL
from PIL import Image
import gzip



HLIFrameFetcherThreadList = []
ImageFrames = collections.deque()

logging.basicConfig( level="INFO" )

def main():
    datastoreId=None
    studyId=None
    ThreadCount = 20
    argumentList = sys.argv[1:]
    short_options = "d:s:t:"
    long_options = ["datastoreId", "studyId", "series"]
    try:
        arguments, values = getopt.getopt(argumentList, short_options, long_options)
        # checking each argument
        for currentArgument, currentValue in arguments:
            if currentArgument in ("-s", "--studyId"):
                studyId=currentValue             
            elif currentArgument in ("-d", "--datastoreId"):
                datastoreId = currentValue    
            elif currentArgument in ("-t", "--thread"):
                ThreadCount = int(currentValue)                       
    except getopt.error as err:
        # output error, and return with an error code
        print(str(err))
    if ((datastoreId is None ) or (studyId is None)):
        print("DatstoreId (-d or --datastoreId) and studyId (-s or --studyId) must be provided.") 
        return
    for x in range(ThreadCount):
        logging.warning("[ServiceInit] - HLIFrameFetcher thread # "+str(x))
        HLIFrameFetcherThreadList.append(HLIFrameFetcher(str(x)))
    starttime = time.time()
    client = boto3.client('medical-imaging')
    print(datastoreId)
    print(studyId)
    hli_metadata = hliGetMetadata(datastoreId,studyId,client) 
    seriesList = getSeriesList(hli_metadata)
    for series in seriesList:
        ImageFrames.extendleft(getImageFrames(datastoreId, studyId , hli_metadata , series["SeriesInstanceUID"])) 
    ImageFrameCount = len(ImageFrames)  
    threadId = 0
    while(len(ImageFrames)> 0):
        HLIFrameFetcherThreadList[threadId].AddFetchJob(ImageFrames.popleft())
        threadId+=1
        if threadId == ThreadCount :
            threadId = 0  
    dicomizedCount = 0
    while(dicomizedCount < (ImageFrameCount)):
        for x in range(ThreadCount):
            entry=HLIFrameFetcherThreadList[x].getFramesFetched()
            if entry is not None:
                cd = HLIDataDICOMizer(hli_metadata , entry)
                ds = cd.getDataset()
                os.makedirs( f"./out/{studyId}" , mode=0o775, exist_ok=True )
                ds.save_as(f"./out/{studyId}/{entry['SOPInstanceUID']}.dcm", write_like_original=False)
                invert = False
                if 'PhotometricInterpretation' in ds and ds.PhotometricInterpretation == "MONOCHROME1": #
                    invert=True
                saveAsPngPIL(ds , f"./out/{studyId}/{entry['SOPInstanceUID']}.png", invert=invert )
                dicomizedCount+=1      
    for x in range(ThreadCount):
        HLIFrameFetcherThreadList[x].Dispose()
    endtime = time.time()
    print( f"{dicomizedCount} instances exported in {endtime - starttime} seconds")

def getImageFrames(datastoreId, studyId , hli_metadata , seriesUid) -> collections.deque:
    instancesList = []
    for instances in hli_metadata["Study"]["Series"][seriesUid]["Instances"]:
        if len(hli_metadata["Study"]["Series"][seriesUid]["Instances"][instances]["ImageFrames"]) < 1:
            print("Skipping the following instances because they do not contain ImageFrames: " + instances)
            continue
        try:        
            frameId = hli_metadata["Study"]["Series"][seriesUid]["Instances"][instances]["ImageFrames"][0]["ID"]
            InstanceNumber = hli_metadata["Study"]["Series"][seriesUid]["Instances"][instances]["DICOM"]["InstanceNumber"]
            instancesList.append( { "datastoreId" : datastoreId, "studyId" : studyId , "frameId" : frameId , "SeriesUID" : seriesUid , "SOPInstanceUID" : instances,  "InstanceNumber" : InstanceNumber , "PixelData" : None})
        except Exception as e: # The code above failes for 
            print(e)
    instancesList.sort(key=getInstanceNumber)
    return collections.deque(instancesList)

def getSeriesList(hli_metadata):
    seriesList = []
    for series in hli_metadata["Study"]["Series"]:
        SeriesNumber = hli_metadata["Study"]["Series"][series]["DICOM"]["SeriesNumber"] 
        Modality = hli_metadata["Study"]["Series"][series]["DICOM"]["Modality"] 
        try: # This is a non-mandatory tag
            SeriesDescription = hli_metadata["Study"]["Series"][series]["DICOM"]["SeriesDescription"]
        except:
            SeriesDescription = ""
        SeriesInstanceUID = series
        seriesList.append({ "SeriesNumber" : SeriesNumber , "Modality" : Modality ,  "SeriesDescription" : SeriesDescription , "SeriesInstanceUID" : SeriesInstanceUID})
    return seriesList

def hliGetMetadata(datastoreId, studyId , client):
    start_time = time.time()
    hli_study_metadata = client.get_image_set_metadata(datastoreId=datastoreId , imageSetId=studyId)
    json_study_metadata = gzip.decompress(hli_study_metadata["imageSetMetadataBlob"].read())
    json_study_metadata = json.loads(json_study_metadata)
    end_time = time.time()  
    print(f"Metadata fetch : {end_time-start_time}")    
    return json_study_metadata

def getInstanceNumber(elem):
    return int(elem["InstanceNumber"])

def saveAsPngPIL(ds: Dataset , destination : str ,  invert : bool =  False):
    import numpy as np
    shape = ds.pixel_array.shape
    image_2d = ds.pixel_array.astype(float)
    image_2d_scaled = (np.maximum(image_2d,0) / image_2d.max()) * 255.0
    image_2d_scaled = np.uint8(image_2d_scaled)
    if invert == True:
        image_2d_scaled = np.max(image_2d_scaled) - image_2d_scaled
    img = Image.fromarray(image_2d_scaled)
    img.save(destination, 'png')

if __name__ == "__main__":
    main()

