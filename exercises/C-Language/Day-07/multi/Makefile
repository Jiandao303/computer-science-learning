CC      = gcc
CFLAGS  = -std=c11 -Wall -Wextra -Wpedantic -g -O0 -Iinclude
TARGET  = app
OBJS    = src/main.o src/util.o

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $(OBJS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: clean
