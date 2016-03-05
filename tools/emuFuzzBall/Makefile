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

# TODO: standardize on a location for Z3 that can be within the
# pokemu-oras subtree (if only by symlink), so that this Makefile
# doesn't need to be changed between users.
Z3ROOT = $(HOME)/Project/lib
# Z3ROOT = $(HOME)/emu/pokeemu/pokemu-oras # (Stephen's system)
UNAME_ARCH = $(shell uname -m)
ifeq ($(UNAME_ARCH),i386)
    Z3_DIR = $(Z3ROOT)/z3-2.15-32bit/z3
else ifeq ($(UNAME_ARCH),i486)
    Z3_DIR = $(Z3ROOT)/z3-2.15-32bit/z3
else ifeq ($(UNAME_ARCH),i586)
    Z3_DIR = $(Z3ROOT)/z3-2.15-32bit/z3
else ifeq ($(UNAME_ARCH),i686)
    Z3_DIR = $(Z3ROOT)/z3-2.15-32bit/z3
else ifeq ($(UNAME_ARCH),x86_64)
    Z3_DIR = $(Z3ROOT)/z3-x64-2.15
else
    $(error We appear not to have a Z3 binary for your architecture.)
endif

export PACKS = str ocamlgraph extlib unix sqlite3 zip
export LIBS = vine z3
export YFLAGS = -v
export INCDIRS += $(VINE_OCAMLDIR) $(Z3_DIR)/ocaml
export EXTLIBDIRS += $(VINEPATH)/stp/ocaml $(VINEPATH)/stp $(VINE_OCAMLDIR)

export STATIC = 1
export CLIBS = asmir vex bfd iberty z3 stdc++ gmp pthread z
export CFLAGS = -O2
export OCAMLINCLUDES = -I $(VINE_OCAMLDIR) -I $(VINE_EXECDIR) -I $(Z3_DIR)/ocaml
export OCAMLFLAGS = -dtypes $(OCAMLINCLUDES)
export LDFLAGS = $(LIBASMIR_LDFLAGS) -static
export CLIBFLAGS= $(LDFLAGS)
export LIBDIRS = $(VINE_OCAMLDIR) $(VINEPATH)/libasmir/src $(VINEPATH)/stp \
                 $(Z3_DIR)/lib

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
        SOURCES=z3vc.mli z3vc.ml \
	        z3vc_query_engine.mli z3vc_query_engine.ml \
		fuzzball.ml
        DOC_FILES=$(SOURCES)
endef
export PROJ_fuzzball

define PROJ_emu_fuzzball
        INCDIRS += $(VINE_EXECDIR) $(VINE_TRACEDIR) $(VINE_STPDIR) 
	LIBS := stpvc $(LIBS)
	LIBS += trace execution
        RESULT=emu_fuzzball
        SOURCES= interpreter.ml z3vc.mli z3vc.ml \
	        z3vc_query_engine.mli z3vc_query_engine.ml \
		emu_fuzzball.ml
        DOC_FILES=$(SOURCES)
endef
export PROJ_emu_fuzzball

define PROJ_diff_behavior
        INCDIRS += $(VINE_EXECDIR) $(VINE_TRACEDIR) $(VINE_STPDIR)  $(Z3ROOT)
	LIBS := stpvc $(LIBS)
	LIBS += trace execution
        RESULT=diff_behavior
        SOURCES=z3vc.mli z3vc.ml \
	        z3vc_query_engine.mli z3vc_query_engine.ml \
		diff_behavior.ml
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

$(Z3_DIR)/ocaml/z3.cmxa: $(Z3_DIR)/ocaml/z3.ml $(Z3_DIR)/ocaml/z3.mli \
	$(Z3_DIR)/lib/libz3.a
	(cd $(Z3_DIR)/ocaml && sh -x ./build-lib.sh $(OCAMLLIB))

clean:
	rm -f $(Z3_DIR)/ocaml/z3.{cmx,cmxa,cma,cmi,cmo}
	make -f $(OCAMLMAKEFILE) subprojs SUBTARGET=$@

%:	$(Z3_DIR)/ocaml/z3.cmxa
	make -f $(OCAMLMAKEFILE) subprojs SUBTARGET=$@
