import string

def print_hex(data, grouping=4, per_line=4, show_offsets=True, offset_start=0):
    padding_size = -len(data) & ((grouping * per_line) - 1)
    
    groups = [''.join([f"{c:02X}" for c in data[i:i + grouping]]) for i in range(0, len(data), grouping)]
    padding_data = ['  ' * padding_size]
    space_groups = [''.join([f"{c}" for c in padding_data[i:i + grouping]]) for i in
                    range(0, len(padding_data), grouping)]
    groups += space_groups
    hex_groups = [' '.join(groups[i:i + per_line]) for i in range(0, len(groups), per_line)]
    
    groups = [''.join([chr(c) if (chr(c) in string.printable and chr(c) not in string.whitespace) else "." for c in
                       data[i:i + grouping]]) for i in range(0, len(data), grouping)]
    str_groups = [''.join(groups[i:i + per_line]) for i in range(0, len(groups), per_line)]
    
    lines = ['\t'.join([hex_group, str_group]) for hex_group, str_group in zip(hex_groups, str_groups)]
    if show_offsets:
        offsets = [f"0x{i:04X}" for i in range(offset_start, offset_start + len(data), grouping * per_line)]
        lines = ['\t'.join([offset, l]) for offset, l in zip(offsets, lines)]
    print('\n'.join(lines))
