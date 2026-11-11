#include <stdio.h>
#include <string.h>
static void safe_copy(char *dst, size_t size, const char *src) {
    if (size == 0) return;
    strncpy(dst, src, size - 1);
    dst[size - 1] = '\0';
}
int main(void) {
    char raw[8]; char safe[8];
    strncpy(raw, "abcdefghij", sizeof raw);
    printf("raw_has_nul=%d\n", memchr(raw, '\0', sizeof raw) != NULL);
    safe_copy(safe, sizeof safe, "abcdefghij");
    printf("safe=\"%s\" len=%zu\n", safe, strlen(safe));
    return 0;
}
