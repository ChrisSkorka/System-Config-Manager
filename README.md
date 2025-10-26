# System-Config-Manager
Configuration based package and config manager

Initially developed for mainstream linux distributions, and acts similar to nixOS.
However instead of placing strong emphasis on absolute reproducibility, this aims to be easy to use and allow configs to transfer between distributions and versions as much as technically possible.

Other processes can still manipulate the system independently of this tool and it's config.
E.g. a major system update may add and remove system packages, but this tool will not remove any packages added by the system update, only packages that this tool added.

## Todo

- tests
- default config location via env var
- support $ref for split configs (use ruamel.yaml)
- package registry system
- edit command
- rollbacks command: apply config before current
- better assert error messages (no stack trace)
- class for overall (cli) command
- logging
- domain for rebost & ordered file edits (not just unordered file-lines)
- handle duplicates in before & after

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

before:
  - sudo apt update

after:
  - sudo apt autoremove -y

config:
  # System Packages
  - apt:
      - python3.12-venv
      - python3-pip
      - git
  - snap:
      - code
  - pip:
      - numpy

  # User Groups
  - groups:
      - docker
  - user-groups:
      $(whoami): 
        - docker

  # User Settings
  - dconf:
      /org/gnome/shell/favorite-apps: [
        'org.gnome.Nautilus.desktop', 
        'firefox_firefox.desktop', 
        'spotify_spotify.desktop', 
        'code_code.desktop', 
        'org.gnome.Terminal.desktop',
      ]
  - gsettings:
      # Terminal
      "org.gnome.Terminal.Legacy.Keybindings:/org/gnome/terminal/legacy/keybindings/":
        copy: '<Primary>c'
        paste: '<Primary>v'
      # IO
      org.gnome.desktop.peripherals.mouse:
        speed: -0.2

    # Git Configurations
  - git.config.global:
      user.email: name@email.com
      user.name: Firstname Lastname

    # VS Code Extensions
  - vscode-extensions:
      - vscode.git # Git

  # Config & Dot Files
  - symlink:
      # Shell
      ~/.bashrc: $pwd/shell/.bashrc

  # File Edits
  - file-lines:
      ~/.profile:
        - alias ll='ls -la'

domains:
  # Simple list of items
  apt:
    type: list
    add: sudo apt install -y $value
    remove: sudo apt remove -y $value

  # List with keys as args
  user-groups:
    type: list
    depth: 1
    add: sudo usermod -aG "$value" "$key"
    remove: |
      echo "Removing group from user not implemented"; 
      exit 1;
    
  # Map with key-value pairs
  git-config-global:
    type: map
    add: git config --global $key "$value"
    update: git config --global $key "$value"
    remove: git config --global --unset $key
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