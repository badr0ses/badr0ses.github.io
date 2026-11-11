"""Read-only readers for the legacy client's archive, scene and language formats.

These readers never launch the client or write to its installation directory.
Localization layout reference: https://github.com/RealIndrit/sso-format
The legacy variant has three 32-bit value metadata fields.
"""
from pathlib import Path
import struct


def hash_name(name):
    value = 0
    for byte in name.encode('utf-8'):
        value = (value << 4) + byte
        high = value & 0xF0000000
        if high:
            value ^= high >> 24
        value &= ~high
    return value


class Scene:
    def __init__(self, data):
        self.data = data
        count, version = struct.unpack_from('<II', data)
        if version != 1 or 8 + count * 12 > len(data):
            raise ValueError('Unsupported legacy scene layout')
        self.base = 8 + count * 12
        self.records = list(struct.iter_unpack('<III', data[8:self.base]))

    def value(self, value, kind):
        if kind == 0x204:
            pos = self.base + value
            length = struct.unpack_from('<I', self.data, pos)[0]
            if pos + 4 + length > len(self.data):
                raise ValueError('String outside scene bounds')
            raw = self.data[pos + 4:pos + 4 + length].rstrip(b'\0')
            try:
                return raw.decode('utf-8')
            except UnicodeDecodeError:
                return raw.decode('cp1252', errors='replace')
        if kind == 0xA03:
            return struct.unpack('<f', struct.pack('<I', value))[0]
        if kind in (0x207, 0x209):
            pos = self.base + value
            length = struct.unpack_from('<I', self.data, pos)[0]
            expected = 12 if kind == 0x207 else 16
            if length != expected:
                raise ValueError('Invalid scene vector')
            return list(struct.unpack_from('<' + 'f' * (expected // 4), self.data, pos + 4))
        return value

    def objects(self, class_id=None):
        current = None
        class_key = hash_name('classId')
        parent_entry = next(((v, t) for k, v, t in self.records if k == hash_name('parentLookup')), None)
        parents = []
        if parent_entry is not None:
            pos = self.base + parent_entry[0]
            length = struct.unpack_from('<I', self.data, pos)[0]
            parents = list(struct.unpack_from('<' + 'I' * (length // 4), self.data, pos + 4))
        index = -1
        for key, value, kind in self.records:
            if key == class_key:
                if current is not None and (class_id is None or current['class'] == class_id):
                    yield current
                index += 1
                current = {'class': value, 'fields': {}, 'records': [], 'objectIndex': index,
                           'parentIndex': parents[index] if index < len(parents) else 0xFFFFFFFF}
            elif current is not None:
                decoded = self.value(value, kind)
                current['fields'][key] = decoded
                current['records'].append((key, decoded, kind))
        if current is not None and (class_id is None or current['class'] == class_id):
            yield current


def field(obj, name, default=None):
    return obj['fields'].get(hash_name(name), default)


class Archive:
    def __init__(self, game):
        self.game = Path(game)
        self.files = {}
        offset_key, length_key, path_key = map(hash_name, (
            'csafileinfo.dwoffset', 'csafileinfo.dwlength', 'csafileinfo.szpath'))
        for path in sorted((self.game / 'PackFiles').glob('*.csaheader')):
            scene = Scene(path.read_bytes())
            pack = path.with_suffix('.csa')
            pack_size = pack.stat().st_size
            offset = length = None
            for key, value, kind in scene.records:
                if key == offset_key:
                    offset = value
                elif key == length_key:
                    length = value
                elif key == path_key:
                    name = scene.value(value, kind)
                    if offset is None or length is None or offset + length > pack_size:
                        raise ValueError(f'Invalid archive entry: {name}')
                    self.files[name.lower()] = (name, pack, offset, length)

    def read(self, name):
        name, pack, offset, length = self.files[name.lower()]
        with pack.open('rb') as stream:
            stream.seek(offset)
            data = stream.read(length)
        if len(data) != length:
            raise ValueError(f'Truncated resource: {name}')
        return data


def translations(data):
    count = struct.unpack_from('<I', data, 12)[0]
    pos, result = 16, {}
    for _ in range(count):
        length, _, _, shift = struct.unpack_from('<BBBB', data, pos)
        pos += 4
        key = bytes((value + shift) & 255 for value in data[pos:pos + length]).decode('utf-8')
        pos += length
        _, _, length, _, _, _ = struct.unpack_from('<IIIIII', data, pos)
        pos += 24
        raw = data[pos:pos + length]
        pos += length
        if len(raw) != length or length < 2 or length % 2:
            raise ValueError('Invalid translation length')
        shift = (-raw[1]) & 255
        result[key] = bytes((value + shift) & 255 for value in raw[:-2]).decode('utf-16-le')
    if pos != len(data):
        raise ValueError('Translation table was not fully consumed')
    return result
