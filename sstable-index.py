#!/usr/bin/env python3

import argparse
import binascii
import struct

cmdline_parser = argparse.ArgumentParser()
cmdline_parser.add_argument('index_file', nargs='+', help='index file to parse')
cmdline_parser.add_argument('--summary', action='store_true', help='generate a summary instead of full output')
cmdline_parser.add_argument('--partition-size-threshold', type=int, default=-2, help='report on partitions this size or larger')
cmdline_parser.add_argument('--ignore-missing', action='store_true', default=False,
                            help='ignore missing files (useful when running on live data that can be compacted)')

args = cmdline_parser.parse_args()

class FullReport:
    def report_file(self, file):
        print(f'Parsing {file}')
    def begin_entries(self):
        print('Index entries:')
    def report_partition_start(self, key, position, promoted_length, partition_size):
        print(
            f'\tKey:\t\t\t{binascii.hexlify(key)}\n\tPosition:\t\t{position}\n\tPromoted length:\t{promoted_length}'
        )

        print(f'\tPartition size:\t{partition_size}')
    def report_promoted_start(self, deletion_time, timestamp, entries_count):
        print(
            f'\tDeletion time:\t\t{deletion_time}\n\tTimestamp:\t\t{timestamp}\n\tEntries count:\t\t{entries_count}'
        )
    def report_promoted_entry(self, start, end, entry_offset, width):
        print(
            f'\t\tStart:\t{binascii.hexlify(start)}\n\t\tEnd:\t{binascii.hexlify(end)}\n\t\tOffset:\t{entry_offset}\n\t\tLength:\t{width}\n'
        )
    def report_partition_end(self):
        print('')
    def report_end(self, partitions):
        print(f'Total partitions:\t\t\t{partitions}')

class SummaryReport:
    def report_file(self, file):
        self.file = file
    def begin_entries(self):
        pass
    def report_partition_start(self, key, position, promoted_length, partition_size):
        self.key = key
        self.position = position
        self.promoted_length = promoted_length
        self.partition_size = partition_size
    def report_promoted_start(self, deletion_time, timestamp, entries_count):
        pass
    def report_promoted_entry(self, start, end, entry_offset, width):
        pass
    def report_partition_end(self):
        print('{:12} {:9} {:12} {} {}'.format(self.position, self.promoted_length, self.partition_size, binascii.hexlify(self.key), self.file))
    def report_end(self, partitions):
        pass

class NullReport:
    def report_file(self, file):
        pass
    def begin_entries(self):
        pass
    def report_partition_start(self, key, position, promoted_length, partition_size):
        pass
    def report_promoted_start(self, deletion_time, timestamp, entries_count):
        pass
    def report_promoted_entry(self, start, end, entry_offset, width):
        pass
    def report_partition_end(self):
        pass
    def report_end(self, partitions):
        pass
    
        
reporter = FullReport()
if args.summary:
    reporter = SummaryReport()

for index_file in args.index_file:
    reporter.report_file(index_file)

    try:
        file = open(index_file, 'rb')
    except:
        if not args.ignore_missing:
            raise

        print(f'File {index_file} missing, possible compacted')
        continue
    data = file.read()

    offset = 0
    size = len(data)

    reporter.begin_entries()
    partitions = 0

    while offset < size:
        partitions += 1

        key_length = struct.unpack_from('>h', data, offset)[0]
        key = struct.unpack_from(f'>{key_length}s', data, offset + 2)[0]
        offset += key_length + 2

        (position, promoted_length) = struct.unpack_from('>ql', data, offset)
        offset += 12

        next_offset = offset + promoted_length
        if next_offset < size:
            (key_length,) = struct.unpack_from('>h', data, next_offset)
            next_offset += 2 + key_length
            (next_position,) = struct.unpack_from('>q', data, next_offset)
            partition_size = next_position - position
        else:
            partition_size = -1 # unknown

        if partition_size < args.partition_size_threshold:
            now_reporter = NullReport()
        else:
            now_reporter = reporter

        now_reporter.report_partition_start(key, position, promoted_length, partition_size)

        if promoted_length:
            (deletion_time, timestamp, entries_count) = struct.unpack_from('>lql', data, offset)
            offset += 16

            now_reporter.report_promoted_start(deletion_time, timestamp, entries_count)

            for _ in range(entries_count):
                start_length = struct.unpack_from('>h', data, offset)[0]
                start = struct.unpack_from(f'>{start_length}s', data, offset + 2)[0]
                offset += start_length + 2

                end_length = struct.unpack_from('>h', data, offset)[0]
                end = struct.unpack_from(f'>{end_length}s', data, offset + 2)[0]
                offset += end_length + 2

                (entry_offset, width) = struct.unpack_from('>qq', data, offset)
                offset += 16

                now_reporter.report_promoted_entry(start, end, entry_offset, width)
        now_reporter.report_partition_end()

    reporter.report_end(partitions)
