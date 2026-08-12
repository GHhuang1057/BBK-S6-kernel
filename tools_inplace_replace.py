#!/usr/bin/env python3
import struct, sys

def inplace_replace(orig_path, new_kernel_path, out_path):
    data = bytearray(open(orig_path,'rb').read())
    newk = open(new_kernel_path,'rb').read()
    k_orig = struct.unpack_from('<I', data, 0x08)[0]
    print('orig kernel_size=%d, new kernel=%d bytes' % (k_orig, len(newk)))
    if len(newk) > k_orig:
        print('ERROR: new kernel larger than slot'); sys.exit(1)
    # overwrite kernel at 0x1000
    ks = ((0x680 + 4095) // 4096) * 4096  # 0x1000
    data[ks:ks+len(newk)] = newk
    # zero out the rest of the kernel slot (padding)
    data[ks+len(newk):ks+k_orig] = b'\x00' * (k_orig - len(newk))
    # kernel_size field: keep ORIGINAL so ramdisk offset unchanged
    open(out_path,'wb').write(bytes(data))
    print('wrote %s: %d bytes' % (out_path, len(data)))

if __name__ == '__main__':
    inplace_replace(sys.argv[1], sys.argv[2], sys.argv[3])
