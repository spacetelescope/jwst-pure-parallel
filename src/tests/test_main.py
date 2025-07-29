from csv import DictReader
from importlib import resources

from pytest import fail, fixture
from jwpure.analyze import Scenario


@fixture
def inp_path():
    path = resources.files('jwpure.data') / 'pure_slots.csv'
    return path



def test_allslots(inp_path, tmp_path_factory):
    """Verify case where all slots should be returned with equal values.

    Ingore extra columns written to output file by `Scenario.save()`.
    """

    slot, config, visit = Scenario.constraint_parameters()
    scenario = Scenario()
    constraint = (
        (slot.inst.isin(['MIRI', 'NIRCam', 'NIRISS', 'NIRSpec'])) &
        (slot.slotdur > 0) &
        (slot.ra.between(0, 360)) &
        (slot.glat.between(-90, 90)) &
        (config.nslot >= 0) &
        (config.configdur > 0) &
        (visit.nconfig >= 0)
    )
    scenario.allocate_slots(constraint)
    scenario.summarize()
    out_path = tmp_path_factory.mktemp("test_data") / "test_allslots.csv"
    scenario.save(out_path)

    with open(inp_path, 'r', newline='') as inp_fobj, \
            open(out_path, 'r', newline='') as out_fobj:
        inp_reader = DictReader(inp_fobj)
        out_reader = DictReader(out_fobj)

        # Step 1: Check that output headers start with input headers
        inp_headers = inp_reader.fieldnames
        out_headers = out_reader.fieldnames

        assert inp_headers == out_headers[:len(inp_headers)], (
            f"Output columns do not start with input columns.\n"
            f"Expected: {inp_headers}\n"
            f"Found:    {out_headers[:len(inp_headers)]}"
        )

        # Step 2: Compare input columns row-by-row
        for i, (in_row, out_row) in enumerate(
                zip(inp_reader, out_reader), start=1):
            for col in inp_headers:
                in_val = in_row[col]
                out_val = out_row[col]
                if '.' in in_val:
                    in_val = float(in_val)
                    out_val = float(out_val)
                assert in_val == out_val, (
                    f"Mismatch at row {i}, column '{col}': "
                    f"input='{in_val}', output='{out_val}'"
                )

        # Step 3: Ensure no extra rows exist
        try:
            next_in = next(inp_reader)
            fail("Input file has more rows than output file.")
        except StopIteration:
            pass

        try:
            next_out = next(out_reader)
            fail("Output file has more rows than input file.")
        except StopIteration:
            pass
