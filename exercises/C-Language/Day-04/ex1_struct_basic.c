#include <stdio.h>
#include <stddef.h>

typedef struct { int x, y; } Point;
typedef struct { Point tl, br; } Rect;

static int rect_area(const Rect *r) {
    int w = r->br.x - r->tl.x;
    int h = r->br.y - r->tl.y;
    return (w < 0 ? -w : w) * (h < 0 ? -h : h);
}

static int rect_perimeter(const Rect *r) {
    int w = r->br.x - r->tl.x, h = r->br.y - r->tl.y;
    if (w < 0) w = -w;
    if (h < 0) h = -h;
    return 2 * (w + h);
}

int main(void) {
    Rect r = {{0, 0}, {3, 4}};
    printf("area=%d perimeter=%d\n", rect_area(&r), rect_perimeter(&r));
    return 0;
}
