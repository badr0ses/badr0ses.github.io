"""Lossless browser-image export of legacy DDS icons; standard library only."""
import struct
import zlib
import binascii


def png(width, height, pixels):
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', binascii.crc32(name + data) & 0xFFFFFFFF)
    stride = width * 4
    scanlines = b''.join(b'\0' + pixels[y * stride:(y + 1) * stride] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(scanlines, 9)) + chunk(b'IEND', b''))


def texture_png(data):
    start = data.find(b'DDS ')
    if start < 0:
        start = data.find(b'Hx')
        if start < 0:
            raise ValueError('No supported texture payload')
        try:
            import texture2ddecoder
        except ImportError as error:
            raise ValueError('Crunch-compressed icon requires the optional texture2ddecoder package') from error
        crn = data[start:]
        width, height = struct.unpack_from('>HH', crn, 12)
        if not 0 < width <= 2048 or not 0 < height <= 2048:
            raise ValueError('Invalid Crunch dimensions')
        format_id = crn[18]
        # Legacy PTEs use Unity's Crunch bitstream variant. The standard Crunch
        # reader accepts the header but produces scrambled block order.
        blocks = texture2ddecoder.unpack_unity_crunch(crn)
        if format_id == 0:
            bgra = texture2ddecoder.decode_bc1(blocks, width, height)
        elif format_id == 2:
            bgra = texture2ddecoder.decode_bc3(blocks, width, height)
        else:
            raise ValueError(f'Unsupported Crunch pixel format: {format_id}')
        rgba = bytearray(bgra)
        rgba[0::4], rgba[2::4] = bgra[2::4], bgra[0::4]
        return png(width, height, rgba)
    data = data[start:]
    height, width = struct.unpack_from('<II', data, 12)
    if not 0 < width <= 2048 or not 0 < height <= 2048:
        raise ValueError('Invalid DDS dimensions')
    _, flags, fourcc, bits, red, green, blue, alpha = struct.unpack_from('<8I', data, 76)
    body = data[128:]
    pixels = bytearray(width * height * 4)
    if flags & 0x40 and bits in (24, 32):
        channels = []
        for mask in (red, green, blue, alpha):
            shift = (mask & -mask).bit_length() - 1 if mask else 0
            channels.append((mask, shift, mask >> shift if mask else 0))
        stride = bits // 8
        if len(body) < width * height * stride:
            raise ValueError('Truncated DDS pixels')
        for index in range(width * height):
            value = int.from_bytes(body[index * stride:(index + 1) * stride], 'little')
            for channel, (mask, shift, maximum) in enumerate(channels):
                pixels[index * 4 + channel] = ((value & mask) >> shift) * 255 // maximum if mask else (255 if channel == 3 else 0)
    elif fourcc == int.from_bytes(b'DXT1', 'little'):
        blocks_w = (width + 3) // 4
        for block in range(blocks_w * ((height + 3) // 4)):
            c0, c1, indices = struct.unpack_from('<HHI', body, block * 8)
            def rgb(c):
                return ((c >> 11) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31, 255)
            a, b = rgb(c0), rgb(c1)
            palette = [a, b]
            if c0 > c1:
                palette += [tuple((2 * a[i] + b[i]) // 3 for i in range(3)) + (255,), tuple((a[i] + 2 * b[i]) // 3 for i in range(3)) + (255,)]
            else:
                palette += [tuple((a[i] + b[i]) // 2 for i in range(3)) + (255,), (0, 0, 0, 0)]
            for pixel in range(16):
                x, y = (block % blocks_w) * 4 + pixel % 4, (block // blocks_w) * 4 + pixel // 4
                if x < width and y < height:
                    offset = (y * width + x) * 4
                    pixels[offset:offset + 4] = bytes(palette[(indices >> (pixel * 2)) & 3])
    else:
        raise ValueError(f'Unsupported DDS pixel format: {fourcc}, {bits} bits')
    return png(width, height, pixels)
