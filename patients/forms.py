from django import forms
from django.conf import settings
from django.forms import widgets
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

import numpy as np
from pathlib import Path
import pandas
import os
import logging

from .models import Patient, Tumor, Diagnose
from .ioports import compute_hash
from .loggers import FormLoggerMixin


class PatientForm(FormLoggerMixin, forms.ModelForm):
    class Meta:
        model = Patient
        fields = ["gender", 
                  "diagnose_date", 
                  "alcohol_abuse", 
                  "nicotine_abuse", 
                  "hpv_status",
                  "neck_dissection", 
                  "n_stage",
                  "m_stage"]
        widgets = {"gender": widgets.Select(attrs={"class": "select"}),
                   "diagnose_date": widgets.NumberInput(attrs={"class": "input",
                                                               "type": "date"}),
                   "alcohol_abuse": widgets.Select(choices=[(True, "yes"),
                                                            (False, "no"),
                                                            (None, "unknown")],
                                                   attrs={"class": "select"}),
                   "nicotine_abuse": widgets.Select(choices=[(True, "yes"),
                                                             (False, "no"),
                                                             (None, "unknown")],
                                                  attrs={"class": "select"}), 
                   "hpv_status": widgets.Select(choices=[(True, "positive"),
                                                         (False, "negative"),
                                                         (None, "unknown")],
                                                attrs={"class": "select"}),
                   "neck_dissection": widgets.Select(choices=[(True, "yes"),
                                                              (False, "no"),
                                                              (None, "unknown")],
                                                     attrs={"class": "select"}),
                   "n_stage": widgets.Select(attrs={"class": "select"}),
                   "m_stage": widgets.Select(attrs={"class": "select"})}

    first_name = forms.CharField(
        widget=widgets.TextInput(attrs={"class": "input",
                                        "placeholder": "First name"}))
    last_name = forms.CharField(
        widget=widgets.TextInput(attrs={"class": "input",
                                        "placeholder": "Last name"}))   
    birthday = forms.DateField(
        widget=widgets.NumberInput(attrs={"class": "input",
                                          "type": "date"}))
    check_for_duplicate = forms.BooleanField(
        widget=widgets.HiddenInput(),
        required=False)


    def save(self, commit=True):
        """Compute hashed ID and age from name, birthday and diagnose date."""
        patient = super(PatientForm, self).save(commit=False)

        patient.hash_value = self.cleaned_data["hash_value"]
        patient.age = self._compute_age()
        
        if commit:
            patient.save()
            
        return patient
    
    
    def clean(self):
        """Override superclass clean method to raise a ValidationError when a 
        duplicate identifier is found."""
        cleaned_data = super(PatientForm, self).clean()
        unique_hash, cleaned_data = self._get_identifier(cleaned_data)
        
        if cleaned_data["check_for_duplicate"]:
            try:
                prev_patient_hash = Patient.objects.get(hash_value=unique_hash)
                
                msg = ("Hash value already in database. Entered patient might be "
                    "duplicate.")
                self.logger.warning(msg)
                raise forms.ValidationError(_(msg))
                
            # if the above does not throw an exception, one can proceed
            except Patient.DoesNotExist: 
                pass

        cleaned_data["hash_value"] = unique_hash
        return cleaned_data
        
        
    def _compute_age(self):
        """Compute age of patient at diagnose/admission."""
        bd = self.cleaned_data["birthday"]
        dd = self.cleaned_data["diagnose_date"]
        age = dd.year - bd.year
        
        if (dd.month < bd.month) or (dd.month == bd.month and dd.day < bd.day):
            age -= 1
            
        self.cleaned_data.pop("birthday")
        return age
    
    
    def _get_identifier(self, cleaned_data):
        """Compute the hashed undique identifier from fields that are of 
        provacy concern."""
        hash_value = compute_hash(cleaned_data["first_name"], 
                                  cleaned_data["last_name"],
                                  cleaned_data["birthday"])
        cleaned_data.pop("first_name")
        cleaned_data.pop("last_name")
        return hash_value, cleaned_data



class TumorForm(FormLoggerMixin, forms.ModelForm):
    class Meta:
        model = Tumor
        fields = ["t_stage",
                  "stage_prefix",
                  "subsite", 
                  "side",
                  "extension",
                  "volume"]
        widgets = {
            "t_stage": forms.Select(attrs={"class": "select"}),
            "stage_prefix": forms.Select(attrs={"class": "select"}),
            "subsite": forms.Select(attrs={"class": "select shorten"}),
            "side": forms.Select(attrs={"class": "select"}),
            "extension": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "volume": forms.NumberInput(attrs={"class": "input", 
                                             "min": 0.0}),
        }
        
    def clean_volume(self):
        volume = self.cleaned_data["volume"]
        if volume is not None and volume < 0.:
            raise ValidationError("volume must be a positive number.")
        return volume
        
        
    def save(self, commit=True):
        """Save tumor to existing patient."""
        tumor = super(TumorForm, self).save(commit=False)
        
        if commit:
            tumor.save()
            
        return tumor
        
        
        
class DiagnoseForm(FormLoggerMixin, forms.ModelForm):
    class Meta:
        model = Diagnose
        fields = ["diagnose_date",
                  "modality",
                  "side",]
        
        widgets = {"diagnose_date": forms.NumberInput(attrs={"class": "input is-small",
                                                             "type": "date"}),
                   "modality": forms.Select(attrs={"class": "select is-small"}),
                   "side": forms.Select(attrs={"class": "select is-small"})}
        
        for lnl in Diagnose.LNLs:
            fields.append(lnl)
            widgets[lnl] = forms.Select(choices=[(True, "pos"),
                                                 (False, "neg"),
                                                 (None, "???")],
                                        attrs={"class": "select"})
            

    def save(self, commit=True):
        """Save diagnose to existing patient."""
        diagnose = super(DiagnoseForm, self).save(commit=False)
        
        if diagnose.Ia or diagnose.Ib:
            diagnose.I = True
            
        if diagnose.IIa or diagnose.IIb:
            diagnose.II = True
        
        if commit:
            diagnose.save()
            
        return diagnose
    
    
    
class DataFileForm(FormLoggerMixin, forms.Form):
    data_file = forms.FileField(
        widget=forms.widgets.FileInput(attrs={"class": "file-input"})
    )
    
    def clean(self):
        cleaned_data = super(DataFileForm, self).clean()
        suffix = cleaned_data["data_file"].name.split(".")[-1]
        if suffix != "csv":
            msg = "Uploaded file is not a CSV table."
            self.logger.warning(msg)
            raise ValidationError(_(msg))
        
        try:
            data_frame = pandas.read_csv(cleaned_data["data_file"], 
                                         header=[0,1,2], 
                                         skip_blank_lines=True, 
                                         infer_datetime_format=True)
        except:
            msg = ("Error while parsing CSV table.")
            self.logger.error(msg)
            raise forms.ValidationError(
                _(msg + " Make sure format is as specified")
            )
            
        cleaned_data["data_frame"] = data_frame
        return cleaned_data



class ThreeWayToggle(forms.ChoiceField):
    """A toggle switch than can be in three different states: Positive/True, 
    unkown/None and negative/False."""
    
    def __init__(self, 
                 widget=None, 
                 attrs={"class": "radio is-hidden"},
                 choices=[( 1 , "plus"),
                          ( 0 , "ban"), 
                          (-1, "minus")],
                 initial=0,
                 required=False,
                 **kwargs):
        """Overwrite the defaults of the ChoiceField."""
        if widget is not None:
            super(ThreeWayToggle, self).__init__(
                widget=widget,
                choices=choices,
                initial=initial,
                required=required,
                **kwargs)
        else:
            super(ThreeWayToggle, self).__init__(
                widget=forms.RadioSelect(attrs=attrs),
                choices=choices,
                initial=initial,
                required=required,
                **kwargs)
    
    def to_python(self, value):
        """Cast the string to an integer."""
        if value not in ["", None]:
            return int(value)
        return 0



class DashboardForm(FormLoggerMixin, forms.Form):
    """Form for querying the database."""
    
    # select modalities to show
    modalities = forms.MultipleChoiceField(
        required=False, 
        widget=forms.CheckboxSelectMultiple(attrs={"class": "checkbox is-hidden"}), 
        choices=Diagnose.Modalities.choices,
        initial=[1,2]
    )
    modality_combine = forms.ChoiceField(
        choices=[("AND", "AND"), 
                 ("OR", "OR")],
        label="Combine",
        initial="OR"
    )
    
    # patient specific fields
    nicotine_abuse = ThreeWayToggle()
    hpv_status = ThreeWayToggle()
    neck_dissection = ThreeWayToggle()
    
    # tumor specific info
    subsite__in = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "checkbox is-hidden"}),
        choices=[("base", "base of tongue"),
                 ("tonsil", "tonsil"), 
                 ("rest" , "other/multiple")],
        initial=["base", "tonsil", "rest"]
    )
    t_stage__in = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "checkbox is-hidden"}),
        choices=Patient.T_stages.choices,
        initial=[1,2,3,4]
    )
    central = ThreeWayToggle()
    extension = ThreeWayToggle()
    
    # checkbutton for switching to percent
    show_percent = forms.BooleanField(
        required=False, initial=False, 
        widget=forms.widgets.RadioSelect(
            attrs={"class": "radio is-hidden"},
            choices=[(True, "percent"), (False, "absolute")]
        )
    )
    
    
    def __init__(self, *args, **kwargs):
        """Extend default initialization to create lots of fields for the 
        LNLs from a list."""
        super(DashboardForm, self).__init__(*args, **kwargs)
        for side in ["ipsi", "contra"]:
            for lnl in Diagnose.LNLs:
                if lnl in ['I', 'II']:
                    self.fields[f"{side}_{lnl}"] = ThreeWayToggle(
                        attrs={"class": "radio is-hidden",
                               "onclick": "bothClickHandler(this);"})
                elif lnl in ['Ia', 'Ib', 'IIa', 'IIb']:
                    self.fields[f"{side}_{lnl}"] = ThreeWayToggle(
                        attrs={"class": "radio is-hidden",
                               "onclick": "subClickHandler(this);"})
                else:
                    self.fields[f"{side}_{lnl}"] = ThreeWayToggle()
                    
                    
    def _to_bool(self, value: int):
        """Transform values of -1, 0 and 1 to False, None and True respectively. 
        Anything else is just passed through."""
        if value == 1:
            return True
        elif value == -1:
            return False
        elif value == 0:
            return None
        else:
            return value
           
                
    def clean(self):
        """Make sure LNLs I & II have correct values corresponding to their 
        sublevels a & b. Also convert tstages from list of str to list of int."""
        cleaned_data = super(DashboardForm, self).clean()
        
        # map all -1,0,1 fields to False,None,True
        cleaned_data = {
            key: self._to_bool(value) for key,value in cleaned_data.items()
        }
        
        # make sure LNLs I & II arent in conflict with their sublevels
        for side in ["ipsi", "contra"]:
            for lnl in ["I", "II"]:
                a = cleaned_data[f"{side}_{lnl}a"]
                b = cleaned_data[f"{side}_{lnl}b"]
                
                # make sure data regarding sublevels is not conflicting
                if a is True or b is True:
                    cleaned_data[f"{side}_{lnl}"] = True
                if a is False and b is False:
                    cleaned_data[f'{side}_{lnl}'] = False

        # map `central` from False,None,True to the respective list of sides
        if cleaned_data['central'] is True:
            cleaned_data['side__in'] = ['central']
        elif cleaned_data['central'] is False:
            cleaned_data["side__in"] = ['left', 'right']
        else:
            cleaned_data["side__in"] = ['left', 'right', 'central']
        
        # map subsites 'base','tonsil','rest' to list of ICD codes.
        subsites = cleaned_data["subsite__in"]
        subsite_dict = {"base":   ["C01.9"], 
                        "tonsil": ["C09.0", "C09.1", "C09.8", "C09.9"],
                        "rest":   ["C10.0", "C10.1", "C10.2", "C10.3", "C10.4", 
                                   "C10.8", "C10.9", "C12.9", "C13.0", "C13.1", 
                                   "C13.2", "C13.8", "C13.9", "C32.0", "C32.1", 
                                   "C32.2", "C32.3", "C32.8", "C32.9"]}
        icd_codes = []
        for sub in subsites:
            icd_codes += subsite_dict[sub]
        cleaned_data["subsite__in"] = icd_codes
        
        # make sure T-stages are list of ints
        str_list = cleaned_data["t_stage__in"]
        cleaned_data["t_stage__in"] = [int(s) for s in str_list]
        
        # make sure list of modalities is list of ints
        str_list = cleaned_data["modalities"]
        cleaned_data["modalities"] = [int(s) for s in str_list]
        
        self.logger.debug(f'cleaned data: {cleaned_data}')
        return cleaned_data
