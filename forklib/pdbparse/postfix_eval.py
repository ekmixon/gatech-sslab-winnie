#!/usr/bin/env python

from operator import add, sub, mul, mod, itruediv, pow, and_, or_, lshift, rshift
from operator import inv

global vars
vars = {}


def assign(a, b):
    global vars
    if not isinstance(a, str) or not a.startswith("$"):
        raise ValueError("Cannot assign to a constant")
    vars[a] = b


binary_ops = {
    "+": add,
    "-": sub,
    "/": itruediv,
    "*": mul,
    "%": mod,
    "**": pow,
    "<<": lshift,
    ">>": rshift,
    "&": and_,
    "|": or_,
}

# Note:
# ^ means "dereference". In the airbag unit tests, this is accompanied by
# a memory region that can deal with dereferencing addresses (presumably).
# Their test uses FakeMemoryRegion, which appears to just return x+1 for
# any pointer x that is dereferenced. So we use lambda x: x+1 as a
# placeholder.
unary_ops = {
    "~": inv,
    "^": lambda x: x + 1,
}


def evaluate(pfstr):
    global vars
    stack = []
    for tok in pfstr.split():
        if tok == "=":
            try:
                b = stack.pop()
                a = stack.pop()
            except IndexError:
                raise ValueError("Not enough values on the stack for requested operation")

            if isinstance(b, str) and (b.startswith("$") or b.startswith(".")):
                try:
                    b = vars[b]
                except KeyError:
                    raise ValueError(f"Name {b} referenced before assignment")

            assign(a, b)
        elif tok in binary_ops:
            try:
                b = stack.pop()
                a = stack.pop()
            except IndexError:
                raise ValueError("Not enough values on the stack for requested operation")

            if isinstance(a, str) and (a.startswith("$") or a.startswith(".")):
                try:
                    a = vars[a]
                except KeyError:
                    raise ValueError(f"Name {a} referenced before assignment")
            if isinstance(b, str) and (b.startswith("$") or b.startswith(".")):
                try:
                    b = vars[b]
                except KeyError:
                    raise ValueError(f"Name {b} referenced before assignment")

            stack.append(binary_ops[tok](a, b))
        elif tok in unary_ops:
            try:
                a = stack.pop()
            except IndexError:
                raise ValueError("Not enough values on the stack for requested operation")

            if isinstance(a, str) and (a.startswith("$") or a.startswith(".")):
                try:
                    a = vars[a]
                except KeyError:
                    raise ValueError(f"Name {a} referenced before assignment")

            stack.append(unary_ops[tok](a))
        elif tok.startswith("$") or tok.startswith("."):
            stack.append(tok)
        else:
            stack.append(int(tok, 0))
    if stack:
        raise ValueError("Values remain on the stack after processing")


if __name__ == "__main__":
    pfstrs = [
        ("$T0 $ebp = $eip $T0 4 + ^ = $ebp $T0 ^ = $esp $T0 8 + = $L $T0 .cbSavedRegs - = $P $T0 8 + .cbParams + =",
         True),
        ("$T0 $ebp = $eip $T0 4 + ^ = $ebp $T0 ^ = $esp $T0 8 + = $L $T0 .cbSavedRegs - = $P $T0 8 + .cbParams + = $ebx $T0 28 - ^ =",
         True),
        ("$T0 $ebp = $T2 $esp = $T1 .raSearchStart = $eip $T1 ^ = $ebp $T0 = $esp $T1 4 + = $L $T0 .cbSavedRegs - = $P $T1 4 + .cbParams + = $ebx $T0 28 - ^ =",
         True),
    ]

    vars["$ebp"] = 0xbfff0010
    vars["$eip"] = 0x10000000
    vars["$esp"] = 0xbfff0000
    vars[".cbSavedRegs"] = 4
    vars[".cbParams"] = 4
    vars[".raSearchStart"] = 0xbfff0020

    for (test, should_succeed) in pfstrs:
        try:
            evaluate(test)
            if len(repr(test)) > 50:
                test = f"{test[:50]}[...]"
            if not should_succeed:
                print('Test %-60s FAILED.' % repr(test))
            else:
                print('Test %-60s PASSED.' % repr(test))
        except ValueError:
            if should_succeed:
                print('Test %-60s FAILED.' % repr(test))
            else:
                print('Test %-60s PASSED.' % repr(test))

    validate_data_1 = {
        "$T0": 3221159954,
        "$T1": 3221159968,
        "$T2": 3221159961,
        "$eip": 3221159969,
        "$ebp": 3221159954,
        "$esp": 3221159972,
        "$L": 3221159950,
        "$P": 3221159976,
        "$ebx": 3221159927,
        ".cbSavedRegs": 4,
        ".cbParams": 4,
    }

    for k in validate_data_1:
        assert vars[k] == validate_data_1[k]

    vars = {}

    validate_data_0 = {
        "$rAdd": 8,
        "$rAdd2": 4,
        "$rSub": 3,
        "$rMul": 54,
        "$rDivQ": 1,
        "$rDivM": 3,
        "$rDeref": 10,
    }

    pfstrs = [
        ("$rAdd 2 2 + =", True),  # $rAdd = 2 + 2 = 4
        ("$rAdd $rAdd 2 + =", True),  # $rAdd = $rAdd + 2 = 6
        ("$rAdd 2 $rAdd + =", True),  # $rAdd = 2 + $rAdd = 8
        ("99", False),  # put some junk on the stack...
        ("$rAdd2 2 2 + =", True),  # ...and make sure things still work
        ("$rAdd2\t2\n2 + =", True),  # same but with different whitespace
        ("$rAdd2 2 2 + = ", True),  # trailing whitespace
        (" $rAdd2 2 2 + =", True),  # leading whitespace
        ("$rAdd2  2 2 +   =", True),  # extra whitespace
        ("$T0 2 = +", False),  # too few operands for add
        ("2 + =", False),  # too few operands for add
        ("2 +", False),  # too few operands for add
        ("+", False),  # too few operands for add
        ("^", False),  # too few operands for dereference
        ("=", False),  # too few operands for assignment
        ("2 =", False),  # too few operands for assignment
        ("2 2 + =", False),  # too few operands for assignment
        ("2 2 =", False),  # can't assign into a literal
        ("k 2 =", False),  # can't assign into a constant
        ("2", False),  # leftover data on stack
        ("2 2 +", False),  # leftover data on stack
        ("$rAdd", False),  # leftover data on stack
        ("0 $T1 0 0 + =", False),  # leftover data on stack
        ("$T2 $T2 2 + =", False),  # can't operate on an undefined value
        ("$rMul 9 6 * =", True),  # $rMul = 9 * 6 = 54
        ("$rSub 9 6 - =", True),  # $rSub = 9 - 6 = 3
        ("$rDivQ 9 6 / =", True),  # $rDivQ = 9 / 6 = 1
        ("$rDivM 9 6 % =", True),  # $rDivM = 9 % 6 = 3
        ("$rDeref 9 ^ =", True)  # $rDeref = ^9 = 10 (FakeMemoryRegion)
    ]

    for (test, should_succeed) in pfstrs:
        try:
            evaluate(test)
            if len(repr(test)) > 50:
                test = f"{test[:50]}[...]"
            if not should_succeed:
                print('Test %-60s FAILED.' % repr(test))
            else:
                print('Test %-60s PASSED.' % repr(test))
        except ValueError:
            if should_succeed:
                print('Test %-60s FAILED.' % repr(test))
            else:
                print('Test %-60s PASSED.' % repr(test))

    for k in validate_data_0:
        assert vars[k] == validate_data_0[k]
