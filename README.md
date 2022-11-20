# healthlakeimaging-to-dicom-exporter

This is a python 3.8+ sample application demonstrating how to rebuild DICOM P10 objects from AWS HealthLake Imaging metadata and HTJ2k frame.


## Getting started

This sample relies on the pylibjpeg-openjpeg wrapper project, and requires a specific version of the openJpeg that supports HTJ2K. Refer to the installation steps below for more information about compiling this python package.


## Installation

Follow these main steps to build and use this project:
*  Clone this project.
*  Clone the project pylibjpeg-openjpeg, branch jmsmkn.
*  Initialize an app env.
*  Compile and install pylibjpeg-openjpeg in the app env.
*  Configure the AWS CLI for `medical-imaging` API.


### Clone this project
This project can be cloned with the below command:
```
    git clone https://github.com/aws-samples/healthlakeimaging-to-dicom-exporter.git
```

### Clone the project pylibjpeg-openjpeg, branch jmsmkn
This project needs to be cloned with its extrnal modules:
```
git clone --recurse-submodules https://github.com/jmsmkn/pylibjpeg-openjpeg.git
```

### Initialize the healthlakeimaging-to-dicom-exporter app env
Locate your terminal sessions in the `healthlakeimaging-to-dicom-exporter` folder and run the below commands to create and activate the application env.
```
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
```
Note: When the source command is successful your terminal prompt will be prefixed with (.venv): eg:

`
(.venv) jpleger@SEA-1801104145:~/Code/healthlakeimaging-to-dicom-exporter$
`

### Compile and install pylibjpeg-openjpeg in the app env
With the .venv env activated, locate your terminal session in the `pylibjpeg-openjpeg` folder and run the following command:
```
    python ./setup.py install
```
When this command is successful the terminal prompt returns the below message :\
`Using /`[your git clone root directory]`/healthlakeimaging-to-dicom-exporter/.venv/lib/python3.8/site-packages`\
`Finished processing dependencies for pylibjpeg-openjpeg==1.2.1`

At this point all the dependencies are installed and the application is ready tobe used.

### Configure the AWS CLI for medical-imaging API
At the moment this code sample is written HealthLake Imaging is still in public beta and the AWS CLI is not configured with its service descriptor. Because Python Boto3 library relies on the AWS service descriptors provided by the AWS CLI, we need to add HealthLake Imaging to the AWS CLI configuration. Becaue HLI ( HealthLake Imaging ) is only enabled in `us-east-1` region, make sure to also configure your AWS CLI in this region. 

Located in the `healthlakeimaging-to-dicom-exporter` cloned folder, type the following command to configure the AWS CLI with the `medical-imaging` API:
```
    aws configure add-model --service-name medical-imaging --service-model file://./service-2.json
```
When the command successfully completes the termianl is returned to its prompt with no message.

## Execute the project application
Still with the .venv env activated, locate your terminal session in the healthlakeimaging-to-dicom-exporter folder, and execute the follow command to export a study from HealthLake Imaging to a P10 DICOM file on your filesystem.
```
    python main.py -d [datastoreId] -s [studyId]
```
Eg:
```
(.venv) jpleger@SEA-1801104145:~/Code/healthlakeimaging-to-dicom-exporter$python main.py  -d d0e51a06705f49dedb58ab0aba1922d8 -s 4df176e4f4ad69d1b0a2618e411d5d29
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
INFO:root:Reading the JSON metadata file
INFO:root:Metadata fetch  : 376.81078910827637 ms
INFO:root:Parsing the Header Tags.
INFO:root:Dataset build   : 0.07462501525878906 ms
INFO:root:Dataset build   : 0.12183189392089844 ms
INFO:root:Dataset build   : 0.2162456512451172 ms
INFO:root:Converting instance 1.3.51.5145.5142.20010109.1105627.1.0.1
INFO:root:Dataset build   : 1.1034011840820312 ms
INFO:root:Frame fetch     : 355.39984703063965 ms
INFO:root:Frame decode    : 1275.4952907562256 ms
INFO:root:Outpout save     : 26.74698829650879 ms
INFO:root:Dataset build   : 0.2353191375732422 ms
INFO:root:Converting instance 1.3.51.5145.5142.20010109.1105752.1.0.1
INFO:root:Dataset build   : 0.03409385681152344 ms
INFO:root:Dataset build   : 1.188039779663086 ms
INFO:root:Frame fetch     : 284.64722633361816 ms
INFO:root:Frame decode    : 497.0667362213135 ms
INFO:root:Outpout save     : 12.300968170166016 ms

```

The DICOM files can be found in the folder `healthlakeimaging-to-dicom-exporter/out/[studyInstanceUID]`. The code also exports a png representation of the DICOM image.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

