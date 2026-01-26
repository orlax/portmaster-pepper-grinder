#!/bin/bash

XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}

if [ -d "/opt/system/Tools/PortMaster/" ]; then
  controlfolder="/opt/system/Tools/PortMaster"
elif [ -d "/opt/tools/PortMaster/" ]; then
  controlfolder="/opt/tools/PortMaster"
elif [ -d "$XDG_DATA_HOME/PortMaster/" ]; then
  controlfolder="$XDG_DATA_HOME/PortMaster"
else
  controlfolder="/roms/ports/PortMaster"
fi

source $controlfolder/control.txt

[ -f "${controlfolder}/mod_${CFW_NAME}.txt" ] && source "${controlfolder}/mod_${CFW_NAME}.txt"

get_controls

# Set directories
GAMEDIR=/$directory/ports/pepper
DATADIR=$GAMEDIR/gamedata
BINARY="Chowdren"

cd "$GAMEDIR"

> "$GAMEDIR/log.txt" && exec > >(tee "$GAMEDIR/log.txt") 2>&1

# Create XDG dirs and set premissions
CONFDIR="$GAMEDIR/conf/config"
$ESUDO mkdir -p "${CONFDIR}"
LOCALDIR="$GAMEDIR/conf/local"
$ESUDO mkdir -p "${LOCALDIR}"
$ESUDO chmod a+x "$DATADIR/bin64/$BINARY"

# Mount Weston runtime
weston_dir=/tmp/weston
$ESUDO mkdir -p "${weston_dir}"
weston_runtime="weston_pkg_0.2"
if [ ! -f "$controlfolder/libs/${weston_runtime}.squashfs" ]; then
  if [ ! -f "$controlfolder/harbourmaster" ]; then
    pm_message "This port requires the latest PortMaster to run, please go to https://portmaster.games/ for more info."
    sleep 5
    exit 1
  fi
  $ESUDO $controlfolder/harbourmaster --quiet --no-check runtime_check "${weston_runtime}.squashfs"
fi
if [[ "$PM_CAN_MOUNT" != "N" ]]; then
    $ESUDO umount "${weston_dir}"
fi
$ESUDO mount "$controlfolder/libs/${weston_runtime}.squashfs" "${weston_dir}"


# rocknix mode on rocknix panfrost/freedreno; libmali not supported
if [[ "$CFW_NAME" = "ROCKNIX" ]]; then
  export rocknix_mode=1
  if ! glxinfo | grep "OpenGL version string"; then
    pm_message "This Port does not support the libMali graphics driver. Switch to Panfrost to continue."
    sleep 5
    exit 1
  fi
fi

# the default pulseaudio backend doesn't always work well
if [[ "$CFW_NAME" = "ROCKNIX" ]] || [[ "$CFW_NAME" = "AmberELEC" ]]; then
  audio_backend=alsa
fi

# Exports (running as root so should work on with WP)
export SENTRY_DSN=""
export SENTRY_DISABLE=1

export CHOWDREN_FPS=30
export LIBGL_FB_TEX_SCALE=0.25
export LIBGL_SKIPTEXCOPIES=1

export BOX64_LOG=1
export BOX64_ALLOWMISSINGLIBS=1
export BOX64_DYNAREC=1

# Start game 
pushd $DATADIR/

$GPTOKEYB "$BINARY" -k &

# Start Westonpack
$ESUDO env \
SDL_AUDIODRIVER=$audio_backend \
BOX64_LD_LIBRARY_PATH="./bin64":"$GAMEDIR/box64/native" \
$weston_dir/westonwrap.sh headless noop kiosk crusty_glx_gl4es \
XDG_CONFIG_HOME=$CONFDIR \
XDG_DATA_HOME=$LOCALDIR \
$GAMEDIR/box64/box64 ./bin64/$BINARY

GAME_RC=$?

popd

# Clean up after ourselves
$ESUDO $weston_dir/westonwrap.sh cleanup
if [[ "$PM_CAN_MOUNT" != "N" ]]; then
    $ESUDO umount "${weston_dir}"
fi

# --- Post-mortem diagnostics (logged to log.txt) ---
echo
echo "===== POST-MORTEM $(date) ====="
echo "Exit code: $GAME_RC"
echo "--- swapon --show ---"
swapon --show || true
echo "--- /proc/swaps ---"
cat /proc/swaps || true
echo "--- free -m ---"
free -m || true
echo "--- OOM (dmesg tail) ---"
dmesg | tail -n 120 | grep -i -E "oom|killed process|out of memory" || true
echo "--- zram stats ---"
cat /sys/block/zram0/mm_stat 2>/dev/null || true
cat /sys/block/zram0/stat 2>/dev/null || true
echo "===== END POST-MORTEM ====="
echo
# --- end post-mortem ---


pm_finish
