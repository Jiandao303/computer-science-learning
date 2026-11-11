#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

typedef struct { int *data; size_t len; size_t cap; } IntVec;

static int vec_push(IntVec *v, int value) {
    if (v->len == v->cap) {
        size_t new_cap = (v->cap == 0) ? 4 : v->cap * 2;
        if (new_cap > SIZE_MAX / sizeof *v->data) return -1;
        int *tmp = realloc(v->data, new_cap * sizeof *v->data);
        if (tmp == NULL) return -1;
        v->data = tmp;
        v->cap = new_cap;
    }
    v->data[v->len++] = value;
    return 0;
}

static void vec_free(IntVec *v) {
    free(v->data);
    v->data = NULL;
    v->len = v->cap = 0;
}

int main(void) {
    IntVec v = {0};
    for (int i = 0; i < 10; i++) {
        if (vec_push(&v, i * i) != 0) { fprintf(stderr, "push failed\n"); vec_free(&v); return 1; }
    }
    for (size_t i = 0; i < v.len; i++) printf("%d ", v.data[i]);
    printf("\nlen=%zu cap=%zu\n", v.len, v.cap);
    vec_free(&v);
    return 0;
}
