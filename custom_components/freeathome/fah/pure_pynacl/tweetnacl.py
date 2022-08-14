# -*- coding: utf-8 -*-

# import python libs
import os
from array import array

# import pure_pynacl libs
from . import lt_py3, lt_py33
from . import TypeEnum, integer, Int, IntArray


class u8(Int):
    """unsigned char"""

    bits = array("B").itemsize * 8
    mask = (1 << bits) - 1
    signed = False
    order = TypeEnum.u8

    def __repr__(self):
        return "u8(%s)" % integer.__repr__(self)


class u32(Int):
    """unsigned long"""

    bits = array("L").itemsize * 8
    mask = (1 << bits) - 1
    signed = False
    order = TypeEnum.u32

    def __repr__(self):
        return "u32(%s)" % integer.__repr__(self)


class u64(Int):
    """unsigned long long"""

    bits = array("L" if lt_py33 else "Q").itemsize * 8
    mask = (1 << bits) - 1
    signed = False
    order = TypeEnum.u64

    def __repr__(self):
        return "u64(%s)" % integer.__repr__(self)


class i64(Int):
    """long long"""

    bits = array("l" if lt_py33 else "q").itemsize * 8
    mask = (1 << bits - 1) - 1
    signed = True
    order = TypeEnum.i64

    def __repr__(self):
        return "i64(%s)" % integer.__repr__(self)


class gf(IntArray):
    def __init__(self, init=()):
        IntArray.__init__(self, i64, init=init, size=16)


def randombytes(c, s):
    """
    insert s random bytes into c
    """
    if lt_py3:
        c[:s] = bytearray(os.urandom(s))
    else:
        c[:s] = os.urandom(s)


_0 = IntArray(u8, size=16)
_9 = IntArray(u8, size=32, init=[9])

gf0 = gf()
gf1 = gf([1])
_121665 = gf([0xDB41, 1])
D = gf(
    [
        0x78A3,
        0x1359,
        0x4DCA,
        0x75EB,
        0xD8AB,
        0x4141,
        0x0A4D,
        0x0070,
        0xE898,
        0x7779,
        0x4079,
        0x8CC7,
        0xFE73,
        0x2B6F,
        0x6CEE,
        0x5203,
    ]
)
D2 = gf(
    [
        0xF159,
        0x26B2,
        0x9B94,
        0xEBD6,
        0xB156,
        0x8283,
        0x149A,
        0x00E0,
        0xD130,
        0xEEF3,
        0x80F2,
        0x198E,
        0xFCE7,
        0x56DF,
        0xD9DC,
        0x2406,
    ]
)
X = gf(
    [
        0xD51A,
        0x8F25,
        0x2D60,
        0xC956,
        0xA7B2,
        0x9525,
        0xC760,
        0x692C,
        0xDC5C,
        0xFDD6,
        0xE231,
        0xC0A4,
        0x53FE,
        0xCD6E,
        0x36D3,
        0x2169,
    ]
)
Y = gf(
    [
        0x6658,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
    ]
)
I = gf(
    [
        0xA0B0,
        0x4A0E,
        0x1B27,
        0xC4EE,
        0xE478,
        0xAD2F,
        0x1806,
        0x2F43,
        0xD7A7,
        0x3DFB,
        0x0099,
        0x2B4D,
        0xDF0B,
        0x4FC1,
        0x2480,
        0x2B83,
    ]
)


def L32(x, c):
    """static u32 L32(u32 x, int c)"""
    return (u32(x) << c) | ((u32(x) & 0xFFFFFFFF) >> (32 - c))


def ld32(x):
    """u32 ld32(const u8*x)"""
    u = u32(x[3])
    u = (u << 8) | u32(x[2])
    u = (u << 8) | u32(x[1])
    return (u << 8) | u32(x[0])


def dl64(x):
    """u64 dl64(const u8*x)"""
    u = u64()
    for i in range(8):
        u = (u << 8) | u8(x[i])
    return u


def st32(x, u):
    """void st32(u8*x, u32 u)"""
    for i in range(4):
        x[i] = u8(u)
        u >>= 8
    return x


def ts64(x, u):
    """void ts64(u8*x, u64 u)"""
    for i in range(7, -1, -1):
        x[i] = u8(u)
        u >>= 8
    return x


def vn(x, y, n):
    """int vn(const u8*x, const u8*y, int n)"""
    d = u32()
    for i in range(n):
        d |= x[i] ^ y[i]
    return (1 & ((d - 1) >> 8)) - 1


def crypto_verify_16_tweet(x, y):
    """int crypto_verify_16_tweet(const u8*x, const u8*y)"""
    return vn(x, y, 16)


def crypto_verify_32_tweet(x, y):
    """int crypto_verify_32_tweet(const u8*x, const u8*y)"""
    return vn(x, y, 32)


def core(out, in_, k, c, h):
    """void core(u8*out, const u8*in, const u8*k, const u8*c, int h)"""
    w = IntArray(u32, size=16)
    x = IntArray(u32, size=16)
    y = IntArray(u32, size=16)
    t = IntArray(u32, size=4)

    for i in range(4):
        x[5 * i] = ld32(c[4 * i :])
        x[1 + i] = ld32(k[4 * i :])
        x[6 + i] = ld32(in_[4 * i :])
        x[11 + i] = ld32(k[16 + 4 * i :])

    for i in range(16):
        y[i] = x[i]

    for i in range(20):
        for j in range(4):
            for m in range(4):
                t[m] = x[(5 * j + 4 * m) % 16]
            t[1] ^= L32(t[0] + t[3], 7)
            t[2] ^= L32(t[1] + t[0], 9)
            t[3] ^= L32(t[2] + t[1], 13)
            t[0] ^= L32(t[3] + t[2], 18)
            for m in range(4):
                w[4 * j + (j + m) % 4] = t[m]
        for m in range(16):
            x[m] = w[m]

    if h:
        for i in range(16):
            x[i] += y[i]
        for i in range(4):
            x[5 * i] -= ld32(c[4 * i :])
            x[6 + i] -= ld32(in_[4 * i :])
        for i in range(4):
            out[4 * i :] = st32(out[4 * i :], x[5 * i])
            out[16 + 4 * i :] = st32(out[16 + 4 * i :], x[6 + i])
    else:
        for i in range(16):
            out[4 * i :] = st32(out[4 * i :], x[i] + y[i])


def crypto_core_salsa20_tweet(out, in_, k, c):
    """int crypto_core_salsa20_tweet(u8*out, const u8*in, const u8*k, const u8*c)"""
    core(out, in_, k, c, False)
    return 0


def crypto_core_hsalsa20_tweet(out, in_, k, c):
    """int crypto_core_hsalsa20_tweet(u8*out, const u8*in, const u8*k, const u8*c)"""
    core(out, in_, k, c, True)
    return 0


sigma = IntArray(u8, size=16, init=b"expand 32-byte k")


def crypto_stream_salsa20_tweet_xor(c, m, b, n, k):
    """int crypto_stream_salsa20_tweet_xor(u8*c, const u8*m, u64 b, const u8*n, const u8*k)"""
    z = IntArray(u8, size=16)
    x = IntArray(u8, size=64)

    if not b:
        return 0

    for i in range(8):
        z[i] = n[i]

    c_off = 0
    m_off = 0
    while b >= 64:
        crypto_core_salsa20_tweet(x, z, k, sigma)
        for i in range(64):
            c[i + c_off] = (m[i + m_off] if m else 0) ^ x[i]
        u = u32(1)
        for i in range(8, 16):
            u += u32(z[i])
            z[i] = u
            u >>= 8
        b -= 64
        c_off += 64
        if m:
            m_off += 64

    if b:
        crypto_core_salsa20_tweet(x, z, k, sigma)
        for i in range(b):
            c[i + c_off] = (m[i + m_off] if m else 0) ^ x[i]

    return 0


def crypto_stream_salsa20_tweet(c, d, n, k):
    """int crypto_stream_salsa20_tweet(u8*c, u64 d, const u8*n, const u8*k)"""
    return crypto_stream_salsa20_tweet_xor(c, IntArray(u8), d, n, k)


def crypto_stream_xsalsa20_tweet(c, d, n, k):
    """int crypto_stream_xsalsa20_tweet(u8*c, u64 d, const u8*n, const u8*k)"""
    s = IntArray(u8, size=32)
    crypto_core_hsalsa20_tweet(s, n, k, sigma)
    return crypto_stream_salsa20_tweet(c, d, n[16:], s)


def crypto_stream_xsalsa20_tweet_xor(c, m, d, n, k):
    """int crypto_stream_xsalsa20_tweet_xor(u8*c, const u8*m, u64 d, const u8*n, const u8*k)"""
    s = IntArray(u8, size=32)
    crypto_core_hsalsa20_tweet(s, n, k, sigma)
    return crypto_stream_salsa20_tweet_xor(c, m, d, n[16:], s)


def add1305(h, c):
    """void add1305(u32*h, const u32*c)"""
    u = u32()
    for j in range(17):
        u += u32(h[j] + c[j])
        h[j] = u & 255
        u >>= 8


minusp = IntArray(
    u32, size=17, init=(5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 252)
)


def crypto_onetimeauth_poly1305_tweet(out, m, n, k):
    """int crypto_onetimeauth_poly1305_tweet(u8*out, const u8*m, u64 n, const u8*k)"""
    s = u32()
    u = u32()
    x = IntArray(u32, size=17)
    r = IntArray(u32, size=17)
    h = IntArray(u32, size=17)
    c = IntArray(u32, size=17)
    g = IntArray(u32, size=17)

    for j in range(16):
        r[j] = k[j]
    r[3] &= 15
    r[4] &= 252
    r[7] &= 15
    r[8] &= 252
    r[11] &= 15
    r[12] &= 252
    r[15] &= 15

    while n > 0:
        c[:17] = 17 * [u32()]
        for j in range(16):
            if j >= n:
                j -= 1
                break
            c[j] = m[j]
        j += 1
        c[j] = 1
        m = m[j:]
        n -= j
        add1305(h, c)

        for i in range(17):
            x[i] = 0
            for j in range(17):
                x[i] += h[j] * (r[i - j] if j <= i else 320 * r[i + 17 - j])

        for i in range(17):
            h[i] = x[i]
        u = 0

        for j in range(16):
            u += h[j]
            h[j] = u & 255
            u >>= 8

        u += h[16]
        h[16] = u & 3
        u = 5 * (u >> 2)

        for j in range(16):
            u += h[j]
            h[j] = u & 255
            u >>= 8

        u += h[16]
        h[16] = u

    for j in range(17):
        g[j] = h[j]
    add1305(h, minusp)
    s = -(h[16] >> 7)
    for j in range(17):
        h[j] ^= s & (g[j] ^ h[j])

    for j in range(16):
        c[j] = k[j + 16]
    c[16] = 0
    add1305(h, c)
    for j in range(16):
        out[j] = h[j]

    return 0


def crypto_onetimeauth_poly1305_tweet_verify(h, m, n, k):
    """int crypto_onetimeauth_poly1305_tweet_verify(const u8*h, const u8*m, u64 n, const u8*k)"""
    x = IntArray(u8, size=16)
    crypto_onetimeauth_poly1305_tweet(x, m, n, k)
    return crypto_verify_16_tweet(h, x)


def crypto_secretbox_xsalsa20poly1305_tweet(c, m, d, n, k):
    """int crypto_secretbox_xsalsa20poly1305_tweet(u8*c, const u8*m, u64 d, const u8*n, const u8*k)"""
    if d < 32:
        return -1
    crypto_stream_xsalsa20_tweet_xor(c, m, d, n, k)
    c_out = c[16:]
    crypto_onetimeauth_poly1305_tweet(c_out, c[32:], d - 32, c)
    c[16:] = c_out
    c[:16] = 16 * [u8()]
    return 0


def crypto_secretbox_xsalsa20poly1305_tweet_open(m, c, d, n, k):
    """int crypto_secretbox_xsalsa20poly1305_tweet_open(u8*m, const u8*c, u64 d, const u8*n, const u8*k)"""
    x = IntArray(u8, size=32)
    if d < 32:
        return -1
    crypto_stream_xsalsa20_tweet(x, 32, n, k)
    if crypto_onetimeauth_poly1305_tweet_verify(c[16:], c[32:], d - 32, x) != 0:
        return -1
    crypto_stream_xsalsa20_tweet_xor(m, c, d, n, k)
    m[:32] = 32 * [u8()]
    return 0


def set25519(r, a):
    """void set25519(gf r, const gf a)"""
    for i in range(16):
        r[i] = a[i]


def car25519(o):
    """void car25519(gf o)"""
    c = i64()
    for i in range(16):
        o[i] += i64(1) << 16
        c = o[i] >> 16
        o[(i + 1) * (i < 15)] += c - 1 + 37 * (c - 1) * (i == 15)
        o[i] -= c << 16


def sel25519(p, q, b):
    """void sel25519(gf p, gf q, int b)"""
    t = i64()
    c = i64(~(b - 1))
    for i in range(16):
        t = c & (p[i] ^ q[i])
        p[i] ^= t
        q[i] ^= t
    return p, q


def pack25519(o, n):
    """void pack25519(u8*o, const gf n)"""
    b = int()
    m = gf()
    t = gf()
    for i in range(16):
        t[i] = n[i]

    car25519(t)
    car25519(t)
    car25519(t)

    for j in range(2):
        m[0] = t[0] - 0xFFED
        for i in range(1, 15):
            m[i] = t[i] - 0xFFFF - ((m[i - 1] >> 16) & 1)
            m[i - 1] &= 0xFFFF

        m[15] = t[15] - 0x7FFF - ((m[14] >> 16) & 1)
        b = (m[15] >> 16) & 1
        m[14] &= 0xFFFF

        sel25519(t, m, 1 - b)

    for i in range(16):
        o[2 * i] = t[i] & 0xFF
        o[2 * i + 1] = t[i] >> 8


def neq25519(a, b):
    """int neq25519(const gf a, const gf b)"""
    c = IntArray(u8, size=32)
    d = IntArray(u8, size=32)
    pack25519(c, a)
    pack25519(d, b)
    return crypto_verify_32_tweet(c, d)


def par25519(a):
    """u8 par25519(const gf a)"""
    d = IntArray(u8, size=32)
    pack25519(d, a)
    return d[0] & 1


def unpack25519(o, n):
    """void unpack25519(gf o, const u8*n)"""
    for i in range(16):
        o[i] = n[2 * i] + (i64(n[2 * i + 1]) << 8)
    o[15] &= 0x7FFF


def A(o, a, b):
    """void A(gf o, const gf a, const gf b)"""
    for i in range(16):
        o[i] = a[i] + b[i]


def Z(o, a, b):
    """void Z(gf o, const gf a, const gf b)"""
    for i in range(16):
        o[i] = a[i] - b[i]


def M(o, a, b):
    """void M(gf o, const gf a, const gf b)"""
    t = IntArray(i64, size=31)
    for i in range(16):
        for j in range(16):
            t[i + j] += a[i] * b[j]
    for i in range(15):
        t[i] += 38 * t[i + 16]
    for i in range(16):
        o[i] = t[i]

    car25519(o)
    car25519(o)

    return o


def S(o, a):
    """void S(gf o, const gf a)"""
    M(o, a, a)


def inv25519(o, i):
    """void inv25519(gf o, const gf i)"""
    c = gf()
    for a in range(16):
        c[a] = i[a]
    for a in range(253, -1, -1):
        S(c, c)
        if a != 2 and a != 4:
            M(c, c, i)

    for a in range(16):
        o[a] = c[a]

    return o


def pow2523(o, i):
    """void pow2523(gf o, const gf i)"""
    c = gf()
    for a in range(16):
        c[a] = i[a]
    for a in range(250, -1, -1):
        S(c, c)
        if a != 1:
            M(c, c, i)

    for a in range(16):
        o[a] = c[a]


def crypto_scalarmult_curve25519_tweet(q, n, p):
    """int crypto_scalarmult_curve25519_tweet(u8*q, const u8*n, const u8*p)"""
    z = IntArray(u8, size=32)
    x = IntArray(i64, size=80)
    r = i64()

    a = gf()
    b = gf()
    c = gf()
    d = gf()
    e = gf()
    f = gf()

    for i in range(31):
        z[i] = n[i]
    z[31] = (n[31] & 127) | 64
    z[0] &= 248

    unpack25519(x, p)

    for i in range(16):
        b[i] = x[i]
        d[i] = a[i] = c[i] = 0

    a[0] = d[0] = 1
    for i in range(254, -1, -1):
        r = (z[i >> 3] >> (i & 7)) & 1
        sel25519(a, b, r)
        sel25519(c, d, r)
        A(e, a, c)
        Z(a, a, c)
        A(c, b, d)
        Z(b, b, d)
        S(d, e)
        S(f, a)
        M(a, c, a)
        M(c, b, e)
        A(e, a, c)
        Z(a, a, c)
        S(b, a)
        Z(c, d, f)
        M(a, c, _121665)
        A(a, a, d)
        M(c, c, a)
        M(a, d, f)
        M(d, b, x)
        S(b, e)
        sel25519(a, b, r)
        sel25519(c, d, r)

    for i in range(16):
        x[i + 16] = a[i]
        x[i + 32] = c[i]
        x[i + 48] = b[i]
        x[i + 64] = d[i]

    x[32:] = inv25519(x[32:], x[32:])
    x[16:] = M(x[16:], x[16:], x[32:])
    pack25519(q, x[16:])
    return 0


def crypto_scalarmult_curve25519_tweet_base(q, n):
    """int crypto_scalarmult_curve25519_tweet_base(u8*q, const u8*n)"""
    return crypto_scalarmult_curve25519_tweet(q, n, _9)


def crypto_box_curve25519xsalsa20poly1305_tweet_keypair(y, x):
    """int crypto_box_curve25519xsalsa20poly1305_tweet_keypair(u8*y, u8*x)"""
    randombytes(x, 32)
    return crypto_scalarmult_curve25519_tweet_base(y, x)


def crypto_box_curve25519xsalsa20poly1305_tweet_beforenm(k, y, x):
    """int crypto_box_curve25519xsalsa20poly1305_tweet_beforenm(u8*k, const u8*y, const u8*x)"""
    s = IntArray(u8, size=32)
    crypto_scalarmult_curve25519_tweet(s, x, y)
    return crypto_core_hsalsa20_tweet(k, _0, s, sigma)


def crypto_box_curve25519xsalsa20poly1305_tweet_afternm(c, m, d, n, k):
    """int crypto_box_curve25519xsalsa20poly1305_tweet_afternm(u8*c, const u8*m, u64 d, const u8*n, const u8*k)"""
    return crypto_secretbox_xsalsa20poly1305_tweet(c, m, d, n, k)


def crypto_box_curve25519xsalsa20poly1305_tweet_open_afternm(m, c, d, n, k):
    """int crypto_box_curve25519xsalsa20poly1305_tweet_open_afternm(u8*m, const u8*c, u64 d, const u8*n, const u8*k)"""
    return crypto_secretbox_xsalsa20poly1305_tweet_open(m, c, d, n, k)


def crypto_box_curve25519xsalsa20poly1305_tweet(c, m, d, n, y, x):
    """int crypto_box_curve25519xsalsa20poly1305_tweet(u8*c, const u8*m, u64 d, const u8*n, const u8*y, const u8*x)"""
    k = IntArray(u8, size=32)
    crypto_box_curve25519xsalsa20poly1305_tweet_beforenm(k, y, x)
    return crypto_box_curve25519xsalsa20poly1305_tweet_afternm(c, m, d, n, k)


def crypto_box_curve25519xsalsa20poly1305_tweet_open(m, c, d, n, y, x):
    """int crypto_box_curve25519xsalsa20poly1305_tweet_open(u8*m, const u8*c, u64 d, const u8*n, const u8*y, const u8*x)"""
    k = IntArray(u8, size=32)
    crypto_box_curve25519xsalsa20poly1305_tweet_beforenm(k, y, x)
    return crypto_box_curve25519xsalsa20poly1305_tweet_open_afternm(m, c, d, n, k)


def R(x, c):
    """u64 R(u64 x, int c)"""
    return (u64(x) >> c) | (u64(x) << (64 - c))


def Ch(x, y, z):
    """u64 Ch(u64 x, u64 y, u64 z)"""
    return (u64(x) & u64(y)) ^ (~u64(x) & u64(z))


def Maj(x, y, z):
    """u64 Maj(u64 x, u64 y, u64 z)"""
    return (u64(x) & u64(y)) ^ (u64(x) & u64(z)) ^ (u64(y) & u64(z))


def Sigma0(x):
    """u64 Sigma0(u64 x)"""
    return R(x, 28) ^ R(x, 34) ^ R(x, 39)


def Sigma1(x):
    """u64 Sigma1(u64 x)"""
    return R(x, 14) ^ R(x, 18) ^ R(x, 41)


def sigma0(x):
    """u64 sigma0(u64 x)"""
    return R(x, 1) ^ R(x, 8) ^ (x >> 7)


def sigma1(x):
    """u64 sigma1(u64 x)"""
    return R(x, 19) ^ R(x, 61) ^ (x >> 6)


K = IntArray(
    u64,
    size=80,
    init=[
        0x428A2F98D728AE22,
        0x7137449123EF65CD,
        0xB5C0FBCFEC4D3B2F,
        0xE9B5DBA58189DBBC,
        0x3956C25BF348B538,
        0x59F111F1B605D019,
        0x923F82A4AF194F9B,
        0xAB1C5ED5DA6D8118,
        0xD807AA98A3030242,
        0x12835B0145706FBE,
        0x243185BE4EE4B28C,
        0x550C7DC3D5FFB4E2,
        0x72BE5D74F27B896F,
        0x80DEB1FE3B1696B1,
        0x9BDC06A725C71235,
        0xC19BF174CF692694,
        0xE49B69C19EF14AD2,
        0xEFBE4786384F25E3,
        0x0FC19DC68B8CD5B5,
        0x240CA1CC77AC9C65,
        0x2DE92C6F592B0275,
        0x4A7484AA6EA6E483,
        0x5CB0A9DCBD41FBD4,
        0x76F988DA831153B5,
        0x983E5152EE66DFAB,
        0xA831C66D2DB43210,
        0xB00327C898FB213F,
        0xBF597FC7BEEF0EE4,
        0xC6E00BF33DA88FC2,
        0xD5A79147930AA725,
        0x06CA6351E003826F,
        0x142929670A0E6E70,
        0x27B70A8546D22FFC,
        0x2E1B21385C26C926,
        0x4D2C6DFC5AC42AED,
        0x53380D139D95B3DF,
        0x650A73548BAF63DE,
        0x766A0ABB3C77B2A8,
        0x81C2C92E47EDAEE6,
        0x92722C851482353B,
        0xA2BFE8A14CF10364,
        0xA81A664BBC423001,
        0xC24B8B70D0F89791,
        0xC76C51A30654BE30,
        0xD192E819D6EF5218,
        0xD69906245565A910,
        0xF40E35855771202A,
        0x106AA07032BBD1B8,
        0x19A4C116B8D2D0C8,
        0x1E376C085141AB53,
        0x2748774CDF8EEB99,
        0x34B0BCB5E19B48A8,
        0x391C0CB3C5C95A63,
        0x4ED8AA4AE3418ACB,
        0x5B9CCA4F7763E373,
        0x682E6FF3D6B2B8A3,
        0x748F82EE5DEFB2FC,
        0x78A5636F43172F60,
        0x84C87814A1F0AB72,
        0x8CC702081A6439EC,
        0x90BEFFFA23631E28,
        0xA4506CEBDE82BDE9,
        0xBEF9A3F7B2C67915,
        0xC67178F2E372532B,
        0xCA273ECEEA26619C,
        0xD186B8C721C0C207,
        0xEADA7DD6CDE0EB1E,
        0xF57D4F7FEE6ED178,
        0x06F067AA72176FBA,
        0x0A637DC5A2C898A6,
        0x113F9804BEF90DAE,
        0x1B710B35131C471B,
        0x28DB77F523047D84,
        0x32CAAB7B40C72493,
        0x3C9EBE0A15C9BEBC,
        0x431D67C49C100D4C,
        0x4CC5D4BECB3E42B6,
        0x597F299CFC657E2A,
        0x5FCB6FAB3AD6FAEC,
        0x6C44198C4A475817,
    ],
)


def crypto_hashblocks_sha512_tweet(x, m, n):
    """int crypto_hashblocks_sha512_tweet(u8*x, const u8*m, u64 n)"""
    z = IntArray(u64, size=8)
    b = IntArray(u64, size=8)
    a = IntArray(u64, size=8)
    w = IntArray(u64, size=16)
    t = u64()

    for i in range(8):
        z[i] = a[i] = dl64(x[8 * i :])

    m_off = 0
    while n >= 128:
        for i in range(16):
            w[i] = dl64(m[8 * i + m_off :])

        for i in range(80):
            for j in range(8):
                b[j] = a[j]
            t = a[7] + Sigma1(a[4]) + Ch(a[4], a[5], a[6]) + K[i] + w[i % 16]
            b[7] = t + Sigma0(a[0]) + Maj(a[0], a[1], a[2])
            b[3] += t

            for j in range(8):
                a[(j + 1) % 8] = b[j]
            if i % 16 == 15:
                for j in range(16):
                    w[j] += (
                        w[(j + 9) % 16]
                        + sigma0(w[(j + 1) % 16])
                        + sigma1(w[(j + 14) % 16])
                    )

        for i in range(8):
            a[i] += z[i]
            z[i] = a[i]

        m_off += 128
        n -= 128

    for i in range(8):
        x[8 * i :] = ts64(x[8 * i :], z[i])

    return n


iv = IntArray(
    u8,
    size=64,
    init=[
        0x6A,
        0x09,
        0xE6,
        0x67,
        0xF3,
        0xBC,
        0xC9,
        0x08,
        0xBB,
        0x67,
        0xAE,
        0x85,
        0x84,
        0xCA,
        0xA7,
        0x3B,
        0x3C,
        0x6E,
        0xF3,
        0x72,
        0xFE,
        0x94,
        0xF8,
        0x2B,
        0xA5,
        0x4F,
        0xF5,
        0x3A,
        0x5F,
        0x1D,
        0x36,
        0xF1,
        0x51,
        0x0E,
        0x52,
        0x7F,
        0xAD,
        0xE6,
        0x82,
        0xD1,
        0x9B,
        0x05,
        0x68,
        0x8C,
        0x2B,
        0x3E,
        0x6C,
        0x1F,
        0x1F,
        0x83,
        0xD9,
        0xAB,
        0xFB,
        0x41,
        0xBD,
        0x6B,
        0x5B,
        0xE0,
        0xCD,
        0x19,
        0x13,
        0x7E,
        0x21,
        0x79,
    ],
)


def crypto_hash_sha512_tweet(out, m, n):
    """int crypto_hash_sha512_tweet(u8*out, const u8*m, u64 n)"""
    h = IntArray(u8, size=64)
    x = IntArray(u8, size=256)
    b = u64(n)

    for i in range(64):
        h[i] = iv[i]

    crypto_hashblocks_sha512_tweet(h, m, n)
    m_off = n
    n &= 127
    m_off -= n

    x[:256] = 256 * [u8()]
    for i in range(n):
        x[i] = m[i + m_off]
    x[n] = 128

    n = 256 - 128 * (n < 112)
    x[n - 9] = b >> 61
    x[n - 8 :] = ts64(x[n - 8 :], b << 3)
    crypto_hashblocks_sha512_tweet(h, x, n)

    for i in range(64):
        out[i] = h[i]

    return 0


def add(p, q):
    """void add(gf p[4], gf q[4])"""
    a = gf()
    b = gf()
    c = gf()
    d = gf()
    t = gf()
    e = gf()
    f = gf()
    g = gf()
    h = gf()

    Z(a, p[1], p[0])
    Z(t, q[1], q[0])
    M(a, a, t)
    A(b, p[0], p[1])
    A(t, q[0], q[1])
    M(b, b, t)
    M(c, p[3], q[3])
    M(c, c, D2)
    M(d, p[2], q[2])
    A(d, d, d)
    Z(e, b, a)
    Z(f, d, c)
    A(g, d, c)
    A(h, b, a)

    M(p[0], e, f)
    M(p[1], h, g)
    M(p[2], g, f)
    M(p[3], e, h)


def cswap(p, q, b):
    """void cswap(gf p[4], gf q[4], u8 b)"""
    for i in range(4):
        p[i], q[i] = sel25519(p[i], q[i], b)


def pack(r, p):
    """void pack(u8*r, gf p[4])"""
    tx = gf()
    ty = gf()
    zi = gf()
    inv25519(zi, p[2])
    M(tx, p[0], zi)
    M(ty, p[1], zi)
    pack25519(r, ty)
    r[31] ^= par25519(tx) << 7


def scalarmult(p, q, s):
    """void scalarmult(gf p[4], gf q[4], const u8*s)"""
    set25519(p[0], gf0)
    set25519(p[1], gf1)
    set25519(p[2], gf1)
    set25519(p[3], gf0)
    for i in range(255, -1, -1):
        b = u8((s[i // 8] >> (i & 7)) & 1)
        cswap(p, q, b)
        add(q, p)
        add(p, p)
        cswap(p, q, b)


def scalarbase(p, s):
    """void scalarbase(gf p[4], const u8*s)"""
    q = [gf() for i in range(4)]
    set25519(q[0], X)
    set25519(q[1], Y)
    set25519(q[2], gf1)
    M(q[3], X, Y)
    scalarmult(p, q, s)


def crypto_sign_ed25519_tweet_keypair(pk, sk):
    """int crypto_sign_ed25519_tweet_keypair(u8*pk, u8*sk)"""
    d = IntArray(u8, size=64)
    p = [gf() for i in range(4)]

    randombytes(sk, 32)
    crypto_hash_sha512_tweet(d, sk, 32)
    d[0] &= 248
    d[31] &= 127
    d[31] |= 64

    scalarbase(p, d)
    pack(pk, p)

    for i in range(32):
        sk[32 + i] = pk[i]
    return 0


L = IntArray(
    u64,
    size=32,
    init=[
        0xED,
        0xD3,
        0xF5,
        0x5C,
        0x1A,
        0x63,
        0x12,
        0x58,
        0xD6,
        0x9C,
        0xF7,
        0xA2,
        0xDE,
        0xF9,
        0xDE,
        0x14,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0x10,
    ],
)


def modL(r, x):
    """void modL(u8*r, i64 x[64])"""
    carry = i64()
    for i in range(63, 31, -1):
        carry = 0
        for j in range(i - 32, i - 12):
            x[j] += carry - 16 * x[i] * L[j - (i - 32)]
            carry = (x[j] + 128) >> 8
            x[j] -= carry << 8
        j += 1
        x[j] += carry
        x[i] = 0

    carry = 0
    for j in range(32):
        x[j] += carry - (x[31] >> 4) * L[j]
        carry = x[j] >> 8
        x[j] &= 255

    for j in range(32):
        x[j] -= carry * L[j]
    for i in range(32):
        x[i + 1] += x[i] >> 8
        r[i] = x[i] & 255

    return r


def reduce(r):
    """void reduce(u8*r)"""
    x = IntArray(i64, size=64)
    for i in range(64):
        x[i] = u64(r[i])
    r[:64] = 64 * [u8()]
    modL(r, x)


def crypto_sign_ed25519_tweet(sm, smlen, m, n, sk):
    """int crypto_sign_ed25519_tweet(u8*sm, u64*smlen, const u8*m, u64 n, const u8*sk)"""
    d = IntArray(u8, size=64)
    h = IntArray(u8, size=64)
    r = IntArray(u8, size=64)
    x = IntArray(i64, size=64)
    p = [gf() for i in range(4)]

    crypto_hash_sha512_tweet(d, sk, 32)
    d[0] &= 248
    d[31] &= 127
    d[31] |= 64

    # There is no (simple?) way to return this argument's value back to the
    # user in python.  Rather than redefining the return value of this function
    # it is better to advise the user that ``smlen`` does not work as it does
    # in the C implementation and that its value will be equal to ``n + 64``.
    smlen = n + 64
    for i in range(n):
        sm[64 + i] = m[i]
    for i in range(32):
        sm[32 + i] = d[32 + i]

    crypto_hash_sha512_tweet(r, sm[32:], n + 32)
    reduce(r)
    scalarbase(p, r)
    pack(sm, p)

    for i in range(32):
        sm[i + 32] = sk[i + 32]
    crypto_hash_sha512_tweet(h, sm, n + 64)
    reduce(h)

    for i in range(64):
        x[i] = 0
    for i in range(32):
        x[i] = u64(r[i])
    for i in range(32):
        for j in range(32):
            x[i + j] += h[i] * u64(d[j])
    sm[32:] = modL(sm[32:], x)

    return 0


def unpackneg(r, p):
    """int unpackneg(gf r[4], const u8 p[32])"""
    t = gf()
    chk = gf()
    num = gf()
    den = gf()
    den2 = gf()
    den4 = gf()
    den6 = gf()

    set25519(r[2], gf1)
    unpack25519(r[1], p)
    S(num, r[1])
    M(den, num, D)
    Z(num, num, r[2])
    A(den, r[2], den)

    S(den2, den)
    S(den4, den2)
    M(den6, den4, den2)
    M(t, den6, num)
    M(t, t, den)

    pow2523(t, t)
    M(t, t, num)
    M(t, t, den)
    M(t, t, den)
    M(r[0], t, den)

    S(chk, r[0])
    M(chk, chk, den)
    if neq25519(chk, num):
        M(r[0], r[0], I)

    S(chk, r[0])
    M(chk, chk, den)
    if neq25519(chk, num):
        return -1

    if par25519(r[0]) == (p[31] >> 7):
        Z(r[0], gf0, r[0])

    M(r[3], r[0], r[1])
    return 0


def crypto_sign_ed25519_tweet_open(m, mlen, sm, n, pk):
    """int crypto_sign_ed25519_tweet_open(u8*m, u64*mlen, const u8*sm, u64 n, const u8*pk)"""
    t = IntArray(u8, size=32)
    h = IntArray(u8, size=64)
    p = [gf() for i in range(4)]
    q = [gf() for i in range(4)]

    mlen = -1
    if n < 64:
        return -1

    if unpackneg(q, pk):
        return -1

    for i in range(n):
        m[i] = sm[i]
    for i in range(32):
        m[i + 32] = pk[i]
    crypto_hash_sha512_tweet(h, m, n)
    reduce(h)
    scalarmult(p, q, h)

    scalarbase(q, sm[32:])
    add(p, q)
    pack(t, p)

    n -= 64
    if crypto_verify_32_tweet(sm, t):
        for i in range(n):
            m[i] = 0
        return -1

    for i in range(n):
        m[i] = sm[i + 64]
    # There is no (simple?) way to return this argument's value back to the
    # user in python.  Rather than redefining the return value of this function
    # it is better to advise the user that ``mlen`` does not work as it does in
    # the C implementation and that its value will be equal to ``-1`` if ``n <
    # 64`` or decryption fails and ``n - 64`` otherwise.
    mlen = n
    return 0
