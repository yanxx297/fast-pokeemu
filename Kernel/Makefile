# This kernel has most recently been compiled successfully with GCC
# version 5.4.0, as in Ubuntu 16.04. If you use a different compiler
# version, you may get a different memory layout, which would require
# changes in other parts of the system to work correctly. For instance
# we've seen this happen with GCC 7. The sanity check on the address of
# "testcase" is designed to catch many instances of this problem.
CC := gcc-5

CFLAGS += -fno-asynchronous-unwind-tables -Wall -m32 -O2 -nostdlib -nostdinc -nostartfiles -I./include/
LDFLAGS=-Wl,--script=kernel.ld,--build-id=none
OBJS=boot.o loader.o kprintf.o console.o main.o interrupts.o asm.o int_wrappers.o tss.o
DEST=kernel

all: $(DEST) disk

$(DEST): $(OBJS) 
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^
	@echo Check that the testcase location is the expected 0x219000:
	nm $(DEST) | grep ' D testcase$$' | fgrep 00219000

%.o:	%.c
	$(CC) $(CFLAGS) -c -o $@ $<

boot.o: boot.S
	$(CC) $(CFLAGS) -c -o $@ $<

int_wrappers.o: int_wrappers.S
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	-rm -f $(DEST) $(OBJS) floppy.img interrupts.c interrupts.h int_wrappers.S 

floppy.img: $(DEST)
	dd if=/dev/zero of=floppy.img bs=1024 count=1440
	/sbin/mkdosfs floppy.img
	mmd -i floppy.img boot
	mmd -i floppy.img boot/grub
	mcopy -i floppy.img grub_stuff/boot/grub/* ::boot/grub
	mcopy -i floppy.img kernel ::
	#/home/grad01/yan/Project/lib/grub-0.97/grub/grub --batch --device-map=/dev/null < grub_stuff/grub.cfg

disk: floppy.img 

int_wrappers.c interrupts.c interrupts.h: gen_ints_asm.py
	# use port 69 to notify interrupts & exceptions
	python gen_ints_asm.py 69
	# At the moment, we've made changes to interrups.c that haven't
	# been merged back into gen_ints_asm.py
	cp interrupts-mod.c interrupts.c

# dependencies
loader.o: interrupts.h
