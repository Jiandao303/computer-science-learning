#include <stdio.h>

/* static 局部变量跨调用保留；注意不要在同一条 printf 里多次调用，
   因为实参求值顺序未定义，输出顺序可能是 3 2 1 而不是 1 2 3。 */
static int next_id(void) {
    static int n = 0;
    return ++n;
}

int main(void) {
    int a = next_id();
    int b = next_id();
    int c = next_id();
    printf("counter: %d %d %d\n", a, b, c);
    return 0;
}
