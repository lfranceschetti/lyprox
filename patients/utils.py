from django.db import IntegrityError
from django.forms import ValidationError

import numpy as np
import pandas as pd
import dateutil.parser as dp
from typing import List, Union, Optional, Dict, Any
import logging
logger = logging.getLogger(__name__)

from .models import (Patient, Diagnose, Tumor)


class ParsingError(Exception):
    """Exception raised when the parsing of an uploaded CSV fails due to 
    missing data columns."""
    
    def __init__(self, column, message="Missing column in uploaded table"):
        self.column = column
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return f"{self.column}: {self.message}"


def compute_hash(*args):
    """Compute a hash vlaue from three patient-specific fields that must be 
    removed due for repecting the patient's privacy."""
    return hash(args)


def nan_to_None(sth):
    if sth != sth:
        return None
    else:
        return sth


def patient_from_row(row, anonymize: List[str]):
    """Create a `Patient` instance from a row of a `DataFrame` containing the 
    appropriate information."""
    patient_dict = row.to_dict()
    _ = nan_to_None
    
    if len(anonymize) != 0:
        to_hash = [patient_dict.pop(a) for a in anonymize]
        hash_value = compute_hash(*to_hash)
    else:
        hash_value = compute_hash(*patient_dict)
    
    patient_fields = [field.name for field in Patient._meta.get_fields()]
    fields_to_remove = ["id", "hash_value", "tumor", "diagnose", "t_stage"]
    [patient_fields.remove(field) for field in fields_to_remove]
    
    valid_patient_dict = {}
    for field in patient_fields:
        try:
            valid_patient_dict[field] = _(patient_dict[field])
        except KeyError:
            column = field
            raise ParsingError(column)
    
    try:
        new_patient = Patient(
            hash_value=hash_value,
            **valid_patient_dict
        )
        new_patient.save()
    except IntegrityError as ie:
        msg = ("Hash value already in database. Patient might have been added "
               "before")
        logger.warn(msg)
        raise ie
    
    return new_patient


def add_tumors_from_row(row, patient):
    """Create `Tumor` instances from row of a `DataFrame` and add them to an 
    existing `Patient` instance."""
    # extract number of tumors in row
    level_zero = row.index.get_level_values(0)
    num_tumors = np.max([int(num) for num in level_zero])
    _ = nan_to_None
    
    tumor_fields = [field.name for field in Tumor._meta.get_fields()]
    fields_to_remove = ["id", "patient"]
    [tumor_fields.remove(field) for field in fields_to_remove]
    
    for i in range(num_tumors):
        tumor_dict = row[(f"{i+1}")].to_dict()
        
        valid_tumor_dict = {}
        for field in tumor_fields:
            try:
                valid_tumor_dict[field] = _(tumor_dict[field])
            except KeyError:
                column = field
                raise ParsingError(column)
        
        new_tumor = Tumor(
            patient=patient,
            **valid_tumor_dict
        )
        new_tumor.save()


def add_diagnoses_from_row(row, patient):
    """Create `Diagnose` instances from row of `DataFrame` and add them to an 
    existing `Patient` instance."""
    modalities_list = list(set(row.index.get_level_values(0)))
    if not set(modalities_list).issubset(Diagnose.Modalities.labels):
        message = ("Unknown diagnostic modalities were provided. Known are "
                   f"only {Diagnose.Modalities.labels}.")
        raise ParsingError(column="Modalities", message=message)
    
    if len(modalities_list) == 0:
        message = "No diagnostic modalities were found in the provided table."
        raise ParsingError(column="Modalities", message=message)
    
    _ = nan_to_None
    
    diagnose_fields = [field.name for field in Diagnose._meta.get_fields()]
    fields_to_remove = ["id", "patient", "modality", "side", "diagnose_date"]
    [diagnose_fields.remove(field) for field in fields_to_remove]
    
    for mod in modalities_list:
        diagnose_date = _(row[(mod, "info", "date")])
        if diagnose_date is not None:
            for side in ["left", "right"]:
                diagnose_dict = row[(mod, side)].to_dict()
                
                valid_diagnose_dict = {}
                for field in diagnose_fields:
                    try:
                        valid_diagnose_dict[field] = _(diagnose_dict[field])
                    except KeyError:
                        column = field
                        raise ParsingError(column)
                
                mod_num = Diagnose.Modalities.labels.index(mod)
                new_diagnosis = Diagnose(
                    patient=patient, modality=mod_num, side=side,
                    diagnose_date=diagnose_date,
                    **valid_diagnose_dict
                )
                new_diagnosis.save()
    

def import_from_pandas(
    data_frame: pd.DataFrame, 
    anonymize: List[str] = ["ID"]
):
    """Import patients from pandas `DataFrame`."""
    num_new = 0
    num_skipped = 0
    
    for i, row in data_frame.iterrows():
        # Make sure first two levels are correct for patient data
        try:
            patient_row = row[("patient", "#")]
        except KeyError:
            missing = "('patient', '#', '...')"
            message = ("For patient info, first level must be 'patient', "
                       "second level must be '#'.")
            raise ParsingError(column=missing, message=message)
        
        # skip row if patient is already in database
        try:
            new_patient = patient_from_row(
                patient_row, anonymize=anonymize
            )
        except IntegrityError:
            msg = ("Skipping row")
            logger.warn(msg)
            num_skipped += 1
            continue
        
        # make sure first level is correct for tumor
        try:
            tumor_row = row[("tumor")]
        except KeyError:
            missing = "('tumor', '1/2/3/...', '...')"
            message = ("For tumor info, first level must be 'tumor' and "
                       "second level must be number of tumor.")
            raise ParsingError(column=missing, message=message)
                
        add_tumors_from_row(
            tumor_row, new_patient
        )
        
        not_patient = row.index.get_level_values(0) != "patient"
        not_tumor = row.index.get_level_values(0) != "tumor"
        add_diagnoses_from_row(
            row.loc[not_patient & not_tumor], new_patient
        )
        
        num_new += 1
        
    return num_new, num_skipped