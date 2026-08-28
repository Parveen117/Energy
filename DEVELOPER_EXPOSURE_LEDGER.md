# Developer exposure ledger

Tournament discipline imported from EMK-Tensor-Cell-Devices: a public
record of which data the implementer had seen before each
preregistration was committed, so every verdict carries its honest
evidentiary grade.

| Preregistration | Data targeted | Implementer exposure at commit time | Grade |
| --- | --- | --- | --- |
| E01-EXP (original) | NASA PCoE | none of the target files opened | blind |
| E01-EXP-2 | NASA 24 C group (already pinned) | per-stage transverse shares SEEN in EXP-R | prespecified statistic, non-blind data |
| E01-EXP-3 | CALCE CS2, NASA other temperature groups | filenames seen; contents unopened | blind |
| E01-EXP-4 | A123 OCV, INR IC-OCV | filenames seen; contents unopened | blind |
| E01-EXP-5 | same files as EXP-4 | EXP-4 results SEEN; whitening scales newly declared | prespecified statistic, non-blind data (AF-2 remedy) |

Cross-validation note: the EXP-3 CALCE pipeline was independently
corroborated against the locked tournament extractor of
EMK-Tensor-Cell-Devices `battery_tournament/trustmeter_battery.py`
(different chronology method — in-file Date_Time vs filename dates —
and different completeness gates): 766 vs 768 accepted cycles on
CS2_33 and stage capacities agreeing within 1% at all six stages.
Discovery-grade certification of EXP-3 still requires an independent
evaluator rerunning the pinned pipeline, exactly as the tournament's
evaluator harness prescribes.
