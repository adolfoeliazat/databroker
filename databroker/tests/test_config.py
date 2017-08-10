from databroker import lookup_config, Broker
from databroker.broker import load_component
import databroker.databroker
from databroker.utils import ensure_path_exists
import imp
import os
import pytest
import six
import sys
import yaml

if six.PY2:
    FileNotFoundError = IOError

if sys.version_info >= (3, 0):
    from bluesky.examples import det
    from bluesky.plans import count

py3 = pytest.mark.skipif(sys.version_info < (3, 0), reason="requires python 3")

EXAMPLE = {
    'metadatastore': {
        'module': 'databroker.headersource.mongo',
        'class': 'MDS',
        'config': {
            'host': 'localhost',
            'port': 27017,
            'database': 'mds_database_placholder',
            'timezone': 'US/Eastern'}
    },
    'assets': {
        'module': 'databroker.assets.mongo',
        'class': 'Registry',
        'config': {
            'host': 'localhost',
            'port': 27017,
            'database': 'assets_database_placeholder'}
    }
}


def test_load_component():
    for config in EXAMPLE.values():
        component = load_component(config)
        assert component.config == config['config']
        assert component.__class__.__name__ == config['class']
        assert component.__module__  == config['module']


def test_from_config():
    Broker.from_config(EXAMPLE)


def test_lookup_config():
    name = '__test_lookup_config'
    path = os.path.join(os.path.expanduser('~'), '.config', 'databroker',
                        name + '.yml')
    ensure_path_exists(os.path.dirname(path))
    with open(path, 'w') as f:
        yaml.dump(EXAMPLE, f)
    actual = lookup_config(name) 
    broker = Broker.named(name)  # smoke test
    os.remove(path)
    assert actual == EXAMPLE

    with pytest.raises(FileNotFoundError):
        lookup_config('__does_not_exist')

def test_legacy_config():
    name = databroker.databroker.SPECIAL_NAME
    assert 'test' in name

    path = os.path.join(os.path.expanduser('~'), '.config', 'databroker',
                        name + '.yml')

    if os.path.isfile(path):
        os.remove(path)
        # Test config was dirty. We cleaned up for next time, but we cannot
        # recover. Tests must be re-run.
        assert False

    # Since it does not exist, no singleton should be made on import.

    with pytest.raises(AttributeError):
        databroker.databroker.DataBroker

    with pytest.raises(AttributeError):
        databroker.databroker.get_table

    # Now make a working legacy config file.
    ensure_path_exists(os.path.dirname(path))
    with open(path, 'w') as f:
        yaml.dump(EXAMPLE, f)

    # The singleton should be made this time.
    imp.reload(databroker.databroker)
    databroker.databroker.DataBroker
    databroker.databroker.get_table
    imp.reload(databroker)
    from databroker import db, DataBroker, get_table, get_images

    # now make a broken legacy config file.
    broken_example = EXAMPLE.copy()
    broken_example['metadatastore'].pop('module')
    with open(path, 'w') as f:
        yaml.dump(broken_example, f)

    # The singleton should not be made, and it should warn on import
    # about the legacy config being broken.
    with pytest.warns(UserWarning):
        imp.reload(databroker.databroker)

    # Clean up
    os.remove(path)


@py3
def test_legacy_config_warnings(RE):
    name = databroker.databroker.SPECIAL_NAME
    assert 'test' in name
    path = os.path.join(os.path.expanduser('~'), '.config', 'databroker',
                        name + '.yml')
    ensure_path_exists(os.path.dirname(path))
    with open(path, 'w') as f:
        yaml.dump(EXAMPLE, f)

    imp.reload(databroker.databroker)
    imp.reload(databroker)
    from databroker import db, DataBroker, get_table, get_events

    RE.subscribe(db.insert)
    uid, = RE(count([det]))
    with pytest.warns(UserWarning):
        assert len(get_table(db[uid]))
    with pytest.warns(UserWarning):
        assert list(get_events(db[uid]))

    # Clean up
    os.remove(path)
