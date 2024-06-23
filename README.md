# port_sp2x_patches

## About

Python script to automatically port as many Spice2x patches as possible from one game version to another.

## Requirements

- Install **python 3.6 or newer** *(according to [vermin](https://github.com/netromdk/vermin))*
- Clone the repo and go to its root directory `git clone https://github.com/akitakedits/port_sp2x_patches.git && cd port_sp2x_patches`

## Technique & Limitations

The script iterates through each patch attempting to find its default hex data in the new dll.  
It tries to find slices\* of said data in the new dll, lowering its margin\* value with each iteration.  
This allows for precision to be maximized, avoiding false positives as much as possible.  
The script stops iterating over a patch once it finds only **one** occurence of its slice in the new dll at which point it **assumes** that's the new offset for that patch.  
\**slice: the bytes modified by the patch PLUS a margin.*  
\**margin: the amount of bytes added on either side of the patch's data for matching purposes.*

- **False positive may occur, don't trust the script will do a perfect job every time**.
- Only accepts Memory and Union type patches.
- Union type patches are only compatible if all sub-patches modify bytes at the same offset.
- Union type patches are only compatible if all sub-patches modify the same amount of bytes.

## Usage

`python port_sp2x_patches.py <game_code> <old_dll> <new_dll>`

### Arguments

- `game_code` - The game code (KFC, LDJ, etc..) corresponding to your dll files, not case sensitive.
- `old_dll` - The path to the game's dll you want to port patches **from**. **Must be an unpatched dll.**
- `new_dll` - The path to the game's dll you want to port patches **to**. **Must be an unpatched dll.**

**Requires** the `.json` file containing patches for your `old_dll` in the same directory as the script.  
**It must be be named properly**, matching the PE Identifier and game code for its dll.  

### Example

#### File tree
> port_sp2x_patches/  
> ├─ KFC-6643ed55_663968.json *(patches for soundvoltex_old.dll)*  
> ├─ port_sp2x_patches.py  
> ├─ soundvoltex_new.dll  
> ├─ soundvoltex_old.dll  

#### Command and Output
```
> python port_sp2x_patches.py kfc soundvoltex_old.dll soundvoltex_new.dll
Creating empty 'KFC-6656ee0c_664a78.json'
18 patches loaded from 'KFC-6643ed55_663968.json'

Searching..

[Memory] 'Disable power change' found!
'2874398' -> '2876878'
[Memory] 'Disable monitor change' found!
'2874550' -> '2877030'
[Memory] 'Force BIO2 (KFC) IO in Valkyrie mode' found!
'5082981' -> '5087445'
[Union] 'Game FPS Target' found!
'8641264' -> '8641264'
[Memory] 'Shared mode WASAPI' found!
'5319153' -> '5323553'
[Memory] 'Shared mode WASAPI Valkyrie' found!
'5319544' -> '5323944'
[Memory] 'Unlock All Songs' found!
'6094775' -> '6099143'
'959824' -> '960096'
[Memory] 'Unlock All Difficulties' found!
'3956958' -> '3959582'
[Memory] 'Uncensor album jackets (for K region only)' found!
'8156432' -> '8161368'
[Memory] 'Disable subscreen in Valkyrie mode' found!
'4790094' -> '4794254'
[Memory] 'Timer freeze' found!
'1322885' -> '1323173'
[Union] 'Premium Time Length' found!
'3843065' -> '3843065'
[Memory] 'Valkyrie Mode 60Hz' found!
'2874589' -> '2877069'
'4791691' -> '4795851'
'4794032' -> '4798192'

[Union] 'Note FPS Target': not found
[Memory] 'Hide all bottom text': not found (8/12)
[Memory] 'Premium timer freeze': not found (2/3)
[Memory] 'Hide premium guide banner': not found (0/1)
[Memory] 'Fake Japan Region': not found (0/1)

Results: [13/18] found, 72.22% success rate!
New patches written to 'KFC-6656ee0c_664a78.json'
```