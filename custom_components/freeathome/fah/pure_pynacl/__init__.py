# -*- coding: utf-8 -*-

import sys
from array import array

if sys.version_info < (2, 6):
    raise NotImplementedError("pure_pynacl requires python-2.6 or later")

lt_py3 = sys.version_info < (3,)
lt_py33 = sys.version_info < (3, 3)

integer = long if lt_py3 else int


class TypeEnum(object):
    """
    order types used by pure_py(tweet)nacl for rapid type promotion
    """

    u8 = 1
    u32 = 2
    u64 = 3
    Int = 5
    i64 = 7
    integer = 11


class Int(integer):
    """
    int types
    """

    bits = array("i").itemsize * 8
    mask = (1 << bits - 1) - 1
    signed = True
    order = TypeEnum.Int

    def __str__(self):
        return integer.__str__(self)

    def __repr__(self):
        return "Int(%s)" % integer.__repr__(self)

    def __new__(self, val=0):
        """
        ensure that new instances have the correct size and sign
        """
        if val < 0:
            residue = integer(-val) & self.mask
            if self.signed:
                residue = -residue
        else:
            residue = integer(val) & self.mask
        return integer.__new__(self, residue)

    def __promote_type(self, other, result):
        """
        determine the largest type from those in self and other; if result is
        negative and both self and other are unsigned, promote it to the least
        signed type
        """
        self_order = self.order
        other_order = other.order if isinstance(other, Int) else TypeEnum.integer

        if result < 0 and self_order < 5 and other_order < 5:
            return Int
        return self.__class__ if self_order > other_order else other.__class__

    def __unary_typed(oper):
        """
        return a function that redefines the operation oper such that the
        result conforms to the type of self
        """

        def operate(self):
            """
            type the result to self
            """
            return self.__class__(oper(self))

        return operate

    def __typed(oper):
        """
        return a function that redefines the operation oper such that the
        result conforms to the type of self or other, whichever is larger if
        both are strongly typed (have a bits attribute); otherwise return the
        result conforming to the type of self
        """

        def operate(self, other):
            """
            type and bitmask the result to either self or other, whichever is
            larger
            """
            result = oper(self, other)
            return self.__promote_type(other, result)(result)

        return operate

    def __shift(oper):
        """
        return a function that performs bit shifting, but preserves the type of
        the left value
        """

        def operate(self, other):
            """
            emulate C bit shifting
            """
            return self.__class__(oper(self, other))

        return operate

    def __invert():
        """
        return a function that performs bit inversion
        """

        def operate(self):
            """
            emulate C bit inversion
            """
            if self.signed:
                return self.__class__(integer.__invert__(self))
            else:
                return self.__class__(integer.__xor__(self, self.mask))

        return operate

    # bitwise operations
    __lshift__ = __shift(integer.__lshift__)
    __rlshift__ = __shift(integer.__rlshift__)
    __rshift__ = __shift(integer.__rshift__)
    __rrshift__ = __shift(integer.__rrshift__)
    __and__ = __typed(integer.__and__)
    __rand__ = __typed(integer.__rand__)
    __or__ = __typed(integer.__or__)
    __ror__ = __typed(integer.__ror__)
    __xor__ = __typed(integer.__xor__)
    __rxor__ = __typed(integer.__rxor__)
    __invert__ = __invert()

    # arithmetic operations
    if not lt_py3:
        __ceil__ = __unary_typed(integer.__ceil__)
        __floor__ = __unary_typed(integer.__floor__)
        __int__ = __unary_typed(integer.__int__)
    __abs__ = __unary_typed(integer.__abs__)
    __pos__ = __unary_typed(integer.__pos__)
    __neg__ = __unary_typed(integer.__neg__)
    __add__ = __typed(integer.__add__)
    __radd__ = __typed(integer.__radd__)
    __sub__ = __typed(integer.__sub__)
    __rsub__ = __typed(integer.__rsub__)
    __mod__ = __typed(integer.__mod__)
    __rmod__ = __typed(integer.__rmod__)
    __mul__ = __typed(integer.__mul__)
    __rmul__ = __typed(integer.__rmul__)
    if lt_py3:
        __div__ = __typed(integer.__div__)
        __rdiv__ = __typed(integer.__rdiv__)
    __floordiv__ = __typed(integer.__floordiv__)
    __rfloordiv__ = __typed(integer.__rfloordiv__)
    __pow__ = __typed(integer.__pow__)
    __rpow__ = __typed(integer.__rpow__)


class IntArray(list):
    """
    arrays of int types
    """

    def __init__(self, typ, init=(), size=0):
        """
        create array of ints
        """
        self.typ = typ

        if lt_py3 and isinstance(init, bytes):
            init = [ord(i) for i in init]

        if size:
            init_size = len(init)
            if init_size < size:
                list.__init__(
                    self,
                    [typ(i) for i in init] + [typ() for i in range(size - init_size)],
                )
            else:
                list.__init__(self, [typ(i) for i in init[:size]])
        else:
            list.__init__(self, [typ(i) for i in init])

    def __str__(self):
        return list.__str__(self)

    def __repr__(self):
        return "IntArray(%s, init=%s)" % (self.typ, list.__repr__(self))


# TweetNaCl external functions
from .tweetnacl import (
    crypto_verify_16_tweet,
    crypto_verify_32_tweet,
    crypto_core_salsa20_tweet,
    crypto_core_hsalsa20_tweet,
    crypto_stream_salsa20_tweet_xor,
    crypto_stream_salsa20_tweet,
    crypto_stream_xsalsa20_tweet,
    crypto_stream_xsalsa20_tweet_xor,
    crypto_onetimeauth_poly1305_tweet,
    crypto_onetimeauth_poly1305_tweet_verify,
    crypto_secretbox_xsalsa20poly1305_tweet,
    crypto_secretbox_xsalsa20poly1305_tweet_open,
    crypto_scalarmult_curve25519_tweet,
    crypto_scalarmult_curve25519_tweet_base,
    crypto_box_curve25519xsalsa20poly1305_tweet_keypair,
    crypto_box_curve25519xsalsa20poly1305_tweet_beforenm,
    crypto_box_curve25519xsalsa20poly1305_tweet_afternm,
    crypto_box_curve25519xsalsa20poly1305_tweet_open_afternm,
    crypto_box_curve25519xsalsa20poly1305_tweet,
    crypto_box_curve25519xsalsa20poly1305_tweet_open,
    crypto_hashblocks_sha512_tweet,
    crypto_hash_sha512_tweet,
    crypto_sign_ed25519_tweet_keypair,
    crypto_sign_ed25519_tweet,
    crypto_sign_ed25519_tweet_open,
)
