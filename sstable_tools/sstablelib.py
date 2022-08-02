import struct
import sys

class Stream:
    size = {
        'c': 1, # char
        'b': 1, # signed char (int8)
        'B': 1, # unsigned char (uint8)
        '?': 1, # bool
        'h': 2, # short (int16)
        'H': 2, # unsigned short (uint16)
        'i': 4, # int (int32)
        'I': 4, # unsigned int (uint32)
        'l': 4, # long (int32)
        'l': 4, # unsigned long (int32)
        'q': 8, # long long (int64)
        'Q': 8, # unsigned long long (uint64)
        'f': 4, # float
        'd': 8, # double
    }

    def __init__(self, data, offset=0):
        self.data = data
        self.offset = offset

    def skip(self, n):
        self.offset += n

    def read(self, typ):
        try:
            (val,) = struct.unpack_from(f'>{typ}', self.data, self.offset)
        except Exception as e:
            raise ValueError(
                f"Failed to read type `{typ}\' from stream at offset {e}: {self.offset}"
            )

        self.offset += self.size[typ]
        return val

    def bool(self):
        return self.read('?')
    def int8(self):
        return self.read('b')
    def uint8(self):
        return self.read('B')
    def int16(self):
        return self.read('h')
    def uint16(self):
        return self.read('H')
    def int32(self):
        return self.read('i')
    def uint32(self):
        return self.read('I')
    def int64(self):
        return self.read('q')
    def uint64(self):
        return self.read('Q')
    def float(self):
        return self.read('f')
    def double(self):
        return self.read('d')
    def bytes(self, len_type):
        len = len_type(self)
        val = self.data[self.offset:self.offset + len]
        self.offset += len
        return val
    def bytes16(self):
        return self.bytes(Stream.uint16)
    def bytes32(self):
        return self.bytes(Stream.uint32)
    def string(self, len_type):
        buf = self.bytes(len_type)
        try:
            return buf.decode('utf-8')
        except UnicodeDecodeError:
            # FIXME why are some strings unintelligible?
            # FIXME Remove this when we finally transition to Python3
            if sys.version_info[0] == 2:
                return 'INVALID(size={}, bytes={})'.format(len(buf), ''.join(map(lambda x: '{:02x}'.format(ord(x)), buf)))
            else:
                return 'INVALID(size={}, bytes={})'.format(len(buf), ''.join(map(lambda x: '{:02x}'.format(x), buf)))
    def string16(self):
        return self.string(Stream.uint16)
    def string32(self):
        return self.string(Stream.uint32)
    def map16(self, keytype=string16, valuetype=string16):
        return {self.keytype(): self.valuetype() for _ in range(self.int16())}
    def map32(self, keytype=string16, valuetype=string16):
        return {keytype(self): valuetype(self) for _ in range(self.int32())}
    def array32(self, valuetype):
        return [valuetype(self) for _ in range(self.int32())]
    def tuple(self, *member_types):
        return (mt(self) for mt in member_types)
    def struct(self, *members):
        return {member_name: member_type(self) for member_name, member_type in members}
    def set_of_tagged_union(self, tag_type, *members):
        members_by_keys = {k: (n, t) for k, n, t in members}
        value = {}
        for _ in range(tag_type(self)):
            key = tag_type(self)
            size = self.uint32()
            if key in members_by_keys:
                name, typ = members_by_keys[key]
                value[name] = typ(self)
                #TODO: check we haven't read more than size
            else:
                self.skip(size)
        return value
    def enum32(self, *values):
        d = dict(values)
        return d[self.uint32()]

    @staticmethod
    def instantiate(template_type, *args):
        def instanciated_type(stream):
            return template_type(stream, *args)
        return instanciated_type


def parse(stream, schema):
    return {name: typ(stream) for name, typ in schema}
