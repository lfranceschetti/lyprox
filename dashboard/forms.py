from django import forms
from django.db.models.expressions import Value
from django.forms import fields

from core.loggers import FormLoggerMixin
from patients.models import Patient, Tumor, Diagnose
from accounts.models import Institution

from typing import Tuple, Dict, List, Optional, Any
import logging
logger = logging.getLogger(__name__)


class ThreeWayToggle(forms.ChoiceField):
    """A toggle switch than can be in three different states: Positive/True, 
    unkown/None and negative/False.
    
    Args:
        widget: Widget to be used. Should probably be left at ``None`` (then it 
            uses :class:`RadioSelect` by default), since it is somewhat 
            specifically written as a radio button.
        attrs: HTML attributes that can be added to the element in the template. 
        choices: List of options to choose from.
        initial: Initial value.
        required: Specify whether it is required to fill out this field.
    """
    def __init__(
        self, 
        widget: Optional[Any] = None, 
        attrs: Dict[str, str] = {"class": "radio is-hidden", 
                                 "onchange": "changeHandler();"}, 
        choices: List[Tuple] = [( 1 , "plus"), 
                                ( 0 , "ban"), 
                                (-1, "minus")], 
        initial: int = 0, 
        required: bool = False, 
        **kwargs
    ):
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
        """Cast the string that is returned by the POST request to an integer.
        """
        try:
            return int(value)
        except ValueError:
            return value


class InstitutionModelChoiceIndexer:
    """Custom class with which one can access additional information from 
    the model that is chosen by the :class:`InstitutionMultipleChoiceField`. 
    It has a ``__getitem__`` function, so while one loops over the checkboxes 
    of the :class:`InstitutionMultipleChoiceField`, the loop index can be used 
    to access additional information, such as here the name and logo URL of the 
    institution in question.
    """
    def __init__(self, field) -> None:
        self.field = field
        self.queryset = field.queryset
    
    def __getitem__(self, key):
        """Make the object indexable."""
        obj = self.queryset[key]
        return self.info(obj)
    
    def info(self, obj: Institution) -> Tuple[int, str]:
        """Return the additional info."""
        return (
            self.field.label_from_instance(obj),
            self.field.logo_url_from_instance(obj)
        )


class InstitutionMultipleChoiceField(forms.ModelMultipleChoiceField):
    """Customize label description and add method that returns name and logo 
    URL for institutions. The implementation is inspired by how the ``choices`` 
    are implemented. But since some other functionality depends on how those 
    choices are implemented, it cannot be changed easily."""
    
    #: Allows one to extract more info about the objects. E.g. name and logo url
    name_and_url_indexer = InstitutionModelChoiceIndexer
    
    def label_from_instance(self, obj: Institution) -> str:
        """Institution name as label."""
        return obj.name
    
    def logo_url_from_instance(self, obj: Institution) -> str:
        """Return URL of Institution's logo."""
        return obj.logo.url
    
    @property
    def names_and_urls(self):
        """Custom property that returns name and URL of the institution from 
        a small indexer class (defined by the attribute 
        ``name_and_url_indexer``), which is also somewhat inspired by Django's 
        :class:`ModelChoiceIterator`."""
        return self.name_and_url_indexer(self)
    

class DashboardForm(FormLoggerMixin, forms.Form):
    """Form for querying the database. It contains patient- and tumor-specific 
    selection criteria to filter out subsets of patients. Upon creation, it 
    creates all fields for the individual lymph node level selection 
    dynamically. It makes heavy use of the :class:`ThreeWayToggle` class.
    """
    #: modalities the user can select
    modalities = forms.MultipleChoiceField(
        required=False, 
        widget=forms.CheckboxSelectMultiple(
            attrs={"class": "checkbox is-hidden",
                   "onchange": "changeHandler();"}
        ), 
        choices=Diagnose.Modalities.choices,
        initial=[1,2]
    )
    #: How to combine the modalities?
    modality_combine = forms.ChoiceField(
        widget=forms.Select(attrs={"onchange": "changeHandler();"}),
        choices=[("AND", "AND"), 
                 ("OR", "OR")],
        label="Combine",
        initial="OR"
    )
    
    #: Smoking status. Uses the :class:`ThreeWayToggle`
    nicotine_abuse = ThreeWayToggle()
    #: HPV status. Uses the :class:`ThreeWayToggle`
    hpv_status = ThreeWayToggle()
    #: Did patient receive neck dissection? Uses the :class:`ThreeWayToggle`
    neck_dissection = ThreeWayToggle()
    #: Select all N+ or N0 patients. Uses the :class:`ThreeWayToggle`
    n_status = ThreeWayToggle()
    
    #: Choose from which institutions data should be included
    institution__in = InstitutionMultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(
            # doesn't do anythin since it's written by hand
            attrs={"class": "checkbox is-hidden", 
                   "onchange": "changeHandler();"}
        ),
        queryset=Institution.objects.all(),
        initial=Institution.objects.all()
    )
    
    #: Tumor subsite. Naming of field such that querying can be done easier.
    subsite__in = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(
            attrs={"class": "checkbox is-hidden",
                   "onchange": "changeHandler();"},
        ),
        choices=[("base", "base of tongue"),
                 ("tonsil", "tonsil"), 
                 ("rest" , "other")],
        initial=["base", "tonsil", "rest"]
    )
    #: Tumor T-stage. Naming of field such that querying can be done easier.
    t_stage__in = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(
            attrs={"class": "checkbox is-hidden",
                   "onchange": "changeHandler();"}
        ),
        choices=Patient.T_stages.choices,
        initial=[1,2,3,4]
    )
    #: Central or lateralized tumor?
    central = ThreeWayToggle()
    #: Does the tumor extend over mid-sagittal line?
    extension = ThreeWayToggle()
    
    #: Checkbutton for switching to percent
    show_percent = forms.BooleanField(
        required=False, initial=False, 
        widget=forms.widgets.RadioSelect(
            attrs={"class": "radio is-hidden", "onchange": "changeHandler();"},
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
                               "onclick": ("bothClickHandler(this);"
                                           "changeHandler();")})
                elif lnl in ['Ia', 'Ib', 'IIa', 'IIb']:
                    self.fields[f"{side}_{lnl}"] = ThreeWayToggle(
                        attrs={"class": "radio is-hidden",
                               "onclick": ("subClickHandler(this);"
                                           "changeHandler();")})
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
        sublevels a & b. Also convert T-stages from list of ``str`` to 
        list of ``int``.
        """
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