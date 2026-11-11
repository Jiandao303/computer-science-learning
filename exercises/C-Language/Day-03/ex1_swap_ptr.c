#include <stdio.h>
#include <stddef.h>
static void swap(int *a, int *b) { int t = *a; *a = *b; *b = t; }
static void reset(int **pp) { *pp = NULL; }
int main(void) {
    int x = 1, y = 2;
    swap(&x, &y);
    printf("after swap: x=%d y=%d\n", x, y);
    int *p = &x;
    reset(&p);
    printf("after reset: %s\n", p == NULL ? "NULL" : "non-NULL");
    int a[5] = {1,2,3,4,5};
    printf("diff=%td sizeof_a=%zu sizeof_ptr=%zu\n", &a[2]-&a[0], sizeof a, sizeof &a[0]);
    return 0;
}
