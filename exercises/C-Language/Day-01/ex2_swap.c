#include <stdio.h>
static void swap_wrong(int a, int b) { int t = a; a = b; b = t; }
static void swap(int *a, int *b) { int t = *a; *a = *b; *b = t; }
int main(void) {
    int a = 1, b = 2;
    printf("before: a=%d b=%d\n", a, b);
    swap_wrong(a, b);
    printf("after value swap: a=%d b=%d\n", a, b);
    swap(&a, &b);
    printf("after pointer swap: a=%d b=%d\n", a, b);
    return 0;
}
