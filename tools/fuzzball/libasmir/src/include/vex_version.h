/* vex_version.h is automatically generated from vex_version.h.in, so
   don't try to modify the former. */

/* This file is essentially a replacement for VEX's old
   priv/main/vex_svnversion.h, allowing us to write code conditional
   on features that were added or removed at various points in VEX's
   development. (By contrast the Valgrind developers don't try to
   support this model, which is probably why the aforementioned file
   was never public and eventually removed: particular versions of
   Valgrind are meant to work with just one corresponding version of
   VEX.)

   Internal to LibASMIR, including if you include config.h, the same
   value is available as a macro "VEX_VERSION", but we don't want
   users of the library to include that file, since any other
   autoconf-based program will have a conflicting config.h of its own.
*/

#ifndef VEX_VERSION_H_
#define VEX_VERSION_H_

#define LIBASMIR_VEX_VERSION 2737

#endif /* !VEX_VERSION_H_ */
