# pyright: strict


from typing import cast

from sysconf.config.domains import Domain
from sysconf.domains.dconf import create_dconf_domain
from sysconf.domains.gsettings import create_gsettings_domain
from sysconf.domains.shell_domains import create_list_shell_domain, create_map_shell_domain
from sysconf.utils.str import unindent


builtin_domains: list[Domain] = cast(
    list[Domain],
    [
        create_dconf_domain(),
        create_gsettings_domain(),
        # can't use these as is becuase they're not encoding the structured values
        # these would need the values to be strings in the dconf format
        # create_map_shell_domain(
        #     key='dconf',
        #     add_script='dconf write $key "$value"',
        #     update_script='dconf write $key "$value"',
        #     remove_script='dconf reset $key',
        # ),
        # create_map_shell_domain(
        #     key='gsettings',
        #     add_script='gsettings set $key1 $key2 "$value"',
        #     update_script='gsettings set $key1 $key2 "$value"',
        #     remove_script='gsettings reset $key1 $key2',
        # ),
        create_list_shell_domain(
            key='apt',
            path_depth=0,
            add_script='sudo apt install -y $value',
            remove_script='sudo apt remove -y $value',
        ),
        create_list_shell_domain(
            key='snap',
            path_depth=0,
            add_script='sudo snap install $value',
            remove_script=unindent("""
                value="$value";
                sudo snap remove ${value%% *};
            """),
        ),
        create_list_shell_domain(
            key='pip',
            path_depth=0,
            add_script='pip install --break-system-packages $value',
            remove_script='pip uninstall --break-system-packages -y $value',
        ),
        create_list_shell_domain(
            key='groups',
            path_depth=0,
            add_script='sudo groupadd "$value"',
            remove_script='sudo groupdel "$value"',
        ),
        create_list_shell_domain(
            key='user-groups',
            path_depth=1,
            add_script='sudo usermod -aG "$value" "$key"',
            remove_script='echo "Removing group from user not implemented"; exit 1;',
        ),
        create_map_shell_domain(
            key='git-config-global',
            path_depth=1,
            add_script='git config --global "$key" "$value"',
            update_script='git config --global "$key" "$value"',
            remove_script='git config --global --unset "$key"',
        ),
        create_list_shell_domain(
            key='vscode-extensions',
            path_depth=0,
            add_script='code --install-extension $value',
            remove_script='code --uninstall-extension $value',
        ),
        create_map_shell_domain(
            key='symlinks',
            path_depth=1,
            add_script=unindent("""
                rm -f $key;
                ln -sf $value $key;
            """),
            update_script=unindent("""
                rm -f $key;
                ln -sf $value $key;
            """),
            remove_script='rm -f $key',
        ),
        create_list_shell_domain(
            key='apt-repository',
            path_depth=0,
            add_script=unindent("""
                sudo add-apt-repository -y $value;
                sudo apt update;
            """),
            remove_script=unindent("""
                sudo add-apt-repository -r -y $value;
                sudo apt update;
            """),
        ),
        create_map_shell_domain(
            key='apt-source-list',
            path_depth=1,
            add_script=unindent("""
                echo "$value" | sudo tee /etc/apt/sources.list.d/$key > /dev/null; 
                sudo chmod 644 /etc/apt/sources.list.d/$key;
                sudo apt update;
            """),
            update_script=unindent("""
                echo "$value" | sudo tee /etc/apt/sources.list.d/$key > /dev/null; 
                sudo chmod 644 /etc/apt/sources.list.d/$key;
                sudo apt update;
            """),
            remove_script=unindent("""
                sudo rm -f /etc/apt/sources.list.d/$key; 
                sudo apt update;
            """),
        ),
        create_map_shell_domain(
            key='apt-keyring',
            path_depth=1,
            add_script=unindent("""
                sudo install -m 0755 -d $(dirname "$key"); 
                echo "$value" | sudo tee "$key" > /dev/null; 
                sudo chmod 644 "$key";
            """),
            update_script=unindent("""
                echo "$value" | sudo tee "$key" > /dev/null; 
                sudo chmod 644 "$key";
            """),
            remove_script='sudo rm -f "$key"',
        ),
        create_list_shell_domain(
            key='file-lines',
            path_depth=1,
            add_script='echo "$value" >> $key',
            remove_script='sed -i "/^$value$/d" $key',
        ),
    ],
)
