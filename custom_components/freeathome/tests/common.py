import os

def load_fixture(filename):
    """Load a fixture."""
    path = os.path.join(os.path.dirname(__file__), "fixtures", filename)
    with open(path, encoding="utf-8") as fptr:
        return fptr.read()


def init_client_state(client, *args, **kwargs):
    """Set up the per instance state that Client.__init__ creates.

    Tests replace the constructor, so they have to bring the containers
    themselves. Without them the tests would fall back on class attributes
    and share their state, which is exactly what the code no longer does.
    """
    client.devices = set()
    client.monitored_datapoints = {}
    client.monitored_parameters = {}
    client._update_handlers = []
