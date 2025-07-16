from jwpure.analyze import Scenario
import pytest
import filecmp
from importlib import resources


@pytest.fixture
def test_file():
    test_data = resources.files('jwpure.data') / 'scenario_slots.csv'
    return test_data



def test_jwpure(test_file, tmp_path_factory):
    """Verify the example scenario matches expectations"""

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

    filename = tmp_path_factory.mktemp("test_data") / "scenario_slots.csv"
    scenario.save(filename)
    are_equal = filecmp.cmp(filename, test_file, shallow=True)
    assert are_equal, f"Files {filename} and {test_file} are not equal"
