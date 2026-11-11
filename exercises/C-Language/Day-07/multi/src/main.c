#include <stdio.h>
#include "util.h"

int main(void) {
    int a[] = {1, 2, 3, 4};
    printf("add(2,3) = %d\n", add(2, 3));
    printf("sum = %d\n", sum_array(a, 4));
    return 0;
}
