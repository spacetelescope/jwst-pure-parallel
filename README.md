# JWST Pure Parallel

The `jwpure` software package facilitates statistical analysis of JWST pure
parallel observing scenarios, based on historical data from previous observing
cycles. The package supports planning and evaluation of future pure parallel
programs by quantifying the availability of past observing opportunities under
specific constraints (e.g., prime instrument, number of required instrument
configurations, exposure time, number of dithers, position in the sky) needed
for a future program.

Unlike coordinated parallel observations, where both the primary and parallel
observations are specified in the same program and managed by a single
observer, pure parallel exposures are proposed independently and must fit
into predefined time windows ("slots") at pointings dictated by the prime
observation. Each previous cycle offers a independent assessment of slot
availability in future cycles, though the number and nature of available
slots depends on the suite of accepted prime programs and varies from
one cycle to the next.

[Documentation wiki](https://github.com/spacetelescope/jwst-pure-parallel/wiki)

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
    1           0 20564    6096   2074  2433
    1           1  1197     399    133   140
    1           2   153      51     17    16
    1           3   498     166     83    67
    2           0 16035    4719   1769  1818
    2           1   711     237     79   100
    2           2    54      18      6     6
    2           3   468     156     78    59
    3           0 14201    3571   1553  2149
    3           1   840     280     94   104
    3           2   117      39     13    13
    3           3   300     100     50    44
    4           0 23181    6285   2382  3228
    4           1   954     318    106   112
    4           2   126      42     14    13
    4           3   402     134     67    54
Subset 1: WHERE (((slot.inst != 'NIRCam' AND slot.slotdur BETWEEN 300 AND 900) AND config.nslot >= 3) AND visit.nconfig >= 3)
Subset 2: WHERE (((slot.inst != 'NIRCam' AND slot.slotdur BETWEEN 300 AND 900) AND config.nslot >= 3) AND visit.nconfig >= 3)
Subset 3: WHERE (((slot.inst != 'NIRCam' AND slot.slotdur BETWEEN 300 AND 900) AND config.nslot >= 3) AND visit.nconfig >= 2)
wrote scenario_slots.csv
```
Output is sorted by observing cycle. Each previous cycle provides a rough estimate of what might be available in future cycles. Each cycle has one row for unallocated slots (`pure_subset == 0`) and one row for each pass (`pure_subset > 0`).
