import sys
import struct
import json
import datetime
from datetime import timezone
from pathlib import Path

# Returns data 'length' number of bits long at 'offset' in 'file'
def read_dword(file, offset):
    file.seek(offset)
    return struct.unpack('<I', file.read(4))[0]

# Returns bytes length from given 'hex_string'
def get_bytes_length(hex_string):
    # Convert hexadecimal string to bytes
    byte_data = bytes.fromhex(hex_string)
    
    # Get the length of the byte data
    return len(byte_data)

# Returns json string from file at 'path'
def get_json(path):
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error reading json from file: {e}")
        return None
    
# Returns identifier for file at 'path' starting 'game_code'
def get_identifier(game_code, path):
    try:
        with open(path, 'rb') as file:
            # Read DOS header to get PE header offset
            pe_header_offset = read_dword(file, 0x3c)
            
            # Check for "PE\0\0" signature
            file.seek(pe_header_offset)
            if file.read(4) != b'PE\0\0':
                raise ValueError(f"File '{path}' is not a valid PE file.")
            
            # Read TimeDateStamp
            timestamp = read_dword(file, pe_header_offset + 8)

            # Read AddressOfEntryPoint
            optional_header_offset = pe_header_offset + 24
            entry_point = read_dword(file, optional_header_offset + 16)

            # Concatenate GameCode, TimeDateStamp, and AddressOfEntryPoint    
            identifier = f"{game_code.upper()}-{timestamp:x}_{entry_point:x}" 
        return identifier
    except Exception as e:
        print(f"Error getting identifier from file: {e}")
        return None

# Returns a list of 'offsets' (accounting for the slice's 'bytes_before") where 'hex_slice' is found in 'dll'
def find_slice(dll, hex_slice, bytes_before):
    slice_bytes = bytes.fromhex(hex_slice) # Convert hex slice string to bytes
    offsets = []  # List to store found offsets
    try:
        with open(dll, 'rb') as f:
            data = f.read()
            offset = 0
            while True:
                # Find the next occurrence of the slice
                offset = data.find(slice_bytes, offset)
                if offset == -1:
                    break  # No more occurrences found
                offsets.append(offset + bytes_before)
                offset += 1  
        return offsets
    except Exception as e:
        print(f"Error finding slice in file: {e}")
        return None
    
# Returns a 'hex_slice' found at 'offset' (-bytes_before and +bytes_after) in 'dll' 
def get_slice(dll, offset, datalength, bytes_before, bytes_after):
    try:
        start_offset = max(0, offset - bytes_before)  # Calculate start offset ensuring it's not negative
        total_size = bytes_before + datalength + bytes_after  # Calculate total size to read
        with open(dll, 'rb') as f:
            # Seek to the specified offset in the file
            f.seek(start_offset)
            # Read the total_size bytes starting from the start_offset, convert to hex
            hex_slice = f.read(total_size).hex().upper()
        return hex_slice
    except Exception as e:
        print(f"Error getting slice from file: {e}")
        return None

# Main
if __name__ == "__main__":    
    # Args handling
    if len(sys.argv) != 4:
        exit("Usage: python port_sp2x_patches.py <game_code> <old_dll> <new_dll>")
    old_dll = sys.argv[2]
    new_dll = sys.argv[3]
    if old_dll == new_dll:
        exit("Error: 'old_dll' must be different from 'new_dll'.")
    game_code = sys.argv[1]
    
    # Sanity checks
    old_identifier = get_identifier(game_code, old_dll)
    new_identifier = get_identifier(game_code, new_dll)
    if old_identifier == new_identifier:
        exit("Error: The provided dll's must differ.")
    
    script_dir = Path(__file__).parent
    old_patches_file = Path(f"{script_dir}\\{old_identifier}.json")
    if not Path.exists(old_patches_file):
        exit(f"Error: Patches '{old_identifier}.json' for the old dll not found.")
    
    # Delete existing new_patches_file if present
    new_patches_file = Path(f"{script_dir}\\{new_identifier}.json")
    if Path.exists(new_patches_file):
        print(f"Deleting existing '{new_patches_file.name}'")
        new_patches_file.unlink()
    
    # Create new_patches_file
    print(f"Creating empty '{new_patches_file.name}'")
    new_patches_file.touch()
    new_items = []

    # Load old_patches_file json data
    old_data = get_json(old_patches_file)
    if "lastUpdated" in old_data[0]:
        if "version" in old_data[0]:
            old_data[0]["version"] = "?"
            old_data[0]["lastUpdated"] = datetime.datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            old_data[0]["source"] = "https://sp2x.two-torial.xyz/"
        new_items.append(json.dumps(old_data[0], indent=4))
        old_data.pop(0)
    old_patches_count = len(old_data)
    print(f"{old_patches_count} patches loaded from '{old_patches_file.name}'")
    
    # Seek patches in new_dll
    print(f"\nSearching..\n")
    not_found = "\n"
    new_patches_count = 0
    # Customizable: Detection sensitivity
    # 'Margin' is the number of bytes added to both sides of hex data slices to be searched for in the new dll
    # The lower the margin the higher the rate of false-positive will be, so adapt max/min values accordingly
    max_margin = 8 # Maximum (starting) margin number
    min_margin_memory = 2 # For memory type patches: Minimum (ending) margin number before it gives up
    min_margin_union = 0 # For union type patches: Same as above. Can typically be lower as union patches tend to look for and replace a larger chunk of hex data 
    min_margin_number = 2 # For union type patches: Same as above. Can typically be lower as union patches tend to look for and replace a larger chunk of hex data 
    # Iterate through patches
    for item in old_data:
        if "type" in item:
            # Memory patches
            if item['type'] == "memory":
                new_item = item
                results = []
                for patch in new_item['patches']:
                    # Reset vars
                    margin = max_margin
                    patchFound = False
                    
                    # Iterate through max -> min margin until ONE match is found in the new dll
                    while not patchFound and margin >= min_margin_memory:
                        old_slice = get_slice(old_dll, patch['offset'], get_bytes_length(patch['dataDisabled']), margin, margin)
                        new_occurences = find_slice(new_dll, old_slice, margin)
                        
                        # If ONE occurence is found in new_dll, assume it's the correct patch
                        if len(new_occurences) == 1:
                            patchFound = True
                            results.append([ patch['offset'], new_occurences[0] ])
                            patch['offset'] = new_occurences[0]
                            break
                        margin -= 1
                
                count_old_patches = len(item['patches'])
                count_results = len(results)
                
                if count_old_patches == count_results:
                    print(f"[Memory] '{new_item['name']}' found!")
                    new_patches_count += 1
                    new_items.append(json.dumps(new_item, indent=4))
                    for result in results:
                        print(f"'{result[0]}' -> '{result[1]}'")
                else:
                    not_found += f"[Memory] '{item['name']}': not found ({count_results}/{count_old_patches})\n"
                        
            # Union patches
            elif item['type'] == "union":
                new_item = item
                # Compatibility checks
                compatible = True
                sample = new_item['patches'][0]['patch']
                for patch in new_item['patches']:
                    if patch['patch']['offset'] != sample['offset']:
                        compatible = False
                        not_found += f"[Union] '{patch['name']}': incompatible (sub-patch offset mismatch)\n"
                        break
                    elif get_bytes_length(patch['patch']['data']) != get_bytes_length(sample['data']):
                        compatible = False
                        not_found += f"[Union] '{patch['name']}': incompatible (sub-patch data length mismatch)\n"
                        break
                    
                if compatible:
                    # Reset vars
                    margin = max_margin
                    itemFound = False
                    result = ""
                    
                    # Iterate through max -> min margin until ONE match is found in the new dll
                    while not itemFound and margin >= min_margin_union:
                        old_slice = get_slice(old_dll, sample['offset'], get_bytes_length(sample['data']), margin, margin)
                        new_occurences = find_slice(new_dll, old_slice, margin)
                        
                        # If ONE occurence is found in new_dll, assume it's the correct patch
                        if len(new_occurences) == 1:
                            itemFound = True
                            result = new_occurences[0]
                            break
                        margin -= 1                        
            
                    if result != "":
                        for patch in new_item['patches']:
                            patch['patch']['offset'] = result
                        new_items.append(json.dumps(new_item, indent=4))
                        new_patches_count += 1
                        print(f"[Union] '{item['name']}' found!\n'{sample['offset']}' -> '{result}'")
                    elif margin <= min_margin_union:
                        not_found += f"[Union] '{item['name']}': not found\n"

            elif item['type'] == "number":
                new_item = item
                margin = max_margin
                patchFound = False
                patch = new_item['patch']

                # Iterate through max -> min margin until ONE match is found in the new dll
                while not patchFound and margin >= min_margin_number:
                    old_slice = get_slice(old_dll, patch['offset'], int(patch['size']), margin, margin)
                    new_occurences = find_slice(new_dll, old_slice, margin)

                    if len(new_occurences) == 1:
                        patchFound = True
                        results.append([ patch['offset'], new_occurences[0] ])
                        patch['offset'] = new_occurences[0]
                        break
                    margin -= 1

    
                if patchFound:
                    print(f"[Number] '{new_item['name']}' found!")
                    new_patches_count += 1
                    new_items.append(json.dumps(new_item, indent=4))
                else:
                    not_found += f"[Number] '{item['name']}': not found\n"

    # Print results
    print(not_found)
    print(f"Results: [{new_patches_count}/{old_patches_count}] found, {round((new_patches_count/old_patches_count) * 100, 2)}% success rate! ")

    # Write final output to file
    new_data = [json.loads(item) for item in new_items]
    try:
        with open(new_patches_file, "w") as file:
            json.dump(new_data, file, indent=4)
            print(f"New patches written to '{new_patches_file.name}'")
    except Exception as e:
        print(f"Error writing file: {e}")