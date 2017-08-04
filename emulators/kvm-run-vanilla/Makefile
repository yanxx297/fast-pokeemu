VANILLA_KVM := 1

CFLAGS = -Wall -g -I. -I./libudis86/
ifndef VANILLA_KVM
CFLAGS += -I../kvm-kmod-2.6.37/
endif
LDFLAGS = -lz

all: libudis86 kvm 

kvm: libudis86/libudis86.a kvm.cc kvm.h x86.h x86_cpustate.h
	$(CXX) $(CFLAGS) -o kvm kvm.cc libudis86/libudis86.a $(LDFLAGS)

libudis86:
	$(MAKE) -C libudis86

clean:
	rm -f *.o *.a *.pyc
	$(MAKE) -C libudis86 clean

distclean: clean
	rm -f kvm
	$(MAKE) -C libudis86 distclean

.PHONY: all distclean libudis86 
