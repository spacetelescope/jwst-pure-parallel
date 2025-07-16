# JWST Pure Parallel

Assess JWST pure parallel opportunities for specific observing requirements.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)

## Installation

Download and install Miniconda from the official
[website](https://docs.conda.io/en/latest/miniconda.html). Open a new shell so that environment variable chages in your startup file take effect.

Clone the repository that contains the package source code:
```bash
git clone https://github.com/spacetelescope/jwst-pure-parallel.git
```
Create the `jwpure` conda environment, using the conda environment.yml configuration file in the downloaded repository:

```bash
cd jwst-pure-parallel
conda env create -f environment.yml
```

## Usage

Switch to your working directory (e.g., `proposal`). Activate the `jwpure` conda environment.
```bash
cd proposal
conda activate jwpure
```
Create a simple test program (e.g., `test.py`), for example:
```
from jwpure.analyze import Scenario

slot, config, visit = Scenario.constraint_parameters()
scenario = Scenario()
for nconfig in [3, 3, 2]:
    constraint = (
        (slot.inst != 'NIRCam') &
        (slot.slotdur.between(300, 900)) &
        (config.nslot >= 3) &
        (visit.nconfig >= nconfig)
    )
    scenario.allocate_slots(constraint, maxslot=3, maxconfig=nconfig)
scenario.summarize()
scenario.save('scenario_slots.csv')
```

In this example, we:
1. Import the main `Scenario` class from the jwpure package.
2. Define `slot`, `config`, and `visit` objects that you can use to specify constraints.
3. Initialize a new `scenario`.
4. Allocate pure parallel slots from the larger pool in three passes.
5. Use the `slot`, `config`, and `visit` with normal python operators to specify a `constraint`. In this example:
   - NIRCam is not the prime instrument because we want to use it as the parallel instrument,
   - Slot duration is between 300 and 900 seconds,
   - The instrument configuration has at least 3 slots (usually dithers) per configuration, and
   - The visit has at least `nconfig` configuration per visit, which is specified for each pass.
5. Allocate pure parallel slots. Do not allocate more than `maxslot` slots per configuration or more than `maxconfig` configurations per visit, even if `constraint` returns more slots and/or configurations. This makes it possible to use slots in a configuration or configurations in a visit for multiple purposes (e.g., share them between observers).
6. Print a summary table to the terminal.
7. Write a summary file (e.g., `test.csv`) with summary information about each allocated slot.

Execute the program:
```bash
python ./test.py
```
The output should look something like:
```ascii
cycle pure_subset nslot nconfig nvisit hours
----- ----------- ----- ------- ------ -----
    1           0 25465    7466   2525  3153
    1           1  1764     588    196   226
    1           2   252      84     28    28
    1           3   636     212    106    83
    2           0 23840    7143   2761  2404
    2           1   945     315    105   139
    2           2    63      21      7     7
    2           3   474     158     79    60
    3           0 17077    4205   1853  2576
    3           1  1131     377    127   150
    3           2   189      63     21    23
    3           3   342     114     57    51
    4           0 24454    6535   2454  3550
    4           1  1197     399    133   155
    4           2    81      27      9     8
    4           3   378     126     63    52
wrote scenario_slots.csv
```
Output is sorted by observing cycle. Each previous cycle provides a rough estimate of what might be available in future cycles. Each cycle has one row for unallocated slots (`pure_subset == 0`) and one row for each pass (`pure_subset > 0`).