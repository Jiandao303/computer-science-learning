#include "util.h"

int add(int a, int b) { return a + b; }

int sum_array(const int *arr, size_t n) {
    int s = 0;
    for (size_t i = 0; i < n; i++) s += arr[i];
    return s;
}
