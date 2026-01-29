# Pepper Grinder (Chowdren 64-bit) on Knulli — Current Status not working

This repo documents my attempt to run **Pepper Grinder** on a retro handheld using PortMaster and the Chowdren (64-bit) build (GOG version, DRM-free).

Buy the game here: [Pepper Grinder](https://www.gog.com/en/game/pepper_grinder)

the game was built using construct 2 and exported with Chowdren, very much like Iconoclasts 
this port is based on the existing [iconoclast port](https://portmaster.games/detail.html?name=iconoclasts)

---------

Last Updated Was: Wednesday 28

- I got a script that is able to make the game "start" running via Westonpack and Box64 but the game closes because of an out of memory error. you can check weston.sh
- The game uses 730mb to 800mb of RAM when running on my Steam deck with linux x86 this is because all assets are preloaded by Chowdren (I think) 
- Iconoclasts in comparison uses 300mb of ram when running 
- So that can explain why Iconoclasts runs but this game will cause an out of memory error. 

## So what did I try? 

I thought that if there was a way to reduce the RAM usage of the game it should be able to run, currently (check log.txt) 
the game is killed when using about 390mb of ram by the system (on Knulli) So I figured if we can half texture resolution that 
should make it so the game uses less ram. 

So I went on an adventure to be able to Unpack the assets of the game, modify them, repack them and have the game continue to work. 
On that I was **Succesful** 

<img width="1602" height="1004" alt="image" src="https://github.com/user-attachments/assets/f732e349-a55d-4410-8741-dc5bf4bd1501" />

I was able to Unpack the files get assets to images, modify the sprites for an animation to be color Magenta, repack the assets and replace the 
original Assets.dat file by my modified file. So on the screenshot you can see the modified asset running. 

So: 
Extracting -> Decoding Images -> modifying image color (pixel data) -> Re-encoding Images -> Re-packing Assets WORKS 

what does not work is changing the size of those textures and re-packing the assets, any time I tried to reduce texture size 
when using the modified Assets.dat file the game will become very slow and RAM usage actually increases: 

<img width="1768" height="587" alt="image" src="https://github.com/user-attachments/assets/bfd4d674-5710-4bd1-884e-09ecadec73ab" />

I vibe coded a number of different fixes and solutions but was ultimately not able to find a way to have "resized images" work. 

I also tried to do only audio modifications by reducing bitrate/samples and this actually worked I did saw about 18mb less of ram being used. But the 
majority of ram still seems to be images. 

for a more detailed view of how this happened and how I was able to extract the files you can check the LLM generated summary at "Pepper Grinder Port Attempt for PortMaster.md"

## Trying to Patch the game via LD_PRELOAD 

My last attempt was to try to hook into the functions of the game loading textures into the GPU and halving texture resultion on that point, however. While the hooks worked and I could see the game become blurier on gameplay, ram comsumption stayed the same. 

- with the pepper_optimizer.c game textures were blurry and ram stayed the same. 
- with the pepper_optimizer_v2.c I tried to half texture resolution AND also keep track of the memory to free it once the texture is uploaded to gpu. BUT this makes the game crash. 

to test this you need to build any of the files and run then: 

### Building and Testing
```bash
# Build the hooks (on Ubuntu/Linux)
gcc -shared -fPIC -O3 -o libpepperopt.so pepper_optimizer.c -ldl -lpthread -lm

# Run with hook on Steam Deck
LD_PRELOAD=/path/to/libpepperopt.so ./Chowdren
```

### Results
```
[PepperOpt2] ========================================
[PepperOpt2] Session Summary:
[PepperOpt2]   Total textures: 10258
[PepperOpt2]   Scaled textures: 3079
[PepperOpt2]   Original size: 601.58 MB
[PepperOpt2]   Optimized size: 187.32 MB
[PepperOpt2]   GPU memory saved: 414.25 MB
[PepperOpt2]   Buffers freed: 0 (0.00 MB)
[PepperOpt2] ========================================
```

**GPU memory was reduced by 414MB, but system RAM stayed at ~717MB.** This confirms that Chowdren keeps all decompressed image buffers in its own internal memory, not just in the GPU. The buffers are allocated BEFORE `glTexImage2D` is called, and Chowdren never frees them (likely needs them for CPU access or context recovery).

### Why This Approach Failed
```
Chowdren's loading flow:
1. Read compressed data from Assets.dat
2. Decompress via zlib → 604MB allocated HERE (internal buffers)
3. Call glTexImage2D() → We intercept HERE (too late!)
4. GPU receives texture
5. Internal buffers are NEVER freed
```

Attempting to free the buffers after GPU upload (`pepper_optimizer_v2.c` with `PEPPER_AGGRESSIVE_FREE=1`) causes a crash because Chowdren still uses those buffers internally.

****

so for now what I have achieved so far is tools to effectively be able to mod the games textures but nothing more. 

the Scripts folder is full with the different tools I created, look at scripts.md for instructions. 

## What is next? 
Nothing haha, I have exhausted the effort and knowledge I am willing to give. Here is my conclussion: 

- Chowdren preloads everything into ram and needs it all to be the same to function.
- textures cannot be resized and repacked. 
- even if you half the textures send to GPU the engine keeps the assets on ram. 
- I don't think it is possible to do this. But hey, YOU could prove me wrong? 

All scripts on this project were vibe coded. 

