"""Independent test oracle for the documented v1 stderr result line (not production code).

Read the final line as JSON, or as two alphabet symbols followed by MSB-first UTF-8 bits.
Expected status/child facts come from the test's real fixture, not from the wrapper implementation.
"""
import json


def read(report):
    try:
        line=report.splitlines()[-1]
        if line.startswith('{'):
            return json.loads(line)
        zero,one=line[:2]
        encoded=line[2:]
        if zero==one or not encoded or len(encoded)%8: return None
        bits=''.join('0' if c==zero else '1' if c==one else '?' for c in encoded)
        data=bytes(int(bits[i:i+8],2) for i in range(0,len(bits),8))
        return json.loads(data.decode('utf-8'))
    except (ValueError,IndexError,UnicodeError):
        return None
