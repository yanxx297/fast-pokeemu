#! /bin/bash
while [ "$1" != "" ]; do
        case $1 in
                -l | --list )
                        for file in /lib/modules/4.4.0-45-generic/kernel/arch/x86/kvm/*-intel.ko; do 
                                basename $file -intel.ko
                        done
                        ;;                  
                * )
                        rmmod kvm-intel
                        rmmod kvm
                        insmod /lib/modules/4.4.0-45-generic/kernel/arch/x86/kvm/$1.ko
                        insmod /lib/modules/4.4.0-45-generic/kernel/arch/x86/kvm/$1-intel.ko
                        ;;
        esac
        shift
done


