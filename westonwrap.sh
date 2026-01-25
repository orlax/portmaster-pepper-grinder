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
  #export PORT_32BIT="Y"

  [ -f "${controlfolder}/mod_${CFW_NAME}.txt" ] && source "${controlfolder}/mod_${CFW_NAME}.txt"

  get_controls

  GAMEDIR="/media/SHARE/roms/ports/pepper"
  > "$GAMEDIR/log.txt" && exec > >(tee "$GAMEDIR/log.txt") 2>&1

  # gl4es
  if [ -f "${controlfolder}/libgl_${CFW_NAME}.txt" ]; then
    source "${controlfolder}/libgl_${CFW_NAME}.txt"
  else
    source "${controlfolder}/libgl_default.txt"
  fi

  cd $GAMEDIR/gamedata

  export CHOWDREN_FPS=30
  # this scale controls texture size the lower the less memory used but more pixelated
  export LIBGL_FB_TEX_SCALE=0.25
  export LIBGL_SKIPTEXCOPIES=1

  export BOX64_LOG=1
  export BOX64_ALLOWMISSINGLIBS=1
  export BOX64_DLSYM_ERROR=1
  #export SDL_DYNAMIC_API="libSDL2-2.0.so.0"

  # Make sure gl4es libs are on the loader path first (app only)
  export LD_LIBRARY_PATH="$GAMEDIR/gl4es:$LD_LIBRARY_PATH:$GAMEDIR/box64/native:/usr/lib/arm-linux-gnueabihf:/usr/lib64:/usr/config/emuelec/lib64"

  export BOX64_LIBGL="$GAMEDIR/gl4es/libGL.so.1"
  export SDL_VIDEO_GL_DRIVER="$GAMEDIR/gl4es/libGL.so.1"

  export BOX64_DYNAREC=1
  export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"

  # an llm told me this could work???
  export SENTRY_DSN=""
  export SENTRY_DISABLE=1

  $ESUDO chmod 666 /dev/tty0
  $ESUDO chmod 666 /dev/tty1
  printf "\033c" > /dev/tty0

  # Set executable permissions for sdcards using ext2 or similar.
  chmod +x "$GAMEDIR/box64/box64"
  chmod +x "$GAMEDIR/gamedata/bin64/Chowdren"

# Westonpack setup
  weston_dir=/tmp/weston
  weston_runtime="weston_pkg_0.2"

  CRUSTY_DIR="$weston_dir/lib_aarch64/graphics/crusty_glx"
  GBM_DIR="$weston_dir/lib_aarch64/graphics/crusty_gbm_fix"


  if [ ! -f "$controlfolder/libs/${weston_runtime}.squashfs" ]; then
    if [ ! -f "$controlfolder/harbourmaster" ]; then
      pm_message "This port requires the latest PortMaster to run, please go to https://portmaster.games/ for more info."
      sleep 5
      exit 1
    fi
    $ESUDO $controlfolder/harbourmaster --quiet --no-check runtime_check "${weston_runtime}.squashfs"
  fi

  $ESUDO mkdir -p "${weston_dir}"
  $ESUDO umount "${weston_dir}" 2>/dev/null
  $ESUDO mount "$controlfolder/libs/${weston_runtime}.squashfs" "${weston_dir}"

  LD_LIBRARY_PATH="$GAMEDIR/gl4es:/tmp/weston/lib_aarch64/graphics/crusty_glx:/tmp/weston/lib_aarch64/extra_wayland:/tmp/weston/lib_aarch64" \
  ldd /tmp/weston/lib_aarch64/graphics/crusty_glx/libcrusty.so

  #$GPTOKEYB "Chowdren" -c "$GAMEDIR/pepper.gptk" &
  #pm_message "Loading, please wait... (might take a while!)"

  $ESUDO env \
    WRAPPED_LIBRARY_PATH="$GAMEDIR/gl4es:$CRUSTY_DIR:$weston_dir/lib_aarch64/extra_wayland:$weston_dir/lib_aarch64:$GAMEDIR/box64/native:$GAMEDIR/
  gamedata/bin64" \
    gllib_xwayland="$GBM_DIR:$weston_dir/lib_aarch64/extra_wayland:$weston_dir/lib_aarch64" \
    BOX64_NATIVELIBS="libcrusty.so:libEGL.so.1:libmali.so.0:libGL.so.1" \
    BOX64_LD_LIBRARY_PATH="$GAMEDIR/gl4es:$CRUSTY_DIR:$weston_dir/lib_aarch64:$GAMEDIR/box64/native:$GAMEDIR/gamedata/bin64" \
    BOX64_LOG=1 BOX64_ALLOWMISSINGLIBS=1 BOX64_DLSYM_ERROR=1 BOX64_DYNAREC=1 \
    BOX64_LIBGL="$GAMEDIR/gl4es/libGL.so.1" \
    SDL_VIDEO_GL_DRIVER="$GAMEDIR/gl4es/libGL.so.1" \
    LIBGL_FB_TEX_SCALE=0.25 LIBGL_SKIPTEXCOPIES=1 CHOWDREN_FPS=30 \
    $weston_dir/westonwrap.sh headless noop kiosk crusty_glx \
    $GAMEDIR/box64/box64 $GAMEDIR/gamedata/bin64/Chowdren


  pm_finish