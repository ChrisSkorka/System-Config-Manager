# pyright: strict

from subprocess import CompletedProcess
from unittest.mock import MagicMock

def create_mock_run(
        return_complete_process: CompletedProcess[bytes] \
            | dict[tuple[str, ...], CompletedProcess[bytes]] \
            | None = None,
) -> MagicMock:
        """
        Creates a mock for subprocess.run which returns configured
        fake CompletedProcess instances without actually running any commands.

        Returns a callable mock to replace subprocess.run
        """

        # default if None
        if return_complete_process is None:
            return_complete_process = CompletedProcess(args=(), returncode=0)

        # dict case (map command to return value)
        if isinstance(return_complete_process, dict):

            def get_side_effect(command: tuple[str, ...]) -> CompletedProcess[bytes]:
                return return_complete_process[command]

            return MagicMock(
                side_effect=get_side_effect
            )

        # single return value case
        else:
            return MagicMock(return_value=return_complete_process)
