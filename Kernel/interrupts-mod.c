// Warning: this file has been automatically generated by gen_ints_asm.py

#include "interrupts.h"

extern int kprintf(const char *format, ...);

static void set_idt_entry(idte_t *idt, uint8_t n, uint16_t seg, uint32_t off)
{
  idt[n].off_0_15 = off & 0xffff;
  idt[n].off_16_31 = (off>>16) & 0xffff;
  idt[n].seg = seg;
  idt[n].zero = 0;
  idt[n].type = 0xe; /* interrupt gate */
  idt[n].dpl = 3;
  idt[n].present = 1;
}

void set_interrupt_handlers(idte_t *pidt, uint16_t seg)
{
  set_idt_entry(pidt, 0, seg, (uint32_t)int_handler_0);
  set_idt_entry(pidt, 1, seg, (uint32_t)int_handler_1);
  set_idt_entry(pidt, 2, seg, (uint32_t)int_handler_2);
  set_idt_entry(pidt, 3, seg, (uint32_t)int_handler_3);
  set_idt_entry(pidt, 4, seg, (uint32_t)int_handler_4);
  set_idt_entry(pidt, 5, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 6, seg, (uint32_t)int_handler_6);
  set_idt_entry(pidt, 7, seg, (uint32_t)int_handler_7);
  set_idt_entry(pidt, 8, seg, (uint32_t)int_handler_8);
  set_idt_entry(pidt, 9, seg, (uint32_t)int_handler_9);
  set_idt_entry(pidt, 10, seg, (uint32_t)int_handler_10);
  set_idt_entry(pidt, 11, seg, (uint32_t)int_handler_11);
  set_idt_entry(pidt, 12, seg, (uint32_t)int_handler_12);
  set_idt_entry(pidt, 13, seg, (uint32_t)int_handler_13);
  set_idt_entry(pidt, 14, seg, (uint32_t)int_handler_14);
  set_idt_entry(pidt, 15, seg, (uint32_t)int_handler_15);
  set_idt_entry(pidt, 16, seg, (uint32_t)int_handler_16);
  set_idt_entry(pidt, 17, seg, (uint32_t)int_handler_17);
  set_idt_entry(pidt, 18, seg, (uint32_t)int_handler_18);
  set_idt_entry(pidt, 19, seg, (uint32_t)int_handler_19);
  set_idt_entry(pidt, 20, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 21, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 22, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 23, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 24, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 25, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 26, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 27, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 28, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 29, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 30, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 31, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 32, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 33, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 34, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 35, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 36, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 37, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 38, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 39, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 40, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 41, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 42, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 43, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 44, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 45, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 46, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 47, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 48, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 49, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 50, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 51, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 52, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 53, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 54, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 55, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 56, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 57, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 58, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 59, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 60, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 61, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 62, seg, (uint32_t)int_handler_null);
  set_idt_entry(pidt, 63, seg, (uint32_t)int_handler_null);
}

void int_handler_0(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 0 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_1(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 1 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_2(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 2 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_3(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 3 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_4(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 4 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_5(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 5 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_6(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 6 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_7(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 7 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_8(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 8 speaking\n");
	asm volatile (
	"push %eax;"
	"mov %cr0,%eax;"
	"and $0x80000000,%eax;"
	"cmpl $0x80000000,%eax;"
	"je .pg;"
	"pop %eax;"
	"pop 0x27800c;"
	"movl $0xb,0x278010;"
	"add $0x4,%esp;"
	"push 0x278008;"
	"jmp .end;"
	".pg:"
	"pop %eax;"
	"pop 0x127800c;"
	"movl $0xb,0x1278010;"
	"add $0x4,%esp;"
	"push 0x1278008;"
	".end:"
	"iret;"
	"hlt;");
  return;
}
void int_handler_9(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 9 speaking\n");
	asm volatile (
	"push %eax;"
	"mov %cr0,%eax;"
	"and $0x80000000,%eax;"
	"cmpl $0x80000000,%eax;"
	"je .pg;"
	"pop %eax;"
	"pop 0x27800c;"
	"movl $0xb,0x278010;"
	"add $0x4,%esp;"
	"push 0x278008;"
	"jmp .end;"
	".pg:"
	"pop %eax;"
	"pop 0x127800c;"
	"movl $0xb,0x1278010;"
	"add $0x4,%esp;"
	"push 0x1278008;"
	".end:"
	"iret;"
	"hlt;");
  return;
}
void int_handler_10(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 10 speaking\n");
	asm volatile (
	"push %eax;"
	"mov %cr0,%eax;"
	"and $0x80000000,%eax;"
	"cmpl $0x80000000,%eax;"
	"je .pg;"
	"pop %eax;"
	"pop 0x27800c;"
	"movl $0xb,0x278010;"
	"add $0x4,%esp;"
	"push 0x278008;"
	"jmp .end;"
	".pg:"
	"pop %eax;"
	"pop 0x127800c;"
	"movl $0xb,0x1278010;"
	"add $0x4,%esp;"
	"push 0x1278008;"
	".end:"
	"iret;"
	"hlt;");
  return;
}
void int_handler_11(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 11 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_12(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 12 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_13(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 13 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_14(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 14 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_15(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 15 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_16(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 16 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_17(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 17 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_18(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 18 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_19(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
//  kprintf("interrupt handler 19 speaking\n");
    asm volatile (
    		"push %eax;"
    		"mov %cr0,%eax;"
    		"and $0x80000000,%eax;"
    		"cmpl $0x80000000,%eax;"
    		"je .pg;"
    		"pop %eax;"
    		"pop 0x27800c;"
    		"movl $0xb,0x278010;"
    		"add $0x4,%esp;"
    		"push 0x278008;"
    		"jmp .end;"
    		".pg:"
    		"pop %eax;"
    		"pop 0x127800c;"
    		"movl $0xb,0x1278010;"
    		"add $0x4,%esp;"
    		"push 0x1278008;"
    		".end:"
    		"iret;"
    		"hlt;");
  return;
}
void int_handler_20(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
  kprintf("interrupt handler 20 speaking\n");
  return;
}
void int_handler_21(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
  kprintf("interrupt handler 21 speaking\n");
  return;
}
void int_handler_22(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
  kprintf("interrupt handler 22 speaking\n");
  return;
}
void int_handler_23(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
  kprintf("interrupt handler 23 speaking\n");
  return;
}
void int_handler_24(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
  kprintf("interrupt handler 24 speaking\n");
  return;
}
void int_handler_25(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
  kprintf("interrupt handler 25 speaking\n");
  return;
}
void int_handler_26(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
  kprintf("interrupt handler 26 speaking\n");
  return;
}
void int_handler_27(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
  kprintf("interrupt handler 27 speaking\n");
  return;
}
void int_handler_28(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
  kprintf("interrupt handler 28 speaking\n");
  return;
}
void int_handler_29(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
  kprintf("interrupt handler 29 speaking\n");
  return;
}
void int_handler_30(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
  kprintf("interrupt handler 30 speaking\n");
  return;
}
void int_handler_31(uint32_t code, uint32_t eip, uint32_t cs, uint32_t eflags)
{
  kprintf("interrupt handler 31 speaking\n");
  return;
}