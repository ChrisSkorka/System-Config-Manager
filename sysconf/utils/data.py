# pyright: strict

from sysconf.config.serialization import YamlSerializable


def get_flattened_dict(
    data: YamlSerializable,
    path_depth: int,
) -> dict[tuple[str, ...], YamlSerializable]:
    """
    Flatten a nested dictionary up to a certain depth.

    Keys are tuples of the keys to get to the value.

    Notes:
    - keys are always strings
    - dictionaries beyond path_depth are not flattened
    - non-dict values at intermediate levels are not allowed except None
    - None values at intermediate levels are skipped

    E.g.: for path_depth=2:
    ```python
        {
            'a': {
                'b': {
                    'c': 1,
                    'd': 2,
                },
                'e': 3,
            },
            'f': None,
        }
        # becomes
        {
            ('a', 'b'): {
                'c': 1,
                'd': 2,
            },
            ('a', 'e'): 3,
            # no f
        }
    ```
    """

    flattaned_map: dict[tuple[str, ...], YamlSerializable] = {(): data}

    # flatten first `path_depth` levels
    for _ in range(path_depth):

        # check this level can be flattened
        assert all(
            isinstance(v, dict) or v is None
            for v in flattaned_map.values()
        ), f'Non-dict value at intermediate level encountered: {flattaned_map}'

        # flatten one level
        flattaned_map = {
            keys + (key,): value
            for keys, next_map in flattaned_map.items()
            if isinstance(next_map, dict)
            for key, value in next_map.items()
        }

    return flattaned_map


class DataStructure:
    """
    Utility class for working with data structures.

    Can be used like a nested dict/list with tuple keys.

    Notes:
    - Should be initialized with the correct root data structure (dict, list, scalar)
    - Automatically creates intermediate dicts/lists as needed when setting values
    - When retrieving, when a path does not exist, returns None
    - When setting does not replace None or other scalar values with collections

    Example:
    ```python
    data = DataStructure({})
    data[('a', 'b', 0)] = 'value1'
    data[('a', 'b', 1)] = 'value2'
    data[('a', 'c')] = 'value3'

    print(data.get_data())
    # Output:
    {
        'a': {
            'b': ['value1', 'value2'],
            'c': 'value3',
        }
    }
    ```
    """

    def __init__(self, data: YamlSerializable) -> None:
        super().__init__()

        self.data = data

    def __getitem__(self, path: tuple[str | int, ...]) -> YamlSerializable:

        assert all(
            isinstance(key, (str, int))
            for key in path
        ), f'Invalid path keys: {path}'

        current_node: YamlSerializable = self.data

        for key in path:

            if current_node is None:
                return None

            match key:
                case str():
                    assert isinstance(current_node, dict)
                    current_node = current_node.get(key, None)
                case int():
                    assert isinstance(current_node, list)
                    if 0 <= key < len(current_node):
                        current_node = current_node[key]
                    else:
                        current_node = None

        return current_node

    def __setitem__(
        self,
        path: tuple[str | int, ...],
        value: YamlSerializable,
    ) -> None:

        assert all(
            isinstance(key, (str, int))
            for key in path
        ), f'Invalid path keys: {path}'

        if path == ():
            self.data = value
            return

        target: YamlSerializable = self.data
        for key_current, key_next in zip(path, [*path[1:], None]):

            next_default: YamlSerializable = None
            match key_next:
                case str():
                    next_default = {}
                case int():
                    next_default = []
                case None:
                    next_default = value

            match key_current:
                case str():
                    assert isinstance(target, dict)
                    if key_current not in target:
                        target[key_current] = next_default
                    target = target[key_current]
                case int():
                    assert isinstance(target, list)
                    assert 0 <= key_current <= len(target)
                    if key_current < len(target):
                        target = target[key_current]
                    else:
                        target.append(next_default)

    def get_data(self) -> YamlSerializable:
        """
        Get the underlying data structure.
        """

        return self.data
