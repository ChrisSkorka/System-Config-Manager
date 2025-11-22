# System-Config-Manager
Configuration based package and config manager

Initially developed for mainstream linux distributions, and acts similar to nixOS.
However instead of placing strong emphasis on absolute reproducibility, this aims to be easy to use and allow configs to transfer between distributions and versions as much as technically possible.

Other processes can still manipulate the system independently of this tool and it's config.
E.g. a major system update may add and remove system packages, but this tool will not remove any packages added by the system update, only packages that this tool added.

## Todo

- tests
- save current.yaml after each action
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
- allow duplicates for lists & handle add/remove

## Installation

Clone (download and extract) the repo and place in your preferred installation directory. (Anywhere where you won't delete it will do)

```shell
cd to/this/repositories/root/directory
pip install --break-system-packages -e .
```

If `pip` is not a command, try repalcing `pip` with `pip3` or `python -m pip`.
Or installing `pip`, `pip3`, or `python3-pip` depending on your system.

## Usage

```shell
# show the commands that would be run if this were to be applied
python3 -m sysconf preview [/path/to/config]

# apply the config file, execute commands to add & remove things that we're added or removed compared to the last applied config
python -m sysconf apply [/path/to/config]

# show last applied config
python3 -m sysconf show

# show specific config:
python3 -m sysconf show /path/to/main.config.file
```

## Config Files

The config file specifies the schema version, commands to run before applying changes, 
commands to run after applying changes, the desired configuration, and the domains.

The default location of the config file will be:
`~/.config/system-config-manager/config.yaml` (you will have to create this manually)

The default location of the automativally maintained current configuration is:
`~/.config/system-config-manager/.history/current.yaml` (this will be created and managed for you)

Note that the any string values (text) can use yamls `|` syntax for multi line values:
```yaml
before:
  # regular string value
  - ping -c 4 google.com
  # multiline string value
  - |
    COUNT=4;
    URL="google.com";
    ping -c $COUNT $URL;

```

### Version

Currently only version `1` is supported and documented below

### Before (optional)

A list of shell commands/scripts to run everytime there are changes in the `config` section compared to the currently applied config.

All `before` entries are executed in order once when the `apply` command is invoked and there are changes in `config`. If there are no changes in `config`, no `before` entries are run.

If any `before` entry fails (returns a non-zero code), you will be prompted for how to continue.

E.g.:
```yaml
before:
  - ping -c 1 google.com # check internet connection
  - sudo apt update
```

### After (optional)

A list of shell commands/scripts to run everytime changes in the `config` section have been applied.

All `after` entries are executed in order once the `apply` command has applied all changes in `config`. If there are no changes in `config`, no `after` entries are run.

If any `after` entry fails (returns a non-zero code), you will be prompted for how to continue.

E.g.:
```yaml
after:
  - sudo apt autoremove -y
  - sudo apt clean
```

### Config

The `config` section is a "list of maps of domain names to domain specific configuration data structures".

The first level in the `config` entry is a list. Each list item is a "section" and can contain each domain at most one time.

Each domain mapping maps the domain name to a datastructure (list or map) specific to that domain.

E.g.:
```yaml
config:
  # section 1
  - list-domain: # first domain in section 1
      - item-1
      - item-2
    # note: no `-` before domain name
    map-domain: # second domain in section 1
      name-1: value-1
      name-2: value-2
    # cannot repeat list-domain within this section
  # section 2
  - list-domain: # first domain in section 2
      - item-3
      - item-4
```

### Domains

The `domains` section specify how domains within the `config` sections are structures and how to process changes.

Each domain specifies the commands/scripts to add, remove, and sometimes update configuration entries.

Domains can be one of two types: list and map

List domains have a list of items and only support the `add` and `remove` actions.

E.g.:
```yaml
domains:
  list-domain:
    type: list
    add: sudo package-manager install -y $value
    remove: sudo package-manager remove -y $value
      
```

Map domains have key-value pairs and support `add` for new keys, `remove` for no longer existing keys, and `update` for entries where the key is the same but the value has changed

E.g.:
```yaml
domains:
  map-domain:
    type: map
    add: setting set $key "$value"
    update: setting update $key "$value"
    remove: setting delete $key
```

List domains can also have a keys that can be used within the commands as variables. Note that when values change it will be interpreted as having removed the old entry, and adding a new entry in it's place.

The 'path' leading to the value / list item is made available to the commands/scripts with variables `$key0`, `$key1`, `$key2`, etc (`$key0` = `$key`)

E.g.:
```yaml
config:
  # a domain demostrating a list that has keys to specify the chown user, 
  # and directory that a file should be created in
  - list-domain-with-keys:
      root:
        /root/directory-1:
          - file-1.txt
          - file-2.txt
        /root/directory-2:
          - file-3.txt
          - file-4.txt
      user:
        /home/user/directory-1:
          - file-1.txt
          - file-2.txt
        /home/user/directory-2:
          - file-3.txt
          - file-4.txt

domains:
  list-domain-with-keys:
    type: list
    depth: 2 # how many levels of keys we have
    # $key0 and $key is the system user that should own the file
    # $key1 is directory path of the file
    # $value is the name of the file
    add: |
      FILE_PATH="$key1/$value"
      mkdir -p "$key1"
      touch $FILE_PATH
      sudo chown $key0 $FILE_PATH
    remove: sudo rm "$key1/$value"
    # there is no update, if you changed the 'user' key to 'guest', 
    # it would remove the user files and create new guest files. 
```

### Example

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

## System Design

### Domain-Based Design Pattern
The system is built around **domains** - isolated areas of system configuration:
- Each domain implements the `Domain[Config, Manager]` abstract base class in `sysconf/config/domains.py`
- Domains must provide: `get_key()`, `get_config_from_data()`, `get_manager()`
- Domain implementations live in `sysconf/domains/` (e.g., `gsettings.py`, `dconf.py`)
- Register new domains in `sysconf/config/domain_registry.py`

### Command Pattern with Mixin Architecture
Commands use a sophisticated mixin system:
- Base class: `Command` in `sysconf/commands/command.py`
- Mixins: `CommandArgumentParserBuilder` for argument parsing
- Example: `ComparativeConfigCommandParser` adds config comparison capabilities
- Commands auto-register in `sysconf/cli.py` via the `commands` dict

### Configuration Flow
1. **Deserialize**: Load YAML config files into `SystemConfig` objects
2. **Parse**: YAML → `SystemConfig` via version-specific parsers (`sysconf/config/parser.py`)
3. **Compare**: Old vs New config using `SystemManager` (`sysconf/config/system_config.py`)
4. **Plan**: Generate `DomainAction`s using `Diff` utility (`sysconf/utils/diff.py`)
5. **Execute**: Actions through `SystemExecutor` abstraction (`sysconf/system/executor.py`)