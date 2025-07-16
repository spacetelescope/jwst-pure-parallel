from .analyze import Scenario


def run_scenario():
    scenario = Scenario()
    print('in run_scenario')
    scenario.export_table('slot', 'junk.csv')
