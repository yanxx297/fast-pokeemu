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

#ifndef _KERNEL_H
#define _KERNEL_H

/* Ring 0 */
#define SEL_RING0_CS 0x68
#define SEL_RING0_DS 0xb0
#define SEL_RING0_SS 0x70
#define SEL_RING0_ES SEL_RING0_DS
#define SEL_RING0_FS SEL_RING0_DS
#define SEL_RING0_GS SEL_RING0_DS

/* Ring 1 */
#define SEL_RING1_CS 0xc0
#define SEL_RING1_DS 0x88
#define SEL_RING1_SS 0x90
#define SEL_RING1_ES SEL_RING1_DS
#define SEL_RING1_FS SEL_RING1_DS
#define SEL_RING1_GS SEL_RING1_DS

/* Ring 2 */
#define SEL_RING2_CS 0x98
#define SEL_RING2_DS 0xa0
#define SEL_RING2_SS 0xa8
#define SEL_RING2_ES SEL_RING2_DS
#define SEL_RING2_FS SEL_RING2_DS
#define SEL_RING2_GS SEL_RING2_DS

/* Ring 3 */
#define SEL_RING3_CS 0x78
#define SEL_RING3_DS 0xb8
#define SEL_RING3_SS 0x80
#define SEL_RING3_ES SEL_RING3_DS
#define SEL_RING3_FS SEL_RING3_DS
#define SEL_RING3_GS SEL_RING3_DS

/* Segments for exception handler */
#define SEL_EXCP_CS 0xd0
#define SEL_EXCP_DS 0xd8
#define SEL_EXCP_SS 0xe0
#define SEL_EXCP_FS 0xe8
#define SEL_EXCP_GS 0xf0

/* Segment selectors of task gates for each exception*/
#define SEL_EXCP00 0xf8
#define SEL_EXCP01 0x100
#define SEL_EXCP02 0x108
#define SEL_EXCP03 0x110
#define SEL_EXCP04 0x118
#define SEL_EXCP05 0x120
#define SEL_EXCP06 0x128
#define SEL_EXCP07 0x130
#define SEL_EXCP08 0x138
#define SEL_EXCP09 0x140
#define SEL_EXCP10 0x148
#define SEL_EXCP11 0x150
#define SEL_EXCP12 0x158
#define SEL_EXCP13 0x160
#define SEL_EXCP14 0x168
#define SEL_EXCP15 0x170
#define SEL_EXCP16 0x178
#define SEL_EXCP17 0x180
#define SEL_EXCP18 0x188
#define SEL_EXCP19 0x190
#define SEL_EXCP32 0x198

/* Add RPL to a segment selector */
#define SEL_RPL(s,r) ((s) | (r))

#if (SEL_RING0_CS != SEL_RING0_SS-8) || (SEL_RING0_SS != SEL_RING3_CS-8) || (SEL_RING3_CS != SEL_RING3_SS-8)
#error "For SYSENTER/SYSEXIT, SEL_RING0_CS, SEL_RING0_SS, SEL_RING3_CS, SEL_RING3_SS must be consecutive"
#endif

#define PAGE_SIZE 0x1000
#define PAGE_ALIGN(x) (((uint32_t) (x)) & ~PAGE_SIZE)

#define GDT_ENTRY 53

/* Virtual 8086 Mode */
#define VM_BIT 1<<17
#define SEL_VM_CS 0x0
#define SEL_VM_DS 0x0
#define SEL_VM_SS 0x80
#define VM_EIP 0x0
#define VM_ESP 0x800
#endif	/* _KERNEL_H */
