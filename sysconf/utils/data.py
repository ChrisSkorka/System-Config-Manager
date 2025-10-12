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
