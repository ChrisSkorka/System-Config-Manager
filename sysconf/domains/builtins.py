# pyright: strict


from typing import cast

from sysconf.config.domains import Domain, DomainConfig, DomainManager
from sysconf.domains.dconf import DConf
from sysconf.domains.gsettings import GSettings
from sysconf.domains.list_domain import ListDomain
from sysconf.domains.map_domain import MapDomain


builtin_domains: list[Domain[DomainConfig, DomainManager]] = cast(
    list[Domain[DomainConfig, DomainManager]],
    [
        DConf(),
        GSettings(),
        # can't use these as is becuase they're not encoding the structured values
        # these would need the values to be strings in the dconf format
        # MapDomain(
        #     key='dconf',
        #     add_script='dconf write $key "$value"',
        #     update_script='dconf write $key "$value"',
        #     remove_script='dconf reset $key',
        # ),
        # MapDomain(
        #     key='gsettings',
        #     add_script='gsettings set $key1 $key2 "$value"',
        #     update_script='gsettings set $key1 $key2 "$value"',
        #     remove_script='gsettings reset $key1 $key2',
        # ),
        ListDomain(
            key='apt',
            add_script='sudo apt install -y "$item"',
            remove_script='sudo apt remove -y "$item"',
        ),
        ListDomain(
            key='snap',
            add_script='sudo snap install "$item"',
            remove_script='sudo snap remove "$item"',
        ),
        ListDomain(
            key='snap-classic',
            add_script='sudo snap install --classic "$item"',
            remove_script='sudo snap remove "$item"',
        ),
        ListDomain(
            key='pip',
            add_script='pip install --break-system-packages "$item"',
            remove_script='pip uninstall --break-system-packages -y "$item"',
        ),
        ListDomain(
            key='groups',
            add_script='sudo groupadd "$item"',
            remove_script='sudo groupdel "$item"',
        ),
        ListDomain(
            key='user-groups',
            add_script='sudo usermod -aG "$item" "$key"',
            remove_script='echo "Removing group from user not implemented"; exit 1;',
        ),
        MapDomain(
            key='git-config-global',
            add_script='git config --global "$key" "$value"',
            update_script='git config --global "$key" "$value"',
            remove_script='git config --global --unset "$key"',
        ),
        ListDomain(
            key='vscode-extensions',
            add_script='code --install-extension "$item"',
            remove_script='code --uninstall-extension "$item"',
        ),
        MapDomain(
            key='symlinks',
            add_script="""
                rm -f $key;
                ln -sf $value $key;
            """,
            update_script="""
                rm -f $key;
                ln -sf $value $key;
            """,
            remove_script='rm -f $key',
        ),
        ListDomain(
            key='apt-repository',
            add_script="""
                sudo add-apt-repository -y "$item";
                sudo apt update;
            """,
            remove_script="""
                sudo add-apt-repository -r -y "$item";
                sudo apt update;
            """,
        ),
        MapDomain(
            key='apt-source-list',
            add_script="""
                echo "$value" | sudo tee /etc/apt/sources.list.d/$key > /dev/null; 
                sudo chmod 644 /etc/apt/sources.list.d/$key;
                sudo apt update;
            """,
            update_script="""
                echo "$value" | sudo tee /etc/apt/sources.list.d/$key > /dev/null; 
                sudo chmod 644 /etc/apt/sources.list.d/$key;
                sudo apt update;
            """,
            remove_script="""
                sudo rm -f /etc/apt/sources.list.d/$key; 
                sudo apt update;
            """,
        ),
        MapDomain(
            key='apt-keyring',
            add_script="""
                sudo install -m 0755 -d $(dirname "$key"); 
                echo "$value" | sudo tee "$key" > /dev/null; 
                sudo chmod 644 "$key";
            """,
            update_script="""
                echo "$value" | sudo tee "$key" > /dev/null; 
                sudo chmod 644 "$key";
            """,
            remove_script='sudo rm -f "$key"',
        ),
    ],
)
