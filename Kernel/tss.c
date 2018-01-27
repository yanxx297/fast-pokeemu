// This file is part of KEmuFuzzer.
// 
// KEmuFuzzer is free software: you can redistribute it and/or modify it under
// the terms of the GNU General Public License as published by the Free
// Software Foundation, either version 3 of the License, or (at your option)
// any later version.
// 
// KEmuFuzzer is distributed in the hope that it will be useful, but WITHOUT ANY
// WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
// FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
// details.
// 
// You should have received a copy of the GNU General Public License along with
// KEmuFuzzer.  If not, see <http://www.gnu.org/licenses/>.

#include <stdio.h>
#include <stdint.h>
#include <sys/tss.h>
#include <sys/asm.h>

void set_tss_base(tss_t *tss, uint32_t eip, uint32_t esp, uint32_t eflags,
	     uint16_t cs, uint16_t ds, uint16_t ss, uint32_t cr3,
	     uint16_t ss0, uint16_t ss1, uint16_t ss2,
	     uint32_t sp0, uint32_t sp1, uint32_t sp2,
	     uint16_t ldt, uint16_t es, uint16_t fs, uint16_t gs) 
{
  int i;
  char *p;

  p = (char *) tss;
  for(i=0;i<sizeof(tss_t);i++)
    p[i]=0;
#ifdef DEBUG
  kprintf("tss addr: 0x%08x\n", (uint32_t) tss);
  kprintf("eip: 0x%08x ", eip);
  kprintf("esp: 0x%08x ", esp);
  kprintf("eflags: 0x%08x ", eflags);
  kprintf("cs: 0x%08x ", cs);
  kprintf("ds: 0x%08x ", ds);
  kprintf("ss: 0x%08x\n", ss);
  kprintf("cr3: 0x%08x ", cr3);
  kprintf("ss0: 0x%08x ", ss0);
  kprintf("ss1: 0x%08x ", ss1);
  kprintf("ss2: 0x%08x ", ss2);
  kprintf("sp0: 0x%08x ", sp0);
  kprintf("sp1: 0x%08x ", sp1);
  kprintf("sp2: 0x%08x\n", sp2);
#endif

  tss->ebp = esp;
  tss->ds = ds;
  tss->es = es;
  tss->fs = fs;
  tss->gs = gs;
  tss->ss = ss;
  tss->ss0 = ss0;
  tss->ss1 = ss1;
  tss->ss2 = ss2;
  tss->cs = cs;
  tss->ldt = ldt;

  tss->esp = esp;
  tss->esp0 = sp0;
  tss->esp1 = sp1;
  tss->esp2 = sp2;
  tss->cr3 = cr3;
  tss->eflags = eflags;
  
  tss->eip = eip;
}

void var_set_tss(tss_args in){
        tss_t *tss = in.tss;
        uint32_t eip = in.eip;
        uint32_t esp = in.esp;
        uint32_t eflags = in.eflags;
        uint16_t cs = in.cs;
        uint16_t ds = in.ds;
        uint16_t ss = in.ss;
        uint32_t cr3 = in.cr3;
        uint16_t ss0 = in.ss0;
        uint16_t ss1 = in.ss1;
        uint16_t ss2 = in.ss2;
        uint32_t sp0 = in.sp0;
        uint32_t sp1 = in.sp1;
        uint32_t sp2 = in.sp2;
        uint16_t ldt = in.ldt;
        uint16_t fs = in.fs ? in.fs : in.ds;
        uint16_t gs = in.gs ? in.gs : in.ds;
        uint16_t es = in.ds;
        set_tss_base(tss, eip, esp, eflags, cs, ds, ss, cr3, ss0, ss1, ss2, sp0, sp1, sp2, ldt, es, fs, gs);
}
