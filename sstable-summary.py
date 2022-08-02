#!/usr/bin/env python3

import argparse
import binascii
import struct

cmdline_parser = argparse.ArgumentParser()
cmdline_parser.add_argument('summary_file', help='summary file to parse')

args = cmdline_parser.parse_args()

with open(args.summary_file, 'rb') as f:
    data = f.read()
offset = 0

(min_interval, entries_count, entries_size, sampling_level, size_at_full_sampling) = struct.unpack_from('>llqll', data)
header_size = 24

print(f'Minimal interval:\t{min_interval}')
print(f'Number of entires:\t{entries_count}')
print(f'Summary entries size:\t{entries_size}')
print(f'Sampling level:\t\t{sampling_level}')
print(f'Size at full sampling:\t{size_at_full_sampling}')

positions = list(struct.unpack_from(f'<{entries_count}l', data, header_size))
positions.append(entries_size)

offset = header_size + entries_size

start_length = struct.unpack_from('>l', data, offset)[0]
start = struct.unpack_from(f'>{start_length}s', data, offset + 4)[0]
offset += start_length + 4

end_length = struct.unpack_from('>l', data, offset)[0]
end = struct.unpack_from(f'>{end_length}s', data, offset + 4)[0]
offset += end_length + 4

print(f'First key:\t\t{binascii.hexlify(start)}')
print(f'Last key:\t\t{binascii.hexlify(end)}')
print(f'Total summary size:\t{offset}')
print('Entries:')

for i in range(entries_count):
    start = positions[i]
    end = positions[i + 1] - 8

    (key, position) = struct.unpack_from(
        f'<{end - start}sq', data, header_size + start
    )


    print(f'\tKey {binascii.hexlify(key)} at position {position}')

