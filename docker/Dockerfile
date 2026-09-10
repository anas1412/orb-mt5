# MetaTrader 5 under Wine, headless, with this repo's pipeline -- the engine
# behind `report.sh`, runnable on any x86_64 box.
#
# The layout inside is the host's layout exactly (portable install under
# ~/.wine_mt5), so research/*.sh run unchanged. History, tester caches and the
# terminal's Config live on volumes: the image holds no account and no data.
#
#   docker build -f docker/Dockerfile -t orb-mt5 .
#   docker run --rm -v orb-bases:"/root/.wine_mt5/drive_c/Program Files/MetaTrader 5/Bases" \
#     -v orb-tester:"/root/.wine_mt5/drive_c/Program Files/MetaTrader 5/Tester" \
#     -v orb-config:"/root/.wine_mt5/drive_c/Program Files/MetaTrader 5/Config" \
#     -v "$PWD/out:/out" --env-file accounts/ftmo.env \
#     orb-mt5 bash research/report.sh strategies/asia-gold.toml 2026.08.24 2026.09.09
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN dpkg --add-architecture i386 && apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates wget gnupg xvfb xauth procps python3 python3-matplotlib git curl \
    && mkdir -pm755 /etc/apt/keyrings \
    && wget -qO /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key \
    && wget -qNP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/ubuntu/dists/noble/winehq-noble.sources \
    && apt-get update && apt-get install -y --install-recommends winehq-stable \
    && rm -rf /var/lib/apt/lists/*

ENV HOME=/root USER=root WINEPREFIX=/root/.wine_mt5 WINEDEBUG=-all DISPLAY=:99 \
    WINEDLLOVERRIDES="mscoree=d;mshtml=d" MT5="/root/.wine_mt5/drive_c/Program Files/MetaTrader 5"

# A fresh prefix. mono and gecko are declined through the overrides above; the
# terminal needs neither.
RUN xvfb-run -a wineboot -u && wineserver -w

# The terminal binaries and the standard MQL5 library, staged from a working
# install (docker/mt5/, ignored by git). servers.dat is the broker directory,
# not an account.
COPY docker/mt5/ "${MT5}/"
RUN touch "${MT5}/portable" && mkdir -p "${MT5}/Bases" "${MT5}/Tester" "${MT5}/logs" \
      "/root/.wine_mt5/drive_c/users/root/AppData/Roaming/MetaQuotes/Terminal/Common/Files"

# The repo, laid out as on the host: sources symlinked into the MQL5 tree, the
# .ini files symlinked into the terminal folder.
WORKDIR /root/orb/strategy
COPY mql5/ mql5/
COPY update.sh README.md ./
COPY research/ research/
COPY strategies/ strategies/
RUN ln -sf /root/orb/strategy/mql5/ORB.mq5 "${MT5}/MQL5/Experts/ORB.mq5" \
    && ln -sf /root/orb/strategy/mql5/BarDump.mq5 "${MT5}/MQL5/Experts/BarDump.mq5" \
    && ln -sf /root/orb/strategy/mql5/CheckBrokerOffset.mq5 "${MT5}/MQL5/Experts/CheckBrokerOffset.mq5" \
    && ln -sf /root/orb/strategy/mql5/Panel.mqh "${MT5}/MQL5/Include/Panel.mqh" \
    && ln -sf /root/orb/strategy/mql5/TimeZones.mqh "${MT5}/MQL5/Include/TimeZones.mqh" \
    && for s in SyncDump DumpD1 TestTimeZones; do ln -sf /root/orb/strategy/mql5/$s.mq5 "${MT5}/MQL5/Scripts/$s.mq5"; done \
    && for i in /root/orb/strategy/mql5/config/*.ini; do ln -sf "$i" "${MT5}/$(basename "$i")"; done \
    && for i in tester dump sync d1; do ln -sf /root/orb/strategy/$i.ini "${MT5}/$i.ini"; done

# bash from here: the loop below uses ${var//x/y}, which dash rejects. Placed
# late so the layers above keep their cache.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Compile at build time and refuse the image if it does not compile. MetaEditor
# exits 1 on success, so the verdict is read from the log (UTF-16LE).
RUN cd "${MT5}" && for f in Experts/ORB Experts/BarDump Scripts/SyncDump Scripts/DumpD1; do \
      xvfb-run -a wine MetaEditor64.exe /compile:"MQL5\\${f//\//\\}.mq5" /log >/dev/null 2>&1 || true; \
      iconv -f UTF-16LE -t UTF-8 "MQL5/$f.log" | grep -q "0 errors" || { echo "compile failed: $f"; iconv -f UTF-16LE -t UTF-8 "MQL5/$f.log" | tail -5; exit 1; }; \
      echo "compiled $f"; done && ls -la "${MT5}/MQL5/Experts/ORB.ex5"

VOLUME ["/root/.wine_mt5/drive_c/Program Files/MetaTrader 5/Bases", \
        "/root/.wine_mt5/drive_c/Program Files/MetaTrader 5/Tester", \
        "/root/.wine_mt5/drive_c/Program Files/MetaTrader 5/Config", \
        "/root/.wine_mt5/drive_c/users/root/AppData/Roaming/MetaQuotes/Terminal/Common/Files"]
COPY docker/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash", "research/run_window.sh", "2026.08.24", "2026.09.09"]
