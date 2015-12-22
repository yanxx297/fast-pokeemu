fpu_tags.o fpu_tags.d : fpu_tags.cc ../config.h softfloat.h softfloat-specialize.h \
 ../cpu/i387.h ../fpu/softfloat.h ../fpu/tag_w.h ../fpu/status_w.h \
 ../fpu/control_w.h
fpu_tags.bc fpu_tags.d : fpu_tags.cc ../config.h softfloat.h softfloat-specialize.h \
 ../cpu/i387.h ../fpu/softfloat.h ../fpu/tag_w.h ../fpu/status_w.h \
 ../fpu/control_w.h
