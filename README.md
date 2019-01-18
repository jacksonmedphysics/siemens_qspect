# siemens_qspect
Small GUI to convert Siemens Lu-177 SPECT images into quantitatie pseudo-PET format

Quantitative SPECT conversion software - updated adaptation of the method by JM Beauregard
Beauregard, Jean-Mathieu, et al. "Quantitative 177Lu SPECT (QSPECT) imaging using a commercially available SPECT/CT system." Cancer Imaging 11.1 (2011): 56.
https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3205754/

For usage - consult Reference Manual PDF

Typical sensitivity factors for modern siemens SPECT cameras on axial reconstruction 9-11 cps/MBq.

Software requires axial recon as well as tomo files for each bed step (used in dead-time correction)

Yields a directory of file-per-slice PET format images in Bq/ml intensity. User inputs injection details and patient weight for SUV calculation

Settings may be modified to perform DICOM transfer to designated AE location on completion
