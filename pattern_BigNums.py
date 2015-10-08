#///// P a t t e r n   f o r   u s i n g   l a r g e   n u m b e r s   a n d   f r a c t i o n s

import progSpec
import codeDogParser

def apply(tags):
    CPP_GlobalText=r"""

typedef mpz_class BigInt;

struct BigFrac :mpq_class {
    BigFrac(const char* numStr, int base);
    BigFrac(const string str);
    BigFrac(const int32_t &num=0):mpq_class(num){};
};

"""

    progSpec.setCodeHeader('cpp', CPP_GlobalText)
    progSpec.setTagValue(tags, 'libraries.gmp.useStatus', 'dynaLoad')
