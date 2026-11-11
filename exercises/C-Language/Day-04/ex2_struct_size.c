#include <stdio.h>
#include <stddef.h>

struct bad_order { char c; int i; char d; };
struct good_order { int i; char c; char d; };

int main(void) {
    printf("bad_order  sizeof=%zu  offsets c=%zu i=%zu d=%zu\n",
           sizeof(struct bad_order),
           offsetof(struct bad_order, c),
           offsetof(struct bad_order, i),
           offsetof(struct bad_order, d));
    printf("good_order sizeof=%zu  offsets i=%zu c=%zu d=%zu\n",
           sizeof(struct good_order),
           offsetof(struct good_order, i),
           offsetof(struct good_order, c),
           offsetof(struct good_order, d));
    return 0;
}
