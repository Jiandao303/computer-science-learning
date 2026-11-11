#include <stdio.h>
#include <limits.h>
int main(void) {
    printf("char=%zu short=%zu int=%zu long=%zu long long=%zu float=%zu double=%zu ptr=%zu\n",
           sizeof(char), sizeof(short), sizeof(int), sizeof(long), sizeof(long long),
           sizeof(float), sizeof(double), sizeof(void *));
    printf("INT_MAX=%d INT_MIN=%d UINT_MAX=%u\n", INT_MAX, INT_MIN, UINT_MAX);
    return 0;
}
