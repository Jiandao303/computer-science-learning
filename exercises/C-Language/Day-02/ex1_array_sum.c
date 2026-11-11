#include <stdio.h>

int main(void) {
    int a[] = {3, 7, 1, 9, 4};
    size_t n = sizeof a / sizeof a[0];
    int sum = 0, max = a[0];
    for (size_t i = 0; i < n; i++) {
        sum += a[i];
        if (a[i] > max) max = a[i];
    }
    printf("sum=%d max=%d n=%zu\n", sum, max, n);
    return 0;
}
