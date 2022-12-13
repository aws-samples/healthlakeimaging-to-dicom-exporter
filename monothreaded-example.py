"""
HLI-toDICOM application entrypoint. Contains the business logic to iterate through all the instances of the DICOM study to be exported.

SPDX-License-Identifier: MIT-0
"""
import getopt
import pydicom
from pydicom.sequence import Sequence
from pydicom import Dataset , DataElement 
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import UID
from pydicom.pixel_data_handlers.util import convert_color_space , apply_color_lut
import json
import logging 
import boto3
from openjpeg import decode
import io
import sys
import time
import os
from PIL import Image
import gzip
import base64 

logging.basicConfig( level="INFO" )
ThreadCount = 10
HLIFrameFetcherThreadList = []

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
    client = boto3.client('medical-imaging')
    logging.info("Reading the JSON metadata file")
    json_dicom_header = hliGetMetadata(datastoreId , studyId , client )
    logging.info("Parsing the Header Tags.")  
    ds = Dataset()
    vrlist = [] 
    file_meta = FileMetaDataset()
    ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
    DICOMStudyId = json_dicom_header["ImageSetID"]
    PatientLevel = json_dicom_header["Patient"]["DICOM"]
    getTags(PatientLevel, ds , vrlist)
    StudyLevel = json_dicom_header["Study"]["DICOM"]
    getTags(StudyLevel, ds , vrlist)
    for series in json_dicom_header["Study"]["Series"]:
        getTags(json_dicom_header["Study"]["Series"][series]["DICOM"] ,  ds , vrlist)
        for instance in json_dicom_header["Study"]["Series"][series]["Instances"]:
            logging.info(f"Converting instance {instance}")
            getDICOMVRs(json_dicom_header["Study"]["Series"][series]["Instances"][instance]["DICOMVRs"] , vrlist)
            frameId = json_dicom_header["Study"]["Series"][series]["Instances"][instance]["ImageFrames"][0]["ID"]
            getTags( json_dicom_header["Study"]["Series"][series]["Instances"][instance]["DICOM"] , ds , vrlist)
            ds.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
            ds.is_little_endian = True
            ds.is_implicit_VR = False
            file_meta.MediaStorageSOPInstanceUID = UID(instance)
            pixels = HLIGetFramePixels(datastoreId,DICOMStudyId,frameId, client)
            start_time = time.time()
            ds.PixelData = pixels.tobytes()
            os.makedirs( f"./out/{studyId}" , mode=0o775, exist_ok=True )
            ds.save_as(f"./out/{studyId}/{instance}.dcm")
            invert = False
            if 'PhotometricInterpretation' in ds and ds.PhotometricInterpretation == "MONOCHROME1":
                invert=True
            saveAsPngPIL(ds , f"./out/{studyId}/{instance}.png", invert=invert )
            ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
            vrlist.clear()
            end_time = time.time()
            logging.info(f"Outpout save     : {stopwatch(start_time,end_time)} ms")             

def getDICOMVRs(taglevel, vrlist):
    for theKey in taglevel:
        vrlist.append( [ theKey , taglevel[theKey] ])
        logging.debug(f"[getDICOMVRs] - List of private tags VRs: {vrlist}\r\n")

def getTags(tagLevel, ds , vrlist):
    start_time = time.time()    
    for theKey in tagLevel:
        try:
            try:
                tagvr = pydicom.datadict.dictionary_VR(theKey)
            except:  #In case the vr is not in the pydicom dictionnary, it might be a private tag , listed in the vrlist
                tagvr = None
                for vr in vrlist:
                    if theKey == vr[0] :
                        tagvr = vr[1]
            datavalue=tagLevel[theKey]
            if(tagvr == 'SQ'):
                logging.debug(f"{theKey} : {tagLevel[theKey]} , {vrlist}")
                seqs = []
                for underSeq in tagLevel[theKey]:
                    seqds = Dataset()
                    getTags(underSeq, seqds, vrlist)
                    seqs.append(seqds)
                datavalue = Sequence(seqs)
                continue
            if( tagvr in  [ 'OB' , 'OD' , 'OF', 'OL', 'OW', 'UN' ] ):
                base64_str = tagLevel[theKey]
                base64_bytes = base64_str.encode('utf-8')
                datavalue = base64.decodebytes(base64_bytes)
            data_element = DataElement(theKey , tagvr , datavalue )
            if data_element.tag.group != 2:
                ds.add(data_element) 
        except Exception as err:
            logging.warning(f"[getTags] - {err}")
            continue 
    end_time = time.time()           
    logging.info(f"Dataset build   : {stopwatch(start_time,end_time)} ms") 

def hliGetMetadata(datastoreId, studyId , client):
    start_time = time.time()
    hli_study_metadata = client.get_image_set_metadata(datastoreId=datastoreId , imageSetId=studyId)
    json_study_metadata = gzip.decompress(hli_study_metadata["imageSetMetadataBlob"].read())
    json_study_metadata = json.loads(json_study_metadata)
    end_time = time.time()  
    print(f"Metadata fetch : {end_time-start_time}")    
    return json_study_metadata

def HLIGetFramePixels(datastoreId, studyId, imageFrameId, client):
    start_time = time.time()
    res = client.get_image_frame(
        datastoreId=datastoreId,
        imageSetId=studyId,
        imageFrameId=imageFrameId)
    end_time = time.time()
    logging.info(f"Frame fetch     : {stopwatch(start_time,end_time)} ms") 
    start_time = time.time() 
    b = io.BytesIO()
    b.write(res['imageFrameBlob'].read())
    b.seek(0)
    d = decode(b)
    end_time = time.time()
    logging.info(f"Frame decode    : {stopwatch(start_time,end_time)} ms")    
    return d

def stopwatch( start_time, end_time ):
    time_lapsed = end_time - start_time
    return time_lapsed*1000  

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

