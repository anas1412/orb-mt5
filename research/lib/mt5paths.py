"""Where MT5 keeps the shared Files folder.

Override with the MT5_COMMON environment variable, which is what you need on
Windows or on any machine whose Wine prefix or username differs:

    Linux / Wine
      export MT5_COMMON="$HOME/.wine_mt5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files"

    Windows
      set MT5_COMMON=%APPDATA%\\MetaQuotes\\Terminal\\Common\\Files
"""
import os

def common_files():
    env = os.environ.get("MT5_COMMON")
    if env:
        return env
    appdata = os.environ.get("APPDATA")
    if appdata:                                    # native Windows
        return os.path.join(appdata, "MetaQuotes", "Terminal", "Common", "Files")
    user = os.environ.get("USER", "")              # Wine mirrors the Linux user
    return os.path.expanduser(
        "~/.wine_mt5/drive_c/users/%s/AppData/Roaming/MetaQuotes/Terminal/Common/Files" % user)

COMMON = common_files()

def bars(symbol="XAUUSD"):
    return os.path.join(COMMON, "bars_%s.csv" % symbol)
