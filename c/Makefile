CC     ?= gcc
CFLAGS ?= -std=c99 -Wall -Wextra -pedantic -O2

all: banker

banker: main.c banker.c samples.c banker.h samples.h
	$(CC) $(CFLAGS) -o banker main.c banker.c samples.c

test: test.c banker.c samples.c banker.h samples.h
	$(CC) $(CFLAGS) -o banker_test test.c banker.c samples.c
	./banker_test

clean:
	rm -f banker banker_test banker.exe banker_test.exe
