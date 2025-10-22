# System-Config-Manager
Configuration based package and config manager

Initially developed for mainstream linux distributions, and acts similar to nixOS.
However instead of placing strong emphasis on absolute reproducibility, this aims to be easy to use and allow configs to transfer between distributions and versions as much as technically possible.

Other processes can still manipulate the system independently of this tool and it's config.
E.g. a major system update may add and remove system packages, but this tool will not remove any packages added by the system update, only packages that this tool added.

## Todo

- tests
- pre & post application scripts (e.g. pre: apt update; post: source ~/.profile)
- default config location via env var
- support $ref for split configs (use ruamel.yaml)
- package registry system
- edit command
- rollbacks command: apply config before current
- better assert error messages (no stack trace)
- class for overall (cli) command
- logging
- domain for rebost & ordered file edits (not just unordered file-lines)

## Usage

### Usage

```shell
# show last applied config
python3 -m sysconf show

# show specific config:
python3 -m sysconf show /path/to/main.config.file

# show the commands that would be run if this were to be applied
python3 -m sysconf preview [/path/to/config]

# apply the config file, execute commands to add & remove things that we're added or removed compared to the last applied config
python -m sysconf apply [/path/to/config]
```

### Config Files

`~/.config/system-config-manager/config.yaml`
```yaml
version: 1
  - keyring:
      /etc/apt/keyrings/docker.asc: 
        get: https://download.docker.com/linux/ubuntu/gpg
  - apt-repository:
      ppa:unit193/encryption:
      /etc/apt/sources.list.d/docker.list:
        shell: |
          # Add the repository to Apt sources:
          echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
            $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Apt packages
    # 
    # Run `apt search <keyboards>` to find available packages
  - apt:
      - python3.12-venv
      - python3-pip
      - git
      - veracrypt
    # Snap packages
    # 
    # Run `snap search <keyboards>` to find available packages
  - snap:
      - code
  - pip:
      - numpy
  - user-groups:
      docker
  - users:
      $(whoami):
        groups:
        - docker
  - grub:
      GRUB_DISTRIBUTOR: 
  - dconf:
      /org/gnome/shell/favorite-apps: ['org.gnome.Nautilus.desktop', 'firefox_firefox.desktop', 'spotify_spotify.desktop', 'code_code.desktop', 'org.gnome.Terminal.desktop']

    # Any Gnome Settings
    # This includes system settings, extensions, and gnome applications
    # 
    # run `gsettings list-recursively` to get a list of all settings and current values
    #
    # For schemas with relocatable paths:
    # Run `gsettings list-schemas --print-paths` to get the path
    # or `dconf watch /` and change the setting in the UI to find the path
    # gsettings:
    #   org.gnome.shell.extensions.dash-to-dock:
    #     dash-max-icon-size:  32
  - gsettings:
      # Terminal
      "org.gnome.Terminal.Legacy.Keybindings:/org/gnome/terminal/legacy/keybindings/":
        copy: '<Primary>c'
        paste: '<Primary>v'
      # IO
      org.gnome.desktop.peripherals.mouse:
        speed: -0.2

    # Any Git Configurations
    #
    # Run `git config --list --show-origin` to get a list of all configurations and current values
  - git.config.global:
      user.email: name@email.com
      user.name: Firstname Lastname
    # VS Code Configurations that are not managed by config files
  - vscode:
      extensions:
      # General
      - vscode.git # Git

  - symlink:
      # Shell
      ~/.bashrc: $pwd/shell/bashrc
```

## Domain-Based Design Pattern
The system is built around **domains** - isolated areas of system configuration:
- Each domain implements the `Domain[Config, Manager]` abstract base class in `sysconf/config/domains.py`
- Domains must provide: `get_key()`, `get_config_from_data()`, `get_manager()`
- Domain implementations live in `sysconf/domains/` (e.g., `gsettings.py`, `dconf.py`)
- Register new domains in `sysconf/config/domain_registry.py`

## Command Pattern with Mixin Architecture
Commands use a sophisticated mixin system:
- Base class: `Command` in `sysconf/commands/command.py`
- Mixins: `CommandArgumentParserBuilder` for argument parsing
- Example: `ComparativeConfigCommandParser` adds config comparison capabilities
- Commands auto-register in `sysconf/cli.py` via the `commands` dict

## Configuration Flow
1. **Deserialize**: Load YAML config files into `SystemConfig` objects
2. **Parse**: YAML → `SystemConfig` via version-specific parsers (`sysconf/config/parser.py`)
3. **Compare**: Old vs New config using `SystemManager` (`sysconf/config/system_config.py`)
4. **Plan**: Generate `DomainAction`s using `Diff` utility (`sysconf/utils/diff.py`)
5. **Execute**: Actions through `SystemExecutor` abstraction (`sysconf/system/executor.py`)