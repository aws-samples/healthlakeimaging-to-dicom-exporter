"""
HLI-to-DICOM HLIDataDICOMizer : This class contains the logic to encapsulate the metadat data and the pixels into a DICOM object.

SPDX-License-Identifier: MIT-0
"""
import pydicom
import logging
from pydicom.sequence import Sequence
from pydicom import Dataset , DataElement 
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import UID
import base64


class HLIDataDICOMizer():

    ds = Dataset()

    def __init__(self, curie_metadata, ImageFrame) -> None:
        pass
        vrlist = []       
        file_meta = FileMetaDataset()
        self.ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
        self.getDICOMVRs(curie_metadata["Study"]["Series"][ImageFrame["SeriesUID"]]["Instances"][ImageFrame["SOPInstanceUID"]]["DICOMVRs"] , vrlist)
        PatientLevel = curie_metadata["Patient"]["DICOM"]
        self.getTags(PatientLevel, self.ds , vrlist)
        StudyLevel = curie_metadata["Study"]["DICOM"]
        self.getTags(StudyLevel, self.ds , vrlist)
        SeriesLevel=curie_metadata["Study"]["Series"][ImageFrame["SeriesUID"]]["DICOM"]
        self.getTags(SeriesLevel, self.ds , vrlist)
        InstanceLevel=curie_metadata["Study"]["Series"][ImageFrame["SeriesUID"]]["Instances"][ImageFrame["SOPInstanceUID"]]["DICOM"] 
        self.getTags(InstanceLevel ,  self.ds , vrlist)
        self.ds.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
        self.ds.is_little_endian = True
        self.ds.is_implicit_VR = False
        file_meta.MediaStorageSOPInstanceUID = UID(ImageFrame["SOPInstanceUID"])
        pixels = ImageFrame["PixelData"]
        if (pixels is not None):
            self.ds.PixelData = pixels.tobytes()
        vrlist.clear()

    def getDataset(self):
        return self.ds

        
    def getDICOMVRs(self,taglevel, vrlist):
        for theKey in taglevel:
            vrlist.append( [ theKey , taglevel[theKey] ])
            logging.debug(f"[HLIDataDICOMizer][getDICOMVRs] - List of private tags VRs: {vrlist}\r\n")



    def getTags(self,tagLevel, ds , vrlist):    
        for theKey in tagLevel:
            try:
                try:
                    tagvr = pydicom.datadict.dictionary_VR(theKey)
                except:  #In case the vr is not in the pydicom dictionnary, it might be a private tag , listed in the vrlist
                    tagvr = None
                    for vr in vrlist:
                        if theKey == vr[0]:
                            tagvr = vr[1]
                datavalue=tagLevel[theKey]
                #print(f"{theKey} : {datavalue}")
                if(tagvr == 'SQ'):
                    logging.debug(f"{theKey} : {tagLevel[theKey]} , {vrlist}")
                    seqs = []
                    for underSeq in tagLevel[theKey]:
                        seqds = Dataset()
                        self.getTags(underSeq, seqds, vrlist)
                        seqs.append(seqds)
                    datavalue = Sequence(seqs)
                    continue
                if(tagvr == 'US or SS'):
                    datavalue=tagLevel[theKey]
                    if (int(datavalue) > 32767):
                        tagvr = 'US'
                if( tagvr in  [ 'OB' , 'OD' , 'OF', 'OL', 'OW', 'UN' ] ):
                    base64_str = tagLevel[theKey]
                    base64_bytes = base64_str.encode('utf-8')
                    datavalue = base64.decodebytes(base64_bytes)
                if theKey == 'PrivateCreatorID': # Ignore this attribute, otherwise it creates an issue because it doesn't resolve to a DICOM tag
                    continue
                data_element = DataElement(theKey , tagvr , datavalue )
                if data_element.tag.group != 2:
                    try:
                        if (int(data_element.tag.group) % 2) == 0 : # we are skipping all the private tags
                            ds.add(data_element) 
                    except:
                        continue
            except Exception as err:
                logging.warning(f"[HLIDataDICOMizer][getTags] - {err}")
                continue 