Choose which of the available modalities to include in the visualization. Only patients
are considered that have at least one of the selected diagnoses available. One may
choose how to combine these - possibly conflicting - diagnoses:

- logical ``OR``: A lymph node level (LNL) is reported as _metastatic_ or _involved_ as soon as one of the selected diagnoses reports a positive finding. Anything else is reported as _healthy_.
- logical ``AND``: LNL's are reported as involved only when **all** diagnoses agree on positive findings. If that is not the case, meaning that none or not all agree on such a finding, it is reported (rather optimistically) as _healthy_.