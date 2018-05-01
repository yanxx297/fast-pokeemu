export VINEROOT=$(shell pwd)/../fuzzball
export VINEPATH=$(VINEROOT)
export VINE_PROJECTS=$(VINEROOT)/projects
export OCAMLMAKEFILE=$(VINEPATH)/ocaml/OCamlMakefile
export LIBASMIR=$(VINEPATH)
export VINE_OCAMLDIR=$(VINEPATH)/ocaml
export VINE_STPDIR=$(VINEPATH)/stp/ocaml
export VINE_EXECDIR=$(VINEPATH)/execution
export VINE_TRACEDIR=$(VINEPATH)/trace
include $(LIBASMIR)/libasmir/makefile.inc

UNAME_ARCH = $(shell uname -m)

export PACKS = str extlib unix zip
export LIBS = vine 
export YFLAGS = -v
export INCDIRS += $(VINE_OCAMLDIR)
export EXTLIBDIRS += $(VINEPATH)/stp/ocaml $(VINEPATH)/stp $(VINE_OCAMLDIR)

export STATIC = 1
export CLIBS = asmir vex bfd iberty stdc++ gmp pthread z
export CFLAGS = -O2
export OCAMLINCLUDES = -I $(VINE_OCAMLDIR) -I $(VINE_EXECDIR)
export OCAMLFLAGS = -dtypes $(OCAMLINCLUDES)
export LDFLAGS = $(LIBASMIR_LDFLAGS) -static
export CLIBFLAGS= $(LDFLAGS)
export LIBDIRS = $(VINE_OCAMLDIR) $(VINEPATH)/libasmir/src $(VINEPATH)/stp

export OCAMLDEP = ocamldep $(OCAMLINCLUDES)

# default subprojects to build
ifndef SUBPROJS
export SUBPROJS = emu_fuzzball fuzzball diff_behavior multi_path multi_path_test
endif

define PROJ_fuzzball
        INCDIRS += $(VINE_EXECDIR) $(VINE_TRACEDIR) $(VINE_STPDIR) 
	LIBS := stpvc $(LIBS)
	LIBS += trace execution
        RESULT=fuzzball
        SOURCES=fuzzball.ml
        DOC_FILES=$(SOURCES)
endef
export PROJ_fuzzball

define PROJ_emu_fuzzball
        INCDIRS += $(VINE_EXECDIR) $(VINE_TRACEDIR) $(VINE_STPDIR) 
	LIBS := stpvc $(LIBS)
	LIBS += trace execution
        RESULT=emu_fuzzball
        SOURCES= interpreter.ml emu_fuzzball.ml
        DOC_FILES=$(SOURCES)
endef
export PROJ_emu_fuzzball

define PROJ_diff_behavior
        INCDIRS += $(VINE_EXECDIR) $(VINE_TRACEDIR) $(VINE_STPDIR)	
	LIBS := stpvc $(LIBS)
	LIBS += trace execution
        RESULT=diff_behavior
        SOURCES=diff_behavior.ml
        DOC_FILES=$(SOURCES)
endef
export PROJ_diff_behavior

define PROJ_multi_path
        INCDIRS += $(VINE_EXECDIR) $(VINE_TRACEDIR) $(VINE_STPDIR) 
	LIBS := stpvc $(LIBS)
	LIBS += trace execution
        RESULT=multi_path
        SOURCES=multi_path.ml
        DOC_FILES=$(SOURCES)
endef
export PROJ_multi_path

define PROJ_multi_path_test
        INCDIRS += $(VINE_EXECDIR) $(VINE_TRACEDIR) $(VINE_STPDIR) 
	LIBS := stpvc $(LIBS)
	LIBS += trace execution
        RESULT=multi_path_test
        SOURCES=interpreter.ml multi_path_test.ml
        DOC_FILES=$(SOURCES)
endef
export PROJ_multi_path_test

# suffix for bytecode (which when we make all is debug code)
export BCSUFFIX = .dbg

all: nc
#dc

OCAMLLIB := $(shell ocamlc -v | grep library | awk '{ print $$4 }')

clean:
	make -f $(OCAMLMAKEFILE) subprojs SUBTARGET=$@

%:	
	make -f $(OCAMLMAKEFILE) subprojs SUBTARGET=$@
