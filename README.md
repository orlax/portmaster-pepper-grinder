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

so for now what I have achieved so far is tools to effectively be able to mod the games textures but nothing more. 

the Scripts folder is full with the different tools I created, look at scripts.md for instructions. 

## What is next? 
I don't know I think I am gonna rest from this project, I have this two ideas: 
- figure out how to succesfully resize images and have the game still work normally.
- PATCH the function of the game that actually loads the textures to half the size "on the fly" but this sounds like.. super complicated. 



