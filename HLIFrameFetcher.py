"""
HLI-to-DICOM HLIFrameFetcher : This class contains the logic to query the Image pixel raster.

SPDX-License-Identifier: MIT-0
"""
import boto3
from botocore.config import Config
import os
import collections
from time import sleep
from threading import Thread
from os.path import exists
import logging
from openjpeg import decode
import io
from HLIDataDICOMizer import *

class HLIFrameFetcher:


    status = 'idle'
    FetchJobs = None
    FetchJobsCompleted = None
    InstanceId= None
    client = None
    thread_running = True

    def __init__(self, InstanceId):
        self.InstanceId = InstanceId
        self.FetchJobs = collections.deque([])
        self.FetchJobsCompleted = collections.deque([])
        self.client = boto3.client('medical-imaging')
        thread = Thread(target = self.ProcessJobs)
        thread.start()


    def AddFetchJob(self,FetchJob):
            self.FetchJobs.append(FetchJob)
            logging.debug("[HLIFrameFetcher][AddFetchJob]["+self.InstanceId+"] - Fetch Job added "+str(FetchJob)+".")

    def ProcessJobs(self):
        while(self.thread_running):
            if(len(self.FetchJobs) > 0):
                self.status="busy"
                try:
                    entry = self.FetchJobs.popleft()
                    entry["PixelData"] = self.curieGetFramePixels(entry["datastoreId"], entry["studyId"], entry["frameId"])
                    self.FetchJobsCompleted.append(entry)
                except Exception as FetchError:
                    logging.error(f"[HLIFrameFetcher][{str(self.InstanceId)}] - {FetchError}")
            else:
                self.status = 'idle'
                sleep(0.1)

    def getFramesFetched(self):
        if len(self.FetchJobsCompleted) > 0:
            obj = self.FetchJobsCompleted.popleft()
            return obj
        else:
            return None

    def curieGetFramePixels(self, datastoreId, studyId, imageFrameId):
        res = self.client.get_image_frame(
            datastoreId=datastoreId,
            imageSetId=studyId,
            imageFrameInformation={"imageFrameId": imageFrameId}
        b = io.BytesIO()
        b.write(res['imageFrameBlob'].read())
        b.seek(0)
        d = decode(b)
        return d

    def Dispose(self):
        self.thread_running = False
