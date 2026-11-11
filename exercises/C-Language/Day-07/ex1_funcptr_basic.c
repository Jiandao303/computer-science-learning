#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (*binop_t)(int, int);

static int add(int a, int b) { return a + b; }
static int sub(int a, int b) { return a - b; }
static int mul(int a, int b) { return a * b; }

static int cmp_int(const void *a, const void *b) {
    int x = *(const int *)a;
    int y = *(const int *)b;
    return (x > y) - (x < y);
}

static void swap_any(void *a, void *b, size_t size) {
    unsigned char tmp[64];
    if (size > sizeof tmp) return;
    memcpy(tmp, a, size);
    memcpy(a, b, size);
    memcpy(b, tmp, size);
}

int main(void) {
    binop_t ops[] = {add, sub, mul};
    const char *names[] = {"add", "sub", "mul"};
    for (int i = 0; i < 3; i++) printf("%s(7,3)=%d\n", names[i], ops[i](7, 3));

    int a[] = {3, 1, 2};
    qsort(a, 3, sizeof a[0], cmp_int);
    printf("sorted: %d %d %d\n", a[0], a[1], a[2]);

    int x = 10, y = 20;
    swap_any(&x, &y, sizeof x);
    printf("after swap_any: x=%d y=%d\n", x, y);
    return 0;
}
