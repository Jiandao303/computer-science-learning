#include <stdio.h>
#include <stdint.h>
#include <limits.h>

static unsigned get_bits(unsigned x, int start, int len) {
    return (x >> start) & ((1u << len) - 1u);
}

static unsigned set_bit(unsigned x, int pos)   { return x | (1u << pos); }
static unsigned clear_bit(unsigned x, int pos) { return x & ~(1u << pos); }
static int test_bit(unsigned x, int pos)       { return (int)((x >> pos) & 1u); }

static void print_bin32(unsigned x) {
    for (int i = 31; i >= 0; i--) putchar(((x >> i) & 1u) ? '1' : '0');
    putchar('\n');
}

int main(void) {
    unsigned x = 0;
    printf("set_bit(0,3)=%u\n", set_bit(x, 3));
    printf("clear_bit(%u,3)=%u\n", set_bit(x, 3), clear_bit(set_bit(x, 3), 3));
    printf("test_bit(%u,3)=%d\n", set_bit(x, 3), test_bit(set_bit(x, 3), 3));
    printf("get_bits(0x12345678,4,4)=0x%X\n", get_bits(0x12345678u, 4, 4));

    int neg5 = -5;
    /* 补码恒等式：-x == ~x + 1。这里验证 x=5 的情形。 */
    int five = 5;
    printf("-5 as unsigned=0x%X\n", (unsigned)neg5);
    printf("5, ~5, ~5+1 = %d, %d, %d\n", five, ~five, ~five + 1);
    printf("INT_MIN negated as unsigned=0x%X\n", (unsigned)(-(unsigned)INT_MIN));

    int8_t s8 = -1;
    printf("sign extend int8 -1 -> int32: 0x%X\n", (unsigned)(int32_t)s8);
    printf("UINT_MAX+1=%u\n", UINT_MAX + 1u);
    printf("0x12345678 = "); print_bin32(0x12345678u);
    return 0;
}
